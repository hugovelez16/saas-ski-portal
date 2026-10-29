"""API v2: empresa y vistas. Autorizacion en los routers (`routers.deps`, `access_policy`); logica en casos de uso."""

from typing import Literal
from uuid import UUID

import access_policy
import models
from access_policy import PolicyError
from application.use_cases.company.create_company import CreateCompanyUseCase
from application.use_cases.company.delete_company import DeleteCompanyUseCase
from application.use_cases.company.get_company import GetCompanyUseCase
from application.use_cases.company.list_companies import ListCompaniesUseCase
from application.use_cases.company.list_my_companies import ListMyCompaniesUseCase
from application.use_cases.company.list_user_companies import ListUserCompaniesUseCase
from application.use_cases.company.update_company import UpdateCompanyUseCase
from auth import get_verified_user
from database import get_db
from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.orm import Session

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(tags=["v2-companies"])


@router.get("/companies")
async def list_companies(
    include: Literal["members"] | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    """Solo PA actuando. `include=members` anade los miembros de cada empresa."""
    items, total = await ListCompaniesUseCase(company_repo, member_repo, user_repo).execute(
        skip=skip, limit=limit, include_members=include == "members"
    )
    if include == "members":
        payload = [schemas.company_full_with_members(item) for item in items]
    else:
        payload = [schemas.company_full(item.company) for item in items]
    return {"items": [item.model_dump(mode="json") for item in payload], "total": total}


@router.post("/companies", status_code=201, response_model=schemas.CompanyFull)
async def create_company(
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


@router.get("/me/companies")
async def read_my_companies(
    current_user: models.User = Depends(get_verified_user),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
):
    """PA actuando: todas las empresas (vista completa). Resto: sus membresias activas (vista reducida)."""
    acting = deps.acting_platform_admin(current_user)
    views = await ListMyCompaniesUseCase(company_repo, member_repo).execute(
        user_id=str(current_user.id), as_platform_admin=acting
    )
    if acting:
        return [schemas.company_full(view.company).model_dump(mode="json") for view in views]
    return [schemas.company_reduced(view).model_dump(mode="json") for view in views]


@router.get("/users/{user_id}/companies")
async def read_user_companies(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_verified_user),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
):
    """PA actuando: todas las empresas del usuario (vista completa con su membresia). Manager: solo la del token (vista reducida)."""
    use_case = ListUserCompaniesUseCase(company_repo, member_repo)
    if deps.acting_platform_admin(current_user):
        views = await use_case.execute(user_id=str(user_id), include_inactive=True)
        return [schemas.company_full_with_membership(view).model_dump(mode="json") for view in views]
    allowed = deps.manager_company_ids(db, current_user)
    if not allowed:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)
    views = await use_case.execute(user_id=str(user_id), include_inactive=False, allowed_company_ids=allowed)
    return [schemas.company_reduced(view).model_dump(mode="json") for view in views]


@router.get("/companies/{company_id}", response_model=None)
async def read_company(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_WORKER)),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
):
    """Vista completa para el PA actuando; reducida para manager, worker y PA en "ver como"."""
    view = await GetCompanyUseCase(company_repo, member_repo).execute(
        company_id=str(company_id), user_id=str(ctx.user.id), role=ctx.role
    )
    if ctx.is_platform_admin:
        return schemas.company_full(view.company)
    return schemas.company_reduced(view)


@router.put("/companies/{company_id}", response_model=schemas.CompanyFull)
async def update_company(
    company_id: UUID,
    body: schemas.CompanyUpdateV2,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    # mode="json": valores JSON-compatibles para la columna JSONB. `reason` es solo para auditoria.
    changes = body.model_dump(exclude_unset=True, mode="json", exclude={"reason"})
    company = await UpdateCompanyUseCase(company_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), changes=changes, reason=body.reason
    )
    return schemas.company_full(company)


@router.delete("/companies/{company_id}", status_code=204)
async def delete_company(
    company_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Borra la empresa si no tiene miembros, turnos ni suscripciones. Sin cascadas."""
    await DeleteCompanyUseCase(company_repo, audit_log).execute(actor_id=str(actor.id), company_id=str(company_id))
    return Response(status_code=204)
