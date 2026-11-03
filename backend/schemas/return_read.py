from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ReturnItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    sale_item_id: int
    product_id: int
    quantity: Decimal
    amount: Decimal
    restocked: bool


class ReturnRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    original_sale_id: int
    user_id: int
    method: str
    total: Decimal
    created_at: datetime
    items: list[ReturnItemRead]
