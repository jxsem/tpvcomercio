from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, String, func
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class StockMovementType(StrEnum):
    INITIAL = "INITIAL"
    PURCHASE = "PURCHASE"
    SALE = "SALE"
    RETURN = "RETURN"
    LOSS = "LOSS"
    ADJUSTMENT = "ADJUSTMENT"


_TYPES_SQL = ", ".join(f"'{t.value}'" for t in StockMovementType)


class StockMovement(Base):
    """Registro inmutable de cada cambio de stock (cantidad con signo)."""

    __tablename__ = "stock_movements"

    id: Mapped[int] = mapped_column(primary_key=True)
    product_id: Mapped[int] = mapped_column(
        ForeignKey("products.id", ondelete="RESTRICT"), index=True
    )
    type: Mapped[str] = mapped_column(String(20))
    quantity: Mapped[int] = mapped_column()
    reason: Mapped[str | None] = mapped_column(String(255))
    reference_id: Mapped[int | None] = mapped_column()
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (
        CheckConstraint("quantity <> 0", name="check_stock_movement_quantity_not_zero"),
        CheckConstraint(f"type IN ({_TYPES_SQL})", name="check_stock_movement_type"),
    )
