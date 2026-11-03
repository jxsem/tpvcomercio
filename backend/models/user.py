from datetime import datetime
from enum import StrEnum

from sqlalchemy import CheckConstraint, DateTime, Index, String, func
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql.expression import true

from backend.database.base import Base


class UserRole(StrEnum):
    ADMIN = "ADMIN"
    EMPLOYEE = "EMPLOYEE"


_ROLES_SQL = ", ".join(f"'{r.value}'" for r in UserRole)


class User(Base):
    """Empleado del negocio. Nunca se borra: ventas y auditoría lo referencian."""

    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    username: Mapped[str] = mapped_column(String(50))
    # Hash Argon2, nunca la contraseña. 255 sobra para el formato del hash.
    password_hash: Mapped[str] = mapped_column(String(255))
    role: Mapped[str] = mapped_column(String(20))
    active: Mapped[bool] = mapped_column(server_default=true())
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now()
    )
    updated_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), onupdate=func.now()
    )

    __table_args__ = (
        # "Ana" y "ana" no pueden ser dos usuarios distintos.
        Index("uq_users_username_lower", func.lower(username), unique=True),
        CheckConstraint(f"role IN ({_ROLES_SQL})", name="check_user_role"),
    )
