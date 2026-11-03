from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from backend.database.connection import engine

SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    # `yield` convierte get_db en un generador: llamarla devuelve un objeto
    # generador, y el cuerpo no se ejecuta hasta que FastAPI pide el siguiente
    # valor. Por eso el tipo es Iterator[Session] y no Session.
    #
    # Flujo de una petición:
    # 1. FastAPI pide el primer valor: se crea la sesión y se ejecuta hasta `yield`.
    # 2. `yield` entrega `db` al endpoint y pausa la función (el `with` sigue abierto).
    # 3. El endpoint usa `db`.
    # 4. Al terminar, FastAPI reanuda la función: se sale del `with` y se llama a
    #    db.close(), incluso si el endpoint lanzó una excepción.
    with SessionLocal() as db:
        yield db
