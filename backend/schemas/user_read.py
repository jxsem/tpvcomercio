from datetime import datetime

from pydantic import BaseModel, ConfigDict


class UserRead(BaseModel):
    # Sin password_hash: ni siquiera el hash debe salir de la API.
    model_config = ConfigDict(from_attributes=True)
    id: int
    username: str
    role: str
    active: bool
    created_at: datetime
    updated_at: datetime | None
