from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from backend.models.payment import PaymentMethod

# Tope de líneas por venta: sin él, una petición enorme bloquearía muchas filas
# de productos a la vez.
MAX_ITEMS = 100


class SaleItemCreate(BaseModel):
    # El cliente solo dice QUÉ producto y CUÁNTO. Precio, IVA y subtotal los
    # calcula el servidor; extra="forbid" rechaza un "price" o "total" enviado.
    model_config = ConfigDict(extra="forbid")

    product_id: int
    # En productos pesables es el peso en kg (hasta 3 decimales).
    quantity: Decimal = Field(gt=0, le=Decimal("9999.999"), decimal_places=3)


class PaymentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    method: PaymentMethod
    cash_received: Decimal | None = Field(
        default=None, ge=0, max_digits=10, decimal_places=2
    )

    @model_validator(mode="after")
    def check_cash_received(self) -> Self:
        if self.method == PaymentMethod.CASH and self.cash_received is None:
            raise ValueError("el pago en efectivo requiere cash_received")
        if self.method == PaymentMethod.CARD and self.cash_received is not None:
            raise ValueError("el pago con tarjeta no lleva cash_received")
        return self


class SaleCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    items: list[SaleItemCreate] = Field(min_length=1, max_length=MAX_ITEMS)
    payment: PaymentCreate
