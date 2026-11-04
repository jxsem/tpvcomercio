from enum import StrEnum
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class AdjustmentType(StrEnum):
    """Solo los tipos que un administrador puede registrar a mano.

    INITIAL, SALE y RETURN los crean sus propios flujos: permitirlos aquí
    dejaría falsificar el historial de ventas o devoluciones.
    """

    PURCHASE = "PURCHASE"
    LOSS = "LOSS"
    ADJUSTMENT = "ADJUSTMENT"


class StockAdjustmentCreate(BaseModel):
    model_config = ConfigDict(extra="forbid")

    product_id: int
    type: AdjustmentType
    # PURCHASE y LOSS: siempre positiva (el signo lo decide el tipo).
    # ADJUSTMENT: con signo, porque corrige tanto por exceso como por defecto.
    quantity: int = Field(ge=-1_000_000, le=1_000_000)
    # Obligatorio: "nunca modificar el stock sin registrar el motivo".
    reason: str = Field(min_length=3, max_length=255)

    @model_validator(mode="after")
    def check_quantity_sign(self) -> Self:
        if self.quantity == 0:
            raise ValueError("la cantidad no puede ser 0")
        if self.type != AdjustmentType.ADJUSTMENT and self.quantity < 0:
            raise ValueError(
                f"con {self.type.value} la cantidad es positiva "
                "(el signo lo decide el tipo)"
            )
        return self

    @property
    def delta(self) -> int:
        """Variación real del stock (con signo)."""
        if self.type == AdjustmentType.LOSS:
            return -self.quantity
        return self.quantity
