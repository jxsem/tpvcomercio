from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import AUTHENTICATED
from backend.database.session import get_db
from backend.models.product import Product
from backend.models.stock_movement import StockMovement, StockMovementType
from backend.schemas.stock_movement_read import StockMovementRead
from backend.schemas.stock_read import StockRead

router = APIRouter(prefix="/stock", tags=["stock"])


@router.get("", dependencies=[AUTHENTICATED], response_model=list[StockRead])
def list_stock(
    db: Annotated[Session, Depends(get_db)],
    # Para detectar stock bajo: solo productos con stock <= este valor.
    max_stock: Annotated[int | None, Query(ge=0)] = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Product]:
    # Los pesables no controlan stock (NULL): no entran en este inventario.
    stmt = (
        select(Product)
        .where(Product.stock.is_not(None))
        .order_by(Product.name, Product.id)
    )
    if max_stock is not None:
        stmt = stmt.where(Product.stock <= max_stock)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


# IMPORTANTE: va antes que /{product_id}. FastAPI usa la primera ruta cuya forma
# coincide; "/stock/movements" también encaja con "/stock/{product_id}" y, al no
# ser un entero, devolvería 422 en lugar de llegar aquí.
@router.get(
    "/movements", dependencies=[AUTHENTICATED], response_model=list[StockMovementRead]
)
def list_movements(
    db: Annotated[Session, Depends(get_db)],
    product_id: int | None = None,
    # El tipo enum hace que ?type=FOO dé 422 sin llegar a la base de datos.
    type: StockMovementType | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[StockMovement]:
    # id como desempate: varios movimientos de una misma transacción comparten
    # created_at (now() es el instante de la transacción) y sin él el orden
    # entre ellos no estaría definido, así que la paginación podría repetir o
    # saltarse filas.
    stmt = select(StockMovement).order_by(
        StockMovement.created_at.desc(), StockMovement.id.desc()
    )
    if product_id is not None:
        stmt = stmt.where(StockMovement.product_id == product_id)
    if type is not None:
        stmt = stmt.where(StockMovement.type == type)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{product_id}", dependencies=[AUTHENTICATED], response_model=StockRead)
def get_stock(product_id: int, db: Annotated[Session, Depends(get_db)]) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product
