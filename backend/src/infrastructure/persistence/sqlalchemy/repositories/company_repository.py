"""
Implementacion de UserRepositoryPort, CompanyRepositoryPort y CompanyMemberRepositoryPort con SQLAlchemy.

Transacciones: save y delete hacen commit (o rollback ante error). Por eso el caso de uso debe llamar
a audit.record ANTES de save/delete: la entrada de auditoria se confirma en la misma transaccion
que la operacion auditada.
"""

from typing import Dict, List, Optional

import access_cache
import models
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember
from domain.entities.user import User
from domain.exceptions.domain_exceptions import ConflictException
from domain.ports.repositories.company_repository_port import CompanyMemberRepositoryPort, CompanyRepositoryPort
from domain.ports.repositories.user_repository_port import UserRepositoryPort
from infrastructure.persistence.sqlalchemy.mappers.company_mapper import SqlAlchemyCompanyMapper
from infrastructure.persistence.sqlalchemy.mappers.user_mapper import (
    SqlAlchemyCompanyMemberMapper,
    SqlAlchemyUserMapper,
)
from redis_config import redis_manager
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from sqlalchemy.orm.attributes import flag_modified

DEPENDENT_DATA_MESSAGE = "No se puede eliminar: existen datos dependientes"


def _invalidate_member_caches(company_id, user_id) -> None:
    """Mismas caches que invalida v1 al cambiar una membresia: acceso del usuario y tarifas de la empresa."""
    redis_manager.delete(f"company_rates:{company_id}")
    access_cache.invalidate_membership(user_id, company_id)


def _commit_or_rollback(db: Session) -> None:
    """Confirma la transaccion; ante error de SQLAlchemy la revierte para no dejar la sesion rota."""
    try:
        db.commit()
    except SQLAlchemyError:
        db.rollback()
        raise


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

    async def count_active_platform_admins(self) -> int:
        # Platform admin = rol admin del sistema (mismo criterio que auth.py y crud.count_active_platform_admins).
        return (
            self.db.query(models.User)
            .filter(models.User.role == models.UserRole.admin, models.User.is_active.is_(True))
            .count()
        )


class SqlAlchemyCompanyRepository(CompanyRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_by_id(self, company_id: str) -> Optional[Company]:
        orm_c = self.db.query(models.Company).filter(models.Company.id == company_id).first()
        return SqlAlchemyCompanyMapper.to_domain(orm_c) if orm_c else None

    async def get_by_name(self, name: str) -> Optional[Company]:
        orm_c = self.db.query(models.Company).filter(models.Company.name == name).first()
        return SqlAlchemyCompanyMapper.to_domain(orm_c) if orm_c else None

    async def list_companies(self, *, skip: int = 0, limit: int = 100) -> List[Company]:
        orm_list = (
            self.db.query(models.Company)
            .order_by(models.Company.name.asc(), models.Company.id.asc())
            .offset(skip)
            .limit(limit)
            .all()
        )
        return [SqlAlchemyCompanyMapper.to_domain(c) for c in orm_list]

    async def count_companies(self) -> int:
        return self.db.query(models.Company).count()

    async def save(self, company: Company) -> Company:
        existing = self.db.query(models.Company).filter(models.Company.id == company.id).first()
        if existing:
            existing.name = company.name
            # Copia: el dominio puede reutilizar el mismo dict, y SQLAlchemy no detectaria el cambio en JSONB.
            existing.tax_config = dict(company.tax_config)
            existing.worklog_definitions = dict(company.worklog_definitions)
            existing.settings = dict(company.settings)
            existing.is_active = company.is_active
            existing.is_managed = company.is_managed
            _commit_or_rollback(self.db)
            self.db.refresh(existing)
            # Suspension, gestion o nombre cambian los hechos de acceso cacheados (igual que crud.update_company).
            access_cache.invalidate_company(existing.id)
            return SqlAlchemyCompanyMapper.to_domain(existing)
        else:
            orm_c = SqlAlchemyCompanyMapper.to_orm(company)
            self.db.add(orm_c)
            _commit_or_rollback(self.db)
            self.db.refresh(orm_c)
            return SqlAlchemyCompanyMapper.to_domain(orm_c)

    async def delete(self, company_id: str) -> None:
        # Borrado masivo: sin cascada ORM (que anularia work_logs.company_id en silencio).
        # Si quedan dependencias la BD rechaza el borrado; el llamador debe consultar count_dependencies antes.
        try:
            self.db.query(models.Company).filter(models.Company.id == company_id).delete(
                synchronize_session="fetch"
            )
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException(DEPENDENT_DATA_MESSAGE) from exc
        except SQLAlchemyError:
            self.db.rollback()
            raise
        access_cache.invalidate_company(company_id)

    async def count_dependencies(self, company_id: str) -> Dict[str, int]:
        members = self.db.query(models.CompanyMember).filter(models.CompanyMember.company_id == company_id).count()
        work_logs = self.db.query(models.WorkLog).filter(models.WorkLog.company_id == company_id).count()
        subscriptions = (
            self.db.query(models.ModuleSubscription).filter(models.ModuleSubscription.company_id == company_id).count()
        )
        return {"members": members, "work_logs": work_logs, "subscriptions": subscriptions}


class SqlAlchemyCompanyMemberRepository(CompanyMemberRepositoryPort):
    def __init__(self, db: Session):
        self.db = db

    async def get_membership(
        self, user_id: str, company_id: str, *, for_update: bool = False
    ) -> Optional[CompanyMember]:
        query = self.db.query(models.CompanyMember).filter(
            models.CompanyMember.user_id == user_id,
            models.CompanyMember.company_id == company_id,
        )
        if for_update:
            # Igual que crud.remove_member: bloquea la fila y refresca el estado ya leido en la sesion.
            query = query.with_for_update().populate_existing()
        orm_m = query.first()
        return SqlAlchemyCompanyMemberMapper.to_domain(orm_m) if orm_m else None

    async def list_members_by_company(self, company_id: str, is_active: Optional[bool] = None) -> List[CompanyMember]:
        query = self.db.query(models.CompanyMember).filter(models.CompanyMember.company_id == company_id)
        if is_active is not None:
            query = query.filter(models.CompanyMember.is_active.is_(is_active))
        orm_list = query.order_by(
            models.CompanyMember.sort_order.asc(),
            models.CompanyMember.joined_at.asc(),
            models.CompanyMember.user_id.asc(),
        ).all()
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
            # Copias: ver nota en CompanyRepository.save sobre la deteccion de cambios en JSONB.
            existing.rates_config = dict(member.rates_config)
            existing.settings = dict(member.settings)
            # Igual que crud.set_member_*: fuerza el UPDATE (y `updated_at`) aunque el valor no cambie.
            flag_modified(existing, "rates_config")
            flag_modified(existing, "settings")
            _commit_or_rollback(self.db)
            self.db.refresh(existing)
            _invalidate_member_caches(member.company_id, member.user_id)
            return SqlAlchemyCompanyMemberMapper.to_domain(existing)
        else:
            orm_m = SqlAlchemyCompanyMemberMapper.to_orm(member)
            self.db.add(orm_m)
            _commit_or_rollback(self.db)
            self.db.refresh(orm_m)
            _invalidate_member_caches(member.company_id, member.user_id)
            return SqlAlchemyCompanyMemberMapper.to_domain(orm_m)

    async def delete(self, user_id: str, company_id: str) -> None:
        try:
            self.db.query(models.CompanyMember).filter(
                models.CompanyMember.user_id == user_id,
                models.CompanyMember.company_id == company_id,
            ).delete(synchronize_session="fetch")
            self.db.commit()
        except IntegrityError as exc:
            self.db.rollback()
            raise ConflictException(DEPENDENT_DATA_MESSAGE) from exc
        except SQLAlchemyError:
            self.db.rollback()
            raise
        _invalidate_member_caches(company_id, user_id)

    async def reorder(self, company_id: str, user_ids: List[str]) -> None:
        orm_members = (
            self.db.query(models.CompanyMember)
            .filter(models.CompanyMember.company_id == company_id, models.CompanyMember.user_id.in_(user_ids))
            .all()
        )
        positions = {str(user_id): index for index, user_id in enumerate(user_ids)}
        for orm_m in orm_members:
            orm_m.sort_order = positions[str(orm_m.user_id)]
        _commit_or_rollback(self.db)
        # Igual que crud.update_company_members_order, no invalida nada: el orden no cambia permisos
        # y la cache de tarifas de v1 no depende de `sort_order`.

    async def count_work_logs(self, user_id: str, company_id: str) -> int:
        return (
            self.db.query(models.WorkLog)
            .filter(
                models.WorkLog.user_id == user_id,
                models.WorkLog.company_id == company_id,
            )
            .count()
        )
