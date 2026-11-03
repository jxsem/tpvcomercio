from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, select, text
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.main import app
from backend.models.sale import Sale
from backend.models.stock_movement import StockMovement, StockMovementType


def create_product(client: TestClient, category: dict, **overrides: object) -> dict:
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


def create_weighted(client: TestClient, category: dict, price: str = "2.20") -> dict:
    return create_product(
        client,
        category,
        ean=None,
        name="Tomate",
        price=price,
        tax_rate="4.00",
        is_weighted=True,
        initial_stock=0,
    )


def card(*items: tuple[int, object]) -> dict:
    return {
        "items": [{"product_id": pid, "quantity": str(qty)} for pid, qty in items],
        "payment": {"method": "CARD"},
    }


def cash(received: str, *items: tuple[int, object]) -> dict:
    body = card(*items)
    body["payment"] = {"method": "CASH", "cash_received": received}
    return body


def stock_of(client: TestClient, product: dict) -> int | None:
    return client.get(f"/products/{product['id']}").json()["stock"]


# --- venta correcta ---------------------------------------------------------


def test_create_sale_with_card_calculates_total_on_server(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], 2)))

    assert response.status_code == 201
    body = response.json()
    assert body["total"] == "2.40"
    assert body["status"] == "COMPLETED"
    assert body["payment"]["method"] == "CARD"
    assert body["payment"]["amount"] == "2.40"
    assert body["payment"]["cash_received"] is None
    assert body["payment"]["change_given"] is None
    [line] = body["items"]
    assert (line["product_name"], line["unit_price"], line["subtotal"]) == (
        "Coca-Cola",
        "1.20",
        "2.40",
    )
    assert line["tax_rate"] == "21.00"


def test_create_sale_decrements_stock_and_records_sale_movement(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category)

    sale = client.post("/sales", json=card((cola["id"], 3))).json()

    assert stock_of(client, cola) == 7
    movements = db.scalars(
        select(StockMovement).where(StockMovement.type == StockMovementType.SALE)
    ).all()
    assert len(movements) == 1
    assert movements[0].quantity == -3
    assert movements[0].reference_id == sale["id"]
    assert movements[0].product_id == cola["id"]


def test_create_sale_selling_all_stock_leaves_zero(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], 10)))

    assert response.status_code == 201
    assert stock_of(client, cola) == 0


def test_cash_payment_calculates_change(client: TestClient, category: dict) -> None:
    cola = create_product(client, category, price="1.30")
    agua = create_product(
        client, category, ean="8410000000002", name="Agua", price="2.60"
    )

    # 2 × 1,30 + 2 × 2,60 = 7,80 (el ejemplo de la especificación)
    response = client.post(
        "/sales", json=cash("10.00", (cola["id"], 2), (agua["id"], 2))
    )

    body = response.json()
    assert body["total"] == "7.80"
    assert body["payment"]["cash_received"] == "10.00"
    assert body["payment"]["change_given"] == "2.20"


def test_cash_payment_with_exact_amount_gives_zero_change(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=cash("2.40", (cola["id"], 2)))

    assert response.status_code == 201
    assert response.json()["payment"]["change_given"] == "0.00"


def test_weighted_product_uses_weight_and_does_not_touch_stock(
    client: TestClient, category: dict, db: Session
) -> None:
    tomate = create_weighted(client, category)

    response = client.post("/sales", json=card((tomate["id"], "1.350")))

    assert response.status_code == 201
    body = response.json()
    assert body["total"] == "2.97"  # 1,350 kg × 2,20 €/kg
    assert body["items"][0]["quantity"] == "1.350"
    assert stock_of(client, tomate) is None
    assert db.scalars(select(StockMovement)).all() == []


@pytest.mark.parametrize(
    ("weight", "price", "expected"),
    [
        ("1.500", "0.01", "0.02"),  # 0,015 → redondeo hacia arriba
        ("1.333", "1.00", "1.33"),
        ("0.333", "3.00", "1.00"),  # 0,999 → 1,00
        ("0.001", "2.20", "0.00"),  # menos de medio céntimo
        ("9999.999", "0.01", "100.00"),
    ],
)
def test_weighted_subtotal_rounds_half_up(
    client: TestClient, category: dict, weight: str, price: str, expected: str
) -> None:
    tomate = create_weighted(client, category, price=price)

    response = client.post("/sales", json=card((tomate["id"], weight)))

    assert response.status_code == 201
    assert response.json()["total"] == expected


def test_sale_keeps_historical_price_after_product_price_changes(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)
    sale = client.post("/sales", json=card((cola["id"], 1))).json()

    client.patch(f"/products/{cola['id']}", json={"price": "9.99", "name": "Otra"})
    historical = client.get(f"/sales/{sale['id']}").json()

    assert historical["total"] == "1.20"
    assert historical["items"][0]["unit_price"] == "1.20"
    assert historical["items"][0]["product_name"] == "Coca-Cola"


def test_same_product_in_several_lines_is_summed_for_stock(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], 4), (cola["id"], 3)))

    assert response.status_code == 201
    assert len(response.json()["items"]) == 2
    assert stock_of(client, cola) == 3


# --- rechazos: no deben dejar rastro ----------------------------------------


def test_insufficient_stock_returns_409_and_changes_nothing(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], 11)))

    assert response.status_code == 409
    assert stock_of(client, cola) == 10
    assert db.scalars(select(Sale)).all() == []


def test_insufficient_stock_summing_duplicate_lines_returns_409(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], 6), (cola["id"], 6)))

    assert response.status_code == 409
    assert stock_of(client, cola) == 10


def test_failure_on_a_later_line_leaves_earlier_products_untouched(
    client: TestClient, category: dict, db: Session
) -> None:
    # Atomicidad: si la segunda línea falla, la primera no puede haber descontado.
    cola = create_product(client, category)
    agua = create_product(client, category, ean="8410000000002", name="Agua")

    response = client.post("/sales", json=card((cola["id"], 2), (agua["id"], 99)))

    assert response.status_code == 409
    assert stock_of(client, cola) == 10
    assert stock_of(client, agua) == 10
    assert db.scalars(select(Sale)).all() == []
    assert (
        db.scalars(
            select(StockMovement).where(StockMovement.type == StockMovementType.SALE)
        ).all()
        == []
    )


def test_cash_less_than_total_returns_422_and_changes_nothing(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=cash("2.39", (cola["id"], 2)))

    assert response.status_code == 422
    assert stock_of(client, cola) == 10
    assert db.scalars(select(Sale)).all() == []


def test_unknown_product_returns_422(client: TestClient) -> None:
    assert client.post("/sales", json=card((999999, 1))).status_code == 422


def test_inactive_product_returns_422(client: TestClient, category: dict) -> None:
    cola = create_product(client, category)
    client.post(f"/products/{cola['id']}/deactivate")

    response = client.post("/sales", json=card((cola["id"], 1)))

    assert response.status_code == 422
    assert stock_of(client, cola) == 10


def test_fractional_quantity_of_non_weighted_product_returns_422(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.post("/sales", json=card((cola["id"], "1.5")))

    assert response.status_code == 422
    assert stock_of(client, cola) == 10


@pytest.mark.parametrize(
    "mutate",
    [
        lambda b: b.update(items=[]),
        lambda b: b["items"][0].update(quantity="0"),
        lambda b: b["items"][0].update(quantity="-1"),
        lambda b: b["items"][0].update(quantity="1.2345"),
        lambda b: b["items"][0].update(quantity="10000"),
        lambda b: b["items"][0].update(quantity="abc"),
        lambda b: b["items"][0].update(price="0.01"),  # el cliente no manda precios
        lambda b: b.update(total="0.01"),  # ni totales
        lambda b: b.update(items=[b["items"][0]] * 101),
        lambda b: b.pop("payment"),
        lambda b: b["payment"].update(method="BIZUM"),
        lambda b: b["payment"].update(method="CASH"),  # efectivo sin cash_received
        lambda b: b["payment"].update(cash_received="5.00"),  # tarjeta con efectivo
        lambda b: b["payment"].update(method="CASH", cash_received="-1"),
    ],
)
def test_invalid_sale_payload_returns_422(
    client: TestClient, category: dict, mutate
) -> None:
    cola = create_product(client, category)
    body = card((cola["id"], 1))
    mutate(body)

    response = client.post("/sales", json=body)

    assert response.status_code == 422
    assert stock_of(client, cola) == 10


# --- consulta ---------------------------------------------------------------


def test_get_sale_returns_items_and_payment(client: TestClient, category: dict) -> None:
    cola = create_product(client, category)
    created = client.post("/sales", json=card((cola["id"], 2))).json()

    response = client.get(f"/sales/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_sale_not_found_returns_404(client: TestClient) -> None:
    assert client.get("/sales/999999").status_code == 404


def test_list_sales_newest_first_and_paginated(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)
    ids = [
        client.post("/sales", json=card((cola["id"], 1))).json()["id"] for _ in range(3)
    ]

    everything = client.get("/sales").json()
    page = client.get("/sales", params={"limit": 1, "offset": 1}).json()

    assert [s["id"] for s in everything] == ids[::-1]
    assert [s["id"] for s in page] == [ids[1]]
    assert all(s["items"] and s["payment"] for s in everything)


def test_list_sales_filters_by_status(client: TestClient, category: dict) -> None:
    cola = create_product(client, category)
    client.post("/sales", json=card((cola["id"], 1)))

    assert len(client.get("/sales", params={"status": "COMPLETED"}).json()) == 1
    assert client.get("/sales", params={"status": "CANCELLED"}).json() == []


@pytest.mark.parametrize(
    "params",
    [{"status": "FOO"}, {"limit": 0}, {"limit": 101}, {"offset": -1}],
)
def test_list_sales_rejects_invalid_params(client: TestClient, params: dict) -> None:
    assert client.get("/sales", params=params).status_code == 422


# --- concurrencia -----------------------------------------------------------


@pytest.fixture
def committed_client(engine: Engine) -> Iterator[TestClient]:
    """Cliente con conexiones y commits reales (sin la transacción de aislamiento).

    Hace falta para probar concurrencia: cada petición usa su propia sesión.
    Al terminar se vacían las tablas a mano.
    """

    def override_get_db() -> Iterator[Session]:
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()
    with engine.begin() as connection:
        connection.execute(
            text(
                "TRUNCATE sale_items, payments, sales, stock_movements, products,"
                " categories RESTART IDENTITY CASCADE"
            )
        )


def test_two_simultaneous_sales_cannot_oversell_the_same_stock(
    committed_client: TestClient,
) -> None:
    category = committed_client.post("/categories", json={"name": "Bebidas"}).json()
    cola = create_product(committed_client, category)  # stock 10
    barrier = Barrier(2)

    def sell_eight() -> int:
        # Un cliente por hilo; la barrera hace que ambas ventas arranquen a la vez.
        client = TestClient(app)
        barrier.wait()
        return client.post("/sales", json=card((cola["id"], 8))).status_code

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(lambda _: sell_eight(), range(2)))

    # 8 + 8 > 10: exactamente una venta debe entrar y la otra recibir 409.
    assert results == [201, 409]
    assert stock_of(committed_client, cola) == 2
    assert len(committed_client.get("/sales").json()) == 1
