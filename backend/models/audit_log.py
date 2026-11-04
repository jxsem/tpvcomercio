from datetime import datetime
from enum import StrEnum
from typing import Any

from sqlalchemy import DateTime, ForeignKey, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from backend.database.base import Base


class AuditAction(StrEnum):
    PRODUCT_CREATED = "PRODUCT_CREATED"
    PRODUCT_UPDATED = "PRODUCT_UPDATED"
    PRODUCT_DEACTIVATED = "PRODUCT_DEACTIVATED"
    PRODUCT_ACTIVATED = "PRODUCT_ACTIVATED"
    SALE_CREATED = "SALE_CREATED"
    RETURN_CREATED = "RETURN_CREATED"
    STOCK_ADJUSTED = "STOCK_ADJUSTED"
    USER_CREATED = "USER_CREATED"
    USER_UPDATED = "USER_UPDATED"


class AuditLog(Base):
    """Quién hizo qué, sobre qué y cuándo. Solo se inserta: nunca se edita ni borra."""

    __tablename__ = "audit_logs"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int | None] = mapped_column(
        ForeignKey("users.id", ondelete="RESTRICT"), index=True
    )
    action: Mapped[str] = mapped_column(String(50))
    entity: Mapped[str] = mapped_column(String(50))
    entity_id: Mapped[int | None] = mapped_column()
    # "metadata" está reservado por SQLAlchemy como atributo de la clase
    # (Base.metadata), así que el atributo se llama details y la columna metadata.
    details: Mapped[dict[str, Any] | None] = mapped_column("metadata", JSONB)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )

    __table_args__ = (Index("ix_audit_logs_entity", "entity", "entity_id"),)
