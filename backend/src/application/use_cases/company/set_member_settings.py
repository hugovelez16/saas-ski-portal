"""Caso de uso: edicion de los ajustes de una membresia (la politica de acceso la decide el router)."""

from typing import Any, Dict

from application.use_cases.company.common import MSG_MEMBER_NOT_FOUND, MemberDetail
from contracts import validate_member_settings
from domain.exceptions.domain_exceptions import EntityNotFoundException, ValidationDomainException
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


class SetMemberSettingsUseCase:
    def __init__(self, member_repo: CompanyMemberRepositoryPort, user_repo: UserRepositoryPort):
        self.member_repo = member_repo
        self.user_repo = user_repo

    async def execute(self, *, company_id: str, user_id: str, settings: Dict[str, Any]) -> MemberDetail:
        """Aplica la lista blanca de claves de usuario (M2) tambien aqui, no solo en el esquema HTTP.

        No genera evento de auditoria.
        """
        try:
            validated = validate_member_settings(settings)
        except ValueError as exc:
            raise ValidationDomainException(str(exc)) from exc

        member = await self.member_repo.get_membership(user_id, company_id)
        if member is None:
            raise EntityNotFoundException(MSG_MEMBER_NOT_FOUND)
        user = await self.user_repo.get_by_id(user_id)
        member.settings = validated
        return MemberDetail(member=await self.member_repo.save(member), user=user)
