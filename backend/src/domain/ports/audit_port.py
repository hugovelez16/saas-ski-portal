"""
Puerto de Auditoria. Registra acciones sobre empresas, membresias y usuarios.
La entrada se anade a la transaccion en curso; el commit lo hace el repositorio que la usa.
"""

from abc import ABC, abstractmethod
from typing import Any, Optional


class AuditLogPort(ABC):
    @abstractmethod
    async def record(
        self,
        *,
        action: str,
        actor_id: Any,
        company_id: Optional[Any] = None,
        target_user_id: Optional[Any] = None,
        old_value: Optional[dict] = None,
        new_value: Optional[dict] = None,
        reason: Optional[str] = None,
    ) -> None:
        pass
