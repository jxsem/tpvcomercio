from collections.abc import Iterator

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


@pytest.fixture
def client(db: Session) -> Iterator[TestClient]:
    def override_get_db() -> Iterator[Session]:
        yield db

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.fixture
def category(client: TestClient) -> dict:
    response = client.post("/categories", json={"name": "Bebidas"})
    assert response.status_code == 201
    return response.json()
