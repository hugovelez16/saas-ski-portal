"""
Entidad de Dominio User: Representa la identidad de un usuario en el sistema.
"""
from dataclasses import dataclass
from datetime import datetime
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "admin"
    USER = "user"


@dataclass
class User:
    id: str
    email: str
    first_name: str = ""
    last_name: str = ""
    is_active: bool = True
    role: UserRole = UserRole.USER
    must_change_password: bool = False
    is_2fa_enabled: bool = False
    default_company_id: Optional[str] = None
    created_at: Optional[datetime] = None

    @property
    def full_name(self) -> str:
        names = [self.first_name, self.last_name]
        return " ".join([n for n in names if n]).strip()

    @property
    def is_platform_admin(self) -> bool:
        return self.role == UserRole.ADMIN

    def activate(self) -> None:
        self.is_active = True

    def deactivate(self) -> None:
        self.is_active = False
