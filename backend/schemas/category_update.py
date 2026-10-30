from pydantic import BaseModel, ConfigDict, Field, field_validator


class CategoryUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str | None = Field(min_length=1, max_length=50, default=None)
    active: bool | None = Field(default=None)

    # Los validadores no se ejecutan si el campo se omite (los defaults no se
    # validan), así que esto solo salta cuando el cliente envía null explícito.
    @field_validator("name", "active")
    @classmethod
    def reject_explicit_null(cls, value: object) -> object:
        if value is None:
            raise ValueError("no puede ser null; omite el campo para no modificarlo")
        return value
