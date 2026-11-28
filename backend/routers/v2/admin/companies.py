"""Seccion Empresas de la API v2 de administracion (`/api/v2/admin/companies...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from typing import Literal
from uuid import UUID

import models
from application.use_cases.company.create_company import CreateCompanyUseCase
from application.use_cases.company.delete_company import DeleteCompanyUseCase
from application.use_cases.company.get_worklog_definition_usage import GetWorklogDefinitionUsageUseCase
from application.use_cases.company.list_companies import ListCompaniesUseCase
from application.use_cases.company.update_company import UpdateCompanyUseCase
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


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
        platform_settings=body.platform_settings.model_dump(mode="json") if body.platform_settings is not None else None,
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


@router.get(
    "/companies/{company_id}/worklog-definitions/usage",
    response_model=dict[str, schemas.WorklogDefinitionUsageOut],
)
async def read_worklog_definition_usage_admin(
    company_id: UUID,
    company_repo=Depends(v2_deps.get_company_repository),
):
    usage = await GetWorklogDefinitionUsageUseCase(company_repo).execute(company_id=str(company_id))
    return {k: schemas.WorklogDefinitionUsageOut(**v) for k, v in usage.items()}
