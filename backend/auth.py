from typing import Annotated

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy.orm import Session

from backend.database.session import get_db
from backend.models.user import User, UserRole
from backend.security import decode_access_token

# auto_error=False: así el 401 lo generamos nosotros, siempre igual.
bearer_scheme = HTTPBearer(auto_error=False)


def get_current_user(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer_scheme)],
    db: Annotated[Session, Depends(get_db)],
) -> User:
    unauthorized = HTTPException(
        status.HTTP_401_UNAUTHORIZED,
        "No autenticado",
        headers={"WWW-Authenticate": "Bearer"},
    )
    if credentials is None:
        raise unauthorized
    user_id = decode_access_token(credentials.credentials)
    if user_id is None:
        raise unauthorized
    # El usuario y su rol se leen de la base de datos en cada petición: un
    # usuario desactivado o degradado pierde el acceso al momento.
    user = db.get(User, user_id)
    if user is None or not user.active:
        raise unauthorized
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


def require_admin(user: CurrentUser) -> User:
    if user.role != UserRole.ADMIN:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Permisos insuficientes")
    return user


AdminUser = Annotated[User, Depends(require_admin)]

# Para usar en el decorador de una ruta cuando no hace falta el objeto usuario:
#   @router.post("", dependencies=[ADMIN_ONLY])
AUTHENTICATED = Depends(get_current_user)
ADMIN_ONLY = Depends(require_admin)
