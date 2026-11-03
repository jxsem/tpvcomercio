from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.auth import CurrentUser
from backend.config import settings
from backend.database.session import get_db
from backend.models.user import User
from backend.schemas.auth_schemas import ChangePasswordRequest, LoginRequest, TokenRead
from backend.schemas.user_read import UserRead
from backend.security import create_access_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=TokenRead)
def login(data: LoginRequest, db: Annotated[Session, Depends(get_db)]) -> TokenRead:
    user = db.scalar(
        select(User).where(func.lower(User.username) == data.username.lower())
    )
    # Siempre se verifica una contraseña (contra un hash falso si no hay usuario
    # válido) y el error es siempre el mismo: no se revela si el usuario existe.
    usable = user is not None and user.active
    password_ok = verify_password(data.password, user.password_hash if usable else None)
    if not (usable and password_ok):
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Credenciales incorrectas",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return TokenRead(
        access_token=create_access_token(user.id),
        expires_in=settings.JWT_EXPIRE_MINUTES * 60,
    )


@router.get("/me", response_model=UserRead)
def me(user: CurrentUser) -> User:
    return user


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(_: CurrentUser) -> Response:
    # Un JWT no se puede revocar en el servidor: el cliente debe descartarlo.
    # Caduca solo (JWT_EXPIRE_MINUTES). Si hiciera falta invalidarlo al
    # instante habría que guardar sesiones en base de datos.
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/change-password", status_code=status.HTTP_204_NO_CONTENT)
def change_password(
    data: ChangePasswordRequest,
    user: CurrentUser,
    db: Annotated[Session, Depends(get_db)],
) -> Response:
    if not verify_password(data.current_password, user.password_hash):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Contraseña actual incorrecta")
    user.password_hash = hash_password(data.new_password)
    db.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)
