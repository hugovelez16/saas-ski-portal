"""Caso de uso: consulta de uso de tipos de turno (turnos y tarifas asociadas, R-EMP-41)."""

from typing import Dict

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


class GetWorklogDefinitionUsageUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort):
        self.company_repo = company_repo

    async def execute(self, *, company_id: str) -> Dict[str, Dict[str, int]]:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        shift_types = list((company.worklog_definitions or {}).keys())
        work_logs_counts = await self.company_repo.count_work_logs_by_types(company_id, shift_types)
        rates_counts = await self.company_repo.count_member_rates_by_types(company_id, shift_types)
        return {
            shift_type: {
                "work_logs_count": work_logs_counts.get(shift_type, 0),
                "member_rates_count": rates_counts.get(shift_type, 0),
            }
            for shift_type in shift_types
        }
