"""Piezas compartidas por los casos de uso de empresa de v2: mensajes, eventos de auditoria y vistas."""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from audit import AuditAction
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember
from domain.entities.user import User

# Mensajes identicos a los de v1 (crud.py, access_policy.py).
MSG_COMPANY_NOT_FOUND = "Empresa no encontrada"
MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_NO_CHANGES = "No hay cambios que guardar"
MSG_DELETE_BLOCKED = "No se puede borrar la empresa: tiene "

# Campos de empresa editables y su accion de auditoria, en el orden en que se emiten.
COMPANY_EVENT_ACTIONS = {
    "name": AuditAction.COMPANY_UPDATED,
    "is_active": AuditAction.COMPANY_SUSPENDED,
    "is_managed": AuditAction.COMPANY_MANAGED_CHANGED,
    "tax_config": AuditAction.COMPANY_TAX_CONFIG_CHANGED,
    "settings": AuditAction.COMPANY_SETTINGS_CHANGED,
    "worklog_definitions": AuditAction.COMPANY_DEFINITIONS_CHANGED,
}


def company_event(field_name: str, new_value: Any) -> str:
    if field_name == "is_active":
        return AuditAction.COMPANY_REACTIVATED if new_value else AuditAction.COMPANY_SUSPENDED
    return COMPANY_EVENT_ACTIONS[field_name]


def company_snapshot(company: Company) -> Dict[str, Any]:
    return {"name": company.name, "is_active": bool(company.is_active), "is_managed": bool(company.is_managed)}


@dataclass(frozen=True)
class CompanyView:
    """Empresa con la membresia del usuario que la consulta (si la hay) y el rol efectivo."""

    company: Company
    member: Optional[CompanyMember]
    role: Optional[str]


@dataclass(frozen=True)
class MemberDetail:
    member: CompanyMember
    user: Optional[User]


@dataclass(frozen=True)
class CompanyWithMembers:
    company: Company
    members: List[MemberDetail] = field(default_factory=list)
