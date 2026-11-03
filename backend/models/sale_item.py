from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, ForeignKey, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.sale import Sale


class SaleItem(Base):
    """Línea de venta con copia del nombre y precio usados en ese momento.

    Cambiar después el precio del producto no altera las ventas históricas.
    En productos pesables, `quantity` es el peso en kg.
    """

    __tablename__ = "sale_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    product_name: Mapped[str] = mapped_column(String(50))
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=3))
    unit_price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(precision=4, scale=2))
    subtotal: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))

    sale: Mapped[Sale] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_sale_item_quantity_positive"),
        CheckConstraint("unit_price >= 0", name="check_sale_item_unit_price"),
        CheckConstraint("subtotal >= 0", name="check_sale_item_subtotal"),
    )
