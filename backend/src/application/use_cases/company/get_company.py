"""Caso de uso: lectura de una empresa con la membresia de quien consulta (la autorizacion la decide el router)."""

from typing import Optional

from application.use_cases.company.common import MSG_NO_ACCESS, CompanyView
from domain.exceptions.domain_exceptions import UnauthorizedDomainActionException
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort


class GetCompanyUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, member_repo: CompanyMemberRepositoryPort):
        self.company_repo = company_repo
        self.member_repo = member_repo

    async def execute(self, *, company_id: str, user_id: str, role: Optional[str]) -> CompanyView:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            # Mismo 403 que v1: el router ya valido la existencia, esto solo cubre una carrera con un borrado.
            raise UnauthorizedDomainActionException(MSG_NO_ACCESS)
        member = await self.member_repo.get_membership(user_id, company_id)
        return CompanyView(company=company, member=member, role=role)
