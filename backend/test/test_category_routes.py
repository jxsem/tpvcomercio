import pytest
from fastapi.testclient import TestClient


def test_create_category_returns_201_and_defaults(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "Bebidas"})

    assert response.status_code == 201
    body = response.json()
    assert body["name"] == "Bebidas"
    assert body["active"] is True
    assert isinstance(body["id"], int)


def test_create_category_strips_whitespace(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "  Bebidas  "})

    assert response.json()["name"] == "Bebidas"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"name": ""},
        {"name": "   "},
        {"name": "x" * 51},
        {"name": None},
        {"name": 123},
        {"name": "Bebidas", "active": "quizá"},
    ],
)
def test_create_category_invalid_payload_returns_422(
    client: TestClient, payload: dict
) -> None:
    response = client.post("/categories", json=payload)

    assert response.status_code == 422


def test_create_category_accepts_max_length_name(client: TestClient) -> None:
    response = client.post("/categories", json={"name": "x" * 50})

    assert response.status_code == 201


@pytest.mark.parametrize("duplicate", ["Bebidas", "bebidas", "BEBIDAS", " bEbIdAs "])
def test_create_category_duplicate_name_returns_409(
    client: TestClient, category: dict, duplicate: str
) -> None:
    response = client.post("/categories", json={"name": duplicate})

    assert response.status_code == 409
    # El mensaje es genérico: no filtra nombres de tabla ni de restricción.
    assert response.json() == {"detail": "Ya existe una categoría con ese nombre"}


def test_list_categories_is_sorted_by_name(client: TestClient) -> None:
    for name in ("Limpieza", "Alimentación", "Bazar"):
        client.post("/categories", json={"name": name})

    response = client.get("/categories")

    assert [c["name"] for c in response.json()] == [
        "Alimentación",
        "Bazar",
        "Limpieza",
    ]


def test_list_categories_filters_by_active(client: TestClient) -> None:
    client.post("/categories", json={"name": "Activa"})
    client.post("/categories", json={"name": "Inactiva", "active": False})

    response = client.get("/categories", params={"active": False})

    assert [c["name"] for c in response.json()] == ["Inactiva"]


def test_list_categories_paginates(client: TestClient) -> None:
    for name in ("A", "B", "C"):
        client.post("/categories", json={"name": name})

    response = client.get("/categories", params={"limit": 2, "offset": 1})

    assert [c["name"] for c in response.json()] == ["B", "C"]


@pytest.mark.parametrize(
    "params", [{"limit": 0}, {"limit": 101}, {"limit": -1}, {"offset": -1}]
)
def test_list_categories_rejects_out_of_range_pagination(
    client: TestClient, params: dict
) -> None:
    response = client.get("/categories", params=params)

    assert response.status_code == 422


def test_get_category(client: TestClient, category: dict) -> None:
    response = client.get(f"/categories/{category['id']}")

    assert response.status_code == 200
    assert response.json() == category


def test_get_category_not_found_returns_404(client: TestClient) -> None:
    response = client.get("/categories/999999")

    assert response.status_code == 404


def test_get_category_non_integer_id_returns_422(client: TestClient) -> None:
    response = client.get("/categories/abc")

    assert response.status_code == 422


def test_update_category_changes_only_sent_fields(
    client: TestClient, category: dict
) -> None:
    response = client.patch(f"/categories/{category['id']}", json={"active": False})

    assert response.status_code == 200
    assert response.json() == {**category, "active": False}


def test_update_category_empty_body_changes_nothing(
    client: TestClient, category: dict
) -> None:
    response = client.patch(f"/categories/{category['id']}", json={})

    assert response.status_code == 200
    assert response.json() == category


@pytest.mark.parametrize("payload", [{"name": None}, {"active": None}])
def test_update_category_explicit_null_returns_422(
    client: TestClient, category: dict, payload: dict
) -> None:
    response = client.patch(f"/categories/{category['id']}", json=payload)

    assert response.status_code == 422


def test_update_category_duplicate_name_returns_409(
    client: TestClient, category: dict
) -> None:
    other = client.post("/categories", json={"name": "Limpieza"}).json()

    response = client.patch(f"/categories/{other['id']}", json={"name": "BEBIDAS"})

    assert response.status_code == 409


def test_update_category_same_name_different_case_is_allowed(
    client: TestClient, category: dict
) -> None:
    # Renombrar a la misma palabra con otra capitalización no es un duplicado.
    response = client.patch(f"/categories/{category['id']}", json={"name": "BEBIDAS"})

    assert response.status_code == 200
    assert response.json()["name"] == "BEBIDAS"


def test_update_category_not_found_returns_404(client: TestClient) -> None:
    response = client.patch("/categories/999999", json={"name": "X"})

    assert response.status_code == 404
