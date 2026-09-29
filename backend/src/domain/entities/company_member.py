"""
Entidad de Dominio CompanyMember: Representa la membresia y permisos de un usuario en una empresa.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional, Dict, Any
from enum import Enum


class CompanyRole(str, Enum):
    ADMIN = "admin"
    MANAGER = "manager"
    WORKER = "worker"


@dataclass
class CompanyMember:
    user_id: str
    company_id: str
    role: CompanyRole = CompanyRole.WORKER
    is_active: bool = True
    sort_order: int = 0
    rates_config: Dict[str, Any] = field(default_factory=dict)
    joined_at: Optional[datetime] = None

    @property
    def is_manager(self) -> bool:
        return self.role in (CompanyRole.ADMIN, CompanyRole.MANAGER)

    def can_manage_team(self) -> bool:
        return self.is_active and self.is_manager
