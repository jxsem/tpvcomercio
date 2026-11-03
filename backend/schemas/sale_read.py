from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict


class SaleItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    product_id: int
    product_name: str
    quantity: Decimal
    unit_price: Decimal
    tax_rate: Decimal
    subtotal: Decimal


class PaymentRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    method: str
    amount: Decimal
    cash_received: Decimal | None
    change_given: Decimal | None
    created_at: datetime


class SaleRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int | None
    total: Decimal
    status: str
    created_at: datetime
    items: list[SaleItemRead]
    payment: PaymentRead
