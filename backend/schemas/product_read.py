from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class ProductRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    ean: str | None
    name: str
    category_id: int
    price: Decimal
    tax_rate: Decimal
    stock: int | None
    active: bool
    is_weighted: bool
    created_at: datetime
    updated_at: datetime | None
