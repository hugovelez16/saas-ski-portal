"""Caso de uso: listado de miembros de una empresa (manager o PA; lo decide el router)."""

from typing import List, Optional

from application.use_cases.company.common import MemberDetail
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class ListMembersUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort, user_repo: UserRepositoryPort):
        self.member_repo = member_repo
        self.user_repo = user_repo

    async def execute(self, *, company_id: str, is_active: Optional[bool] = None) -> List[MemberDetail]:
        members = await self.member_repo.list_members_by_company(company_id, is_active)
        return [MemberDetail(member=m, user=await self.user_repo.get_by_id(m.user_id)) for m in members]
