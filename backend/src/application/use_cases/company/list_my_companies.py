"""Caso de uso: empresas del usuario autenticado."""

from typing import List

from application.use_cases.company.common import CompanyView
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort


class ListMyCompaniesUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, member_repo: CompanyMemberRepositoryPort):
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(self, *, user_id: str, as_platform_admin: bool) -> List[CompanyView]:
        """PA actuando: todas las empresas. Resto (y PA en "ver como"): membresias activas en empresas activas."""
        if as_platform_admin:
            total = await self.company_repo.count_companies()
            companies = await self.company_repo.list_companies(skip=0, limit=max(total, 1))
            return [CompanyView(company=c, member=None, role="admin") for c in companies]

        views: List[CompanyView] = []
        for member in await self.member_repo.list_companies_by_user(user_id):
            if not member.is_active:
                continue
            company = await self.company_repo.get_by_id(member.company_id)
            if company is None or not company.is_active:
                continue
            views.append(CompanyView(company=company, member=member, role=member.role.value))
        return views
