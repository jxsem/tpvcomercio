from sqlalchemy import MetaData
from sqlalchemy.orm import DeclarativeBase

# Nombres predecibles para índices y restricciones: Alembic los necesita para
# poder modificarlas o borrarlas en migraciones futuras. "ck" se omite porque
# los CheckConstraint ya llevan nombre propio.
NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING_CONVENTION)
