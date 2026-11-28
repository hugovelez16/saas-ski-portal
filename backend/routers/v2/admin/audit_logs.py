"""Seccion Auditoria de la API v2 de administracion (`/api/v2/admin/audit-logs...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from datetime import datetime
from uuid import UUID

import models
import schemas as legacy_schemas
from database import get_db
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from routers import audit_logs as audit_router
from routers import deps

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


@router.get("/audit-logs", response_model=legacy_schemas.AuditLogPage)
def read_audit_logs_admin(
    company_id: UUID | None = None,
    actor_user_id: UUID | None = None,
    target_user_id: UUID | None = None,
    action: str | None = Query(None, max_length=100),
    from_date: datetime | None = Query(None, alias="from"),
    to_date: datetime | None = Query(None, alias="to"),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0, le=2_147_483_647),
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return audit_router.read_audit_logs(
        company_id=company_id,
        actor_user_id=actor_user_id,
        target_user_id=target_user_id,
        action=action,
        from_date=from_date,
        to_date=to_date,
        limit=limit,
        offset=offset,
        db=db,
        current_user=actor,
    )


@router.get("/audit-logs/actions", response_model=list[str])
def read_audit_actions_admin():
    return audit_router.KNOWN_ACTIONS


@router.get("/audit-logs/purge-preview", response_model=legacy_schemas.AuditLogPurgePreview)
def preview_audit_purge_admin(
    before: datetime = Query(...),
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return audit_router.preview_audit_purge(before=before, db=db, current_user=actor)


@router.post("/audit-logs/purge", response_model=legacy_schemas.AuditLogPurgeResponse)
def purge_audit_logs_admin(
    body: legacy_schemas.AuditLogPurgeRequest,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return audit_router.purge_audit_logs(body=body, db=db, current_user=actor)
