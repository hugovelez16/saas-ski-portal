"""Caso de uso: cambio de rol de una membresia (solo PA; lo decide el router). No hay guardia de ultimo manager (E7)."""

from application.use_cases.company.common import MSG_MEMBER_NOT_FOUND, MemberDetail
from audit import AuditAction
from domain.entities.company_member import CompanyRole
from domain.exceptions.domain_exceptions import EntityNotFoundException, ValidationDomainException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort

ASSIGNABLE_ROLES = (CompanyRole.WORKER.value, CompanyRole.MANAGER.value)


class SetMemberRoleUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort, user_repo: UserRepositoryPort, audit_log: AuditLogPort):
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str, user_id: str, role: str) -> MemberDetail:
        """El rol `admin` de membresia esta reservado y no se puede asignar. Mismo rol: sin cambios ni evento."""
        if role not in ASSIGNABLE_ROLES:
            raise ValidationDomainException("Rol no permitido: usa worker o manager")
        member = await self.member_repo.get_membership(user_id, company_id)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)
        user = await self.user_repo.get_by_id(user_id)

        old_role = member.role.value
        if old_role == role:
            return MemberDetail(member=member, user=user)

        member.role = CompanyRole(role)
        await self.audit_log.record(
            action=AuditAction.MEMBER_ROLE_CHANGED,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user_id,
            old_value={"role": old_role},
            new_value={"role": role},
        )
        return MemberDetail(member=await self.member_repo.save(member), user=user)
