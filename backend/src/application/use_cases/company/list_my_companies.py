"""Caso de uso: empresas del usuario autenticado."""

from typing import List

from application.use_cases.company.common import CompanyView
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort


class ListMyCompaniesUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, member_repo: CompanyMemberRepositoryPort):
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(self, *, user_id: str) -> List[CompanyView]:
        """Membresias activas del usuario en empresas activas (`R-ACC-81`)."""
        views: List[CompanyView] = []
        for member in await self.member_repo.list_companies_by_user(user_id):
            if not member.is_active:
                continue
            company = await self.company_repo.get_by_id(member.company_id)
            if company is None or not company.is_active:
                continue
            views.append(CompanyView(company=company, member=member, role=member.role.value))
        return views
