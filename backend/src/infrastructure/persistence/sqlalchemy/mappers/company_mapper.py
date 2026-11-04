"""
Mapeador de persistencia para Company entre SQLAlchemy ORM y Entidades de Dominio.
"""

import models
from domain.entities.company import Company


class SqlAlchemyCompanyMapper:
    @staticmethod
    def to_domain(orm_company: models.Company) -> Company:
        return Company(
            id=str(orm_company.id),
            name=orm_company.name,
            tax_config=orm_company.tax_config or {},
            worklog_definitions=orm_company.worklog_definitions or {},
            settings=orm_company.settings or {},
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
            "settings": domain_company.settings,
            "is_active": domain_company.is_active,
            "is_managed": domain_company.is_managed,
        }
        # Un None explicito sobrescribiria el default de la columna en el INSERT.
        if domain_company.updated_at is not None:
            kwargs["updated_at"] = domain_company.updated_at
        return models.Company(**kwargs)
