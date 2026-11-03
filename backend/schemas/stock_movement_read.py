from datetime import datetime

from pydantic import BaseModel, ConfigDict


class StockMovementRead(BaseModel):
    # user_id no se expone: es un dato interno y aún no hay usuarios.
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    type: str
    quantity: int
    reason: str | None
    reference_id: int | None
    created_at: datetime
