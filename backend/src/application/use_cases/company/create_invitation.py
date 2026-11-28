"""Caso de uso: crear o renovar una invitacion por correo (R-MEM-07, R-MEM-23 a R-MEM-25)."""

import logging
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Optional

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND
from application.use_cases.company.invitation_common import (
    EmailSenderFn,
    InvitationEmailDeliveryError,
    InvitationView,
    default_email_sender,
    resolve_inviter_name,
)
from application.use_cases.company.plan_limits import ensure_member_limit_allows_addition
from audit import AuditAction
from domain.entities.company_invitation import (
    CompanyInvitation,
    generate_invitation_token,
    normalize_invitation_email,
)
from domain.entities.company_member import CompanyRole
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class CreateInvitationResult:
    view: InvitationView
    created: bool


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
        self.email_sender = email_sender or default_email_sender

    async def execute(self, *, actor_id: str, company_id: str, email: str) -> CreateInvitationResult:
        """Crea o renueva una invitacion de 7 dias y envia correo; respuesta neutra exista o no la cuenta."""
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)

        await ensure_member_limit_allows_addition(company, self.member_repo, target_role=CompanyRole.WORKER)

        normalized_email = normalize_invitation_email(email)
        actor = await self.user_repo.get_by_id(actor_id)
        inviter_name = resolve_inviter_name(actor)

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
