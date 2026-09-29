"""
Mapeador de persistencia para User y CompanyMember entre SQLAlchemy ORM y Entidades de Dominio.
"""
from typing import Optional
from domain.entities.user import User, UserRole
from domain.entities.company_member import CompanyMember, CompanyRole
import models


class SqlAlchemyUserMapper:

    @staticmethod
    def to_domain(orm_user: models.User) -> User:
        role_enum = UserRole.ADMIN if orm_user.role == models.UserRole.admin else UserRole.USER
        return User(
            id=str(orm_user.id),
            email=orm_user.email,
            first_name=orm_user.first_name or "",
            last_name=orm_user.last_name or "",
            is_active=bool(orm_user.is_active),
            role=role_enum,
            must_change_password=bool(orm_user.must_change_password),
            is_2fa_enabled=bool(orm_user.is_2fa_enabled),
            default_company_id=str(orm_user.default_company_id) if orm_user.default_company_id else None,
            created_at=orm_user.created_at,
        )

    @staticmethod
    def to_orm(domain_user: User, hashed_password: Optional[str] = None) -> models.User:
        role_orm = models.UserRole.admin if domain_user.role == UserRole.ADMIN else models.UserRole.user
        kwargs = {
            "id": domain_user.id,
            "email": domain_user.email,
            "first_name": domain_user.first_name,
            "last_name": domain_user.last_name,
            "is_active": domain_user.is_active,
            "role": role_orm,
            "must_change_password": domain_user.must_change_password,
            "is_2fa_enabled": domain_user.is_2fa_enabled,
            "default_company_id": domain_user.default_company_id,
        }
        if hashed_password:
            kwargs["hashed_password"] = hashed_password
        return models.User(**kwargs)


class SqlAlchemyCompanyMemberMapper:

    @staticmethod
    def to_domain(orm_member: models.CompanyMember) -> CompanyMember:
        role_str = str(orm_member.role.value if hasattr(orm_member.role, 'value') else orm_member.role)
        role_enum = CompanyRole(role_str) if role_str in ("admin", "manager", "worker") else CompanyRole.WORKER
        return CompanyMember(
            user_id=str(orm_member.user_id),
            company_id=str(orm_member.company_id),
            role=role_enum,
            is_active=bool(orm_member.is_active),
            sort_order=int(orm_member.sort_order or 0),
            rates_config=orm_member.rates_config or {},
            joined_at=orm_member.joined_at,
        )
