"""Caso de uso: edicion de empresa y ajustes (autorizacion decidida por el router)."""

import copy
from typing import Any, Dict, Optional

from application.use_cases.company.common import (
    COMPANY_EVENT_ACTIONS,
    MSG_COMPANY_NOT_FOUND,
    company_event,
)
from contracts import CompanySettings, PlatformSettings
from domain.entities.company import Company
from domain.exceptions.domain_exceptions import ConflictException, EntityNotFoundException
from domain.ports.audit_port import AuditLogPort
from domain.ports.repositories.company_repository_port import CompanyRepositoryPort


def _normalize_for_diff(field_name: str, value: Any) -> Any:
    """Normaliza defaults de campos JSON para detectar guardados sin cambios reales (R-EMP-16)."""
    if field_name == "settings":
        return CompanySettings.from_db(value).model_dump(mode="json")
    if field_name == "platform_settings":
        return PlatformSettings.from_db(value).model_dump(mode="json")
    if field_name == "worklog_definitions" and isinstance(value, dict):
        normalized: Dict[str, Any] = {}
        for key, raw_def in value.items():
            if not isinstance(raw_def, dict):
                normalized[key] = raw_def
                continue
            item = dict(raw_def)
            item.setdefault("options", [])
            item.setdefault("is_active", True)
            normalized[key] = item
        return normalized
    return value


class UpdateCompanyUseCase:
    def __init__(self, company_repo: CompanyRepositoryPort, audit_log: AuditLogPort):
        self.company_repo = company_repo
        self.audit_log = audit_log

    async def execute(
        self,
        *,
        actor_id: str,
        company_id: str,
        changes: Dict[str, Any],
        reason: Optional[str] = None,
    ) -> Company:
        """`changes` contiene solo los campos enviados (JSON plano).

        - Sin cambios reales (incluido `{}` o mismos valores): devuelve la empresa sin modificar nada ni auditar (R-EMP-16).
        - Al eliminar un tipo de turno de `worklog_definitions`, rechaza con 409 si tiene turnos en BD;
          si tiene 0 turnos, limpia sus tarifas asociadas en `rates_config` (R-EMP-41).
        """
        company = await self.company_repo.get_by_id(company_id)
        if company is None:
            raise EntityNotFoundException(MSG_COMPANY_NOT_FOUND)

        diffs = []
        for field_name in COMPANY_EVENT_ACTIONS:
            if field_name not in changes:
                continue
            old_value = getattr(company, field_name)
            new_value = changes[field_name]
            if _normalize_for_diff(field_name, old_value) != _normalize_for_diff(field_name, new_value):
                diffs.append((field_name, old_value, new_value))
        if not diffs:
            return company

        removed_types: list[str] = []
        for field_name, old_value, new_value in diffs:
            if field_name == "worklog_definitions":
                old_defs = old_value if isinstance(old_value, dict) else {}
                new_defs = new_value if isinstance(new_value, dict) else {}
                removed_types = [key for key in old_defs if key not in new_defs]
                if removed_types:
                    counts = await self.company_repo.count_work_logs_by_types(company_id, removed_types)
                    blocked = [(shift_type, count) for shift_type, count in counts.items() if count > 0]
                    if blocked:
                        shift_type, count = blocked[0]
                        raise ConflictException(
                            f"No se puede borrar el tipo de turno '{shift_type}' porque tiene {count} turnos "
                            "registrados; puedes desactivarlo"
                        )

        for field_name, old_value, new_value in diffs:
            await self.audit_log.record(
                action=company_event(field_name, new_value),
                actor_id=actor_id,
                company_id=company.id,
                old_value={field_name: old_value},
                new_value={field_name: new_value},
                reason=reason if field_name == "is_active" else None,
            )
        for field_name, _old_value, new_value in diffs:
            setattr(company, field_name, copy.deepcopy(new_value))
        saved = await self.company_repo.save(company)
        if removed_types:
            await self.company_repo.remove_shift_types_from_rates(company_id, removed_types)
        return saved
