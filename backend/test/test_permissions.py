"""Matriz de permisos: qué puede hacer cada rol en cada endpoint.

Es la red de seguridad contra el olvido más típico: añadir un endpoint nuevo
y no protegerlo. Si se crea una ruta, tiene que aparecer en una de estas listas.
"""

import pytest
from fastapi.testclient import TestClient

# Solo ADMIN. El cuerpo es irrelevante: la autorización se comprueba antes.
ADMIN_ONLY = [
    ("POST", "/categories"),
    ("PATCH", "/categories/1"),
    ("POST", "/products"),
    ("PATCH", "/products/1"),
    ("POST", "/products/1/deactivate"),
    ("POST", "/products/1/activate"),
    ("GET", "/sales"),
    ("GET", "/users"),
    ("POST", "/users"),
    ("GET", "/users/1"),
    ("PATCH", "/users/1"),
]

# Cualquier usuario autenticado.
AUTHENTICATED = [
    ("GET", "/categories"),
    ("GET", "/categories/1"),
    ("GET", "/products"),
    ("GET", "/products/1"),
    ("GET", "/products/ean/8410000000001"),
    ("POST", "/sales"),
    ("GET", "/sales/1"),
    ("GET", "/auth/me"),
    ("POST", "/auth/logout"),
    ("POST", "/auth/change-password"),
]

PUBLIC = [("GET", "/health"), ("POST", "/auth/login")]


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY + AUTHENTICATED)
def test_anonymous_gets_401(anon_client: TestClient, method: str, path: str) -> None:
    assert anon_client.request(method, path, json={}).status_code == 401


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY)
def test_employee_gets_403_on_admin_endpoints(
    employee_client: TestClient, method: str, path: str
) -> None:
    assert employee_client.request(method, path, json={}).status_code == 403


@pytest.mark.parametrize(("method", "path"), AUTHENTICATED)
def test_employee_is_not_blocked_on_shared_endpoints(
    employee_client: TestClient, method: str, path: str
) -> None:
    status = employee_client.request(method, path, json={}).status_code

    assert status not in (401, 403)


@pytest.mark.parametrize(("method", "path"), ADMIN_ONLY + AUTHENTICATED)
def test_admin_is_never_blocked(client: TestClient, method: str, path: str) -> None:
    status = client.request(method, path, json={}).status_code

    assert status not in (401, 403)


@pytest.mark.parametrize(("method", "path"), PUBLIC)
def test_public_endpoints_need_no_token(
    anon_client: TestClient, method: str, path: str
) -> None:
    assert anon_client.request(method, path, json={}).status_code not in (401, 403)


def test_every_registered_route_is_in_the_permission_matrix() -> None:
    from backend.main import app

    covered = {
        (method, path.split("?")[0])
        for method, path in ADMIN_ONLY + AUTHENTICATED + PUBLIC
    }
    documented = {
        (method.upper(), path)
        for path, operations in app.openapi()["paths"].items()
        for method in operations
    }

    def normalize(entry: tuple[str, str]) -> tuple[str, str]:
        import re

        method, path = entry
        # /categories/1 -> /categories/{x}; /products/ean/84... -> /products/ean/{x}
        return method, re.sub(
            r"/(\d+)(?=/|$)", "/{x}", re.sub(r"\{[^}]+\}", "{x}", path)
        )

    uncovered = {normalize(e) for e in documented} - {normalize(e) for e in covered}
    # /products/ean/{ean} tiene un EAN de 13 dígitos en la matriz: se normaliza aparte.
    uncovered.discard(("GET", "/products/ean/{x}"))
    assert uncovered == set(), f"Rutas sin probar en la matriz de permisos: {uncovered}"
