from datetime import date, datetime, time, timedelta
from decimal import Decimal
from zoneinfo import ZoneInfo

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.cash_session import CashSession, CashSessionStatus
from backend.models.payment import Payment, PaymentMethod
from backend.models.product import Product
from backend.models.sale import Sale, SaleStatus
from backend.models.sale_item import SaleItem
from backend.models.sale_return import Return

# Hora local del negocio: "el día" se corta a medianoche de Madrid, no de UTC.
BUSINESS_TZ = ZoneInfo("Europe/Madrid")
ZERO = Decimal("0.00")


class CashError(Exception):
    """Error de negocio relacionado con la caja (la ruta lo traduce a HTTP)."""


class NoOpenCashSessionError(CashError):
    def __init__(self) -> None:
        super().__init__("No hay caja abierta")


class CashSessionAlreadyOpenError(CashError):
    def __init__(self) -> None:
        super().__init__("Ya hay una caja abierta")


def lock_open_session_shared(db: Session) -> CashSession:
    """Caja abierta, con bloqueo compartido hasta el final de la transacción.

    Varias ventas pueden compartirla a la vez, pero el cierre de caja (que la
    bloquea en exclusiva) espera a que terminen: ninguna venta se cuela en una
    caja ya cerrada.
    """
    session = db.scalar(
        select(CashSession)
        .where(CashSession.status == CashSessionStatus.OPEN)
        .with_for_update(read=True)
    )
    if session is None:
        raise NoOpenCashSessionError
    return session


def expected_cash(db: Session, session: CashSession) -> Decimal:
    """Efectivo que debería haber en caja: apertura + ventas - devoluciones en efectivo.

    Del cobro en efectivo solo queda en la caja el importe de la venta: el cambio
    que se devuelve al cliente ya sale de lo que entregó.
    """
    cash_sales = db.scalar(
        select(func.coalesce(func.sum(Payment.amount), 0))
        .join(Sale, Sale.id == Payment.sale_id)
        .where(
            Sale.cash_session_id == session.id,
            Sale.status == SaleStatus.COMPLETED,
            Payment.method == PaymentMethod.CASH,
        )
    )
    cash_refunds = db.scalar(
        select(func.coalesce(func.sum(Return.total), 0)).where(
            Return.cash_session_id == session.id, Return.method == PaymentMethod.CASH
        )
    )
    return session.opening_amount + cash_sales - cash_refunds


def open_session(db: Session, user_id: int, opening_amount: Decimal) -> CashSession:
    already = db.scalar(
        select(CashSession.id).where(CashSession.status == CashSessionStatus.OPEN)
    )
    if already is not None:
        raise CashSessionAlreadyOpenError
    session = CashSession(user_id=user_id, opening_amount=opening_amount)
    db.add(session)
    return session


def close_session(db: Session, closing_amount: Decimal) -> CashSession:
    # Bloqueo exclusivo: espera a las ventas en curso y bloquea las nuevas.
    session = db.scalar(
        select(CashSession)
        .where(CashSession.status == CashSessionStatus.OPEN)
        .with_for_update()
    )
    if session is None:
        raise NoOpenCashSessionError
    session.expected_amount = expected_cash(db, session)
    session.closing_amount = closing_amount
    session.closed_at = func.now()
    session.status = CashSessionStatus.CLOSED
    return session


def day_bounds(day: date) -> tuple[datetime, datetime]:
    """[inicio, fin) del día local; el fin es medianoche del día siguiente."""
    start = datetime.combine(day, time.min, tzinfo=BUSINESS_TZ)
    end = datetime.combine(day + timedelta(days=1), time.min, tzinfo=BUSINESS_TZ)
    return start, end


def daily_summary(db: Session, day: date) -> dict:
    start, end = day_bounds(day)
    sale_in_day = (
        Sale.created_at >= start,
        Sale.created_at < end,
        Sale.status == SaleStatus.COMPLETED,
    )

    sales_count = db.scalar(select(func.count(Sale.id)).where(*sale_in_day))
    by_method = dict(
        db.execute(
            select(Payment.method, func.sum(Payment.amount))
            .join(Sale, Sale.id == Payment.sale_id)
            .where(*sale_in_day)
            .group_by(Payment.method)
        ).all()
    )
    refunds_by_method = dict(
        db.execute(
            select(Return.method, func.sum(Return.total))
            .where(Return.created_at >= start, Return.created_at < end)
            .group_by(Return.method)
        ).all()
    )

    # Solo productos con unidades (los pesables se miden en kg, no se suman).
    units = func.sum(SaleItem.quantity)
    per_product = (
        select(Product.name, units.label("units"))
        .join(Sale, Sale.id == SaleItem.sale_id)
        .join(Product, Product.id == SaleItem.product_id)
        .where(*sale_in_day, Product.is_weighted.is_(False))
        .group_by(Product.id, Product.name)
    )
    top = db.execute(per_product.order_by(units.desc(), Product.name).limit(1)).first()
    items_sold = db.scalar(
        select(func.coalesce(func.sum(per_product.subquery().c.units), 0))
    )

    cash_sales = by_method.get(PaymentMethod.CASH, ZERO)
    card_sales = by_method.get(PaymentMethod.CARD, ZERO)
    cash_refunds = refunds_by_method.get(PaymentMethod.CASH, ZERO)
    card_refunds = refunds_by_method.get(PaymentMethod.CARD, ZERO)
    return {
        "date": day,
        "sales_count": sales_count,
        "cash_sales": cash_sales,
        "card_sales": card_sales,
        "sales_total": cash_sales + card_sales,
        "cash_refunds": cash_refunds,
        "card_refunds": card_refunds,
        "refunds_total": cash_refunds + card_refunds,
        "net_total": cash_sales + card_sales - cash_refunds - card_refunds,
        "expected_cash_movement": cash_sales - cash_refunds,
        "items_sold": int(items_sold),
        "top_product": (
            {"name": top.name, "units": int(top.units)} if top is not None else None
        ),
    }
