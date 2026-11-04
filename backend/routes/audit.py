from typing import Annotated

from fastapi import APIRouter, Depends, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.auth import ADMIN_ONLY
from backend.database.session import get_db
from backend.models.audit_log import AuditAction, AuditLog
from backend.schemas.audit_log_read import AuditLogRead

router = APIRouter(prefix="/audit-logs", tags=["audit"], dependencies=[ADMIN_ONLY])


@router.get("", response_model=list[AuditLogRead])
def list_audit_logs(
    db: Annotated[Session, Depends(get_db)],
    # Enum: ?action=FOO da 422 sin llegar a la base de datos.
    action: AuditAction | None = None,
    entity: Annotated[str | None, Query(max_length=50)] = None,
    entity_id: int | None = None,
    user_id: int | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 50,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[AuditLog]:
    # id como desempate: mismo motivo que en /stock/movements.
    stmt = select(AuditLog).order_by(AuditLog.created_at.desc(), AuditLog.id.desc())
    if action is not None:
        stmt = stmt.where(AuditLog.action == action)
    if entity is not None:
        stmt = stmt.where(AuditLog.entity == entity)
    if entity_id is not None:
        stmt = stmt.where(AuditLog.entity_id == entity_id)
    if user_id is not None:
        stmt = stmt.where(AuditLog.user_id == user_id)
    return list(db.scalars(stmt.limit(limit).offset(offset)))
