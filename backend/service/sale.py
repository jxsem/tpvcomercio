from collections import defaultdict
from decimal import ROUND_HALF_UP, Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.payment import Payment, PaymentMethod
from backend.models.product import Product
from backend.models.sale import Sale
from backend.models.sale_item import SaleItem
from backend.models.stock_movement import StockMovement, StockMovementType
from backend.schemas.sale_create import SaleCreate

CENT = Decimal("0.01")


class SaleError(Exception):
    """Error de negocio al crear una venta (la ruta lo traduce a HTTP)."""


class ProductNotAvailableError(SaleError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El producto {product_id} no existe o está inactivo")
        self.product_id = product_id


class InvalidQuantityError(SaleError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"El producto {product_id} solo se vende por unidades enteras")
        self.product_id = product_id


class InsufficientStockError(SaleError):
    def __init__(self, product_id: int) -> None:
        super().__init__(f"Stock insuficiente para el producto {product_id}")
        self.product_id = product_id


class InsufficientPaymentError(SaleError):
    def __init__(self) -> None:
        super().__init__("El efectivo entregado es menor que el total")


def line_subtotal(quantity: Decimal, unit_price: Decimal) -> Decimal:
    """cantidad × precio, redondeado a céntimos (mitad hacia arriba)."""
    return (quantity * unit_price).quantize(CENT, rounding=ROUND_HALF_UP)


def create_sale(db: Session, data: SaleCreate, user_id: int | None = None) -> Sale:
    """Crea venta, líneas, pago y movimientos de stock en una sola transacción.

    No hace commit: quien llama decide cuándo confirmar o deshacer, de modo que
    o se guarda todo (venta + pago + stock) o no se guarda nada.
    """
    # Se bloquean las filas de los productos hasta el final de la transacción:
    # dos ventas simultáneas del mismo producto se ejecutan una detrás de otra y
    # la segunda ve el stock ya descontado. El orden por id evita deadlocks
    # cuando dos ventas bloquean varios productos a la vez.
    product_ids = sorted({item.product_id for item in data.items})
    locked = db.scalars(
        select(Product)
        .where(Product.id.in_(product_ids))
        .order_by(Product.id)
        .with_for_update()
        # Si el producto ya estaba cargado en la sesión, se relee: el stock
        # que se comprueba tiene que ser el actual, no uno antiguo.
        .execution_options(populate_existing=True)
    )
    products = {product.id: product for product in locked}

    needed: dict[int, int] = defaultdict(int)
    for item in data.items:
        product = products.get(item.product_id)
        if product is None or not product.active:
            raise ProductNotAvailableError(item.product_id)
        if not product.is_weighted:
            if item.quantity != item.quantity.to_integral_value():
                raise InvalidQuantityError(product.id)
            needed[product.id] += int(item.quantity)

    # El mismo producto puede aparecer en varias líneas: se suma antes de comprobar.
    for product_id, quantity in needed.items():
        stock = products[product_id].stock
        if stock is None or stock < quantity:
            raise InsufficientStockError(product_id)

    # Los importes salen siempre de los precios guardados, nunca del cliente.
    sale = Sale(user_id=user_id, total=Decimal("0.00"))
    for item in data.items:
        product = products[item.product_id]
        sale.items.append(
            SaleItem(
                product_id=product.id,
                product_name=product.name,
                quantity=item.quantity,
                unit_price=product.price,
                tax_rate=product.tax_rate,
                subtotal=line_subtotal(item.quantity, product.price),
            )
        )
    sale.total = sum((line.subtotal for line in sale.items), Decimal("0.00"))

    cash_received = data.payment.cash_received
    change_given = None
    if data.payment.method == PaymentMethod.CASH:
        if cash_received < sale.total:
            raise InsufficientPaymentError
        change_given = cash_received - sale.total
    sale.payment = Payment(
        method=data.payment.method,
        amount=sale.total,
        cash_received=cash_received,
        change_given=change_given,
    )

    db.add(sale)
    # flush: así sale.id existe para referenciarlo en los movimientos de stock.
    db.flush()

    for product_id, quantity in needed.items():
        products[product_id].stock -= quantity
        db.add(
            StockMovement(
                product_id=product_id,
                type=StockMovementType.SALE,
                quantity=-quantity,
                reference_id=sale.id,
                user_id=user_id,
            )
        )
    return sale
