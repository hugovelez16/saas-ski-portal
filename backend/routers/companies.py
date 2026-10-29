import json
from datetime import date
from uuid import UUID

import access_policy
import crud
import schemas
from access_policy import PolicyError
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import JSONResponse
from redis_config import redis_manager
from sqlalchemy.orm import Session

from routers import deps

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get(
    "/{company_id}/daily-report",
    response_model=None,
    responses={200: {"model": schemas.DailyReportFullResponse | schemas.DailyReportWorkerResponse}},
)
def read_daily_report(
    company_id: UUID,
    day: date | None = Query(None, alias="date"),
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_WORKER, module="worker_daily_report")),
):
    """
    Parte diario de la empresa: miembros activos y turnos del dia de toda la empresa.
    Manager y platform admin reciben importes; el worker (incluido el PA en "ver como" worker) recibe
    un esquema distinto en el que las claves de importe no existen [P-14].
    """
    day = day or date.today()
    company = ctx.company
    if company is None:
        raise PolicyError(403, access_policy.MSG_NO_ACCESS)

    logs = crud.get_daily_report_logs(db=ctx.db, company_id=ctx.company_id, day=day)
    log_user_ids = {log.user_id for log in logs}
    members = [
        {
            "user_id": m.user_id,
            "first_name": m.user.first_name if m.user else None,
            "last_name": m.user.last_name if m.user else None,
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            "is_active": bool(m.is_active),
            "sort_order": m.sort_order if m.sort_order is not None else 1000,
        }
        for m in company.members
        if m.is_active or m.user_id in log_user_ids
    ]
    work_types = {
        code: {**definition, "label": str(definition.get("label", code)), "unit": str(definition.get("unit", "hours"))}
        for code, definition in (company.worklog_definitions or {}).items()
        if isinstance(definition, dict)
    }
    payload = {"company_id": company.id, "date": day, "members": members, "work_types": work_types}

    if ctx.role in (access_policy.ROLE_MANAGER, access_policy.ROLE_PLATFORM_ADMIN):
        body = schemas.DailyReportFullResponse(
            **payload, logs=[schemas.DailyReportLogFull.model_validate(log) for log in logs]
        )
    else:
        body = schemas.DailyReportWorkerResponse(
            **payload, logs=[schemas.DailyReportLogWorker.model_validate(log) for log in logs]
        )
    return JSONResponse(content=body.model_dump(mode="json", by_alias=True))


@router.get("/{company_id}/dashboard-summary", response_model=schemas.DashboardSummaryResponse)
def get_company_dashboard_summary(
    company_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Retorna el resumen analitico y operativo para el dashboard de gestores,
    integrando cache en Redis y agregacion optimizada.
    """
    cid = str(company_id)

    # Redis Cache Key
    cache_key = f"dashboard_summary:{cid}:{start_date or ''}:{end_date or ''}"
    # T11: un fallo de Redis o una cache ilegible nunca rompen el dashboard
    try:
        cached_data = redis_manager.get(cache_key)
        if cached_data:
            return schemas.DashboardSummaryResponse(**json.loads(cached_data))
    except Exception:
        pass

    try:
        summary = schemas.DashboardSummaryResponse(
            **crud.get_dashboard_summary(db=db, company_id=cid, start_date=start_date, end_date=end_date)
        )
        try:
            redis_manager.set(cache_key, json.dumps(summary.model_dump(mode="json", by_alias=True)), ex=300)
        except Exception:
            pass

        return summary
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
