from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import ADMIN_ONLY, AdminUser
from backend.database.errors import unique_violation_constraint
from backend.database.session import get_db
from backend.models.audit_log import AuditAction
from backend.models.user import User, UserRole
from backend.schemas.user_create import UserCreate
from backend.schemas.user_read import UserRead
from backend.schemas.user_update import UserUpdate
from backend.security import hash_password
from backend.service.audit import log_action

# Todo el router es solo para administradores.
router = APIRouter(prefix="/users", tags=["users"], dependencies=[ADMIN_ONLY])

USERNAME_CONSTRAINT = "uq_users_username_lower"


def get_user_or_404(db: Session, user_id: int) -> User:
    user = db.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Usuario no encontrado")
    return user


@router.post("", response_model=UserRead, status_code=status.HTTP_201_CREATED)
def create_user(
    data: UserCreate, db: Annotated[Session, Depends(get_db)], admin: AdminUser
) -> User:
    user = User(
        username=data.username,
        password_hash=hash_password(data.password),
        role=data.role,
    )
    db.add(user)
    try:
        db.flush()
        # Nunca se audita la contraseña: solo quién se creó y con qué rol.
        log_action(
            db,
            admin.id,
            AuditAction.USER_CREATED,
            "user",
            user.id,
            {"username": user.username, "role": user.role},
        )
        db.commit()
    except IntegrityError as exc:
        db.rollback()
        if unique_violation_constraint(exc) == USERNAME_CONSTRAINT:
            raise HTTPException(
                status.HTTP_409_CONFLICT, "Ya existe un usuario con ese nombre"
            ) from exc
        raise
    db.refresh(user)
    return user


@router.get("", response_model=list[UserRead])
def list_users(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[User]:
    stmt = select(User).order_by(User.username, User.id)
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{user_id}", response_model=UserRead)
def get_user(user_id: int, db: Annotated[Session, Depends(get_db)]) -> User:
    return get_user_or_404(db, user_id)


@router.patch("/{user_id}", response_model=UserRead)
def update_user(
    user_id: int,
    data: UserUpdate,
    db: Annotated[Session, Depends(get_db)],
    admin: AdminUser,
) -> User:
    user = get_user_or_404(db, user_id)
    changes = data.model_dump(exclude_unset=True)

    loses_admin = (
        user.role == UserRole.ADMIN
        and user.active
        and (
            changes.get("role", user.role) != UserRole.ADMIN
            or changes.get("active", user.active) is False
        )
    )
    if loses_admin:
        # Se bloquean los administradores activos mientras se cuenta: dos
        # administradores degradándose a la vez no pueden dejar el sistema sin ninguno.
        admins = db.scalars(
            select(User.id)
            .where(User.role == UserRole.ADMIN, User.active)
            .with_for_update()
        ).all()
        if len(admins) <= 1:
            raise HTTPException(
                status.HTTP_409_CONFLICT,
                "No se puede dejar el sistema sin administradores activos",
            )

    password_changed = "password" in changes
    if password_changed:
        user.password_hash = hash_password(changes.pop("password"))
    for field, value in changes.items():
        setattr(user, field, value)
    log_action(
        db,
        admin.id,
        AuditAction.USER_UPDATED,
        "user",
        user.id,
        # Solo se indica QUE se cambió la contraseña, nunca su valor.
        {"fields": sorted(changes), "password_changed": password_changed},
    )
    db.commit()
    db.refresh(user)
    return user
