"""Politica central de permisos sobre una empresa.

Modulo puro: sin imports de fastapi ni sqlalchemy. Decide a partir de hechos ya
cargados (CompanyFacts); quien lo llama se encarga de leerlos de BD o cache y de
traducir PolicyError a HTTP.
"""

from dataclasses import dataclass

ROLE_PLATFORM_ADMIN = "platform_admin"
ROLE_MANAGER = "manager"
ROLE_WORKER = "worker"

VIEW_AS_ROLES = frozenset({ROLE_WORKER, ROLE_MANAGER})
SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})
VIEW_AS_WRITE_ALLOWLIST = frozenset({"/auth/switch-scope", "/logout", "/refresh-token"})

MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_FORBIDDEN = "No tienes permisos para esta accion"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_SWITCH_COMPANY = "Cambia a esta empresa para gestionarla"
MSG_MANAGED_READONLY = "En empresas gestionadas solo el equipo gestor puede modificar turnos y tarifas"
MSG_VIEW_AS_READONLY = "Modo 'ver como' de solo lectura: sal del modo para modificar datos"

_ROLE_RANK = {ROLE_WORKER: 1, ROLE_MANAGER: 2}


class PolicyError(Exception):
    def __init__(self, status_code: int, detail: str):
        super().__init__(detail)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class CompanyFacts:
    company_id: str
    exists: bool
    is_active: bool
    is_managed: bool
    membership_active: bool
    membership_role: str | None  # ya normalizado


def normalize_member_role(role: str | None) -> str | None:
    """El rol `admin` de membresia esta reservado y se trata como manager."""
    if role in ("admin", ROLE_MANAGER):
        return ROLE_MANAGER
    if role == ROLE_WORKER:
        return ROLE_WORKER
    return None


def assert_view_as_read_only(view_as: str | None, method: str, path: str) -> None:
    if view_as and method.upper() not in SAFE_METHODS and path not in VIEW_AS_WRITE_ALLOWLIST:
        raise PolicyError(403, MSG_VIEW_AS_READONLY)


def _rank(role: str | None) -> int:
    return _ROLE_RANK.get(role or "", 0)


def authorize_company(
    *,
    is_platform_admin: bool,
    view_as: str | None = None,
    token_company_id: str | None,
    facts: CompanyFacts,
    min_role: str,
) -> str:
    """Devuelve el rol efectivo sobre la empresa o lanza PolicyError.

    La membresia se comprueba ANTES que la suspension para no revelar la
    existencia de empresas suspendidas a quien no es miembro.
    """
    if min_role not in (ROLE_WORKER, ROLE_MANAGER, ROLE_PLATFORM_ADMIN):
        raise ValueError(f"min_role invalido: {min_role}")

    if is_platform_admin:
        if not facts.exists:
            raise PolicyError(404, "Empresa no encontrada")
        if view_as in VIEW_AS_ROLES:
            if min_role == ROLE_PLATFORM_ADMIN or _rank(view_as) < _rank(min_role):
                raise PolicyError(403, MSG_FORBIDDEN)
            if min_role == ROLE_MANAGER and token_company_id != facts.company_id:
                raise PolicyError(403, MSG_SWITCH_COMPANY)
            return view_as
        return ROLE_PLATFORM_ADMIN

    if not facts.exists or not facts.membership_active:
        raise PolicyError(403, MSG_NO_ACCESS)
    if not facts.is_active:
        raise PolicyError(403, MSG_SUSPENDED)
    if min_role == ROLE_PLATFORM_ADMIN:
        raise PolicyError(403, MSG_FORBIDDEN)
    role = normalize_member_role(facts.membership_role)
    if role is None or _rank(role) < _rank(min_role):
        raise PolicyError(403, MSG_FORBIDDEN)
    if min_role == ROLE_MANAGER and token_company_id != facts.company_id:
        raise PolicyError(403, MSG_SWITCH_COMPANY)
    return role


def require_platform_admin(is_platform_admin: bool) -> None:
    if not is_platform_admin:
        raise PolicyError(403, MSG_FORBIDDEN)


def can_write_work_log(*, role: str, is_managed: bool, is_owner: bool) -> None:
    if role in (ROLE_PLATFORM_ADMIN, ROLE_MANAGER):
        return
    if is_managed:
        raise PolicyError(403, MSG_MANAGED_READONLY)
    if not is_owner:
        raise PolicyError(403, MSG_FORBIDDEN)


def can_edit_member_rates(*, role: str, is_managed: bool, is_self: bool) -> None:
    if role in (ROLE_PLATFORM_ADMIN, ROLE_MANAGER):
        return
    if not is_self:
        raise PolicyError(403, MSG_FORBIDDEN)
    if is_managed:
        raise PolicyError(403, MSG_MANAGED_READONLY)


def can_edit_member_settings(*, role: str, is_self: bool) -> None:
    if role in (ROLE_PLATFORM_ADMIN, ROLE_MANAGER):
        return
    if not is_self:
        raise PolicyError(403, MSG_FORBIDDEN)
