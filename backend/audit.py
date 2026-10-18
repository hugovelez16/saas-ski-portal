"""Helper de registro de auditoria.

Centraliza la creacion de entradas en `audit_logs` para que todos los escritores
usen los mismos nombres de accion y el mismo formato de valores.
"""

import json
from typing import Any

import models
from sqlalchemy.orm import Session

REASON_MAX_LENGTH = 500


class AuditAction:
    """Nombres de accion permitidos en el registro de auditoria."""

    COMPANY_CREATED = "company.created"
    COMPANY_UPDATED = "company.updated"
    COMPANY_SUSPENDED = "company.suspended"
    COMPANY_REACTIVATED = "company.reactivated"
    COMPANY_MANAGED_CHANGED = "company.managed_changed"
    COMPANY_DELETED = "company.deleted"
    COMPANY_TAX_CONFIG_CHANGED = "company.tax_config_changed"
    COMPANY_SETTINGS_CHANGED = "company.settings_changed"
    COMPANY_DEFINITIONS_CHANGED = "company.worklog_definitions_changed"
    MEMBER_ADDED = "member.added"
    MEMBER_DEACTIVATED = "member.deactivated"
    MEMBER_REACTIVATED = "member.reactivated"
    MEMBER_REMOVED = "member.removed"
    MEMBER_ROLE_CHANGED = "member.role_changed"
    MEMBER_RATES_CHANGED = "member.rates_changed"
    USER_STATUS_CHANGED = "user.status_changed"


def _to_json_safe(value: Any) -> Any:
    """Convierte un valor a estructura JSON (UUID, fechas y similares pasan a string)."""
    if value is None:
        return None
    return json.loads(json.dumps(value, default=str))


def record_audit(
    db: Session,
    *,
    action: str,
    actor_id,
    company_id=None,
    target_user_id=None,
    old_value: dict | None = None,
    new_value: dict | None = None,
    reason: str | None = None,
    extra: dict | None = None,
) -> models.AuditLog:
    """Anade una entrada de auditoria a la sesion SIN hacer commit.

    El llamador es responsable de confirmar la transaccion junto con la operacion
    auditada, de forma que la entrada y el cambio se persistan o se descarten juntos.
    Los valores no serializables (UUID, fechas) se convierten a string.
    `admin_user_id` se rellena con `actor_id` por compatibilidad con el esquema previo.
    """
    row = models.AuditLog(
        action=action,
        actor_user_id=actor_id,
        admin_user_id=actor_id,
        company_id=company_id,
        target_user_id=target_user_id,
        old_value=_to_json_safe(old_value),
        new_value=_to_json_safe(new_value),
        reason=reason[:REASON_MAX_LENGTH] if reason is not None else None,
        extra_data=_to_json_safe(extra) if extra is not None else {},
    )
    db.add(row)
    return row
