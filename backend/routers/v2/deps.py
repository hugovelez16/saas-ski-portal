"""Fabricas de repositorios y casos de uso de v2 a partir de la sesion de BD de la peticion.

La autorizacion no vive aqui: los routers de v2 reutilizan `routers.deps.require_company`,
`routers.deps.require_platform_admin` y `access_policy`.
"""

from database import get_db
from fastapi import Depends
from infrastructure.persistence.sqlalchemy.repositories.audit_repository import SqlAlchemyAuditLog
from infrastructure.persistence.sqlalchemy.repositories.company_repository import (
    SqlAlchemyCompanyMemberRepository,
    SqlAlchemyCompanyRepository,
    SqlAlchemyUserRepository,
)
from sqlalchemy.orm import Session


def get_company_repository(db: Session = Depends(get_db)) -> SqlAlchemyCompanyRepository:
    return SqlAlchemyCompanyRepository(db)


def get_member_repository(db: Session = Depends(get_db)) -> SqlAlchemyCompanyMemberRepository:
    return SqlAlchemyCompanyMemberRepository(db)


def get_user_repository(db: Session = Depends(get_db)) -> SqlAlchemyUserRepository:
    return SqlAlchemyUserRepository(db)


def get_audit_log(db: Session = Depends(get_db)) -> SqlAlchemyAuditLog:
    return SqlAlchemyAuditLog(db)
