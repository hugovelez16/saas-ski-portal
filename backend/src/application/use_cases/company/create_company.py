"""Caso de uso: alta de empresa (solo PA; la autorizacion la decide el router)."""

import uuid
from typing import Any, Dict, Optional

from application.use_cases.company.common import company_snapshot
from audit import AuditAction
from domain.entities.company import Company
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


class CreateCompanyUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, audit_log: AuditLogPort):
        self.company_repo = company_repo
        self.audit_log = audit_log

    async def execute(
        self,
        *,
        actor_id: str,
        name: str,
        tax_config: Dict[str, Any],
        worklog_definitions: Optional[Dict[str, Any]] = None,
        settings: Optional[Dict[str, Any]] = None,
        is_active: bool = True,
        is_managed: bool = False,
    ) -> Company:
        company = Company(
            id=str(uuid.uuid4()),
            name=name,
            tax_config=tax_config,
            worklog_definitions=worklog_definitions or {},
            settings=settings or {},
            is_active=is_active,
            is_managed=is_managed,
        )
        # La auditoria va antes de save: el commit del repositorio confirma ambas a la vez.
        await self.audit_log.record(
            action=AuditAction.COMPANY_CREATED,
            actor_id=actor_id,
            company_id=company.id,
            new_value=company_snapshot(company),
        )
        return await self.company_repo.save(company)
