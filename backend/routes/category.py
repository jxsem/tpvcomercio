from typing import Annotated

from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.category import Category
from backend.schemas.category_create import CategoryCreate
from backend.schemas.category_read import CategoryRead

router = APIRouter(prefix="/categories", tags=["categories"])


@router.post("", response_model=CategoryRead, status_code=status.HTTP_201_CREATED)
def create_category(data: CategoryCreate, db: Annotated[Session, Depends(get_db)]) -> Category:
    # se declara `data` ya llega validado por Pydantic: si no cumple CategoryCreate,
    # FastAPI responde 422 y esta función no se ejecuta.
    # `db` viene de get_db y se cierra solo al terminar la petición.

    #Annotated[A, B] significa: "el tipo es A, y además lleva esta información extra B".

    # Session es el tipo. Sirve a tu editor para autocompletar y detectar errores.
    # Depends(get_db) es la metainformación. FastAPI la lee

    # data es una instancia de CategoryCreate
    # data.model_dump() la convierte en un dicionario {"name": "bebidas, "active: True"}
    # ** desempaqueta ese diccionario en argumentos con nombre.
    # Es lo mismo que Category(name="Bebidas", active=True)
    category = Category(**data.model_dump())

    # La sesión empieza a vigilar el objeto. No se envía nada a PostgreSQL.
    db.add(category)

    # Aquí ocurre el INSERT y se confirma la transacción. Puede fallar
    # (base de datos caída, nombre duplicado por el unique).
    db.commit()

    # Tras el commit el objeto queda caducado; refresh lo vuelve a leer para
    # tener el id y los valores finales (active viene de un server_default).
    db.refresh(category)

    # Se devuelve un objeto SQLAlchemy; response_model=CategoryRead lo convierte
    # (from_attributes) y filtra los campos que salen en la respuesta.
    return category
