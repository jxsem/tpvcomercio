from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.payment import PaymentMethod


class ReturnItemCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    sale_item_id: int
    quantity: Decimal = Field(gt=0, le=Decimal("9999.999"), decimal_places=3)
    # False si el producto vuelve dañado: se devuelve el dinero pero no entra a stock.
    restock: bool = True


class ReturnCreate(BaseModel):
    # El importe lo calcula el servidor a partir de la venta original.
    model_config = ConfigDict(extra="forbid")

    original_sale_id: int
    method: PaymentMethod
    items: list[ReturnItemCreate] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def check_unique_lines(self) -> Self:
        ids = [item.sale_item_id for item in self.items]
        if len(ids) != len(set(ids)):
            raise ValueError("una línea de venta solo puede aparecer una vez")
        return self
