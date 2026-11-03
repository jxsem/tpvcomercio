from sqlalchemy.exc import IntegrityError

UNIQUE_VIOLATION = "23505"


def unique_violation_constraint(exc: IntegrityError) -> str | None:
    """Nombre de la restricción única violada, o None si el error es de otro tipo.

    No toda IntegrityError es un duplicado (también lo son NOT NULL, FK, CHECK),
    así que se comprueba el código SQLSTATE de PostgreSQL antes de devolver nada.
    """
    if getattr(exc.orig, "sqlstate", None) != UNIQUE_VIOLATION:
        return None
    return exc.orig.diag.constraint_name
