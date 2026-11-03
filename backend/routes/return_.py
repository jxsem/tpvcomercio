from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.auth import ADMIN_ONLY, AUTHENTICATED, CurrentUser
from backend.database.session import get_db
from backend.models.sale_return import Return
from backend.schemas.return_create import ReturnCreate
from backend.schemas.return_read import ReturnRead
from backend.service.return_ import (
    ExceedsSoldQuantityError,
    InvalidReturnItemError,
    ReturnError,
    ReturnNotAllowedError,
    SaleNotFoundError,
    create_return,
)

router = APIRouter(prefix="/returns", tags=["returns"])


@router.post("", response_model=ReturnRead, status_code=status.HTTP_201_CREATED)
def create_return_route(
    data: ReturnCreate, db: Annotated[Session, Depends(get_db)], user: CurrentUser
) -> Return:
    try:
        ret = create_return(db, data, user_id=user.id)
        db.commit()
    except SaleNotFoundError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_404_NOT_FOUND, str(exc)) from exc
    except InvalidReturnItemError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_422_UNPROCESSABLE_CONTENT, str(exc)) from exc
    except (ExceedsSoldQuantityError, ReturnNotAllowedError) as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except ReturnError as exc:  # cualquier otro error de negocio
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except Exception:
        db.rollback()
        raise
    db.refresh(ret)
    return ret


@router.get("", dependencies=[ADMIN_ONLY], response_model=list[ReturnRead])
def list_returns(
    db: Annotated[Session, Depends(get_db)],
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Return]:
    stmt = (
        select(Return)
        .options(selectinload(Return.items))
        .order_by(Return.created_at.desc(), Return.id.desc())
    )
    return list(db.scalars(stmt.limit(limit).offset(offset)))


@router.get("/{return_id}", dependencies=[AUTHENTICATED], response_model=ReturnRead)
def get_return(return_id: int, db: Annotated[Session, Depends(get_db)]) -> Return:
    ret = db.scalar(
        select(Return).options(selectinload(Return.items)).where(Return.id == return_id)
    )
    if ret is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Devolución no encontrada")
    return ret
