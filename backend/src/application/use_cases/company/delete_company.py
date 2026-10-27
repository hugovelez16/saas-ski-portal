"""Caso de uso: borrado de empresa sin cascadas (solo PA; la autorizacion la decide el router)."""

from application.use_cases.company.common import MSG_COMPANY_NOT_FOUND, MSG_DELETE_BLOCKED, company_snapshot
from audit import AuditAction
from domain.exceptions.domain_exceptions import ConflictException, EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


class DeleteCompanyUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, audit_log: AuditLogPort):
        self.company_repo = company_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str) -> None:
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)

        dependencies = await self.company_repo.count_dependencies(company_id)
        labels = (("members", "miembros"), ("work_logs", "turnos"), ("subscriptions", "suscripciones"))
        blockers = [f"{dependencies[key]} {label}" for key, label in labels if dependencies.get(key)]
        if blockers:
            raise ConflictException(MSG_DELETE_BLOCKED + ", ".join(blockers))

        # La auditoria va antes de delete: el commit del repositorio confirma ambas a la vez.
        await self.audit_log.record(
            action=AuditAction.COMPANY_DELETED,
            actor_id=actor_id,
            company_id=company.id,
            old_value=company_snapshot(company),
        )
        await self.company_repo.delete(company_id)
