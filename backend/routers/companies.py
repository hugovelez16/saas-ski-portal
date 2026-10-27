import json
from datetime import date
from typing import Literal
from uuid import UUID

import access_policy
import auth
import crud
import models
import schemas
from access_policy import PolicyError
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from fastapi.responses import JSONResponse
from redis_config import redis_manager
from sqlalchemy.orm import Session, joinedload

from routers import deps

router = APIRouter(prefix="/companies", tags=["companies"])

# Valores de `PUT .../status`: los actuales y los heredados. Solo `active`, `approved`, `true` y `1` activan.
MemberStatusValue = Literal["active", "inactive", "approved", "rejected", "true", "false", "1", "0"]
ACTIVE_STATUS_VALUES = frozenset({"active", "approved", "true", "1"})
MSG_COMPANY_NOT_FOUND = "Empresa no encontrada"
MSG_MEMBER_NOT_FOUND = "Member not found"


@router.get("", response_model=list[schemas.CompanyResponse])
def read_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    return db.query(models.Company).offset(skip).limit(limit).all()


@router.post("", response_model=schemas.CompanyResponse)
def create_company(
    company: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    return crud.create_company(db, company, actor_id=current_user.id)


@router.put("/{company_id}", response_model=schemas.CompanyResponse)
def update_company(
    company_id: UUID,
    company: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    updated_company = crud.update_company(db, company_id, company, actor=actor, reason=company.reason)
    if updated_company is None:
        raise HTTPException(status_code=404, detail=MSG_COMPANY_NOT_FOUND)
    return updated_company


@router.delete("/{company_id}", status_code=204)
def delete_company(
    company_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    """
    Platform admin: borra la empresa si no tiene miembros, turnos ni suscripciones. Sin cascadas.
    """
    if not crud.delete_company(db, company_id, actor_id=actor.id):
        raise HTTPException(status_code=404, detail=MSG_COMPANY_NOT_FOUND)
    return Response(status_code=204)


@router.get("/detailed", response_model=None)
def read_companies_detailed(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    # If platform admin (actuando), return all (vista completa)
    if deps.acting_platform_admin(current_user):
        all_companies = db.query(models.Company).options(joinedload(models.Company.members)).all()
        return JSONResponse(
            [schemas.CompanyWithMembers.model_validate(c).model_dump(mode="json", by_alias=True) for c in all_companies]
        )

    # If not admin, check for permissions
    # 1. Supervisor permissions: manager of the company the token points to
    active_cid = deps.canonical_id(getattr(current_user, "active_company_id", None))
    supervisor_memberships = (
        db.query(models.CompanyMember)
        .join(models.Company)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.role.in_([models.CompanyRole.manager, models.CompanyRole.admin]),
            models.CompanyMember.is_active == True,
            models.Company.is_active == True,
        )
        .all()
    )

    allowed_company_ids = {m.company_id for m in supervisor_memberships if active_cid and str(m.company_id) == active_cid}

    if allowed_company_ids:
        companies = (
            db.query(models.Company)
            .options(joinedload(models.Company.members))
            .filter(models.Company.id.in_(allowed_company_ids), models.Company.is_active == True)
            .all()
        )
        own = {m.company_id: m for m in supervisor_memberships}
        payload = []
        for company in companies:
            view = crud.to_reduced_company(crud.company_view_dict(company, own[company.id]))
            view["members"] = company.members
            payload.append(schemas.CompanyReducedWithMembers.model_validate(view).model_dump(mode="json", by_alias=True))
        return JSONResponse(payload)

    raise PolicyError(403, access_policy.MSG_FORBIDDEN)


@router.get("/{company_id}/members", response_model=list[schemas.CompanyMemberResponse])
def read_company_members(
    company_id: UUID,
    status: Literal["active", "inactive"] | None = None,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Get members of a company.
    """
    is_active = None if status is None else status == "active"
    return crud.get_company_members(db, str(company_id), is_active)


@router.put("/{company_id}/members/order", response_model=dict)
def update_members_order(
    company_id: UUID,
    order_data: schemas.UpdateCompanyMembersOrder,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Update the sort order of company members.
    """
    crud.update_company_members_order(db, str(company_id), order_data.user_ids)
    return {"message": "Order updated successfully"}


@router.post("/{company_id}/members/add", response_model=schemas.CompanyMemberResponse)
def add_company_member(
    company_id: UUID,
    member_data: schemas.AddMemberRequest,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    """
    Platform admin: anade un usuario a la empresa por email (alta directa, sin solicitud).
    """
    if crud.get_company(db, company_id) is None:
        raise HTTPException(status_code=404, detail=MSG_COMPANY_NOT_FOUND)

    user_to_add = crud.get_user_by_email(db, member_data.email)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User email not found")

    return crud.add_member(db, company_id, user_to_add.id, actor_id=actor.id)


@router.put("/{company_id}/members/{user_id}/status", response_model=schemas.CompanyMemberResponse)
def update_member_status(
    company_id: UUID,
    user_id: UUID,
    status: MemberStatusValue,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    """
    Platform admin: activa o desactiva la membresia.
    """
    member = crud.set_member_status(
        db, company_id, user_id, status in ACTIVE_STATUS_VALUES, actor_id=actor.id
    )
    if member is None:
        raise HTTPException(status_code=404, detail=MSG_MEMBER_NOT_FOUND)

    return member


@router.put("/{company_id}/members/{user_id}/role", response_model=schemas.CompanyMemberResponse)
def update_member_role(
    company_id: UUID,
    user_id: UUID,
    role_data: schemas.MemberRoleUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    """
    Platform admin: cambia el rol de la membresia (worker o manager).
    """
    member = crud.set_member_role(db, company_id, user_id, role_data.role, actor_id=actor.id)
    if member is None:
        raise HTTPException(status_code=404, detail=MSG_MEMBER_NOT_FOUND)

    return member


@router.delete("/{company_id}/members/{user_id}", response_model=schemas.MemberDeleteResponse)
def delete_company_member(
    company_id: UUID,
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    """
    Platform admin: borra la membresia; si tiene turnos, la desactiva y conserva los turnos.
    """
    result = crud.remove_member(db, company_id, user_id, actor_id=actor.id)
    if result is None:
        raise HTTPException(status_code=404, detail=MSG_MEMBER_NOT_FOUND)

    return result


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


@router.get("/{company_id}", response_model=None)
def read_company(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company("worker")),
    db: Session = Depends(get_db),
):
    """Vista completa para el PA actuando; reducida para manager, worker y PA en 'ver como'."""
    if ctx.company is None:
        raise PolicyError(403, access_policy.MSG_NO_ACCESS)
    member = crud.get_company_member(db, ctx.user.id, company_id)
    view = crud.company_view_dict(ctx.company, member, role=ctx.role)
    return JSONResponse(crud.serialize_company_view(view, full=ctx.is_platform_admin))


@router.get("/{company_id}/rates-v2", response_model=list[schemas.CompanyMemberResponse])
def read_company_rates(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
    db: Session = Depends(get_db),
):
    return crud.get_company_rates(db, str(company_id))


@router.put("/{company_id}/members/{user_id}/rates", response_model=schemas.CompanyMemberResponse)
def update_member_rates(
    company_id: UUID,
    user_id: UUID,
    rates_data: schemas.MemberRatesUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
    ctx: deps.AccessContext = Depends(deps.require_company("worker")),
):
    """
    Edita las tarifas de una membresia. Gestor o PA: cualquier miembro. Trabajador: solo las suyas
    y solo en empresas autonomas.
    """
    access_policy.can_edit_member_rates(
        role=ctx.role, is_managed=ctx.is_managed, is_self=user_id == current_user.id
    )
    if ctx.company is None:
        raise HTTPException(status_code=404, detail=MSG_COMPANY_NOT_FOUND)
    definitions = ctx.company.worklog_definitions or {}
    # Solo se exige definicion a los tipos nuevos: los ya presentes en la tarifa del miembro se conservan
    # aunque el tipo se haya retirado de la empresa.
    member = crud.get_company_member(db, user_id, company_id)
    existing = set((member.rates_config or {}).keys()) if member is not None else set()
    new_shift_types = [shift_type for shift_type in rates_data.rates_config.root if shift_type not in existing]
    if any(shift_type not in definitions for shift_type in new_shift_types):
        raise HTTPException(status_code=422, detail="Tipo de turno desconocido")
    # Se guarda lo que envio el cliente, ya validado y en JSON plano; las lecturas aplican los defaults.
    rates_config = rates_data.rates_config.model_dump(mode="json", exclude_unset=True)
    member = crud.set_member_rates(db, company_id, user_id, rates_config, actor_id=current_user.id)
    if member is None:
        raise HTTPException(status_code=404, detail=MSG_MEMBER_NOT_FOUND)
    return member


@router.put("/{company_id}/members/{user_id}/settings", response_model=schemas.CompanyMemberResponse)
def update_member_settings(
    company_id: UUID,
    user_id: UUID,
    settings_data: schemas.MemberSettingsUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
    ctx: deps.AccessContext = Depends(deps.require_company("worker")),
):
    """
    Edita los ajustes de una membresia. Gestor o PA: cualquier miembro. Trabajador: solo los suyos.
    """
    access_policy.can_edit_member_settings(role=ctx.role, is_self=user_id == current_user.id)
    member = crud.set_member_settings(db, company_id, user_id, settings_data.settings)
    if member is None:
        raise HTTPException(status_code=404, detail=MSG_MEMBER_NOT_FOUND)
    return member


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
