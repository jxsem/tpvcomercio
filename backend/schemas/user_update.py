from pydantic import BaseModel, ConfigDict, Field, field_validator

from backend.models.user import UserRole
from backend.schemas.auth_schemas import MAX_PASSWORD_LENGTH


class UserUpdate(BaseModel):
    # El username no se cambia: ventas y auditoría lo referencian por id y
    # cambiarlo confundiría los registros.
    model_config = ConfigDict(extra="forbid")

    role: UserRole | None = None
    active: bool | None = None
    password: str | None = Field(
        default=None, min_length=10, max_length=MAX_PASSWORD_LENGTH
    )

    @field_validator("role", "active", "password")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("no puede ser null; omite el campo para no modificarlo")
        return value
