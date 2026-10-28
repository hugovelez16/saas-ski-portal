"""Caso de uso: alta directa de un usuario en una empresa por email (solo PA; lo decide el router)."""

from dataclasses import dataclass

from application.use_cases.company.common import (
    DEFAULT_MEMBER_SORT_ORDER,
    MSG_COMPANY_NOT_FOUND,
    MSG_USER_EMAIL_NOT_FOUND,
    MemberDetail,
    member_snapshot,
)
from audit import AuditAction
from domain.entities.company_member import CompanyMember, CompanyRole
from domain.exceptions.domain_exceptions import EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


@dataclass(frozen=True)
class AddMemberResult:
    detail: MemberDetail
    created: bool


class AddMemberUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        audit_log: AuditLogPort,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.audit_log = audit_log

    async def execute(self, *, actor_id: str, company_id: str, email: str) -> AddMemberResult:
        """Miembro nuevo: `worker` activo. Inactivo: se reactiva forzando `worker` (M6). Activo: sin cambios."""
        if await self.company_repo.get_by_id(company_id) is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        user = await self.user_repo.get_by_email(email)
        if user is None:
            raise EntityNotFoundException(MSG_USER_EMAIL_NOT_FOUND)

        member = await self.member_repo.get_membership(user.id, company_id)
        if member is not None and member.is_active:
            return AddMemberResult(MemberDetail(member=member, user=user), created=False)

        if member is None:
            member = CompanyMember(
                user_id=user.id,
                company_id=company_id,
                role=CompanyRole.WORKER,
                is_active=True,
                sort_order=DEFAULT_MEMBER_SORT_ORDER,
            )
            action, before, created = AuditAction.MEMBER_ADDED, None, True
        else:
            before = member_snapshot(member)
            member.is_active = True
            member.role = CompanyRole.WORKER
            action, created = AuditAction.MEMBER_REACTIVATED, False

        # La auditoria va antes de save: el commit del repositorio confirma ambas a la vez.
        await self.audit_log.record(
            action=action,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user.id,
            old_value=before,
            new_value=member_snapshot(member),
        )
        saved = await self.member_repo.save(member)
        return AddMemberResult(MemberDetail(member=saved, user=user), created=created)
