from typing import TYPE_CHECKING

from sqlalchemy import Index, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import true

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.product import Product


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50))
    active: Mapped[bool] = mapped_column(server_default=true())

    products: Mapped[list[Product]] = relationship(back_populates="category")

    # Unicidad sin distinguir mayúsculas: "Bebidas" y "bebidas" compiten por
    # la misma entrada del índice. En la columna se guarda lo que escribió el usuario.
    __table_args__ = (Index("uq_categories_name_lower", func.lower(name), unique=True),)
