"""Caso de uso: aceptar una invitacion y crear o reactivar la membresia (R-MEM-07, R-MEM-23 a R-MEM-25)."""

from dataclasses import dataclass
from datetime import UTC, datetime

from access_policy import MSG_SUSPENDED
from application.use_cases.company.common import (
    DEFAULT_MEMBER_SORT_ORDER,
    MSG_COMPANY_NOT_FOUND,
    MemberDetail,
    member_snapshot,
)
from application.use_cases.company.invitation_common import MSG_INVITATION_WRONG_EMAIL, validate_active_invitation
from application.use_cases.company.plan_limits import ensure_member_limit_allows_addition
from audit import AuditAction
from domain.entities.company import Company
from domain.entities.company_invitation import hash_invitation_token, normalize_invitation_email
from domain.entities.company_member import CompanyMember, CompanyRole
from domain.exceptions.domain_exceptions import (
    EntityNotFoundException,
    UnauthorizedDomainActionException,
    ValidationDomainException,
)
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_invitation_repository_port import CompanyInvitationRepositoryPort
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort


@dataclass(frozen=True)
class AcceptInvitationResult:
    company: Company
    detail: MemberDetail
    changed: bool


class AcceptInvitationUseCase:
    def __init__(
        self,
        company_repo: CompanyRepositoryPort,
        member_repo: CompanyMemberRepositoryPort,
        user_repo: UserRepositoryPort,
        invitation_repo: CompanyInvitationRepositoryPort,
        audit_log: AuditLogPort,
    ):
        self.company_repo = company_repo
        self.member_repo = member_repo
        self.user_repo = user_repo
        self.invitation_repo = invitation_repo
        self.audit_log = audit_log

    async def execute(self, *, user_id: str, token: str) -> AcceptInvitationResult:
        """Valida el token y el correo de sesion, comprueba limites y crea/reactiva la membresia."""
        now = datetime.now(UTC)
        token_hash = hash_invitation_token(token)
        invitation = await self.invitation_repo.get_by_token_hash(token_hash, for_update=True)
        invitation = validate_active_invitation(invitation, now=now)

        user = await self.user_repo.get_by_id(user_id)
        if user is None:
            raise EntityNotFoundException("Usuario no encontrado")

        if normalize_invitation_email(user.email) != normalize_invitation_email(invitation.email):
            raise UnauthorizedDomainActionException(MSG_INVITATION_WRONG_EMAIL)

        if user.is_platform_admin:
            raise ValidationDomainException("Un administrador de plataforma no puede ser miembro de una empresa")

        company = await self.company_repo.get_by_id(invitation.company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)
        if not company.is_active:
            raise UnauthorizedDomainActionException(MSG_SUSPENDED)

        member = await self.member_repo.get_membership(user.id, company.id, for_update=True)
        invitation.accepted_at = now
        invitation.accepted_by_user_id = user.id

        if member is not None and member.is_active:
            await self.invitation_repo.save(invitation, commit=True)
            return AcceptInvitationResult(
                company=company,
                detail=MemberDetail(member=member, user=user),
                changed=False,
            )

        target_role = member.role if member is not None else CompanyRole.WORKER
        await ensure_member_limit_allows_addition(company, self.member_repo, target_role=target_role)

        if member is None:
            member = CompanyMember(
                user_id=user.id,
                company_id=company.id,
                role=CompanyRole.WORKER,
                is_active=True,
                sort_order=DEFAULT_MEMBER_SORT_ORDER,
            )
            action, before = AuditAction.MEMBER_ADDED, None
        else:
            before = member_snapshot(member)
            member.is_active = True
            action = AuditAction.MEMBER_REACTIVATED

        await self.audit_log.record(
            action=action,
            actor_id=user.id,
            company_id=company.id,
            target_user_id=user.id,
            old_value=before,
            new_value=member_snapshot(member),
            reason="invitation",
            extra={"invitation_id": invitation.id},
        )
        await self.invitation_repo.save(invitation, commit=False)
        saved_member = await self.member_repo.save(member)
        return AcceptInvitationResult(
            company=company,
            detail=MemberDetail(member=saved_member, user=user),
            changed=True,
        )
