from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.product import Product
from backend.models.stock_movement import StockMovement
from backend.schemas.stock_adjustment_create import StockAdjustmentCreate


class StockError(Exception):
    """Error de negocio al ajustar stock (la ruta lo traduce a HTTP)."""


class ProductNotFoundError(StockError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El producto {product_id} no existe")


class WeightedProductError(StockError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El producto {product_id} es pesable y no controla stock")


class NegativeStockError(StockError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El ajuste dejaría el stock del producto {product_id} < 0")


def adjust_stock(
    db: Session, data: StockAdjustmentCreate, user_id: int
) -> StockMovement:
    """Cambia el stock y registra el movimiento en la misma transacción.

    No hace commit: quien llama decide (así se puede auditar en la misma transacción).
    """
    # Bloqueo de fila: una venta simultánea del mismo producto espera a que
    # termine el ajuste (y al revés), así nadie calcula con un stock antiguo.
    product = db.scalar(
        select(Product)
        .where(Product.id == data.product_id)
        .with_for_update()
        .execution_options(populate_existing=True)
    )
    if product is None:
        raise ProductNotFoundError(data.product_id)
    if product.is_weighted or product.stock is None:
        raise WeightedProductError(product.id)

    new_stock = product.stock + data.delta
    if new_stock < 0:
        raise NegativeStockError(product.id)

    product.stock = new_stock
    movement = StockMovement(
        product_id=product.id,
        type=data.type,
        quantity=data.delta,
        reason=data.reason,
        user_id=user_id,
    )
    db.add(movement)
    db.flush()
    return movement
