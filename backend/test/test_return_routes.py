from concurrent.futures import ThreadPoolExecutor
from decimal import Decimal
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.main import app
from backend.models.sale import Sale, SaleStatus
from backend.models.stock_movement import StockMovement, StockMovementType

# Muchos hilos a la vez: con solo dos, la ventana de la carrera es tan pequeña que
# sin el bloqueo el test a veces pasaba igual.
WORKERS = 6


def make_product(client: TestClient, category: dict, **overrides: object) -> dict:
    payload = {
        "ean": "8410000000001",
        "name": "Coca-Cola",
        "category_id": category["id"],
        "price": "1.20",
        "tax_rate": "21.00",
        "initial_stock": 10,
    }
    response = client.post("/products", json={**payload, **overrides})
    assert response.status_code == 201, response.text
    return response.json()


def sell(client: TestClient, product: dict, quantity: object) -> dict:
    body = {
        "items": [{"product_id": product["id"], "quantity": str(quantity)}],
        "payment": {"method": "CARD"},
    }
    response = client.post("/sales", json=body)
    assert response.status_code == 201, response.text
    return response.json()


def give_back(client, sale: dict, quantity: object, **extra: object):
    body = {
        "original_sale_id": sale["id"],
        "method": "CASH",
        "items": [
            {"sale_item_id": sale["items"][0]["id"], "quantity": str(quantity), **extra}
        ],
    }
    return client.post("/returns", json=body)


def stock_of(client: TestClient, product: dict) -> int | None:
    return client.get(f"/products/{product['id']}").json()["stock"]


@pytest.fixture
def sold(client: TestClient, category: dict) -> tuple[dict, dict]:
    """Producto con stock 10 y una venta de 4 unidades (stock 6)."""
    product = make_product(client, category)
    return product, sell(client, product, 4)


# --- devolución correcta ----------------------------------------------------


def test_full_return_refunds_the_line_and_restocks(
    client: TestClient, sold: tuple[dict, dict], db: Session
) -> None:
    product, sale = sold

    response = give_back(client, sale, 4)

    assert response.status_code == 201
    body = response.json()
    assert body["total"] == "4.80"
    assert body["method"] == "CASH"
    assert body["original_sale_id"] == sale["id"]
    assert body["items"][0]["restocked"] is True
    assert stock_of(client, product) == 10
    movement = db.scalars(
        select(StockMovement).where(StockMovement.type == StockMovementType.RETURN)
    ).one()
    assert (movement.quantity, movement.reference_id) == (4, body["id"])


def test_original_sale_is_untouched(
    client: TestClient, sold: tuple[dict, dict]
) -> None:
    _, sale = sold

    give_back(client, sale, 4)

    assert client.get(f"/sales/{sale['id']}").json() == sale


def test_return_records_the_authenticated_user(
    employee_client: TestClient, client: TestClient, sold: tuple[dict, dict]
) -> None:
    _, sale = sold
    me = employee_client.get("/auth/me").json()

    response = give_back(employee_client, sale, 1)

    assert response.status_code == 201
    assert response.json()["user_id"] == me["id"]


def test_partial_returns_add_up_to_exactly_the_line_subtotal(
    client: TestClient, category: dict
) -> None:
    # 1,000 kg a 0,99 €/kg = 0,99 €. Tres devoluciones parciales con redondeo
    # incómodo (0,333 kg → 0,33 €) deben sumar exactamente 0,99 €.
    tomate = make_product(
        client,
        category,
        ean=None,
        name="Tomate",
        price="0.99",
        is_weighted=True,
        initial_stock=0,
    )
    sale = sell(client, tomate, "1.000")

    totals = [
        Decimal(give_back(client, sale, q).json()["total"])
        for q in ("0.333", "0.333", "0.334")
    ]

    assert totals == [Decimal("0.33"), Decimal("0.33"), Decimal("0.33")]
    assert sum(totals) == Decimal(sale["items"][0]["subtotal"])


def test_restock_false_refunds_without_touching_stock(
    client: TestClient, sold: tuple[dict, dict], db: Session
) -> None:
    product, sale = sold

    response = give_back(client, sale, 2, restock=False)

    assert response.status_code == 201
    assert response.json()["items"][0]["restocked"] is False
    assert stock_of(client, product) == 6
    assert not db.scalars(
        select(StockMovement).where(StockMovement.type == StockMovementType.RETURN)
    ).all()


def test_weighted_product_is_never_restocked(
    client: TestClient, category: dict
) -> None:
    tomate = make_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )
    sale = sell(client, tomate, "1.500")

    response = give_back(client, sale, "0.500")

    assert response.json()["items"][0]["restocked"] is False
    assert stock_of(client, tomate) is None


# --- rechazos: no deben dejar rastro ----------------------------------------


def test_cannot_return_more_than_sold(
    client: TestClient, sold: tuple[dict, dict], db: Session
) -> None:
    product, sale = sold

    response = give_back(client, sale, 5)

    assert response.status_code == 409
    assert stock_of(client, product) == 6


def test_cannot_return_the_same_units_twice(
    client: TestClient, sold: tuple[dict, dict]
) -> None:
    product, sale = sold
    give_back(client, sale, 3)

    again = give_back(client, sale, 2)  # solo queda 1 por devolver

    assert again.status_code == 409
    assert stock_of(client, product) == 9
    assert give_back(client, sale, 1).status_code == 201


def test_fully_returned_line_cannot_be_returned_again(
    client: TestClient, sold: tuple[dict, dict]
) -> None:
    _, sale = sold
    give_back(client, sale, 4)

    assert give_back(client, sale, 1).status_code == 409


def test_fractional_quantity_of_non_weighted_product_returns_422(
    client: TestClient, sold: tuple[dict, dict]
) -> None:
    _, sale = sold

    assert give_back(client, sale, "1.5").status_code == 422


def test_unknown_sale_returns_404(client: TestClient) -> None:
    body = {
        "original_sale_id": 999999,
        "method": "CASH",
        "items": [{"sale_item_id": 1, "quantity": "1"}],
    }

    assert client.post("/returns", json=body).status_code == 404


def test_line_from_another_sale_returns_422(client: TestClient, category: dict) -> None:
    product = make_product(client, category)
    sale_a, sale_b = sell(client, product, 1), sell(client, product, 1)
    body = {
        "original_sale_id": sale_a["id"],
        "method": "CASH",
        "items": [{"sale_item_id": sale_b["items"][0]["id"], "quantity": "1"}],
    }

    assert client.post("/returns", json=body).status_code == 422


def test_unknown_line_returns_422(client: TestClient, sold: tuple[dict, dict]) -> None:
    _, sale = sold
    body = {
        "original_sale_id": sale["id"],
        "method": "CARD",
        "items": [{"sale_item_id": 999999, "quantity": "1"}],
    }

    assert client.post("/returns", json=body).status_code == 422


def test_cancelled_sale_cannot_be_returned(
    client: TestClient, sold: tuple[dict, dict], db: Session
) -> None:
    _, sale = sold
    db.get(Sale, sale["id"]).status = SaleStatus.CANCELLED
    db.commit()

    assert give_back(client, sale, 1).status_code == 409


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.update(items=[]),
        lambda b: b["items"][0].update(quantity="0"),
        lambda b: b["items"][0].update(quantity="-1"),
        lambda b: b["items"][0].update(quantity="1.2345"),
        lambda b: b["items"][0].update(
            amount="99.00"
        ),  # el importe lo calcula el servidor
        lambda b: b.update(method="BIZUM"),
        lambda b: b.update(total="99.00"),
        lambda b: b.update(items=b["items"] * 2),  # misma línea repetida
        lambda b: b.pop("method"),
    ],
)
def test_invalid_return_payload_returns_422(
    client: TestClient, sold: tuple[dict, dict], mutate
) -> None:
    product, sale = sold
    body = {
        "original_sale_id": sale["id"],
        "method": "CASH",
        "items": [{"sale_item_id": sale["items"][0]["id"], "quantity": "1"}],
    }
    mutate(body)

    assert client.post("/returns", json=body).status_code == 422
    assert stock_of(client, product) == 6


# --- consulta ---------------------------------------------------------------


def test_get_and_list_returns(client: TestClient, sold: tuple[dict, dict]) -> None:
    _, sale = sold
    first = give_back(client, sale, 1).json()
    second = give_back(client, sale, 1).json()

    assert client.get(f"/returns/{first['id']}").json() == first
    assert [r["id"] for r in client.get("/returns").json()] == [
        second["id"],
        first["id"],
    ]
    assert client.get("/returns/999999").status_code == 404


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_returns_rejects_invalid_params(client: TestClient, params: dict) -> None:
    assert client.get("/returns", params=params).status_code == 422


# --- concurrencia -----------------------------------------------------------


def test_two_simultaneous_returns_cannot_refund_the_same_units_twice(
    committed_client: TestClient,
) -> None:
    category = committed_client.post("/categories", json={"name": "Bebidas"}).json()
    product = make_product(committed_client, category)
    sale = sell(committed_client, product, 8)
    barrier = Barrier(WORKERS)

    def give_back_eight() -> int:
        client = TestClient(app, headers=committed_client.headers)
        barrier.wait()
        return give_back(client, sale, 8).status_code

    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        results = sorted(pool.map(lambda _: give_back_eight(), range(WORKERS)))

    # Se vendieron 8: de todas las devoluciones de 8, solo una puede entrar.
    assert results == [201] + [409] * (WORKERS - 1)
    assert stock_of(committed_client, product) == 10
