from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from typing import TYPE_CHECKING

from sqlalchemy import CheckConstraint, DateTime, Numeric, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.database.base import Base

if TYPE_CHECKING:
    from backend.models.payment import Payment
    from backend.models.sale_item import SaleItem


class SaleStatus(StrEnum):
    COMPLETED = "COMPLETED"
    CANCELLED = "CANCELLED"


_STATUSES_SQL = ", ".join(f"'{s.value}'" for s in SaleStatus)


class Sale(Base):
    """Venta registrada. Nunca se borra ni se modifica: se corrige con operaciones."""

    __tablename__ = "sales"

    id: Mapped[int] = mapped_column(primary_key=True)
    # Sin FK todavía: la tabla users llega con la fase de autenticación.
    user_id: Mapped[int | None] = mapped_column()
    total: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    status: Mapped[str] = mapped_column(
        String(20), server_default=SaleStatus.COMPLETED.value
    )
    # Índice: el historial y el resumen diario filtran y ordenan por fecha.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), index=True
    )

    items: Mapped[list[SaleItem]] = relationship(
        back_populates="sale", order_by="SaleItem.id"
    )
    payment: Mapped[Payment] = relationship(back_populates="sale", uselist=False)

    __table_args__ = (
        CheckConstraint("total >= 0", name="check_sale_total_not_negative"),
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="check_sale_status"),
    )
