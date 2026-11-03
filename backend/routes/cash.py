from datetime import date, datetime
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from backend.auth import ADMIN_ONLY, AUTHENTICATED, CurrentUser
from backend.database.session import get_db
from backend.models.cash_session import CashSession, CashSessionStatus
from backend.schemas.cash_schemas import (
    CashClose,
    CashOpen,
    CashSessionDetail,
    DailySummaryRead,
)
from backend.service.cash import (
    BUSINESS_TZ,
    CashError,
    CashSessionAlreadyOpenError,
    close_session,
    daily_summary,
    expected_cash,
    open_session,
)

router = APIRouter(prefix="/cash", tags=["cash"])


def detail(db: Session, session: CashSession) -> CashSessionDetail:
    current = (
        session.expected_amount
        if session.status == CashSessionStatus.CLOSED
        else expected_cash(db, session)
    )
    difference = (
        session.closing_amount - session.expected_amount
        if session.status == CashSessionStatus.CLOSED
        else None
    )
    return CashSessionDetail.model_validate(
        {
            **{
                c: getattr(session, c)
                for c in CashSessionDetail.model_fields
                if c not in ("current_expected", "difference")
            },
            "current_expected": current,
            "difference": difference,
        }
    )


@router.post(
    "/open",
    dependencies=[AUTHENTICATED],
    response_model=CashSessionDetail,
    status_code=status.HTTP_201_CREATED,
)
def open_cash(
    data: CashOpen, db: Annotated[Session, Depends(get_db)], user: CurrentUser
) -> CashSessionDetail:
    try:
        session = open_session(db, user.id, data.opening_amount)
        db.commit()
    except CashSessionAlreadyOpenError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    except IntegrityError as exc:
        # Dos aperturas simultáneas: el índice único parcial deja pasar solo una.
        db.rollback()
        raise HTTPException(
            status.HTTP_409_CONFLICT, "Ya hay una caja abierta"
        ) from exc
    db.refresh(session)
    return detail(db, session)


@router.post("/close", dependencies=[AUTHENTICATED], response_model=CashSessionDetail)
def close_cash(
    data: CashClose, db: Annotated[Session, Depends(get_db)]
) -> CashSessionDetail:
    try:
        session = close_session(db, data.closing_amount)
        db.commit()
    except CashError as exc:
        db.rollback()
        raise HTTPException(status.HTTP_409_CONFLICT, str(exc)) from exc
    db.refresh(session)
    return detail(db, session)


@router.get("/current", dependencies=[AUTHENTICATED], response_model=CashSessionDetail)
def current_cash(db: Annotated[Session, Depends(get_db)]) -> CashSessionDetail:
    session = db.scalar(
        select(CashSession).where(CashSession.status == CashSessionStatus.OPEN)
    )
    if session is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No hay caja abierta")
    return detail(db, session)


@router.get(
    "/daily-summary", dependencies=[ADMIN_ONLY], response_model=DailySummaryRead
)
def get_daily_summary(
    db: Annotated[Session, Depends(get_db)],
    day: Annotated[date | None, Query(alias="date")] = None,
) -> dict:
    # Por defecto, hoy en la hora local del negocio (no la del servidor).
    return daily_summary(db, day or datetime.now(BUSINESS_TZ).date())
