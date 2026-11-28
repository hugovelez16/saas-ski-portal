"""
Mapeador de persistencia para Company entre SQLAlchemy ORM y Entidades de Dominio.
"""

from typing import Any, Dict

import models
from domain.entities.company import Company

PLATFORM_SETTINGS_KEY = "_platform"


def split_stored_settings(raw: Dict[str, Any] | None) -> tuple[Dict[str, Any], Dict[str, Any]]:
    """Separa los ajustes de empresa y los ajustes de plataforma almacenados en `companies.settings`."""
    source = dict(raw or {})
    raw_platform = source.pop(PLATFORM_SETTINGS_KEY, None)
    platform = dict(raw_platform) if isinstance(raw_platform, dict) else {}
    return source, platform


def merge_stored_settings(settings: Dict[str, Any] | None, platform_settings: Dict[str, Any] | None) -> Dict[str, Any]:
    """Combina los ajustes de empresa y los de plataforma para persistirlos en la columna JSONB."""
    stored = dict(settings or {})
    stored.pop(PLATFORM_SETTINGS_KEY, None)
    if platform_settings:
        stored[PLATFORM_SETTINGS_KEY] = dict(platform_settings)
    return stored


class SqlAlchemyCompanyMapper:
    @staticmethod
    def to_domain(orm_company: models.Company) -> Company:
        settings, platform_settings = split_stored_settings(orm_company.settings)
        return Company(
            id=str(orm_company.id),
            name=orm_company.name,
            tax_config=orm_company.tax_config or {},
            worklog_definitions=orm_company.worklog_definitions or {},
            settings=settings,
            platform_settings=platform_settings,
            is_active=True if orm_company.is_active is None else bool(orm_company.is_active),
            is_managed=False if orm_company.is_managed is None else bool(orm_company.is_managed),
            created_at=orm_company.created_at,
            updated_at=orm_company.updated_at,
        )

    @staticmethod
    def to_orm(domain_company: Company) -> models.Company:
        kwargs = {
            "id": domain_company.id,
            "name": domain_company.name,
            "tax_config": domain_company.tax_config,
            "worklog_definitions": domain_company.worklog_definitions,
            "settings": merge_stored_settings(domain_company.settings, domain_company.platform_settings),
            "is_active": domain_company.is_active,
            "is_managed": domain_company.is_managed,
        }
        # Un None explicito sobrescribiria el default de la columna en el INSERT.
        if domain_company.updated_at is not None:
            kwargs["updated_at"] = domain_company.updated_at
        return models.Company(**kwargs)
