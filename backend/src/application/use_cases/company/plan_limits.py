"""Comprobacion de limites del plan sobre miembros activos (R-MEM-24, R-MOD-22)."""

from domain.entities.company import Company
from domain.entities.company_member import CompanyRole
from domain.exceptions.domain_exceptions import ConflictException
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort


def _positive_int_limit(value) -> int | None:
    if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
        return value
    return None


def extract_plan_limits(company: Company) -> dict[str, int]:
    """Extrae limites de miembros si la empresa los tiene configurados en `settings.plan_limits`."""
    settings = company.settings if isinstance(company.settings, dict) else {}
    raw_limits = settings.get("plan_limits")
    if not isinstance(raw_limits, dict):
        return {}
    limits: dict[str, int] = {}
    for key in ("max_members", "max_workers", "max_managers"):
        parsed = _positive_int_limit(raw_limits.get(key))
        if parsed is not None:
            limits[key] = parsed
    return limits


async def ensure_member_limit_allows_addition(
    company: Company,
    member_repo: CompanyMemberRepositoryPort,
    *,
    target_role: CompanyRole = CompanyRole.WORKER,
) -> None:
    """Si la empresa tiene limites configurados, bloquea cuando los miembros activos alcanzan el tope."""
    limits = extract_plan_limits(company)
    if not limits:
        return

    active_members = await member_repo.list_members_by_company(company.id, is_active=True)

    max_members = limits.get("max_members")
    if max_members is not None and len(active_members) >= max_members:
        raise ConflictException("La empresa ha alcanzado el limite de miembros de su plan")

    if target_role == CompanyRole.WORKER:
        max_workers = limits.get("max_workers")
        if max_workers is not None:
            active_workers = sum(1 for member in active_members if member.role == CompanyRole.WORKER)
            if active_workers >= max_workers:
                raise ConflictException("La empresa ha alcanzado el limite de trabajadores de su plan")
    elif target_role in (CompanyRole.MANAGER, CompanyRole.ADMIN):
        max_managers = limits.get("max_managers")
        if max_managers is not None:
            active_managers = sum(1 for member in active_members if member.is_manager)
            if active_managers >= max_managers:
                raise ConflictException("La empresa ha alcanzado el limite de responsables de su plan")
