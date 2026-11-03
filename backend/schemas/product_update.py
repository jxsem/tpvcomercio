from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ProductUpdate(BaseModel):
    # extra="forbid": stock, is_weighted y active no se cambian por aquí. El stock
    # solo se mueve con movimientos y active tiene sus propios endpoints.
    model_config = ConfigDict(str_strip_whitespace=True, extra="forbid")

    ean: str | None = Field(default=None, pattern=r"^[0-9]{13}$")
    name: str | None = Field(default=None, min_length=1, max_length=50)
    category_id: int | None = None
    price: Decimal | None = Field(default=None, ge=0, max_digits=10, decimal_places=2)
    tax_rate: Decimal | None = Field(
        default=None, ge=0, le=21, max_digits=4, decimal_places=2
    )

    # Mismo criterio que CategoryUpdate: omitir el campo = no modificarlo; un
    # null explícito se rechaza porque ninguna de estas columnas se puede vaciar.
    @field_validator("ean", "name", "category_id", "price", "tax_rate")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("no puede ser null; omite el campo para no modificarlo")
        return value
