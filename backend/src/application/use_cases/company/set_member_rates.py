"""Caso de uso: edicion de tarifas de una membresia (la politica de acceso la decide el router)."""

from typing import Any, Dict

from application.use_cases.company.common import (
    MSG_COMPANY_NOT_FOUND,
    MSG_MEMBER_NOT_FOUND,
    MSG_UNKNOWN_SHIFT_TYPE,
    MemberDetail,
)
from audit import AuditAction
from domain.exceptions.domain_exceptions import EntityNotFoundException, ValidationDomainException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class SetMemberRatesUseCase:
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

    async def execute(
        self, *, actor_id: str, company_id: str, user_id: str, rates_config: Dict[str, Any]
    ) -> MemberDetail:
        """`rates_config` llega ya validado (RatesConfig) y en JSON plano; se guarda tal cual, siempre con evento."""
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        member = await self.member_repo.get_membership(user_id, company_id)

        # Solo se exige definicion a los tipos nuevos: los ya presentes en la tarifa del miembro se conservan
        # aunque el tipo se haya retirado de la empresa. Igual que v1, este chequeo precede al 404 del miembro.
        definitions = company.worklog_definitions or {}
        existing = set((member.rates_config or {}).keys()) if member is not None else set()
        if any(shift_type not in definitions for shift_type in rates_config if shift_type not in existing):
            raise ValidationDomainException(MSG_UNKNOWN_SHIFT_TYPE)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)

        user = await self.user_repo.get_by_id(user_id)
        old_rates = member.rates_config
        member.rates_config = rates_config
        await self.audit_log.record(
            action=AuditAction.MEMBER_RATES_CHANGED,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=user_id,
            old_value=old_rates,
            new_value=rates_config,
        )
        return MemberDetail(member=await self.member_repo.save(member), user=user)
