"""Caso de uso: empresas de un usuario concreto, vistas por un PA o por un manager (P8)."""

from typing import List, Optional, Set

from application.use_cases.company.common import CompanyView
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort


class ListUserCompaniesUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, member_repo: CompanyMemberRepositoryPort):
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(
        self, *, user_id: str, include_inactive: bool, allowed_company_ids: Optional[Set[str]] = None
    ) -> List[CompanyView]:
        """`allowed_company_ids=None` no restringe (PA); un conjunto limita a esas empresas (manager)."""
        views: List[CompanyView] = []
        for member in await self.member_repo.list_companies_by_user(user_id):
            if not include_inactive and not member.is_active:
                continue
            if allowed_company_ids is not None and str(member.company_id) not in allowed_company_ids:
                continue
            company = await self.company_repo.get_by_id(member.company_id)
            if company is None or (not include_inactive and not company.is_active):
                continue
            views.append(CompanyView(company=company, member=member, role=member.role.value))
        return views
