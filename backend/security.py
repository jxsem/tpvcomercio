from datetime import UTC, datetime, timedelta

import jwt
from pwdlib import PasswordHash

from backend.config import settings

ALGORITHM = "HS256"

# Argon2id con parámetros recomendados por la librería.
_password_hash = PasswordHash.recommended()

# Hash de una contraseña que nadie conoce. Se verifica contra él cuando el
# usuario no existe, para que login tarde lo mismo exista o no el usuario y no
# se pueda averiguar qué usernames hay midiendo tiempos.
_DUMMY_HASH = _password_hash.hash("contraseña-inexistente-para-igualar-tiempos")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_access_token(user_id: int, expires_in: timedelta | None = None) -> str:
    expires_in = expires_in or timedelta(minutes=settings.JWT_EXPIRE_MINUTES)
    now = datetime.now(UTC)
    # Solo el id: nada de rol ni permisos. Los permisos se leen de la base de
    # datos en cada petición, así que desactivar a alguien o cambiarle el rol
    # surte efecto al instante y no cuando caduque el token.
    payload = {"sub": str(user_id), "iat": now, "exp": now + expires_in}
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=ALGORITHM)


def decode_access_token(token: str) -> int | None:
    """Id de usuario del token, o None si no es válido o ha caducado."""
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET,
            # Lista fija de algoritmos: evita que un token declare "alg: none".
            algorithms=[ALGORITHM],
            options={"require": ["exp", "sub"]},
        )
        return int(payload["sub"])
    except jwt.PyJWTError, ValueError:
        return None
