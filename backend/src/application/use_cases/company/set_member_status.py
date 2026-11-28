"""Caso de uso: activar o desactivar una membresia (PA cualquiera; manager solo workers de su empresa activa)."""

from typing import Optional

import access_policy
from application.use_cases.company.common import MSG_MEMBER_NOT_FOUND, MemberDetail, member_snapshot
from application.use_cases.company.plan_limits import ensure_member_limit_allows_addition
from audit import AuditAction
from domain.exceptions.domain_exceptions import EntityNotFoundException, UnauthorizedDomainActionException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class SetMemberStatusUseCase:
    def __init__(
        self,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        audit_log: AuditLogPort,
        company_repo: Optional[CompanyRepositoryPort] = None,
    ):
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.audit_log = audit_log
        self.company_repo = company_repo

    async def execute(
        self,
        *,
        actor_id: str,
        company_id: str,
        user_id: str,
        is_active: bool,
        actor_is_platform_admin: bool = True,
    ) -> MemberDetail:
        """Reactivar conserva el rol previo (R-MEM-12). El manager solo actua sobre workers (R-MEM-10, R-MEM-11)."""
        member = await self.member_repo.get_membership(user_id, company_id)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)
        if member.is_manager and not actor_is_platform_admin:
            raise UnauthorizedDomainActionException(access_policy.MSG_FORBIDDEN)

        user = await self.user_repo.get_by_id(user_id)
        if member.is_active == is_active:
            return MemberDetail(member=member, user=user)

        if is_active and self.company_repo is not None:
            company = await self.company_repo.get_by_id(company_id)
            if company is not None:
                await ensure_member_limit_allows_addition(company, self.member_repo, target_role=member.role)

        before = member_snapshot(member)
        member.is_active = is_active
        action = AuditAction.MEMBER_REACTIVATED if is_active else AuditAction.MEMBER_DEACTIVATED
        await self.audit_log.record(
            action=action,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user_id,
            old_value=before,
            new_value=member_snapshot(member),
        )
        return MemberDetail(member=await self.member_repo.save(member), user=user)
