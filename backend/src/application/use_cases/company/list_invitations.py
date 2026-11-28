"""Caso de uso: listar las invitaciones de una empresa (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from typing import List, Optional

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND
from application.use_cases.company.invitation_common import InvitationView, resolve_inviter_name
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


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
                inviter_names[inv.invited_by_user_id] = resolve_inviter_name(inviter) if inviter else None
            views.append(InvitationView(invitation=inv, invited_by_name=inviter_names[inv.invited_by_user_id]))
        return views
