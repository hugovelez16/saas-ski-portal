"""Seccion Invitaciones de la API v2 de administracion (`/api/v2/admin/companies/{id}/invitations...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from typing import Literal
from uuid import UUID

import models
from application.use_cases.company.cancel_invitation import CancelInvitationUseCase
from application.use_cases.company.create_invitation import CreateInvitationUseCase
from application.use_cases.company.invitation_common import InvitationEmailDeliveryError
from application.use_cases.company.list_invitations import ListInvitationsUseCase
from application.use_cases.company.resend_invitation import ResendInvitationUseCase
from fastapi import APIRouter, Depends, HTTPException, Response

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


@router.get("/companies/{company_id}/invitations", response_model=list[schemas.InvitationOut])
async def list_invitations_admin(
    company_id: UUID,
    status: Literal["pending", "accepted", "cancelled", "expired", "all"] | None = None,
    company_repo=Depends(v2_deps.get_company_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    views = await ListInvitationsUseCase(company_repo, invitation_repo, user_repo).execute(
        company_id=str(company_id), status=status
    )
    return [schemas.invitation_out(view) for view in views]


@router.post("/companies/{company_id}/invitations", response_model=schemas.InvitationOut, status_code=201)
async def create_invitation_admin(
    company_id: UUID,
    body: schemas.InvitationCreateIn,
    response: Response,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    try:
        result = await CreateInvitationUseCase(
            company_repo, member_repo, user_repo, invitation_repo, audit_log
        ).execute(actor_id=str(actor.id), company_id=str(company_id), email=body.email)
    except InvitationEmailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not result.created:
        response.status_code = 200
    return schemas.invitation_out(result.view)


@router.post("/companies/{company_id}/invitations/{invitation_id}/resend", response_model=schemas.InvitationOut)
async def resend_invitation_admin(
    company_id: UUID,
    invitation_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    try:
        view = await ResendInvitationUseCase(
            company_repo, member_repo, user_repo, invitation_repo, audit_log
        ).execute(actor_id=str(actor.id), company_id=str(company_id), invitation_id=str(invitation_id))
    except InvitationEmailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return schemas.invitation_out(view)


@router.delete("/companies/{company_id}/invitations/{invitation_id}", response_model=schemas.InvitationOut)
async def cancel_invitation_admin(
    company_id: UUID,
    invitation_id: UUID,
    actor: models.User = Depends(deps.require_platform_admin),
    company_repo=Depends(v2_deps.get_company_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    view = await CancelInvitationUseCase(company_repo, invitation_repo, user_repo, audit_log).execute(
        actor_id=str(actor.id), company_id=str(company_id), invitation_id=str(invitation_id)
    )
    return schemas.invitation_out(view)
