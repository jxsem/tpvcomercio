from datetime import datetime
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base
from backend.models.payment import _METHODS_SQL


class Return(Base):
    """Devolución: operación nueva que compensa una venta sin modificarla."""

    __tablename__ = "returns"

    id: Mapped[int] = mapped_column(primary_key=True)
    original_sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), index=True
    )
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    cash_session_id: Mapped[int | None] = mapped_column(
        ForeignKey("cash_sessions.id", ondelete="RESTRICT"), index=True
    )
    # Cómo se devuelve el dinero (afecta al efectivo esperado en caja).
    method: Mapped[str] = mapped_column(String(10))
    total: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    items: Mapped[list[ReturnItem]] = relationship(
        back_populates="return_", order_by="ReturnItem.id"
    )

    __table_args__ = (
        CheckConstraint(f"method IN ({_METHODS_SQL})", name="check_return_method"),
        CheckConstraint("total >= 0", name="check_return_total_not_negative"),
    )


class ReturnItem(Base):
    __tablename__ = "return_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    return_id: Mapped[int] = mapped_column(
        ForeignKey("returns.id", ondelete="RESTRICT"), index=True
    )
    sale_item_id: Mapped[int] = mapped_column(
        ForeignKey("sale_items.id", ondelete="RESTRICT"), index=True
    )
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    quantity: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=3))
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    # ¿Volvió el producto al stock? (no si está dañado, o si es pesable)
    restocked: Mapped[bool] = mapped_column()

    return_: Mapped[Return] = relationship(back_populates="items")

    __table_args__ = (
        CheckConstraint("quantity > 0", name="check_return_item_quantity_positive"),
        CheckConstraint("amount >= 0", name="check_return_item_amount_not_negative"),
    )
