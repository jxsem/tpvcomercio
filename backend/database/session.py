from collections.abc import Iterator

from sqlalchemy.orm import Session, sessionmaker

from backend.database.connection import engine

SessionLocal = sessionmaker(bind=engine)


def get_db() -> Iterator[Session]:
    with SessionLocal() as db:
        yield db
