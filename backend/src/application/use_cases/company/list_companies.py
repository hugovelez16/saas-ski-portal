"""Caso de uso: listado global de empresas, con miembros opcionales (solo PA; lo decide el router)."""

from typing import List, Tuple

from application.use_cases.company.common import CompanyWithMembers, MemberDetail
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class ListCompaniesUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo

    async def execute(
        self, *, skip: int = 0, limit: int = 100, include_members: bool = False
    ) -> Tuple[List[CompanyWithMembers], int]:
        companies = await self.company_repo.list_companies(skip=skip, limit=limit)
        total = await self.company_repo.count_companies()
        items = []
        for company in companies:
            members: List[MemberDetail] = []
            if include_members:
                for member in await self.member_repo.list_members_by_company(company.id):
                    members.append(MemberDetail(member=member, user=await self.user_repo.get_by_id(member.user_id)))
            items.append(CompanyWithMembers(company=company, members=members))
        return items, total
