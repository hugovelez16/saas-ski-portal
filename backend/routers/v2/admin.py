"""API v2 de administracion de plataforma (`/api/v2/admin/...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from datetime import datetime
from typing import Literal
from uuid import UUID

import crud
import models
import schemas as legacy_schemas
from application.use_cases.company.add_member import AddMemberUseCase
from application.use_cases.company.create_company import CreateCompanyUseCase
from application.use_cases.company.delete_company import DeleteCompanyUseCase
from application.use_cases.company.list_companies import ListCompaniesUseCase
from application.use_cases.company.list_members import ListMembersUseCase
from application.use_cases.company.list_user_companies import ListUserCompaniesUseCase
from application.use_cases.company.remove_member import RemoveMemberUseCase
from application.use_cases.company.set_member_role import SetMemberRoleUseCase
from application.use_cases.company.set_member_status import SetMemberStatusUseCase
from application.use_cases.company.update_company import UpdateCompanyUseCase
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from sqlalchemy.orm import Session, joinedload

from routers import audit_logs as audit_router
from routers import auth as auth_router
from routers import deps
from routers import modules as modules_router
from routers import users as users_router
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


# --- Empresas ---


@router.get("/companies")
async def list_companies_admin(
    include: Literal["members"] | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    items, total = await ListCompaniesUseCase(company_repo, member_repo, user_repo).execute(
        skip=skip, limit=limit, include_members=include == "members"
    )
    if include == "members":
        payload = [schemas.company_full_with_members(item) for item in items]
    else:
        payload = [schemas.company_full(item.company) for item in items]
    return {"items": [item.model_dump(mode="json") for item in payload], "total": total}


@router.post("/companies", status_code=201, response_model=schemas.CompanyFull)
async def create_company_admin(
    body: schemas.CompanyCreateV2,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    company = await CreateCompanyUseCase(company_repo, audit_log).execute(
        actor_id=str(actor.id),
        name=body.name,
        tax_config=body.tax_config.as_dict(),
        worklog_definitions=body.worklog_definitions.model_dump(mode="json"),
        settings=body.settings.model_dump(mode="json") if body.settings is not None else None,
        is_active=body.is_active,
        is_managed=body.is_managed,
    )
    return schemas.company_full(company)


@router.get("/companies/{company_id}", response_model=schemas.CompanyFull)
async def read_company_admin(
    company_id: UUID,
    company_repo=Depends(v2_deps.get_company_repository),
):
    company = await company_repo.get_by_id(str(company_id))
    if company is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    return schemas.company_full(company)


@router.put("/companies/{company_id}", response_model=schemas.CompanyFull)
async def update_company_admin(
    company_id: UUID,
    body: schemas.CompanyUpdateV2,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    changes = body.model_dump(exclude_unset=True, mode="json", exclude={"reason"})
    company = await UpdateCompanyUseCase(company_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), changes=changes, reason=body.reason
    )
    return schemas.company_full(company)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company_admin(
    company_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    await DeleteCompanyUseCase(company_repo, audit_log).execute(actor_id=str(actor.id), company_id=str(company_id))
    return Response(status_code=204)


# --- Membresias ---


@router.get("/companies/{company_id}/members", response_model=list[schemas.MemberOut])
async def list_members_admin(
    company_id: UUID,
    is_active: bool | None = None,
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    if await company_repo.get_by_id(str(company_id)) is None:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")
    details = await ListMembersUseCase(member_repo, user_repo).execute(company_id=str(company_id), is_active=is_active)
    return [schemas.member_out(detail) for detail in details]


@router.post("/companies/{company_id}/members", response_model=schemas.MemberOut, status_code=201)
async def add_member_admin(
    company_id: UUID,
    body: schemas.MemberAddIn,
    response: Response,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    result = await AddMemberUseCase(company_repo, member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), email=body.email
    )
    if not result.created:
        response.status_code = 200
    return schemas.member_out(result.detail)


@router.delete("/companies/{company_id}/members/{user_id}", response_model=schemas.MemberDeleteOut)
async def remove_member_admin(
    company_id: UUID,
    user_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    result = await RemoveMemberUseCase(member_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id)
    )
    return schemas.MemberDeleteOut(deleted=result.deleted, deactivated=result.deactivated, reason=result.reason)


@router.put("/companies/{company_id}/members/{user_id}/status", response_model=schemas.MemberOut)
async def set_member_status_admin(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberStatusIn,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    detail = await SetMemberStatusUseCase(member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), is_active=body.is_active
    )
    return schemas.member_out(detail)


@router.put("/companies/{company_id}/members/{user_id}/role", response_model=schemas.MemberOut)
async def set_member_role_admin(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberRoleIn,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    detail = await SetMemberRoleUseCase(member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), role=body.role
    )
    return schemas.member_out(detail)


# --- Usuarios y suplantacion ---


@router.get("/users", response_model=list[legacy_schemas.UserResponse])
def list_users_admin(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@router.post("/users", response_model=legacy_schemas.UserResponse)
async def create_user_admin_route(
    user: legacy_schemas.UserCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return await users_router.create_user_admin(user=user, db=db, current_user=actor)


@router.get("/users/{user_id}", response_model=legacy_schemas.UserResponse)
def read_user_admin(user_id: UUID, db: Session = Depends(get_db)):
    user = crud.get_user(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=legacy_schemas.UserResponse)
def update_user_admin_route(
    user_id: UUID,
    user: legacy_schemas.UserUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.update_user(user_id=user_id, user=user, db=db, current_user=actor)


@router.put("/users/{user_id}/status")
def toggle_user_status_admin_route(
    user_id: UUID,
    is_active: bool,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.toggle_user_status(user_id=user_id, is_active=is_active, db=db, current_user=actor)


@router.post("/users/{user_id}/reset-password-email")
async def reset_password_email_admin_route(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return await users_router.reset_password_via_email(user_id=user_id, db=db, current_user=actor)


@router.post("/users/{user_id}/reset-2fa")
def reset_2fa_admin_route(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.reset_user_2fa(user_id=user_id, db=db, current_user=actor)


@router.get("/users/{user_id}/companies", response_model=list[schemas.CompanyFullWithMembership])
async def read_user_companies_admin(
    user_id: UUID,
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
):
    views = await ListUserCompaniesUseCase(company_repo, member_repo).execute(
        user_id=str(user_id), include_inactive=True
    )
    return [schemas.company_full_with_membership(view) for view in views]


@router.post("/impersonate/{user_id}", response_model=legacy_schemas.Token)
async def impersonate_user_admin(
    user_id: UUID,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return auth_router.execute_impersonate_user(
        user_id=user_id, response=response, request=request, db=db, current_user=actor
    )


# --- Modulos y suscripciones ---


@router.get("/modules", response_model=list[legacy_schemas.AppModuleResponse])
def list_modules_admin(include_inactive: bool = True, db: Session = Depends(get_db)):
    return crud.get_modules(db, include_inactive=include_inactive)


@router.post("/modules", response_model=legacy_schemas.AppModuleResponse)
def create_module_admin(
    data: legacy_schemas.AppModuleCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.create_module(data=data, db=db, current_user=actor)


@router.get("/modules/subscriptions", response_model=list[legacy_schemas.ModuleSubscriptionResponse])
def list_subscriptions_admin(
    company_id: str | None = None,
    user_id: str | None = None,
    module_id: str | None = None,
    db: Session = Depends(get_db),
):
    return (
        db.query(models.ModuleSubscription)
        .options(
            joinedload(models.ModuleSubscription.module),
            joinedload(models.ModuleSubscription.company),
            joinedload(models.ModuleSubscription.user),
        )
        .filter(
            (models.ModuleSubscription.company_id == company_id) if company_id else True,
            (models.ModuleSubscription.user_id == user_id) if user_id else True,
            (models.ModuleSubscription.module_id == module_id) if module_id else True,
        )
        .order_by(models.ModuleSubscription.created_at.desc())
        .all()
    )


@router.post("/modules/subscriptions", response_model=legacy_schemas.ModuleSubscriptionResponse)
def create_subscription_admin(
    data: legacy_schemas.ModuleSubscriptionCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.create_subscription(data=data, db=db, current_user=actor)


@router.put("/modules/subscriptions/{sub_id}", response_model=legacy_schemas.ModuleSubscriptionResponse)
def update_subscription_admin(
    sub_id: str,
    data: legacy_schemas.ModuleSubscriptionUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.update_subscription(sub_id=sub_id, data=data, db=db, current_user=actor)


@router.delete("/modules/subscriptions/{sub_id}")
def delete_subscription_admin(
    sub_id: str,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.delete_subscription(sub_id=sub_id, db=db, current_user=actor)


@router.get("/modules/{module_id}", response_model=legacy_schemas.AppModuleResponse)
def get_module_admin(
    module_id: str,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.get_module(module_id=module_id, db=db, current_user=actor)


@router.put("/modules/{module_id}", response_model=legacy_schemas.AppModuleResponse)
def update_module_admin(
    module_id: str,
    data: legacy_schemas.AppModuleUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.update_module(module_id=module_id, data=data, db=db, current_user=actor)


# --- Auditoria ---


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
