# ruff: noqa: E402
import os

# Antes de importar la app: Settings exige JWT_SECRET y los tests no deben
# depender del .env de nadie.
os.environ.setdefault("JWT_SECRET", "clave-solo-para-tests-" + "x" * 32)

from collections.abc import Callable, Iterator

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import Engine, create_engine
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

import backend.models  # noqa: F401  (registra los modelos en Base.metadata)
from backend.config import settings
from backend.database.base import Base
from backend.database.session import get_db
from backend.main import app
from backend.models.user import User, UserRole
from backend.security import create_access_token, hash_password

TEST_PASSWORD = "contraseña-de-test-1"
# Argon2 es lento a propósito: se calcula una vez para toda la sesión de tests.
_TEST_PASSWORD_HASH = hash_password(TEST_PASSWORD)


def _same_database(url_a: str, url_b: str) -> bool:
    a, b = make_url(url_a), make_url(url_b)
    return (a.host, a.port, a.database) == (b.host, b.port, b.database)


@pytest.fixture(scope="session")
def engine() -> Iterator[Engine]:
    url = settings.TEST_DATABASE_URL
    # Freno de seguridad: create_all/drop_all sobre la base de desarrollo
    # borraría datos reales.
    if not url or _same_database(url, settings.DATABASE_URL):
        pytest.exit(
            "TEST_DATABASE_URL no está definida o apunta a la base de desarrollo",
            returncode=2,
        )
    engine = create_engine(url)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    yield engine
    Base.metadata.drop_all(engine)
    engine.dispose()


@pytest.fixture
def db(engine: Engine) -> Iterator[Session]:
    """Sesión por test, aislada: todo lo que haga se deshace al terminar.

    La sesión se une a una transacción externa con un savepoint: los commit()
    de las rutas solo liberan el savepoint, y el rollback final lo borra todo.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection, join_transaction_mode="create_savepoint")
    yield session
    session.close()
    transaction.rollback()
    connection.close()


def bearer(user_id: int) -> dict[str, str]:
    return {"Authorization": f"Bearer {create_access_token(user_id)}"}


@pytest.fixture
def password() -> str:
    """Contraseña de todos los usuarios creados con make_user."""
    return TEST_PASSWORD


@pytest.fixture
def make_user(db: Session) -> Callable[..., User]:
    def _make_user(
        username: str, role: UserRole = UserRole.EMPLOYEE, active: bool = True
    ) -> User:
        user = User(
            username=username,
            password_hash=_TEST_PASSWORD_HASH,
            role=role,
            active=active,
        )
        db.add(user)
        db.commit()
        return user

    return _make_user


@pytest.fixture
def admin_user(make_user: Callable[..., User]) -> User:
    return make_user("admin", UserRole.ADMIN)


@pytest.fixture
def employee_user(make_user: Callable[..., User]) -> User:
    return make_user("empleado", UserRole.EMPLOYEE)


@pytest.fixture
def client_factory(db: Session) -> Iterator[Callable[..., TestClient]]:
    """Fábrica de clientes independientes que comparten la sesión de test."""

    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db

    def _client(user: User | None = None) -> TestClient:
        headers = bearer(user.id) if user is not None else {}
        return TestClient(app, headers=headers)

    yield _client
    app.dependency_overrides.clear()


@pytest.fixture
def anon_client(client_factory: Callable[..., TestClient]) -> TestClient:
    """Cliente sin credenciales."""
    return client_factory()


@pytest.fixture
def client(client_factory: Callable[..., TestClient], admin_user: User) -> TestClient:
    """Cliente autenticado como administrador (el caso por defecto de los tests)."""
    return client_factory(admin_user)


@pytest.fixture
def employee_client(
    client_factory: Callable[..., TestClient], employee_user: User
) -> TestClient:
    return client_factory(employee_user)


@pytest.fixture
def category(client: TestClient) -> dict:
    response = client.post("/categories", json={"name": "Bebidas"})
    assert response.status_code == 201
    return response.json()
