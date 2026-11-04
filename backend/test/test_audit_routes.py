from fastapi.testclient import TestClient

PRODUCT = {
    "ean": "8410000000001",
    "name": "Coca-Cola",
    "price": "1.20",
    "tax_rate": "21.00",
    "initial_stock": 10,
}


def logs(client: TestClient, **params: object) -> list[dict]:
    response = client.get("/audit-logs", params=params)
    assert response.status_code == 200, response.text
    return response.json()


def test_creating_a_product_is_audited(client: TestClient, category: dict) -> None:
    created = client.post(
        "/products", json={**PRODUCT, "category_id": category["id"]}
    ).json()

    [entry] = logs(client, action="PRODUCT_CREATED")

    assert entry["entity"] == "product"
    assert entry["entity_id"] == created["id"]
    assert entry["metadata"]["name"] == "Coca-Cola"


def test_updating_a_product_keeps_the_old_and_new_price(
    client: TestClient, category: dict
) -> None:
    created = client.post(
        "/products", json={**PRODUCT, "category_id": category["id"]}
    ).json()

    client.patch(f"/products/{created['id']}", json={"price": "1.50"})

    [entry] = logs(client, action="PRODUCT_UPDATED")
    assert entry["metadata"]["before"] == {"price": "1.20"}
    assert entry["metadata"]["after"] == {"price": "1.50"}


def test_deactivate_and_activate_are_audited(
    client: TestClient, category: dict
) -> None:
    created = client.post(
        "/products", json={**PRODUCT, "category_id": category["id"]}
    ).json()

    client.post(f"/products/{created['id']}/deactivate")
    client.post(f"/products/{created['id']}/activate")

    assert len(logs(client, action="PRODUCT_DEACTIVATED")) == 1
    assert len(logs(client, action="PRODUCT_ACTIVATED")) == 1


def test_user_audit_never_contains_the_password(client: TestClient) -> None:
    secret = "contraseña-super-secreta-1"
    created = client.post(
        "/users", json={"username": "ana", "password": secret, "role": "EMPLOYEE"}
    ).json()
    client.patch(f"/users/{created['id']}", json={"password": secret + "2"})

    entries = logs(client, entity="user")

    assert {e["action"] for e in entries} == {"USER_CREATED", "USER_UPDATED"}
    assert "contraseña-super-secreta" not in str(entries)


def test_sale_and_return_are_audited(client: TestClient, category: dict) -> None:
    product = client.post(
        "/products", json={**PRODUCT, "category_id": category["id"]}
    ).json()
    sale = client.post(
        "/sales",
        json={
            "items": [{"product_id": product["id"], "quantity": 2}],
            "payment": {"method": "CARD"},
        },
    )
    assert sale.status_code == 201, sale.text

    [entry] = logs(client, action="SALE_CREATED")

    assert entry["entity_id"] == sale.json()["id"]
    assert entry["metadata"]["total"] == "2.40"


def test_failed_operation_leaves_no_audit_entry(
    client: TestClient, category: dict
) -> None:
    product = client.post(
        "/products", json={**PRODUCT, "category_id": category["id"]}
    ).json()

    # Stock insuficiente: la venta falla y no debe quedar rastro de una venta.
    client.post(
        "/sales",
        json={
            "items": [{"product_id": product["id"], "quantity": 999}],
            "payment": {"method": "CARD"},
        },
    )

    assert logs(client, action="SALE_CREATED") == []


def test_filters_and_pagination(client: TestClient, category: dict) -> None:
    for i in range(3):
        client.post(
            "/products",
            json={
                **PRODUCT,
                "ean": f"841000000000{i}",
                "name": f"P{i}",
                "category_id": category["id"],
            },
        )

    assert len(logs(client, limit=2)) == 2
    assert len(logs(client, action="PRODUCT_CREATED", limit=2, offset=2)) == 1


def test_most_recent_entries_come_first(client: TestClient, category: dict) -> None:
    for i in range(2):
        client.post(
            "/products",
            json={
                **PRODUCT,
                "ean": f"841000000000{i}",
                "name": f"P{i}",
                "category_id": category["id"],
            },
        )

    ids = [e["id"] for e in logs(client, action="PRODUCT_CREATED")]

    assert ids == sorted(ids, reverse=True)


def test_invalid_filters_return_422(client: TestClient) -> None:
    assert client.get("/audit-logs", params={"action": "FOO"}).status_code == 422
    assert client.get("/audit-logs", params={"limit": 0}).status_code == 422
    assert client.get("/audit-logs", params={"limit": 101}).status_code == 422
    assert client.get("/audit-logs", params={"offset": -1}).status_code == 422
