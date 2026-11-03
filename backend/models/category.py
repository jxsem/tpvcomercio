from typing import TYPE_CHECKING

from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import true

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.product import Product


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True)
    active: Mapped[bool] = mapped_column(server_default=true())

    products: Mapped[list[Product]] = relationship(back_populates="category")
