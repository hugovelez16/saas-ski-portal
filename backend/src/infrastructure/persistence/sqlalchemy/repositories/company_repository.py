"""
Implementacion de UserRepositoryPort, CompanyRepositoryPort y CompanyMemberRepositoryPort con SQLAlchemy.
"""

from typing import List, Optional

import models
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember
from domain.entities.user import User
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort
from infrastructure.persistence.sqlalchemy.mappers.company_mapper import SqlAlchemyCompanyMapper
from infrastructure.persistence.sqlalchemy.mappers.user_mapper import (
    SqlAlchemyCompanyMemberMapper,
    SqlAlchemyUserMapper,
)
from sqlalchemy.orm import Session


class SqlAlchemyUserRepository(UserRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_by_id(self, user_id: str) -> Optional[User]:
        orm_user = self.db.query(models.User).filter(models.User.id == user_id).first()
        return SqlAlchemyUserMapper.to_domain(orm_user) if orm_user else None

    async def get_by_email(self, email: str) -> Optional[User]:
        orm_user = self.db.query(models.User).filter(models.User.email == email).first()
        return SqlAlchemyUserMapper.to_domain(orm_user) if orm_user else None

    async def list_users(self, skip: int = 0, limit: int = 100) -> List[User]:
        orm_users = self.db.query(models.User).offset(skip).limit(limit).all()
        return [SqlAlchemyUserMapper.to_domain(u) for u in orm_users]

    async def save(self, user: User) -> User:
        existing = self.db.query(models.User).filter(models.User.id == user.id).first()
        if existing:
            existing.first_name = user.first_name
            existing.last_name = user.last_name
            existing.is_active = user.is_active
            existing.default_company_id = user.default_company_id
            self.db.commit()
            self.db.refresh(existing)
            return SqlAlchemyUserMapper.to_domain(existing)
        else:
            orm_user = SqlAlchemyUserMapper.to_orm(user)
            self.db.add(orm_user)
            self.db.commit()
            self.db.refresh(orm_user)
            return SqlAlchemyUserMapper.to_domain(orm_user)

    async def update_status(self, user_id: str, is_active: bool) -> Optional[User]:
        existing = self.db.query(models.User).filter(models.User.id == user_id).first()
        if existing:
            existing.is_active = is_active
            self.db.commit()
            self.db.refresh(existing)
            return SqlAlchemyUserMapper.to_domain(existing)
        return None


class SqlAlchemyCompanyRepository(CompanyRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        orm_c = self.db.query(models.Company).filter(models.Company.id == company_id).first()
        return SqlAlchemyCompanyMapper.to_domain(orm_c) if orm_c else None

    async def get_by_name(self, name: str) -> Optional[Company]:
        orm_c = self.db.query(models.Company).filter(models.Company.name == name).first()
        return SqlAlchemyCompanyMapper.to_domain(orm_c) if orm_c else None

    async def list_companies(self) -> List[Company]:
        orm_list = self.db.query(models.Company).all()
        return [SqlAlchemyCompanyMapper.to_domain(c) for c in orm_list]

    async def save(self, company: Company) -> Company:
        existing = self.db.query(models.Company).filter(models.Company.id == company.id).first()
        if existing:
            existing.name = company.name
            existing.fiscal_id = company.fiscal_id
            existing.tax_config = company.tax_config
            existing.worklog_definitions = company.worklog_definitions
            existing.settings = company.settings
            self.db.commit()
            self.db.refresh(existing)
            return SqlAlchemyCompanyMapper.to_domain(existing)
        else:
            orm_c = SqlAlchemyCompanyMapper.to_orm(company)
            self.db.add(orm_c)
            self.db.commit()
            self.db.refresh(orm_c)
            return SqlAlchemyCompanyMapper.to_domain(orm_c)


class SqlAlchemyCompanyMemberRepository(CompanyMemberRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_membership(self, user_id: str, company_id: str) -> Optional[CompanyMember]:
        orm_m = (
            self.db.query(models.CompanyMember)
            .filter(
                models.CompanyMember.user_id == user_id,
                models.CompanyMember.company_id == company_id,
            )
            .first()
        )
        return SqlAlchemyCompanyMemberMapper.to_domain(orm_m) if orm_m else None

    async def list_members_by_company(self, company_id: str) -> List[CompanyMember]:
        orm_list = (
            self.db.query(models.CompanyMember)
            .filter(models.CompanyMember.company_id == company_id)
            .order_by(models.CompanyMember.sort_order.asc())
            .all()
        )
        return [SqlAlchemyCompanyMemberMapper.to_domain(m) for m in orm_list]

    async def list_companies_by_user(self, user_id: str) -> List[CompanyMember]:
        orm_list = self.db.query(models.CompanyMember).filter(models.CompanyMember.user_id == user_id).all()
        return [SqlAlchemyCompanyMemberMapper.to_domain(m) for m in orm_list]

    async def save(self, member: CompanyMember) -> CompanyMember:
        existing = (
            self.db.query(models.CompanyMember)
            .filter(
                models.CompanyMember.user_id == member.user_id,
                models.CompanyMember.company_id == member.company_id,
            )
            .first()
        )
        if existing:
            existing.role = getattr(models.CompanyRole, member.role.value)
            existing.is_active = member.is_active
            existing.sort_order = member.sort_order
            existing.rates_config = member.rates_config
            self.db.commit()
            self.db.refresh(existing)
            return SqlAlchemyCompanyMemberMapper.to_domain(existing)
        else:
            orm_m = models.CompanyMember(
                user_id=member.user_id,
                company_id=member.company_id,
                role=getattr(models.CompanyRole, member.role.value),
                is_active=member.is_active,
                sort_order=member.sort_order,
                rates_config=member.rates_config,
            )
            self.db.add(orm_m)
            self.db.commit()
            self.db.refresh(orm_m)
            return SqlAlchemyCompanyMemberMapper.to_domain(orm_m)
