from collections.abc import Callable
from datetime import timedelta

import jwt
import pytest
from fastapi.testclient import TestClient

from backend.config import settings
from backend.models.user import User, UserRole
from backend.security import ALGORITHM, create_access_token

# --- login ------------------------------------------------------------------


def login(client: TestClient, username: str, password: str):
    return client.post("/auth/login", json={"username": username, "password": password})


def test_login_returns_a_token_that_works(
    anon_client: TestClient, employee_user: User, password: str
) -> None:
    response = login(anon_client, "empleado", password)

    assert response.status_code == 200
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["expires_in"] == settings.JWT_EXPIRE_MINUTES * 60
    me = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {body['access_token']}"}
    )
    assert me.json()["username"] == "empleado"


@pytest.mark.parametrize("typed", ["empleado", "EMPLEADO", "Empleado"])
def test_login_username_is_case_insensitive(
    anon_client: TestClient, employee_user: User, password: str, typed: str
) -> None:
    assert login(anon_client, typed, password).status_code == 200


def test_login_failures_are_indistinguishable(
    anon_client: TestClient,
    employee_user: User,
    make_user: Callable[..., User],
    password: str,
) -> None:
    make_user("baja", active=False)

    wrong_password = login(anon_client, "empleado", "contraseña-incorrecta")
    unknown_user = login(anon_client, "nadie", password)
    inactive_user = login(anon_client, "baja", password)

    # Misma respuesta en los tres casos: no se revela si el usuario existe.
    for response in (wrong_password, unknown_user, inactive_user):
        assert response.status_code == 401
        assert response.json() == {"detail": "Credenciales incorrectas"}
        assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"username": "x"},
        {"password": "x"},
        {"username": "", "password": "x"},
        {"username": "x", "password": ""},
        {"username": "x" * 51, "password": "x"},
        {"username": "x", "password": "x" * 129},  # tope: Argon2 es costoso
        {"username": "x", "password": "x", "role": "ADMIN"},
    ],
)
def test_login_invalid_payload_returns_422(
    anon_client: TestClient, payload: dict
) -> None:
    assert anon_client.post("/auth/login", json=payload).status_code == 422


# --- tokens inválidos -------------------------------------------------------


def test_missing_token_returns_401(anon_client: TestClient) -> None:
    response = anon_client.get("/auth/me")

    assert response.status_code == 401
    assert response.headers["www-authenticate"] == "Bearer"


@pytest.mark.parametrize(
    "header",
    ["Bearer", "Bearer abc", "Basic dXNlcjpwYXNz", "abc", "Bearer a.b.c"],
)
def test_malformed_authorization_header_returns_401(
    anon_client: TestClient, header: str
) -> None:
    response = anon_client.get("/auth/me", headers={"Authorization": header})

    assert response.status_code == 401


def test_expired_token_returns_401(
    anon_client: TestClient, employee_user: User
) -> None:
    token = create_access_token(employee_user.id, expires_in=timedelta(seconds=-1))

    response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_tampered_token_returns_401(
    anon_client: TestClient, employee_user: User
) -> None:
    token = create_access_token(employee_user.id)
    tampered = token[:-4] + ("AAAA" if not token.endswith("AAAA") else "BBBB")

    response = anon_client.get(
        "/auth/me", headers={"Authorization": f"Bearer {tampered}"}
    )

    assert response.status_code == 401


def test_token_cannot_claim_a_role(
    anon_client: TestClient, employee_user: User
) -> None:
    # Un token firmado con un "role" inventado no concede nada: el rol sale
    # siempre de la base de datos.
    token = jwt.encode(
        {"sub": str(employee_user.id), "exp": 9999999999, "role": "ADMIN"},
        settings.JWT_SECRET,
        algorithm=ALGORITHM,
    )

    response = anon_client.get("/users", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 403


def test_token_of_deleted_user_returns_401(anon_client: TestClient) -> None:
    token = create_access_token(999999)

    response = anon_client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401


def test_deactivated_user_loses_access_immediately(
    client: TestClient, employee_client: TestClient, employee_user: User
) -> None:
    assert employee_client.get("/auth/me").status_code == 200

    client.patch(f"/users/{employee_user.id}", json={"active": False})

    assert employee_client.get("/auth/me").status_code == 401


def test_demoted_admin_loses_admin_rights_immediately(
    client: TestClient, make_user: Callable[..., User], client_factory: Callable
) -> None:
    other_admin = make_user("otro", UserRole.ADMIN)
    other_client = client_factory(other_admin)
    assert other_client.get("/users").status_code == 200

    client.patch(f"/users/{other_admin.id}", json={"role": "EMPLOYEE"})

    assert other_client.get("/users").status_code == 403


# --- me / logout ------------------------------------------------------------


def test_me_does_not_expose_password_hash(client: TestClient) -> None:
    body = client.get("/auth/me").json()

    assert set(body) == {"id", "username", "role", "active", "created_at", "updated_at"}


def test_logout_requires_authentication_and_returns_204(
    client: TestClient, anon_client: TestClient
) -> None:
    assert anon_client.post("/auth/logout").status_code == 401
    assert client.post("/auth/logout").status_code == 204


# --- cambio de contraseña ---------------------------------------------------


def test_change_password_then_login_with_the_new_one(
    employee_client: TestClient, anon_client: TestClient, password: str
) -> None:
    response = employee_client.post(
        "/auth/change-password",
        json={"current_password": password, "new_password": "nueva-contraseña-123"},
    )

    assert response.status_code == 204
    assert login(anon_client, "empleado", password).status_code == 401
    assert login(anon_client, "empleado", "nueva-contraseña-123").status_code == 200


def test_change_password_with_wrong_current_returns_400(
    employee_client: TestClient, anon_client: TestClient, password: str
) -> None:
    response = employee_client.post(
        "/auth/change-password",
        json={"current_password": "incorrecta", "new_password": "nueva-contraseña-123"},
    )

    assert response.status_code == 400
    assert login(anon_client, "empleado", password).status_code == 200


def test_change_password_rejects_short_new_password(
    employee_client: TestClient, password: str
) -> None:
    response = employee_client.post(
        "/auth/change-password",
        json={"current_password": password, "new_password": "corta"},
    )

    assert response.status_code == 422


def test_change_password_requires_authentication(anon_client: TestClient) -> None:
    response = anon_client.post(
        "/auth/change-password",
        json={"current_password": "x", "new_password": "nueva-contraseña-123"},
    )

    assert response.status_code == 401
