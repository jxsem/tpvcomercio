import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.stock_movement import StockMovement, StockMovementType

EAN = "8412345678901"


def product_payload(category: dict, **overrides: object) -> dict:
    payload = {
        "ean": EAN,
        "name": "Coca-Cola",
        "category_id": category["id"],
        "price": "1.20",
        "tax_rate": "21.00",
        "initial_stock": 10,
    }
    return {**payload, **overrides}


def create_product(client: TestClient, category: dict, **overrides: object) -> dict:
    response = client.post("/products", json=product_payload(category, **overrides))
    assert response.status_code == 201, response.text
    return response.json()


# --- creación ---------------------------------------------------------------


def test_create_product_returns_201_with_stock_and_exact_money(
    client: TestClient, category: dict
) -> None:
    body = create_product(client, category)

    assert body["ean"] == EAN
    assert body["stock"] == 10
    assert body["active"] is True
    assert body["is_weighted"] is False
    # El dinero viaja como cadena para no perder precisión (nada de float).
    assert body["price"] == "1.20"
    assert body["tax_rate"] == "21.00"


def test_create_product_records_initial_stock_movement(
    client: TestClient, category: dict, db: Session
) -> None:
    body = create_product(client, category)

    movements = db.scalars(select(StockMovement)).all()
    assert len(movements) == 1
    assert movements[0].product_id == body["id"]
    assert movements[0].type == StockMovementType.INITIAL
    assert movements[0].quantity == 10


def test_create_product_with_zero_stock_records_no_movement(
    client: TestClient, category: dict, db: Session
) -> None:
    body = create_product(client, category, initial_stock=0)

    assert body["stock"] == 0
    assert db.scalars(select(StockMovement)).all() == []


def test_create_weighted_product_has_no_stock_and_no_movement(
    client: TestClient, category: dict, db: Session
) -> None:
    body = create_product(
        client,
        category,
        ean=None,
        name="Tomate",
        price="2.20",
        tax_rate="4.00",
        is_weighted=True,
        initial_stock=0,
    )

    assert body["stock"] is None
    assert body["is_weighted"] is True
    assert db.scalars(select(StockMovement)).all() == []


def test_create_product_duplicate_ean_returns_409_and_no_orphan_movement(
    client: TestClient, category: dict, db: Session
) -> None:
    create_product(client, category)

    response = client.post(
        "/products", json=product_payload(category, name="Otra Cola")
    )

    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe un producto con ese EAN"}
    assert len(db.scalars(select(StockMovement)).all()) == 1


def test_create_product_same_name_in_different_products_is_allowed(
    client: TestClient, category: dict
) -> None:
    create_product(client, category)

    response = client.post(
        "/products", json=product_payload(category, ean="8412345678902")
    )

    assert response.status_code == 201


def test_create_product_without_ean_is_allowed(
    client: TestClient, category: dict
) -> None:
    body = create_product(client, category, ean=None)

    assert body["ean"] is None


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": ""},
        {"name": "x" * 51},
        {"price": "-0.01"},
        {"price": "1.234"},
        {"price": "100000000.00"},
        {"price": "abc"},
        {"tax_rate": "21.01"},
        {"tax_rate": "-1"},
        {"initial_stock": -1},
        {"ean": "123456789012"},  # 12 dígitos
        {"ean": "84123456789012"},  # 14 dígitos
        {"ean": "84123456abcde"},
        {"ean": "٠٠٠٠٠٠٠٠٠٠٠٠٠"},  # 13 dígitos árabes: \d los aceptaría
        {"stock": 999},  # campo no permitido: el stock solo se mueve con movimientos
        {"is_weighted": True},  # pesable con EAN y con stock
        {"is_weighted": True, "ean": None},  # pesable con stock
    ],
)
def test_create_product_invalid_payload_returns_422(
    client: TestClient, category: dict, overrides: dict
) -> None:
    response = client.post("/products", json=product_payload(category, **overrides))

    assert response.status_code == 422


def test_create_product_missing_required_field_returns_422(
    client: TestClient, category: dict
) -> None:
    payload = product_payload(category)
    del payload["price"]

    response = client.post("/products", json=payload)

    assert response.status_code == 422


def test_create_product_unknown_category_returns_422(client: TestClient) -> None:
    response = client.post("/products", json=product_payload({"id": 999999}))

    assert response.status_code == 422


def test_create_product_inactive_category_returns_422(
    client: TestClient, category: dict
) -> None:
    client.patch(f"/categories/{category['id']}", json={"active": False})

    response = client.post("/products", json=product_payload(category))

    assert response.status_code == 422


# --- lectura ----------------------------------------------------------------


def test_get_product(client: TestClient, category: dict) -> None:
    created = create_product(client, category)

    response = client.get(f"/products/{created['id']}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_product_not_found_returns_404(client: TestClient) -> None:
    assert client.get("/products/999999").status_code == 404


def test_get_product_by_ean(client: TestClient, category: dict) -> None:
    created = create_product(client, category)

    response = client.get(f"/products/ean/{EAN}")

    assert response.status_code == 200
    assert response.json() == created


def test_get_product_by_unknown_ean_returns_404(client: TestClient) -> None:
    assert client.get("/products/ean/8412345678999").status_code == 404


@pytest.mark.parametrize("ean", ["123", "abcdefghijklm", "84123456789012"])
def test_get_product_by_malformed_ean_returns_422(client: TestClient, ean: str) -> None:
    assert client.get(f"/products/ean/{ean}").status_code == 422


# --- listado y búsqueda -----------------------------------------------------


@pytest.fixture
def catalog(client: TestClient, category: dict) -> dict:
    """Tres productos: dos en Bebidas y uno en otra categoría."""
    other = client.post("/categories", json={"name": "Limpieza"}).json()
    return {
        "cola": create_product(client, category, ean="8410000000001", name="Coca-Cola"),
        "agua": create_product(client, category, ean="8410000000002", name="Agua"),
        "lejia": create_product(
            client, other, ean="8410000000003", name="Lejía 100% pura"
        ),
        "other_category": other,
    }


def names(response) -> list[str]:
    return [p["name"] for p in response.json()]


def test_list_products_is_sorted_by_name(client: TestClient, catalog: dict) -> None:
    response = client.get("/products")

    assert names(response) == ["Agua", "Coca-Cola", "Lejía 100% pura"]


@pytest.mark.parametrize(
    ("q", "expected"),
    [
        ("cola", ["Coca-Cola"]),  # sin distinguir mayúsculas
        ("AGU", ["Agua"]),  # coincidencia parcial
        ("8410000000002", ["Agua"]),  # EAN exacto
        ("841000000000", []),  # EAN parcial: no coincide
        ("%", ["Lejía 100% pura"]),  # % se busca como texto, no como comodín
        ("_", []),  # _ tampoco es comodín
        ("zzz", []),
    ],
)
def test_list_products_search(
    client: TestClient, catalog: dict, q: str, expected: list[str]
) -> None:
    response = client.get("/products", params={"q": q})

    assert names(response) == expected


def test_list_products_filters_by_category(client: TestClient, catalog: dict) -> None:
    response = client.get(
        "/products", params={"category_id": catalog["other_category"]["id"]}
    )

    assert names(response) == ["Lejía 100% pura"]


def test_list_products_filters_by_active(client: TestClient, catalog: dict) -> None:
    client.post(f"/products/{catalog['agua']['id']}/deactivate")

    active = client.get("/products", params={"active": True})
    inactive = client.get("/products", params={"active": False})

    assert names(active) == ["Coca-Cola", "Lejía 100% pura"]
    assert names(inactive) == ["Agua"]


def test_list_products_paginates(client: TestClient, catalog: dict) -> None:
    response = client.get("/products", params={"limit": 1, "offset": 1})

    assert names(response) == ["Coca-Cola"]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"offset": -1}, {"q": ""}, {"q": "x" * 51}]
)
def test_list_products_rejects_invalid_params(client: TestClient, params: dict) -> None:
    assert client.get("/products", params=params).status_code == 422


# --- actualización ----------------------------------------------------------


def test_update_product_changes_only_sent_fields(
    client: TestClient, category: dict
) -> None:
    created = create_product(client, category)

    response = client.patch(f"/products/{created['id']}", json={"price": "1.50"})

    assert response.status_code == 200
    body = response.json()
    assert body["price"] == "1.50"
    assert body["name"] == created["name"]
    assert body["stock"] == created["stock"]


def test_update_product_can_move_to_another_active_category(
    client: TestClient, category: dict
) -> None:
    created = create_product(client, category)
    other = client.post("/categories", json={"name": "Limpieza"}).json()

    response = client.patch(
        f"/products/{created['id']}", json={"category_id": other["id"]}
    )

    assert response.json()["category_id"] == other["id"]


@pytest.mark.parametrize(
    "payload",
    [
        {"stock": 5},
        {"active": False},
        {"is_weighted": True},
        {"id": 7},
        {"price": None},
        {"name": None},
        {"price": "-1"},
        {"category_id": 999999},
    ],
)
def test_update_product_rejects_forbidden_or_invalid_fields(
    client: TestClient, category: dict, payload: dict
) -> None:
    created = create_product(client, category)

    response = client.patch(f"/products/{created['id']}", json=payload)

    assert response.status_code == 422
    assert client.get(f"/products/{created['id']}").json() == created


def test_update_product_duplicate_ean_returns_409(
    client: TestClient, category: dict
) -> None:
    create_product(client, category)
    second = create_product(client, category, ean="8412345678902", name="Fanta")

    response = client.patch(f"/products/{second['id']}", json={"ean": EAN})

    assert response.status_code == 409


def test_update_weighted_product_ean_returns_422(
    client: TestClient, category: dict
) -> None:
    weighted = create_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )

    response = client.patch(f"/products/{weighted['id']}", json={"ean": EAN})

    assert response.status_code == 422


def test_update_product_not_found_returns_404(client: TestClient) -> None:
    assert client.patch("/products/999999", json={"price": "1"}).status_code == 404


# --- activar / desactivar ---------------------------------------------------


def test_deactivate_and_activate_product(client: TestClient, category: dict) -> None:
    created = create_product(client, category)

    deactivated = client.post(f"/products/{created['id']}/deactivate")
    activated = client.post(f"/products/{created['id']}/activate")

    assert deactivated.json()["active"] is False
    assert activated.json()["active"] is True


def test_deactivate_is_idempotent(client: TestClient, category: dict) -> None:
    created = create_product(client, category)

    client.post(f"/products/{created['id']}/deactivate")
    response = client.post(f"/products/{created['id']}/deactivate")

    assert response.status_code == 200
    assert response.json()["active"] is False


@pytest.mark.parametrize("action", ["activate", "deactivate"])
def test_activate_deactivate_unknown_product_returns_404(
    client: TestClient, action: str
) -> None:
    assert client.post(f"/products/999999/{action}").status_code == 404
