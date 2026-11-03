from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.database.session import get_db
from backend.models.sale import Sale, SaleStatus
from backend.schemas.sale_create import SaleCreate
from backend.schemas.sale_read import SaleRead
from backend.service.sale import (
    InsufficientPaymentError,
    InsufficientStockError,
    InvalidQuantityError,
    ProductNotAvailableError,
    create_sale,
)

router = APIRouter(prefix="/sales", tags=["sales"])


def load_options():
    # Carga líneas y pago en consultas aparte (no una por venta): evita el
    # problema N+1 al serializar un listado.
    return (selectinload(Sale.items), selectinload(Sale.payment))


@router.post("", response_model=SaleRead, status_code=status.HTTP_201_CREATED)
def create_sale_route(
    data: SaleCreate, db: Annotated[Session, Depends(get_db)]
) -> Sale:
    try:
        sale = create_sale(db, data)
        # Venta, líneas, pago y stock se confirman juntos.
        db.commit()
    except (
        ProductNotAvailableError,
        InvalidQuantityError,
        InsufficientPaymentError,
    ) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except InsufficientStockError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except Exception:
        # Cualquier fallo inesperado deja la base de datos como estaba.
        db.rollback()
        raise
    db.refresh(sale)
    return sale


@router.get("", response_model=list[SaleRead])
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


@router.get("/{sale_id}", response_model=SaleRead)
def get_sale(sale_id: int, db: Annotated[Session, Depends(get_db)]) -> Sale:
    sale = db.scalar(select(Sale).options(*load_options()).where(Sale.id == sale_id))
    if sale is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Venta no encontrada")
    return sale
