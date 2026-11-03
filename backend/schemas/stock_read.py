from pydantic import BaseModel, ConfigDict


class StockRead(BaseModel):
    """Stock actual de un producto (None en los pesables, que no controlan stock)."""

    model_config = ConfigDict(from_attributes=True)
    id: int
    name: str
    stock: int | None
    is_weighted: bool
