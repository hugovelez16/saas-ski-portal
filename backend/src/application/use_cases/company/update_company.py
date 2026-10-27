"""Caso de uso: edicion de empresa (solo PA; la autorizacion la decide el router)."""

import copy
from typing import Any, Dict, Optional

from application.use_cases.company.common import (
    COMPANY_EVENT_ACTIONS,
    MSG_COMPANY_NOT_FOUND,
    MSG_NO_CHANGES,
    company_event,
)
from domain.entities.company import Company
from domain.exceptions.domain_exceptions import EntityNotFoundException, ValidationDomainException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


class UpdateCompanyUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, audit_log: AuditLogPort):
        self.company_repo = company_repo
        self.audit_log = audit_log

    async def execute(
        self,
        *,
        actor_id: str,
        company_id: str,
        changes: Dict[str, Any],
        reason: Optional[str] = None,
    ) -> Company:
        """`changes` contiene solo los campos enviados (JSON plano). Un evento de auditoria por campo que cambia."""
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)

        diffs = []
        for field_name in COMPANY_EVENT_ACTIONS:
            if field_name not in changes:
                continue
            old_value = getattr(company, field_name)
            new_value = changes[field_name]
            if old_value != new_value:
                diffs.append((field_name, old_value, new_value))
        if not diffs:
            raise ValidationDomainException(MSG_NO_CHANGES)

        for field_name, old_value, new_value in diffs:
            await self.audit_log.record(
                action=company_event(field_name, new_value),
                actor_id=actor_id,
                company_id=company.id,
                old_value={field_name: old_value},
                new_value={field_name: new_value},
                reason=reason if field_name == "is_active" else None,
            )
        for field_name, _old_value, new_value in diffs:
            setattr(company, field_name, copy.deepcopy(new_value))
        return await self.company_repo.save(company)
