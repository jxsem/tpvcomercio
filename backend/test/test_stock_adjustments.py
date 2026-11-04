import pytest
from fastapi.testclient import TestClient
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.audit_log import AuditAction, AuditLog
from backend.models.stock_movement import StockMovement


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


def adjust(client: TestClient, product: dict, **overrides: object):
    payload = {
        "product_id": product["id"],
        "type": "PURCHASE",
        "quantity": 5,
        "reason": "Pedido del proveedor",
    }
    return client.post("/stock/adjustments", json={**payload, **overrides})


def current_stock(client: TestClient, product: dict) -> int | None:
    return client.get(f"/stock/{product['id']}").json()["stock"]


@pytest.mark.parametrize(
    ("type", "quantity", "expected_stock", "expected_movement"),
    [
        ("PURCHASE", 5, 15, 5),
        ("LOSS", 3, 7, -3),
        ("ADJUSTMENT", 4, 14, 4),
        ("ADJUSTMENT", -4, 6, -4),
    ],
)
def test_adjustment_changes_stock_with_the_sign_of_its_type(
    client: TestClient,
    category: dict,
    type: str,
    quantity: int,
    expected_stock: int,
    expected_movement: int,
) -> None:
    cola = create_product(client, category)

    response = adjust(client, cola, type=type, quantity=quantity)

    assert response.status_code == 201, response.text
    assert response.json()["type"] == type
    assert response.json()["quantity"] == expected_movement
    assert current_stock(client, cola) == expected_stock


def test_adjustment_records_user_reason_and_audit_log(
    client: TestClient, category: dict, db: Session, admin_user
) -> None:
    cola = create_product(client, category)

    adjust(client, cola, type="LOSS", quantity=2, reason="Botellas rotas")

    movement = db.scalars(
        select(StockMovement).where(StockMovement.type == "LOSS")
    ).one()
    assert movement.user_id == admin_user.id
    assert movement.reason == "Botellas rotas"
    log = db.scalars(
        select(AuditLog).where(AuditLog.action == AuditAction.STOCK_ADJUSTED)
    ).one()
    assert log.user_id == admin_user.id
    assert log.entity == "product"
    assert log.entity_id == cola["id"]
    assert log.details["delta"] == -2


def test_loss_cannot_leave_negative_stock_and_changes_nothing(
    client: TestClient, category: dict, db: Session
) -> None:
    cola = create_product(client, category, initial_stock=2)

    response = adjust(client, cola, type="LOSS", quantity=3)

    assert response.status_code == 409
    assert current_stock(client, cola) == 2
    # Ni movimiento ni auditoría del intento fallido.
    assert (
        db.scalars(select(StockMovement).where(StockMovement.type == "LOSS")).all()
        == []
    )
    assert (
        db.scalars(
            select(AuditLog).where(AuditLog.action == AuditAction.STOCK_ADJUSTED)
        ).all()
        == []
    )


def test_loss_down_to_exactly_zero_is_allowed(
    client: TestClient, category: dict
) -> None:
    cola = create_product(client, category, initial_stock=2)

    assert adjust(client, cola, type="LOSS", quantity=2).status_code == 201
    assert current_stock(client, cola) == 0


def test_weighted_product_cannot_be_adjusted(
    client: TestClient, category: dict
) -> None:
    tomate = create_product(
        client, category, ean=None, name="Tomate", is_weighted=True, initial_stock=0
    )

    assert adjust(client, tomate).status_code == 409


def test_unknown_product_returns_404(client: TestClient) -> None:
    response = client.post(
        "/stock/adjustments",
        json={
            "product_id": 999999,
            "type": "PURCHASE",
            "quantity": 1,
            "reason": "Prueba de producto",
        },
    )

    assert response.status_code == 404


@pytest.mark.parametrize(
    "overrides",
    [
        {"type": "SALE"},  # reservado al flujo de ventas
        {"type": "RETURN"},
        {"type": "INITIAL"},
        {"type": "FOO"},
        {"quantity": 0},
        {"type": "PURCHASE", "quantity": -1},  # el signo lo decide el tipo
        {"type": "LOSS", "quantity": -1},
        {"reason": ""},
        {"reason": "x" * 256},
        {"quantity": "abc"},
        {"extra_field": 1},
    ],
)
def test_invalid_payloads_return_422(
    client: TestClient, category: dict, overrides: dict
) -> None:
    cola = create_product(client, category)

    assert adjust(client, cola, **overrides).status_code == 422
    assert current_stock(client, cola) == 10


def test_missing_reason_returns_422(client: TestClient, category: dict) -> None:
    cola = create_product(client, category)

    response = client.post(
        "/stock/adjustments",
        json={"product_id": cola["id"], "type": "PURCHASE", "quantity": 1},
    )

    assert response.status_code == 422


def test_employee_cannot_adjust_stock(
    client: TestClient, employee_client: TestClient, category: dict
) -> None:
    cola = create_product(client, category)

    assert adjust(employee_client, cola).status_code == 403
    assert current_stock(client, cola) == 10
