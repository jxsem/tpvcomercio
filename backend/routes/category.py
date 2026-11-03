from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.database.errors import unique_violation_constraint
from backend.database.session import get_db
from backend.models.category import Category
from backend.schemas.category_create import CategoryCreate
from backend.schemas.category_read import CategoryRead
from backend.schemas.category_update import CategoryUpdate

router = APIRouter(prefix="/categories", tags=["categories"])

NAME_CONSTRAINT = "uq_categories_name_lower"
NAME_CONFLICT = "Ya existe una categoría con ese nombre"


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(
    data: CategoryCreate, db: Annotated[Session, Depends(get_db)]
) -> Category:
    # se declara `data` ya llega validado por Pydantic: si no cumple CategoryCreate,
    # FastAPI responde 422 y esta función no se ejecuta.
    # `db` viene de get_db y se cierra solo al terminar la petición.

    # Annotated[A, B] significa: "el tipo es A, y además lleva esta información extra B"

    # Session es el tipo. Sirve a tu editor para autocompletar y detectar errores.
    # Depends(get_db) es la metainformación. FastAPI la lee

    # data es una instancia de CategoryCreate
    # data.model_dump() la convierte en un dicionario {"name": "bebidas, "active: True"}
    # ** desempaqueta ese diccionario en argumentos con nombre.
    # Es lo mismo que Category(name="Bebidas", active=True)
    category = Category(**data.model_dump())

    # La sesión empieza a vigilar el objeto. No se envía nada a PostgreSQL.
    db.add(category)

    # Aquí ocurre el INSERT y se confirma la transacción. Puede fallar
    # (base de datos caída, nombre duplicado por el índice único).
    try:
        db.commit()
    except IntegrityError as exc:
        # Tras un fallo la sesión no se puede reutilizar hasta hacer rollback.
        db.rollback()
        # Solo el duplicado de nombre es culpa del cliente (409). Cualquier otra
        # IntegrityError es inesperada: sube como 500 sin enseñar al cliente
        # detalles internos de la base de datos.
        if unique_violation_constraint(exc) == NAME_CONSTRAINT:
            raise HTTPException(status.HTTP_409_CONFLICT, NAME_CONFLICT) from exc
        raise

    # Tras el commit el objeto queda caducado; refresh lo vuelve a leer para
    # tener el id y los valores finales (active viene de un server_default).
    db.refresh(category)

    # Se devuelve un objeto SQLAlchemy; response_model=CategoryRead lo convierte
    # (from_attributes) y filtra los campos que salen en la respuesta.
    return category


@router.get("", response_model=list[CategoryRead])
def list_categories(
    db: Annotated[Session, Depends(get_db)],
    active: bool | None = None,
    # Tope máximo: sin él, un listado grande podría saturar la API.
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Category]:
    stmt = select(Category).order_by(Category.name, Category.id)
    if active is not None:
        stmt = stmt.where(Category.active == active)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{category_id}", response_model=CategoryRead)
def get_category(category_id: int, db: Annotated[Session, Depends(get_db)]) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")
    return category


@router.patch("/{category_id}", response_model=CategoryRead)
def update_category(
    category_id: int,
    data: CategoryUpdate,
    db: Annotated[Session, Depends(get_db)],
) -> Category:
    category = db.get(Category, category_id)
    if category is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Categoría no encontrada")

    # exclude_unset: solo los campos que el cliente envió de verdad. Sin esto,
    # los omitidos llegarían como None y pisarían los valores guardados.
    for field, value in data.model_dump(exclude_unset=True).items():
        setattr(category, field, value)

    try:
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if unique_violation_constraint(exc) == NAME_CONSTRAINT:
            raise HTTPException(status.HTTP_409_CONFLICT, NAME_CONFLICT) from exc
        raise
    db.refresh(category)
    return category
