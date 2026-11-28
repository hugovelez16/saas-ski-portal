"""Seccion Membresias de la API v2 de administracion (`/api/v2/admin/companies/{id}/members...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from uuid import UUID

import models
from application.use_cases.company.add_member import AddMemberUseCase
from application.use_cases.company.list_members import ListMembersUseCase
from application.use_cases.company.remove_member import RemoveMemberUseCase
from application.use_cases.company.set_member_role import SetMemberRoleUseCase
from application.use_cases.company.set_member_status import SetMemberStatusUseCase
from fastapi import APIRouter, Depends, HTTPException, Response

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


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
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    detail = await SetMemberStatusUseCase(member_repo, user_repo, audit_log, company_repo).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), is_active=body.is_active
    )
    return schemas.member_out(detail)


@router.put("/companies/{company_id}/members/{user_id}/role", response_model=schemas.MemberOut)
async def set_member_role_admin(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberRoleIn,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    detail = await SetMemberRoleUseCase(member_repo, user_repo, audit_log, company_repo).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), role=body.role
    )
    return schemas.member_out(detail)
