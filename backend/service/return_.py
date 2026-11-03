from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.models.product import Product
from backend.models.sale import Sale, SaleStatus
from backend.models.sale_item import SaleItem
from backend.models.sale_return import Return, ReturnItem
from backend.models.stock_movement import StockMovement, StockMovementType
from backend.schemas.return_create import ReturnCreate
from backend.service.cash import lock_open_session_shared
from backend.service.sale import line_subtotal


class ReturnError(Exception):
    """Error de negocio al crear una devolución (la ruta lo traduce a HTTP)."""


class SaleNotFoundError(ReturnError):
    pass


class ReturnNotAllowedError(ReturnError):
    pass


class InvalidReturnItemError(ReturnError):
    def __init__(self, sale_item_id: int, reason: str) -> None:
        super().__init__(f"Línea {sale_item_id}: {reason}")


class ExceedsSoldQuantityError(ReturnError):
    def __init__(self, sale_item_id: int) -> None:
        super().__init__(
            f"Línea {sale_item_id}: se intenta devolver más de lo que queda"
        )


def create_return(db: Session, data: ReturnCreate, user_id: int) -> Return:
    """Crea la devolución, sus líneas y los movimientos de stock. No hace commit."""
    cash_session = lock_open_session_shared(db)
    sale = db.get(Sale, data.original_sale_id)
    if sale is None:
        raise SaleNotFoundError("Venta no encontrada")
    if sale.status != SaleStatus.COMPLETED:
        raise ReturnNotAllowedError("Solo se pueden devolver ventas completadas")

    # Bloquear las líneas de venta serializa devoluciones simultáneas de la
    # misma línea: sin esto, dos devoluciones concurrentes podrían devolver
    # cada una la cantidad completa.
    ids = sorted(item.sale_item_id for item in data.items)
    sale_items = {
        si.id: si
        for si in db.scalars(
            select(SaleItem)
            .where(SaleItem.id.in_(ids))
            .order_by(SaleItem.id)
            .with_for_update()
        )
    }
    # Ya devuelto por línea (cantidad e importe), contando devoluciones previas.
    already = {
        row.sale_item_id: (row.quantity, row.amount)
        for row in db.execute(
            select(
                ReturnItem.sale_item_id,
                func.sum(ReturnItem.quantity).label("quantity"),
                func.sum(ReturnItem.amount).label("amount"),
            )
            .where(ReturnItem.sale_item_id.in_(ids))
            .group_by(ReturnItem.sale_item_id)
        )
    }
    products = {
        p.id: p
        for p in db.scalars(
            select(Product)
            .where(Product.id.in_({si.product_id for si in sale_items.values()}))
            .order_by(Product.id)
            .with_for_update()
            .execution_options(populate_existing=True)
        )
    }

    ret = Return(
        original_sale_id=sale.id,
        user_id=user_id,
        cash_session_id=cash_session.id,
        method=data.method,
    )
    restock: dict[int, int] = {}
    for item in data.items:
        line = sale_items.get(item.sale_item_id)
        if line is None or line.sale_id != sale.id:
            raise InvalidReturnItemError(item.sale_item_id, "no pertenece a esa venta")
        product = products[line.product_id]
        if (
            not product.is_weighted
            and item.quantity != item.quantity.to_integral_value()
        ):
            raise InvalidReturnItemError(
                item.sale_item_id, "este producto solo se devuelve por unidades enteras"
            )

        done_qty, done_amount = already.get(line.id, (Decimal(0), Decimal("0.00")))
        remaining_qty = line.quantity - done_qty
        if item.quantity > remaining_qty:
            raise ExceedsSoldQuantityError(line.id)

        remaining_amount = line.subtotal - done_amount
        if item.quantity == remaining_qty:
            # Última devolución de la línea: se reembolsa exactamente lo que
            # queda: así el redondeo de las parciales no crea ni pierde céntimos.
            amount = remaining_amount
        else:
            amount = min(
                line_subtotal(item.quantity, line.unit_price), remaining_amount
            )

        reinstate = item.restock and not product.is_weighted
        ret.items.append(
            ReturnItem(
                sale_item_id=line.id,
                product_id=product.id,
                quantity=item.quantity,
                amount=amount,
                restocked=reinstate,
            )
        )
        if reinstate:
            restock[product.id] = restock.get(product.id, 0) + int(item.quantity)

    ret.total = sum((i.amount for i in ret.items), Decimal("0.00"))
    db.add(ret)
    db.flush()  # ret.id disponible para referenciarlo en los movimientos

    for product_id, quantity in restock.items():
        products[product_id].stock += quantity
        db.add(
            StockMovement(
                product_id=product_id,
                type=StockMovementType.RETURN,
                quantity=quantity,
                reference_id=ret.id,
                user_id=user_id,
            )
        )
    return ret
