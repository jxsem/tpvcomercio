from datetime import datetime
from decimal import Decimal
from enum import StrEnum

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Numeric,
    String,
    func,
    text,
)
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class CashSessionStatus(StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"


_STATUSES_SQL = ", ".join(f"'{s.value}'" for s in CashSessionStatus)


class CashSession(Base):
    __tablename__ = "cash_sessions"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    status: Mapped[str] = mapped_column(
        String(10), server_default=CashSessionStatus.OPEN.value
    )
    opened_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    closed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    opening_amount: Mapped[Decimal] = mapped_column(Numeric(precision=10, scale=2))
    # Efectivo contado por el empleado al cerrar.
    closing_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2)
    )
    # Efectivo que el sistema esperaba al cerrar (se guarda: queda auditable).
    expected_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(precision=10, scale=2)
    )

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUSES_SQL})", name="check_cash_status"),
        CheckConstraint("opening_amount >= 0", name="check_cash_opening_amount"),
        CheckConstraint("closing_amount >= 0", name="check_cash_closing_amount"),
        CheckConstraint(
            "(status = 'OPEN' AND closed_at IS NULL AND closing_amount IS NULL"
            " AND expected_amount IS NULL)"
            " OR (status = 'CLOSED' AND closed_at IS NOT NULL"
            " AND closing_amount IS NOT NULL AND expected_amount IS NOT NULL)",
            name="check_cash_open_closed_fields",
        ),
        # Solo puede haber UNA caja abierta: la base de datos lo garantiza aunque
        # dos peticiones intenten abrirla a la vez.
        Index(
            "uq_cash_sessions_single_open",
            "status",
            unique=True,
            postgresql_where=text("status = 'OPEN'"),
        ),
    )
