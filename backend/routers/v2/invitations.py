"""API v2: invitaciones por correo para miembros de empresa (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from typing import Literal
from uuid import UUID

import access_policy
import auth
import models
from application.use_cases.company.accept_invitation import AcceptInvitationUseCase
from application.use_cases.company.cancel_invitation import CancelInvitationUseCase
from application.use_cases.company.create_invitation import CreateInvitationUseCase
from application.use_cases.company.invitation_common import InvitationEmailDeliveryError
from application.use_cases.company.list_invitations import ListInvitationsUseCase
from application.use_cases.company.preview_invitation import PreviewInvitationUseCase
from application.use_cases.company.resend_invitation import ResendInvitationUseCase
from fastapi import APIRouter, Depends, HTTPException, Query, Response

from routers import deps
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(tags=["v2-invitations"])


@router.get("/companies/{company_id}/invitations", response_model=list[schemas.InvitationOut])
async def list_invitations(
    company_id: UUID,
    status: Literal["pending", "accepted", "cancelled", "expired", "all"] | None = None,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    company_repo=Depends(v2_deps.get_company_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    user_repo=Depends(v2_deps.get_user_repository),
):
    """Lista las invitaciones de la empresa (por defecto pendientes y caducadas sin cancelar/aceptar)."""
    views = await ListInvitationsUseCase(company_repo, invitation_repo, user_repo).execute(
        company_id=str(company_id), status=status
    )
    return [schemas.invitation_out(view) for view in views]


@router.post("/companies/{company_id}/invitations", response_model=schemas.InvitationOut, status_code=201)
async def create_invitation(
    company_id: UUID,
    body: schemas.InvitationCreateIn,
    response: Response,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Manager de empresa activa o PA: crea o renueva invitacion de 7 dias con respuesta neutra."""
    try:
        result = await CreateInvitationUseCase(
            company_repo, member_repo, user_repo, invitation_repo, audit_log
        ).execute(actor_id=str(ctx.user.id), company_id=str(company_id), email=body.email)
    except InvitationEmailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    if not result.created:
        response.status_code = 200
    return schemas.invitation_out(result.view)


@router.post(
    "/companies/{company_id}/invitations/{invitation_id}/resend",
    response_model=schemas.InvitationOut,
)
async def resend_invitation(
    company_id: UUID,
    invitation_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Reenvia una invitacion pendiente renovando token y caducidad de 7 dias."""
    try:
        view = await ResendInvitationUseCase(
            company_repo, member_repo, user_repo, invitation_repo, audit_log
        ).execute(actor_id=str(ctx.user.id), company_id=str(company_id), invitation_id=str(invitation_id))
    except InvitationEmailDeliveryError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    return schemas.invitation_out(view)


@router.delete("/companies/{company_id}/invitations/{invitation_id}", response_model=schemas.InvitationOut)
async def cancel_invitation(
    company_id: UUID,
    invitation_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company(access_policy.ROLE_MANAGER)),
    company_repo=Depends(v2_deps.get_company_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Cancela una invitacion pendiente."""
    view = await CancelInvitationUseCase(company_repo, invitation_repo, user_repo, audit_log).execute(
        actor_id=str(ctx.user.id), company_id=str(company_id), invitation_id=str(invitation_id)
    )
    return schemas.invitation_out(view)


@router.get("/invitations/preview", response_model=schemas.InvitationPreviewOut)
async def preview_invitation(
    token: str = Query(..., min_length=1, max_length=512),
    company_repo=Depends(v2_deps.get_company_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
):
    """Previsualiza una invitacion valida (empresa y caducidad) sin exponer el correo."""
    preview = await PreviewInvitationUseCase(company_repo, invitation_repo).execute(token=token)
    return schemas.invitation_preview_out(preview)


@router.post("/invitations/accept", response_model=schemas.InvitationAcceptOut)
async def accept_invitation(
    body: schemas.InvitationAcceptIn,
    current_user: models.User = Depends(auth.get_verified_user),
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
    user_repo=Depends(v2_deps.get_user_repository),
    invitation_repo=Depends(v2_deps.get_invitation_repository),
    audit_log=Depends(v2_deps.get_audit_log),
):
    """Acepta una invitacion de un solo uso comprobando el correo de la sesion y los limites del plan."""
    result = await AcceptInvitationUseCase(
        company_repo, member_repo, user_repo, invitation_repo, audit_log
    ).execute(user_id=str(current_user.id), token=body.token)
    return schemas.invitation_accept_out(result)
