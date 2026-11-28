"""Caso de uso: cancelar una invitacion no aceptada (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from datetime import UTC, datetime

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND
from application.use_cases.company.invitation_common import (
    MSG_INVITATION_NOT_FOUND,
    MSG_INVITATION_USED,
    InvitationView,
    resolve_inviter_name,
)
from audit import AuditAction
from domain.exceptions.domain_exceptions import ConflictException, EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


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
        inviter_name = resolve_inviter_name(inviter) if inviter else None

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
