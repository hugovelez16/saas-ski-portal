"""Caso de uso: activar o desactivar una membresia (solo PA; lo decide el router)."""

from application.use_cases.company.common import MSG_MEMBER_NOT_FOUND, MemberDetail, member_snapshot
from audit import AuditAction
from domain.entities.company_member import CompanyRole
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class SetMemberStatusUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort, user_repo: UserRepositoryPort, audit_log: AuditLogPort):
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str, user_id: str, is_active: bool) -> MemberDetail:
        """Reactivar fuerza `worker` (M6); desactivar no reasigna nada. Sin cambio de estado no hay evento."""
        member = await self.member_repo.get_membership(user_id, company_id)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)
        user = await self.user_repo.get_by_id(user_id)
        if member.is_active == is_active:
            return MemberDetail(member=member, user=user)

        before = member_snapshot(member)
        member.is_active = is_active
        if is_active:
            member.role = CompanyRole.WORKER
            action = AuditAction.MEMBER_REACTIVATED
        else:
            action = AuditAction.MEMBER_DEACTIVATED
        await self.audit_log.record(
            action=action,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user_id,
            old_value=before,
            new_value=member_snapshot(member),
        )
        return MemberDetail(member=await self.member_repo.save(member), user=user)
