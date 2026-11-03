from pydantic import BaseModel, ConfigDict, Field

from backend.models.user import UserRole
from backend.schemas.auth_schemas import MAX_PASSWORD_LENGTH


class UserCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    # Solo ASCII sencillo: evita nombres que se vean iguales y no lo sean.
    username: str = Field(pattern=r"^[A-Za-z0-9_.-]{3,50}$")
    password: str = Field(min_length=10, max_length=MAX_PASSWORD_LENGTH)
    role: UserRole = UserRole.EMPLOYEE
