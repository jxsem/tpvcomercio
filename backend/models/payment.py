from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.sale import Sale


class PaymentMethod(StrEnum):
    CASH = "CASH"
    CARD = "CARD"


_METHODS_SQL = ", ".join(f"'{m.value}'" for m in PaymentMethod)


class Payment(Base):
    __tablename__ = "payments"

    id: Mapped[int] = mapped_column(primary_key=True)
    # unique: una venta tiene un único pago en el MVP (sin pagos divididos).
    sale_id: Mapped[int] = mapped_column(
        ForeignKey("sales.id", ondelete="RESTRICT"), unique=True
    )
    method: Mapped[str] = mapped_column(String(10))
    amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    # Solo en efectivo: lo entregado por el cliente y el cambio devuelto.
    cash_received: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2)
    )
    change_given: Mapped[Decimal | None] = mapped_column(Numeric(precision=10, scale=2))
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    sale: Mapped[Sale] = relationship(back_populates="payment")

    __table_args__ = (
        CheckConstraint(f"method IN ({_METHODS_SQL})", name="check_payment_method"),
        CheckConstraint("amount >= 0", name="check_payment_amount_not_negative"),
        CheckConstraint(
            "(method = 'CASH' AND cash_received IS NOT NULL"
            " AND change_given IS NOT NULL"
            " AND cash_received >= amount"
            " AND change_given = cash_received - amount)"
            " OR (method = 'CARD' AND cash_received IS NULL AND change_given IS NULL)",
            name="check_payment_cash_fields",
        ),
    )
