from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql.expression import false, true

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.category import Category


class Product(Base):
    __tablename__ = "products"

    id: Mapped[int] = mapped_column(primary_key=True)
    ean: Mapped[str | None] = mapped_column(String(13), unique=True)
    name: Mapped[str] = mapped_column(String(50))
    category_id: Mapped[int] = mapped_column(
        ForeignKey("categories.id", ondelete="CASCADE")
    )
    price: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    tax_rate: Mapped[Decimal] = mapped_column(Numeric(precision=4, scale=2))
    stock: Mapped[int | None] = mapped_column()
    active: Mapped[bool] = mapped_column(server_default=true())
    is_weighted: Mapped[bool] = mapped_column(server_default=false())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    category: Mapped["Category"] = relationship(back_populates="products")

    __table_args__ = (
        CheckConstraint("price >= 0", name="check_product_price_positive"),
        CheckConstraint(
            "tax_rate >= 0 AND tax_rate <= 21", name="check_product_tax_rate_range"
        ),
        CheckConstraint("stock >= 0", name="check_product_stock_positive"),
        CheckConstraint("ean ~ '^[0-9]{13}$'", name="check_ean_13_digits"),
        CheckConstraint(
            "(NOT is_weighted) OR (stock IS NULL)", name="check_is_weighted_stock_null"
        ),
        CheckConstraint(
            "(NOT is_weighted) OR (ean IS NULL)", name="check_is_weighted_ean_null"
        ),
        CheckConstraint(
            "(is_weighted) OR (stock IS NOT NULL)",
            name="check_is_not_weighted_stock_not_null",
        ),
    )
