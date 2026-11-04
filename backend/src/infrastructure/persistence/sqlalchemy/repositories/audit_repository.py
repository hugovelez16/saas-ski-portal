"""
Implementacion de AuditLogPort con SQLAlchemy. Delega en audit.record_audit.

No hace commit: la entrada se confirma junto con la operacion auditada, porque el commit
lo hace el save/delete del repositorio de la misma sesion. Por tanto el caso de uso debe
llamar a audit.record ANTES de save/delete para que ambos se confirmen en la misma transaccion.
"""

from typing import Any, Optional

import audit
from domain.ports.audit_port import AuditLogPort
from sqlalchemy.orm import Session


class SqlAlchemyAuditLog(AuditLogPort):
    """Registro de auditoria sobre la sesion compartida. record() no confirma: ver docstring del modulo.

    Orden obligatorio en los casos de uso: audit.record(...) y luego save/delete del repositorio.
    """

    def __init__(self, db: Session):
        self.db = db

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
        audit.record_audit(
            self.db,
            action=action,
            actor_id=actor_id,
            company_id=company_id,
            target_user_id=target_user_id,
            old_value=old_value,
            new_value=new_value,
            reason=reason,
        )
