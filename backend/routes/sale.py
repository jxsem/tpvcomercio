import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.auth import ADMIN_ONLY, AUTHENTICATED, CurrentUser
from backend.database.session import get_db
from backend.models.audit_log import AuditAction
from backend.models.sale import Sale, SaleStatus
from backend.schemas.sale_create import SaleCreate
from backend.schemas.sale_read import SaleRead
from backend.service.audit import log_action
from backend.service.cash import CashError
from backend.service.sale import (
    InsufficientPaymentError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotAvailableError,
    create_sale,
)

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sales", tags=["sales"])


def load_options():
    # Carga líneas y pago en consultas aparte (no una por venta): evita el
    # problema N+1 al serializar un listado.
    return (selectinload(Sale.items), selectinload(Sale.payment))


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale_route(
    data: SaleCreate, db: Annotated[Session, Depends(get_db)], user: CurrentUser
) -> Sale:
    try:
        sale = create_sale(db, data, user_id=user.id)
        log_action(
            db,
            user.id,
            AuditAction.SALE_CREATED,
            "sale",
            sale.id,
            {"total": str(sale.total), "method": sale.payment.method},
        )
        # Venta, líneas, pago, stock y auditoría se confirman juntos.
        db.commit()
    except (
        ProductNotAvailableError,
        InvalidQuantityError,
        InsufficientPaymentError,
    ) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except (InsufficientStockError, CashError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except Exception:
        logger.exception("Sale creation failed user_id=%s", user.id)
        # Cualquier fallo inesperado deja la base de datos como estaba.
        db.rollback()
        raise
    db.refresh(sale)
    return sale


@router.get("", dependencies=[ADMIN_ONLY], response_model=list[SaleRead])
def list_sales(
    db: Annotated[Session, Depends(get_db)],
    sale_status: Annotated[SaleStatus | None, Query(alias="status")] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Sale]:
    stmt = (
        select(Sale)
        .options(*load_options())
        .order_by(Sale.created_at.desc(), Sale.id.desc())
    )
    if sale_status is not None:
        stmt = stmt.where(Sale.status == sale_status)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{sale_id}", dependencies=[AUTHENTICATED], response_model=SaleRead)
def get_sale(sale_id: int, db: Annotated[Session, Depends(get_db)]) -> Sale:
    sale = db.scalar(select(Sale).options(*load_options()).where(Sale.id == sale_id))
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return sale
