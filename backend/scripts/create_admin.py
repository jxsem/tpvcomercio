"""Crea el primer administrador (o uno más) desde la terminal.

Uso:  python -m backend.scripts.create_admin NOMBRE

La contraseña se pide por teclado: así no queda en el historial del shell ni
en la lista de procesos.
"""

import argparse
import getpass
import sys

from pydantic import ValidationError

from backend.database.session import SessionLocal
from backend.models.user import User, UserRole
from backend.schemas.user_create import UserCreate
from backend.security import hash_password


def main() -> int:
    parser = argparse.ArgumentParser(description="Crea un usuario administrador")
    parser.add_argument("username")
    args = parser.parse_args()

    password = getpass.getpass("Contraseña: ")
    if password != getpass.getpass("Repite la contraseña: "):
        print("Las contraseñas no coinciden", file=sys.stderr)
        return 1

    try:
        data = UserCreate(
            username=args.username, password=password, role=UserRole.ADMIN
        )
    except ValidationError as exc:
        for error in exc.errors():
            print(f"{error['loc'][0]}: {error['msg']}", file=sys.stderr)
        return 1

    with SessionLocal() as db:
        db.add(
            User(
                username=data.username,
                password_hash=hash_password(data.password),
                role=data.role,
            )
        )
        try:
            db.commit()
        except Exception as exc:  # p. ej. el usuario ya existe
            db.rollback()
            print(f"No se pudo crear el usuario: {type(exc).__name__}", file=sys.stderr)
            return 1
    print(f"Administrador '{data.username}' creado")
    return 0


if __name__ == "__main__":
    sys.exit(main())
