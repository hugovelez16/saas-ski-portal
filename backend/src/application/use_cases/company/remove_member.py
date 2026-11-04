"""Caso de uso: borrado de una membresia (solo PA; lo decide el router). No hay guardia de ultimo manager (E7)."""

from dataclasses import dataclass
from typing import Optional

from application.use_cases.company.common import MSG_MEMBER_NOT_FOUND, member_snapshot
from audit import AuditAction
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort

REASON_HAS_WORK_LOGS = "has_work_logs"


@dataclass(frozen=True)
class RemoveMemberResult:
    deleted: bool
    deactivated: bool
    reason: Optional[str] = None


class RemoveMemberUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort, audit_log: AuditLogPort):
        self.member_repo = member_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str, user_id: str) -> RemoveMemberResult:
        """Sin turnos borra la membresia; con turnos la desactiva y conserva los turnos."""
        # Bloquea la fila antes de contar turnos (la carrera con la creacion de
        # turnos sigue anotada en el plan: work_logs no tiene FK a company_members).
        member = await self.member_repo.get_membership(user_id, company_id, for_update=True)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)

        before = member_snapshot(member)
        if await self.member_repo.count_work_logs(user_id, company_id) > 0:
            if member.is_active:
                member.is_active = False
                await self.audit_log.record(
                    action=AuditAction.MEMBER_DEACTIVATED,
                    actor_id=actor_id,
                    company_id=company_id,
                    target_user_id=user_id,
                    old_value=before,
                    new_value=member_snapshot(member),
                    reason=REASON_HAS_WORK_LOGS,
                )
                await self.member_repo.save(member)
            return RemoveMemberResult(deleted=False, deactivated=True, reason=REASON_HAS_WORK_LOGS)

        await self.audit_log.record(
            action=AuditAction.MEMBER_REMOVED,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user_id,
            old_value=before,
        )
        await self.member_repo.delete(user_id, company_id)
        return RemoveMemberResult(deleted=True, deactivated=False)
