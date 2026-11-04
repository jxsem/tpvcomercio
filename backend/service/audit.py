import json
from typing import Any

from sqlalchemy.orm import Session

from backend.models.audit_log import AuditAction, AuditLog

# Claves que jamás deben llegar a la auditoría (el md prohíbe registrar secretos).
FORBIDDEN_KEYS = {"password", "password_hash", "token"}


def to_json_safe(values: dict[str, Any]) -> dict[str, Any]:
    """Convierte a tipos JSON sin pasar los Decimal por float.

    jsonable_encoder de FastAPI convierte Decimal("1.20") en 1.2 (float): se
    pierde la precisión y el formato. Con default=str el importe queda "1.20".
    """
    return json.loads(json.dumps(values, default=str))


def log_action(
    db: Session,
    user_id: int | None,
    action: AuditAction,
    entity: str,
    entity_id: int | None,
    details: dict[str, Any] | None = None,
) -> AuditLog:
    """Añade un registro de auditoría a la transacción en curso.

    No hace commit: el registro se confirma o se deshace junto con la operación
    auditada, así nunca hay una acción sin rastro ni un rastro de algo que no ocurrió.
    """
    if details is not None:
        details = {k: v for k, v in details.items() if k not in FORBIDDEN_KEYS}
    entry = AuditLog(
        user_id=user_id,
        action=action,
        entity=entity,
        entity_id=entity_id,
        details=details,
    )
    db.add(entry)
    return entry
