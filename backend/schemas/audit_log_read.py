from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class AuditLogRead(BaseModel):
    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
    id: int
    user_id: int | None
    action: str
    entity: str
    entity_id: int | None
    # En el modelo el atributo es `details`; la API lo expone como `metadata`.
    metadata: dict[str, Any] | None = Field(validation_alias="details")
    created_at: datetime
