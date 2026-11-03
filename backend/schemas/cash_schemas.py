from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field


class CashOpen(BaseModel):
    model_config = ConfigDict(extra="forbid")

    opening_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class CashClose(BaseModel):
    model_config = ConfigDict(extra="forbid")

    closing_amount: Decimal = Field(ge=0, max_digits=10, decimal_places=2)


class CashSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    user_id: int
    status: str
    opened_at: datetime
    closed_at: datetime | None
    opening_amount: Decimal
    closing_amount: Decimal | None
    expected_amount: Decimal | None


class CashSessionDetail(CashSessionRead):
    # Esperado en vivo si está abierta (o el guardado si está cerrada).
    current_expected: Decimal
    # contado - esperado (None mientras está abierta). Negativo = falta dinero.
    difference: Decimal | None


class TopProduct(BaseModel):
    name: str
    units: int


class DailySummaryRead(BaseModel):
    date: date
    sales_count: int
    cash_sales: Decimal
    card_sales: Decimal
    sales_total: Decimal
    cash_refunds: Decimal
    card_refunds: Decimal
    refunds_total: Decimal
    net_total: Decimal
    expected_cash_movement: Decimal
    items_sold: int
    top_product: TopProduct | None
