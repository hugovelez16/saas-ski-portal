"""Caso de uso: previsualizar una invitacion por token (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND
from application.use_cases.company.invitation_common import validate_active_invitation
from domain.entities.company import Company
from domain.entities.company_invitation import CompanyInvitation, hash_invitation_token
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


@dataclass(frozen=True)
class PreviewInvitationResult:
    invitation: CompanyInvitation
    company: Company


class PreviewInvitationUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, invitation_repo: CompanyInvitationRepositoryPort):
        self.company_repo = company_repo
        self.invitation_repo = invitation_repo

    async def execute(self, *, token: str) -> PreviewInvitationResult:
        now = datetime.now(UTC)
        invitation = await self.invitation_repo.get_by_token_hash(hash_invitation_token(token))
        valid_invitation = validate_active_invitation(invitation, now=now)
        company = await self.company_repo.get_by_id(valid_invitation.company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        return PreviewInvitationResult(invitation=valid_invitation, company=company)
