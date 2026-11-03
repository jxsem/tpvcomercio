from decimal import Decimal
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ProductCreate(BaseModel):
    # extra="forbid": un campo desconocido (p. ej. "stock") da 422 en vez de
    # ignorarse en silencio.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    # [0-9] y no \d: \d también acepta dígitos Unicode que el CHECK de la base
    # de datos rechazaría (y acabaría en un 500).
    ean: str | None = Field(default=None, pattern=r"^[0-9]{13}$")
    name: str = Field(min_length=1, max_length=50)
    category_id: int
    price: Decimal = Field(ge=0, max_digits=10, decimal_places=2)
    tax_rate: Decimal = Field(ge=0, le=21, max_digits=4, decimal_places=2)
    is_weighted: bool = False
    initial_stock: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def check_weighted_rules(self) -> Self:
        # Reglas equivalentes a los CHECK de la tabla products: se validan aquí
        # para devolver un 422 claro en lugar de un error de base de datos.
        if self.is_weighted:
            if self.ean is not None:
                raise ValueError("un producto pesable no lleva EAN")
            if self.initial_stock != 0:
                raise ValueError("un producto pesable no controla stock")
        return self
