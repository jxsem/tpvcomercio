from collections.abc import Callable

import pytest
from fastapi.testclient import TestClient

from backend.models.user import User, UserRole

VALID = {"username": "maria", "password": "contraseña-larga-1"}


def test_create_user_defaults_to_employee_and_hides_the_hash(
    client: TestClient,
) -> None:
    response = client.post("/users", json=VALID)

    assert response.status_code == 201
    body = response.json()
    assert body["username"] == "maria"
    assert body["role"] == "EMPLOYEE"
    assert body["active"] is True
    assert "password" not in body
    assert "password_hash" not in body


def test_created_user_can_log_in(client: TestClient, anon_client: TestClient) -> None:
    client.post("/users", json=VALID)

    response = anon_client.post(
        "/auth/login", json={"username": "maria", "password": VALID["password"]}
    )

    assert response.status_code == 200


@pytest.mark.parametrize("duplicate", ["maria", "MARIA", "Maria"])
def test_create_user_duplicate_username_returns_409(
    client: TestClient, duplicate: str
) -> None:
    client.post("/users", json=VALID)

    response = client.post("/users", json={**VALID, "username": duplicate})

    assert response.status_code == 409
    assert response.json() == {"detail": "Ya existe un usuario con ese nombre"}


@pytest.mark.parametrize(
    "overrides",
    [
        {"username": "ab"},  # muy corto
        {"username": "x" * 51},
        {"username": "con espacio"},
        {"username": "ñandú"},  # solo ASCII
        {"username": "a;drop"},
        {"password": "corta"},
        {"password": "x" * 129},
        {"role": "SUPERUSER"},
        {"active": False},  # campo no permitido al crear
        {"password_hash": "abc"},
    ],
)
def test_create_user_invalid_payload_returns_422(
    client: TestClient, overrides: dict
) -> None:
    assert client.post("/users", json={**VALID, **overrides}).status_code == 422


def test_list_users_sorted_and_paginated(client: TestClient) -> None:
    for name in ("carlos", "beatriz"):
        client.post("/users", json={**VALID, "username": name})

    names = [u["username"] for u in client.get("/users").json()]  # incluye "admin"
    page = client.get("/users", params={"limit": 1, "offset": 1}).json()

    assert names == ["admin", "beatriz", "carlos"]
    assert [u["username"] for u in page] == ["beatriz"]


@pytest.mark.parametrize("params", [{"limit": 0}, {"limit": 101}, {"offset": -1}])
def test_list_users_rejects_invalid_pagination(
    client: TestClient, params: dict
) -> None:
    assert client.get("/users", params=params).status_code == 422


def test_get_user_and_404(client: TestClient, employee_user: User) -> None:
    assert client.get(f"/users/{employee_user.id}").json()["username"] == "empleado"
    assert client.get("/users/999999").status_code == 404


def test_update_user_role_and_active(client: TestClient, employee_user: User) -> None:
    response = client.patch(
        f"/users/{employee_user.id}", json={"role": "ADMIN", "active": False}
    )

    assert response.status_code == 200
    assert response.json()["role"] == "ADMIN"
    assert response.json()["active"] is False


def test_update_user_password(
    client: TestClient, anon_client: TestClient, employee_user: User, password: str
) -> None:
    client.patch(f"/users/{employee_user.id}", json={"password": "otra-contraseña-9"})

    old = anon_client.post(
        "/auth/login", json={"username": "empleado", "password": password}
    )
    new = anon_client.post(
        "/auth/login", json={"username": "empleado", "password": "otra-contraseña-9"}
    )
    assert (old.status_code, new.status_code) == (401, 200)


@pytest.mark.parametrize(
    "payload",
    [
        {"username": "otro"},  # el username no se cambia
        {"role": None},
        {"active": None},
        {"password": None},
        {"password": "corta"},
        {"role": "SUPERUSER"},
        {"password_hash": "x"},
    ],
)
def test_update_user_invalid_payload_returns_422(
    client: TestClient, employee_user: User, payload: dict
) -> None:
    response = client.patch(f"/users/{employee_user.id}", json=payload)

    assert response.status_code == 422


def test_update_unknown_user_returns_404(client: TestClient) -> None:
    assert client.patch("/users/999999", json={"active": False}).status_code == 404


# --- protección del último administrador -----------------------------------


@pytest.mark.parametrize("payload", [{"active": False}, {"role": "EMPLOYEE"}])
def test_cannot_remove_the_last_active_admin(
    client: TestClient, admin_user: User, payload: dict
) -> None:
    response = client.patch(f"/users/{admin_user.id}", json=payload)

    assert response.status_code == 409
    assert client.get("/auth/me").status_code == 200  # sigue pudiendo entrar


def test_can_demote_an_admin_when_another_active_one_exists(
    client: TestClient, make_user: Callable[..., User]
) -> None:
    other = make_user("segundo", UserRole.ADMIN)

    response = client.patch(f"/users/{other.id}", json={"role": "EMPLOYEE"})

    assert response.status_code == 200


def test_inactive_admin_does_not_count_as_a_spare_admin(
    client: TestClient, admin_user: User, make_user: Callable[..., User]
) -> None:
    make_user("baja", UserRole.ADMIN, active=False)

    response = client.patch(f"/users/{admin_user.id}", json={"active": False})

    assert response.status_code == 409


def test_editing_the_last_admin_in_harmless_ways_is_allowed(
    client: TestClient, admin_user: User
) -> None:
    response = client.patch(
        f"/users/{admin_user.id}", json={"password": "nueva-pass-123"}
    )

    assert response.status_code == 200
