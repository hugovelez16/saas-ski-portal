"""API v2: membresias y tarifas. Autorizacion en el router (`routers.deps`, `access_policy`); logica en casos de uso."""

from uuid import UUID

import access_policy
import models
from application.use_cases.company.add_member import AddMemberUseCase
from application.use_cases.company.list_members import ListMembersUseCase
from application.use_cases.company.list_rates import ListRatesUseCase
from application.use_cases.company.remove_member import RemoveMemberUseCase
from application.use_cases.company.reorder_members import ReorderMembersUseCase
from application.use_cases.company.set_member_rates import SetMemberRatesUseCase
from application.use_cases.company.set_member_role import SetMemberRoleUseCase
from application.use_cases.company.set_member_settings import SetMemberSettingsUseCase
from application.use_cases.company.set_member_status import SetMemberStatusUseCase
from fastapi import APIRouter, Depends, Response

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(tags=["v2-members"])

MSG_ORDER_UPDATED = "Order updated successfully"


@router.get("/companies/{company_id}/members", response_model=list[schemas.MemberOut])
async def list_members(
    company_id: UUID,
    is_active: bool | None = None,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    details = await ListMembersUseCase(member_repo, user_repo).execute(company_id=str(company_id), is_active=is_active)
    return [schemas.member_out(detail) for detail in details]


@router.post("/companies/{company_id}/members", response_model=schemas.MemberOut, status_code=201)
async def add_member(
    company_id: UUID,
    body: schemas.MemberAddIn,
    response: Response,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Solo PA. 201 si crea la membresia; 200 si ya existia (reactivada o ya activa)."""
    result = await AddMemberUseCase(company_repo, member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), email=body.email
    )
    if not result.created:
        response.status_code = 200
    return schemas.member_out(result.detail)


@router.put("/companies/{company_id}/members/order")
async def reorder_members(
    company_id: UUID,
    body: schemas.MemberOrderIn,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    member_repo=Depends(v2_deps.get_member_repository),
):
    await ReorderMembersUseCase(member_repo).execute(
        company_id=str(company_id), user_ids=[str(user_id) for user_id in body.user_ids]
    )
    return {"message": MSG_ORDER_UPDATED}


@router.delete("/companies/{company_id}/members/{user_id}", response_model=schemas.MemberDeleteOut)
async def remove_member(
    company_id: UUID,
    user_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Solo PA. Sin turnos borra la membresia; con turnos la desactiva y conserva los turnos."""
    result = await RemoveMemberUseCase(member_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id)
    )
    return schemas.MemberDeleteOut(deleted=result.deleted, deactivated=result.deactivated, reason=result.reason)


@router.put("/companies/{company_id}/members/{user_id}/status", response_model=schemas.MemberOut)
async def set_member_status(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberStatusIn,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Solo PA. Reactivar fuerza el rol `worker`."""
    detail = await SetMemberStatusUseCase(member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), is_active=body.is_active
    )
    return schemas.member_out(detail)


@router.put("/companies/{company_id}/members/{user_id}/role", response_model=schemas.MemberOut)
async def set_member_role(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberRoleIn,
    actor: models.User = Depends(deps.require_platform_admin),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Solo PA. Sin guardia de ultimo manager (E7)."""
    detail = await SetMemberRoleUseCase(member_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), user_id=str(user_id), role=body.role
    )
    return schemas.member_out(detail)


@router.put("/companies/{company_id}/members/{user_id}/rates", response_model=schemas.MemberOut)
async def set_member_rates(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberRatesIn,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_WORKER)),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Gestor o PA: cualquier miembro. Trabajador: solo las suyas y solo en empresas autonomas."""
    access_policy.can_edit_member_rates(role=ctx.role, is_managed=ctx.is_managed, is_self=user_id == ctx.user.id)
    # Se guarda lo que envio el cliente, ya validado y en JSON plano; las lecturas aplican los defaults.
    rates_config = body.rates_config.model_dump(mode="json", exclude_unset=True)
    detail = await SetMemberRatesUseCase(company_repo, member_repo, user_repo, audit_log).execute(
        actor_id=str(ctx.user.id), company_id=str(company_id), user_id=str(user_id), rates_config=rates_config
    )
    return schemas.member_out(detail)


@router.put("/companies/{company_id}/members/{user_id}/settings", response_model=schemas.MemberOut)
async def set_member_settings(
    company_id: UUID,
    user_id: UUID,
    body: schemas.MemberSettingsIn,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_WORKER)),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    """Gestor o PA: cualquier miembro. Trabajador: solo los suyos."""
    access_policy.can_edit_member_settings(role=ctx.role, is_self=user_id == ctx.user.id)
    detail = await SetMemberSettingsUseCase(member_repo, user_repo).execute(
        company_id=str(company_id), user_id=str(user_id), settings=body.settings
    )
    return schemas.member_out(detail)


@router.get("/companies/{company_id}/rates", response_model=list[schemas.MemberOut])
async def list_rates(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    """Tarifas de todos los miembros (X3: sustituye a `rates-v2` de v1)."""
    details = await ListRatesUseCase(ListMembersUseCase(member_repo, user_repo)).execute(company_id=str(company_id))
    return [schemas.member_out(detail) for detail in details]
