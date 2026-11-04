from datetime import datetime, timezone
from uuid import UUID

import audit
import crud
import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from routers import deps

router = APIRouter(prefix="/audit-logs", tags=["audit-logs"])

# Acciones que aun aparecen en eventos antiguos o se escriben fuera de AuditAction.
LEGACY_ACTIONS = ("2fa_reset", "create_work_log", "create_work_log_bulk", "update_work_log", "delete_work_log")
KNOWN_ACTIONS = sorted(
    {v for k, v in vars(audit.AuditAction).items() if k.isupper() and isinstance(v, str)} | set(LEGACY_ACTIONS)
)


def _to_naive_utc(value: datetime | None) -> datetime | None:
    """`created_at` es naive en UTC: las fechas con zona horaria se convierten a UTC y se les quita."""
    if value is not None and value.tzinfo is not None:
        return value.astimezone(timezone.utc).replace(tzinfo=None)
    return value


@router.get("", response_model=schemas.AuditLogPage)
def read_audit_logs(
    company_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    action: str | None = Query(None, max_length=100),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=2_147_483_647),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    from_date = _to_naive_utc(from_date)
    to_date = _to_naive_utc(to_date)
    if from_date is not None and to_date is not None and from_date > to_date:
        raise HTTPException(status_code=422, detail="'from' no puede ser posterior a 'to'")

    total, rows = crud.get_audit_logs(
        db,
        company_id=company_id,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
    )

    actor_ids = {row.actor_user_id for row in rows if row.actor_user_id is not None}
    emails: dict = {}
    if actor_ids:
        emails = dict(db.query(models.User.id, models.User.email).filter(models.User.id.in_(actor_ids)).all())

    items = [
        schemas.AuditLogItem(
            id=row.id,
            action=row.action,
            created_at=row.created_at,
            actor_user_id=row.actor_user_id,
            actor_email=emails.get(row.actor_user_id) if row.actor_user_id is not None else None,
            company_id=row.company_id,
            target_user_id=row.target_user_id,
            old_value=row.old_value,
            new_value=row.new_value,
            reason=row.reason,
            extra_data=row.extra_data,
        )
        for row in rows
    ]
    return schemas.AuditLogPage(total=total, items=items)


@router.get("/actions", response_model=list[str])
def read_audit_actions(
    current_user: models.User = Depends(deps.require_platform_admin),
):
    return KNOWN_ACTIONS
