from typing import Annotated, NoReturn

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy import or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import ADMIN_ONLY, AUTHENTICATED
from backend.database.errors import unique_violation_constraint
from backend.database.session import get_db
from backend.models.category import Category
from backend.models.product import Product
from backend.models.stock_movement import StockMovement, StockMovementType
from backend.schemas.product_create import ProductCreate
from backend.schemas.product_read import ProductRead
from backend.schemas.product_update import ProductUpdate

router = APIRouter(prefix="/products", tags=["products"])

EAN_CONSTRAINT = "uq_products_ean"
EAN_CONFLICT = "Ya existe un producto con ese EAN"


def get_product_or_404(db: Session, product_id: int) -> Product:
    product = db.get(Product, product_id)
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product


def require_active_category(db: Session, category_id: int) -> None:
    category = db.get(Category, category_id)
    if category is None or not category.active:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT,
            "La categoría no existe o está inactiva",
        )


def raise_for_integrity_error(db: Session, exc: IntegrityError) -> NoReturn:
    """Deshace la transacción y traduce el EAN duplicado a 409.

    Cualquier otra IntegrityError es inesperada y se relanza (500), sin enseñar
    detalles internos de la base de datos al cliente.
    """
    db.rollback()
    if unique_violation_constraint(exc) == EAN_CONSTRAINT:
        raise HTTPException(status.HTTP_409_CONFLICT, EAN_CONFLICT) from exc
    raise exc


def escape_like(text: str) -> str:
    """Escapa % y _ para que se busquen como texto literal en un LIKE."""
    return text.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


@router.post(
    "",
    dependencies=[ADMIN_ONLY],
    response_model=ProductRead,
    status_code=status.HTTP_201_CREATED,
)
def create_product(
    data: ProductCreate, db: Annotated[Session, Depends(get_db)]
) -> Product:
    require_active_category(db, data.category_id)

    # Los pesables no controlan stock (NULL); el resto empieza en initial_stock.
    stock = None if data.is_weighted else data.initial_stock
    product = Product(**data.model_dump(exclude={"initial_stock"}), stock=stock)
    db.add(product)

    try:
        # flush envía el INSERT sin confirmar la transacción: así product.id ya
        # existe para el movimiento, pero todo sigue pudiéndose deshacer.
        db.flush()
        if stock:
            db.add(
                StockMovement(
                    product_id=product.id,
                    type=StockMovementType.INITIAL,
                    quantity=stock,
                    reason="Stock inicial",
                )
            )
        # Producto y movimiento se confirman juntos o no se confirma ninguno.
        db.commit()
    except IntegrityError as exc:
        raise_for_integrity_error(db, exc)

    db.refresh(product)
    return product


@router.get("", dependencies=[AUTHENTICATED], response_model=list[ProductRead])
def list_products(
    db: Annotated[Session, Depends(get_db)],
    q: Annotated[str | None, Query(min_length=1, max_length=50)] = None,
    category_id: int | None = None,
    active: bool | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Product]:
    stmt = select(Product).order_by(Product.name, Product.id)
    if q is not None:
        # Nombre: contiene el texto. EAN: coincidencia exacta (usa su índice único).
        stmt = stmt.where(
            or_(
                Product.name.ilike(f"%{escape_like(q)}%", escape="\\"),
                Product.ean == q,
            )
        )
    if category_id is not None:
        stmt = stmt.where(Product.category_id == category_id)
    if active is not None:
        stmt = stmt.where(Product.active == active)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


# Esta ruta no choca con /{product_id}: "ean/123" tiene una barra de más.
@router.get("/ean/{ean}", dependencies=[AUTHENTICATED], response_model=ProductRead)
def get_product_by_ean(
    ean: Annotated[str, Path(pattern=r"^[0-9]{13}$")],
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = db.scalar(select(Product).where(Product.ean == ean))
    if product is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Producto no encontrado")
    return product


@router.get("/{product_id}", dependencies=[AUTHENTICATED], response_model=ProductRead)
def get_product(product_id: int, db: Annotated[Session, Depends(get_db)]) -> Product:
    return get_product_or_404(db, product_id)


@router.patch("/{product_id}", dependencies=[ADMIN_ONLY], response_model=ProductRead)
def update_product(
    product_id: int,
    data: ProductUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Product:
    product = get_product_or_404(db, product_id)
    changes = data.model_dump(exclude_unset=True)

    if "category_id" in changes:
        require_active_category(db, changes["category_id"])
    if "ean" in changes and product.is_weighted:
        raise HTTPException(
            status.HTTP_422_UNPROCESSABLE_CONTENT, "Un producto pesable no lleva EAN"
        )

    for field, value in changes.items():
        setattr(product, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        raise_for_integrity_error(db, exc)

    db.refresh(product)
    return product


@router.post(
    "/{product_id}/deactivate", dependencies=[ADMIN_ONLY], response_model=ProductRead
)
def deactivate_product(
    product_id: int, db: Annotated[Session, Depends(get_db)]
) -> Product:
    # Nunca se borra un producto: puede estar en ventas históricas.
    product = get_product_or_404(db, product_id)
    product.active = False
    db.commit()
    db.refresh(product)
    return product


@router.post(
    "/{product_id}/activate", dependencies=[ADMIN_ONLY], response_model=ProductRead
)
def activate_product(
    product_id: int, db: Annotated[Session, Depends(get_db)]
) -> Product:
    product = get_product_or_404(db, product_id)
    product.active = True
    db.commit()
    db.refresh(product)
    return product
