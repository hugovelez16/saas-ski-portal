"""
Mapeador de persistencia para Company entre SQLAlchemy ORM y Entidades de Dominio.
"""
from domain.entities.company import Company
import models


class SqlAlchemyCompanyMapper:

    @staticmethod
    def to_domain(orm_company: models.Company) -> Company:
        return Company(
            id=str(orm_company.id),
            name=orm_company.name,
            fiscal_id=orm_company.fiscal_id,
            tax_config=orm_company.tax_config or {},
            worklog_definitions=orm_company.worklog_definitions or {},
            settings=orm_company.settings or {},
            created_at=orm_company.created_at,
        )

    @staticmethod
    def to_orm(domain_company: Company) -> models.Company:
        return models.Company(
            id=domain_company.id,
            name=domain_company.name,
            fiscal_id=domain_company.fiscal_id,
            tax_config=domain_company.tax_config,
            worklog_definitions=domain_company.worklog_definitions,
            settings=domain_company.settings,
        )
