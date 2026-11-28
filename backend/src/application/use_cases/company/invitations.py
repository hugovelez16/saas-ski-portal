"""Casos de uso de invitaciones por correo para incorporar miembros a una empresa (R-MEM-07, R-MEM-23 a R-MEM-25)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Awaitable, Callable, List, Optional

import email_utils
from access_policy import MSG_SUSPENDED
from application.use_cases.company.common import (
    DEFAULT_MEMBER_SORT_ORDER,
    MSG_COMPANY_NOT_FOUND,
    MemberDetail,
    member_snapshot,
)
from application.use_cases.company.plan_limits import ensure_member_limit_allows_addition
from audit import AuditAction
from domain.entities.company import Company
from domain.entities.company_invitation import (
    CompanyInvitation,
    generate_invitation_token,
    hash_invitation_token,
    normalize_invitation_email,
)
from domain.entities.company_member import CompanyMember, CompanyRole
from domain.exceptions.domain_exceptions import (
    ConflictException,
    EntityNotFoundException,
    UnauthorizedDomainActionException,
    ValidationDomainException,
)
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort

logger = logging.getLogger(__name__)

MSG_INVITATION_NOT_FOUND = "Invitacion no encontrada"
MSG_INVITATION_LINK_INVALID = "Invitacion no encontrada o enlace no valido"
MSG_INVITATION_WRONG_EMAIL = "Esta invitacion es para otro correo"
MSG_INVITATION_EXPIRED = "Esta invitacion ha caducado"
MSG_INVITATION_USED = "Esta invitacion ya ha sido utilizada"
MSG_INVITATION_CANCELLED = "Esta invitacion ha sido cancelada"


class InvitationEmailDeliveryError(Exception):
    """Error al enviar el correo de invitacion tras registrar la invitacion en la transaccion."""


EmailSenderFn = Callable[..., Awaitable[None]]


async def _default_email_sender(
    *, email: str, company_name: str, inviter_name: str, token: str
) -> None:
    await email_utils.send_company_invitation_email(
        email,
        company_name=company_name,
        inviter_name=inviter_name,
        token=token,
    )


@dataclass(frozen=True)
class InvitationView:
    invitation: CompanyInvitation
    invited_by_name: Optional[str] = None


@dataclass(frozen=True)
class CreateInvitationResult:
    view: InvitationView
    created: bool


@dataclass(frozen=True)
class PreviewInvitationResult:
    invitation: CompanyInvitation
    company: Company


@dataclass(frozen=True)
class AcceptInvitationResult:
    company: Company
    detail: MemberDetail
    changed: bool


def _resolve_inviter_name(user) -> str:
    if user is None:
        return "Un responsable"
    return user.full_name or user.email


def _validate_active_invitation(invitation: Optional[CompanyInvitation], *, now: datetime) -> CompanyInvitation:
    if invitation is None:
        raise EntityNotFoundException(MSG_INVITATION_LINK_INVALID)
    if invitation.cancelled_at is not None:
        raise ConflictException(MSG_INVITATION_CANCELLED)
    if invitation.accepted_at is not None:
        raise ConflictException(MSG_INVITATION_USED)
    if invitation.is_expired(now):
        raise ValidationDomainException(MSG_INVITATION_EXPIRED)
    return invitation


class CreateInvitationUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        audit_log: AuditLogPort,
        email_sender: Optional[EmailSenderFn] = None,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.audit_log = audit_log
        self.email_sender = email_sender or _default_email_sender

    async def execute(self, *, actor_id: str, company_id: str, email: str) -> CreateInvitationResult:
        """Crea o renueva una invitacion de 7 dias y envia correo; respuesta neutra exista o no la cuenta."""
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)

        await ensure_member_limit_allows_addition(company, self.member_repo, target_role=CompanyRole.WORKER)

        normalized_email = normalize_invitation_email(email)
        actor = await self.user_repo.get_by_id(actor_id)
        inviter_name = _resolve_inviter_name(actor)

        now = datetime.now(UTC)
        raw_token, token_hash = generate_invitation_token()
        expires_at = CompanyInvitation.default_expires_at(now)

        existing = await self.invitation_repo.get_pending_by_company_and_email(company_id, normalized_email)
        if existing is not None:
            existing.token_hash = token_hash
            existing.invited_by_user_id = actor_id
            existing.expires_at = expires_at
            invitation = existing
            created = False
        else:
            invitation = CompanyInvitation(
                company_id=company_id,
                email=normalized_email,
                token_hash=token_hash,
                invited_by_user_id=actor_id,
                expires_at=expires_at,
            )
            created = True

        saved = await self.invitation_repo.save(invitation, commit=False)
        await self.audit_log.record(
            action=AuditAction.MEMBER_INVITED,
            actor_id=actor_id,
            company_id=company_id,
            new_value={
                "invitation_id": saved.id,
                "email": normalized_email,
                "expires_at": expires_at.isoformat(),
            },
        )
        try:
            await self.email_sender(
                email=normalized_email,
                company_name=company.name,
                inviter_name=inviter_name,
                token=raw_token,
            )
        except Exception as exc:
            await self.invitation_repo.rollback()
            logger.warning("Error enviando correo de invitacion %s para empresa %s", saved.id, company_id)
            raise InvitationEmailDeliveryError("No se pudo enviar el correo de invitacion") from exc

        await self.invitation_repo.commit()
        return CreateInvitationResult(view=InvitationView(invitation=saved, invited_by_name=inviter_name), created=created)


class ListInvitationsUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        user_repo: UserRepositoryPort,
    ):
        self.company_repo = company_repo
        self.invitation_repo = invitation_repo
        self.user_repo = user_repo

    async def execute(self, *, company_id: str, status: Optional[str] = None) -> List[InvitationView]:
        if await self.company_repo.get_by_id(company_id) is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        invitations = await self.invitation_repo.list_by_company(company_id, status=status)
        inviter_names: dict[str, Optional[str]] = {}
        views: List[InvitationView] = []
        for inv in invitations:
            if inv.invited_by_user_id not in inviter_names:
                inviter = await self.user_repo.get_by_id(inv.invited_by_user_id)
                inviter_names[inv.invited_by_user_id] = _resolve_inviter_name(inviter) if inviter else None
            views.append(InvitationView(invitation=inv, invited_by_name=inviter_names[inv.invited_by_user_id]))
        return views


class ResendInvitationUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        audit_log: AuditLogPort,
        email_sender: Optional[EmailSenderFn] = None,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.audit_log = audit_log
        self.email_sender = email_sender or _default_email_sender

    async def execute(self, *, actor_id: str, company_id: str, invitation_id: str) -> InvitationView:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        invitation = await self.invitation_repo.get_by_id(invitation_id, company_id)
        if invitation is None:
            raise EntityNotFoundException(MSG_INVITATION_NOT_FOUND)
        if invitation.accepted_at is not None or invitation.cancelled_at is not None:
            raise ConflictException("Solo se pueden reenviar invitaciones pendientes")

        await ensure_member_limit_allows_addition(company, self.member_repo, target_role=CompanyRole.WORKER)

        actor = await self.user_repo.get_by_id(actor_id)
        inviter_name = _resolve_inviter_name(actor)

        now = datetime.now(UTC)
        old_expires_at = invitation.expires_at
        raw_token, token_hash = generate_invitation_token()
        invitation.token_hash = token_hash
        invitation.invited_by_user_id = actor_id
        invitation.expires_at = CompanyInvitation.default_expires_at(now)

        saved = await self.invitation_repo.save(invitation, commit=False)
        await self.audit_log.record(
            action=AuditAction.MEMBER_INVITED,
            actor_id=actor_id,
            company_id=company_id,
            old_value={"invitation_id": saved.id, "email": saved.email, "expires_at": old_expires_at.isoformat()},
            new_value={"invitation_id": saved.id, "email": saved.email, "expires_at": saved.expires_at.isoformat()},
            reason="resend",
        )
        try:
            await self.email_sender(
                email=saved.email,
                company_name=company.name,
                inviter_name=inviter_name,
                token=raw_token,
            )
        except Exception as exc:
            await self.invitation_repo.rollback()
            logger.warning("Error reenviando correo de invitacion %s para empresa %s", saved.id, company_id)
            raise InvitationEmailDeliveryError("No se pudo enviar el correo de invitacion") from exc

        await self.invitation_repo.commit()
        return InvitationView(invitation=saved, invited_by_name=inviter_name)


class CancelInvitationUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        user_repo: UserRepositoryPort,
        audit_log: AuditLogPort,
    ):
        self.company_repo = company_repo
        self.invitation_repo = invitation_repo
        self.user_repo = user_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str, invitation_id: str) -> InvitationView:
        if await self.company_repo.get_by_id(company_id) is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        invitation = await self.invitation_repo.get_by_id(invitation_id, company_id)
        if invitation is None:
            raise EntityNotFoundException(MSG_INVITATION_NOT_FOUND)
        if invitation.accepted_at is not None:
            raise ConflictException(MSG_INVITATION_USED)

        inviter = await self.user_repo.get_by_id(invitation.invited_by_user_id)
        inviter_name = _resolve_inviter_name(inviter) if inviter else None

        if invitation.cancelled_at is not None:
            return InvitationView(invitation=invitation, invited_by_name=inviter_name)

        now = datetime.now(UTC)
        prev_status = invitation.status_at(now)
        invitation.cancelled_at = now
        await self.audit_log.record(
            action=AuditAction.MEMBER_INVITATION_CANCELLED,
            actor_id=actor_id,
            company_id=company_id,
            old_value={"invitation_id": invitation.id, "email": invitation.email, "status": prev_status},
            new_value={"invitation_id": invitation.id, "email": invitation.email, "status": "cancelled"},
        )
        saved = await self.invitation_repo.save(invitation, commit=True)
        return InvitationView(invitation=saved, invited_by_name=inviter_name)


class PreviewInvitationUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, invitation_repo: CompanyInvitationRepositoryPort):
        self.company_repo = company_repo
        self.invitation_repo = invitation_repo

    async def execute(self, *, token: str) -> PreviewInvitationResult:
        now = datetime.now(UTC)
        invitation = await self.invitation_repo.get_by_token_hash(hash_invitation_token(token))
        valid_invitation = _validate_active_invitation(invitation, now=now)
        company = await self.company_repo.get_by_id(valid_invitation.company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        return PreviewInvitationResult(invitation=valid_invitation, company=company)


class AcceptInvitationUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        audit_log: AuditLogPort,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.audit_log = audit_log

    async def execute(self, *, user_id: str, token: str) -> AcceptInvitationResult:
        """Valida el token y el correo de sesion, comprueba limites y crea/reactiva la membresia."""
        now = datetime.now(UTC)
        token_hash = hash_invitation_token(token)
        invitation = await self.invitation_repo.get_by_token_hash(token_hash, for_update=True)
        invitation = _validate_active_invitation(invitation, now=now)

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundException("Usuario no encontrado")

        if normalize_invitation_email(user.email) != normalize_invitation_email(invitation.email):
            raise UnauthorizedDomainActionException(MSG_INVITATION_WRONG_EMAIL)

        if user.is_platform_admin:
            raise ValidationDomainException("Un administrador de plataforma no puede ser miembro de una empresa")

        company = await self.company_repo.get_by_id(invitation.company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        if not company.is_active:
            raise UnauthorizedDomainActionException(MSG_SUSPENDED)

        member = await self.member_repo.get_membership(user.id, company.id, for_update=True)
        invitation.accepted_at = now
        invitation.accepted_by_user_id = user.id

        if member is not None and member.is_active:
            await self.invitation_repo.save(invitation, commit=True)
            return AcceptInvitationResult(
                company=company,
                detail=MemberDetail(member=member, user=user),
                changed=False,
            )

        target_role = member.role if member is not None else CompanyRole.WORKER
        await ensure_member_limit_allows_addition(company, self.member_repo, target_role=target_role)

        if member is None:
            member = CompanyMember(
                user_id=user.id,
                company_id=company.id,
                role=CompanyRole.WORKER,
                is_active=True,
                sort_order=DEFAULT_MEMBER_SORT_ORDER,
            )
            action, before = AuditAction.MEMBER_ADDED, None
        else:
            before = member_snapshot(member)
            member.is_active = True
            action = AuditAction.MEMBER_REACTIVATED

        await self.audit_log.record(
            action=action,
            actor_id=user.id,
            company_id=company.id,
            target_user_id=user.id,
            old_value=before,
            new_value=member_snapshot(member),
            reason="invitation",
            extra={"invitation_id": invitation.id},
        )
        await self.invitation_repo.save(invitation, commit=False)
        saved_member = await self.member_repo.save(member)
        return AcceptInvitationResult(
            company=company,
            detail=MemberDetail(member=saved_member, user=user),
            changed=True,
        )
