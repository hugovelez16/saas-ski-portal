"""Comprobacion de limites del plan sobre miembros activos (R-MEM-24, R-MOD-22, R-EMP-45)."""

from contracts import PlatformSettings
from domain.entities.company import Company
from domain.entities.company_member import CompanyRole
from domain.exceptions.domain_exceptions import ConflictException
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort


async def ensure_member_limit_allows_addition(
    company: Company,
    member_repo: CompanyMemberRepositoryPort,
    *,
    target_role: CompanyRole = CompanyRole.WORKER,
) -> None:
    """Si la empresa tiene limites configurados en `platform_settings.limits`, bloquea al alcanzar el tope."""
    limits = PlatformSettings.from_db(company.platform_settings).limits
    if limits.max_monitors is None and limits.max_managers is None:
        return

    active_members = await member_repo.list_members_by_company(company.id, is_active=True)

    if target_role == CompanyRole.WORKER and limits.max_monitors is not None:
        active_workers = sum(1 for member in active_members if member.role == CompanyRole.WORKER)
        if active_workers >= limits.max_monitors:
            raise ConflictException("La empresa ha alcanzado el limite de monitores de su plan")
    elif target_role in (CompanyRole.MANAGER, CompanyRole.ADMIN) and limits.max_managers is not None:
        active_managers = sum(1 for member in active_members if member.is_manager)
        if active_managers >= limits.max_managers:
            raise ConflictException("La empresa ha alcanzado el limite de responsables de su plan")
