import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

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


def add_movement(db: Session, product: dict, type: str, quantity: int) -> None:
    db.add(StockMovement(product_id=product["id"], type=type, quantity=quantity))
    db.commit()


# --- GET /stock/{product_id} ------------------------------------------------


def test_get_stock_returns_only_the_stock_fields(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    response = client.get(f"/stock/{cola['id']}")

    assert response.status_code == 200
    assert response.json() == {
        "id": cola["id"],
        "name": "Coca-Cola",
        "stock": 10,
        "is_weighted": False,
    }


def test_get_stock_of_weighted_product_is_null(
    client: TestClient, category: dict
) -> None:
    tomate = create_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )

    body = client.get(f"/stock/{tomate['id']}").json()

    assert body["stock"] is None
    assert body["is_weighted"] is True


def test_get_stock_unknown_product_returns_404(client: TestClient) -> None:
    assert client.get("/stock/999999").status_code == 404


def test_get_stock_non_integer_id_returns_422(client: TestClient) -> None:
    assert client.get("/stock/abc").status_code == 422


# --- GET /stock -------------------------------------------------------------


@pytest.fixture
def inventory(client: TestClient, category: dict) -> None:
    create_product(client, category, ean="8410000000001", name="Agua", initial_stock=3)
    create_product(client, category, ean="8410000000002", name="Cola", initial_stock=30)
    create_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )


def test_list_stock_excludes_weighted_products(
    client: TestClient, inventory: None
) -> None:
    response = client.get("/stock")

    assert [p["name"] for p in response.json()] == ["Agua", "Cola"]


@pytest.mark.parametrize(
    ("max_stock", "expected"),
    [(2, []), (3, ["Agua"]), (30, ["Agua", "Cola"])],
)
def test_list_stock_filters_low_stock(
    client: TestClient, inventory: None, max_stock: int, expected: list[str]
) -> None:
    response = client.get("/stock", params={"max_stock": max_stock})

    assert [p["name"] for p in response.json()] == expected


@pytest.mark.parametrize(
    "params", [{"max_stock": -1}, {"limit": 0}, {"limit": 101}, {"offset": -1}]
)
def test_list_stock_rejects_invalid_params(client: TestClient, params: dict) -> None:
    assert client.get("/stock", params=params).status_code == 422


# --- GET /stock/movements ---------------------------------------------------


def test_movements_route_is_not_shadowed_by_product_id(client: TestClient) -> None:
    # Regresión: si /{product_id} se declarara antes, esto daría 422.
    assert client.get("/stock/movements").status_code == 200


def test_movements_newest_first_with_expected_shape(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category)  # genera el INITIAL (+10)
    add_movement(db, cola, StockMovementType.LOSS, -2)

    body = client.get("/stock/movements").json()

    assert [m["type"] for m in body] == ["LOSS", "INITIAL"]
    assert [m["quantity"] for m in body] == [-2, 10]
    assert set(body[0]) == {
        "id",
        "product_id",
        "type",
        "quantity",
        "reason",
        "reference_id",
        "created_at",
    }  # user_id no se expone


def test_movements_filter_by_product_and_type(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category, ean="8410000000001", name="Cola")
    agua = create_product(client, category, ean="8410000000002", name="Agua")
    add_movement(db, cola, StockMovementType.LOSS, -1)

    only_agua = client.get("/stock/movements", params={"product_id": agua["id"]})
    only_loss = client.get("/stock/movements", params={"type": "LOSS"})

    assert [m["product_id"] for m in only_agua.json()] == [agua["id"]]
    assert [m["type"] for m in only_loss.json()] == ["LOSS"]


def test_movements_filter_unknown_product_returns_empty_list(
    client: TestClient,
) -> None:
    response = client.get("/stock/movements", params={"product_id": 999999})

    assert response.status_code == 200
    assert response.json() == []


def test_movements_paginate_without_repeating_rows(
    client: TestClient, category: dict
) -> None:
    for i in range(3):
        create_product(client, category, ean=f"841000000000{i}", name=f"P{i}")

    first = client.get("/stock/movements", params={"limit": 2}).json()
    second = client.get("/stock/movements", params={"limit": 2, "offset": 2}).json()

    ids = [m["id"] for m in first + second]
    assert len(ids) == 3
    assert len(set(ids)) == 3


@pytest.mark.parametrize(
    "params",
    [
        {"type": "FOO"},
        {"type": "sale"},
        {"product_id": "x"},
        {"limit": 0},
        {"limit": 101},
    ],
)
def test_movements_reject_invalid_params(client: TestClient, params: dict) -> None:
    assert client.get("/stock/movements", params=params).status_code == 422
