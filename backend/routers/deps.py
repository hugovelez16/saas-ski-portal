"""Dependencias de autorizacion: unico punto donde un router decide quien puede que sobre una empresa.

Lee rol y estados de BD (con cache en `access_cache`) y delega la decision en `access_policy`.
"""

import uuid
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import access_cache
import access_policy
import auth
import crud
import models
from access_policy import CompanyFacts, PolicyError
from database import get_db
from fastapi import Depends
from sqlalchemy.orm import Session


@dataclass
class AccessContext:
    db: Session
    user: models.User
    role: str
    is_platform_admin: bool
    is_managed: bool
    company_id: str | None
    is_read_only_view: bool
    _company: models.Company | None = field(default=None, init=False, repr=False)

    @property
    def company(self) -> models.Company | None:
        """Carga perezosa de la empresa desde BD (None si no existe)."""
        if not self.company_id:
            return None
        if self._company is None:
            self._company = self.db.get(models.Company, uuid.UUID(self.company_id))
        return self._company


def acting_platform_admin(user) -> bool:
    """PA real (BD) que no esta en modo 'ver como'. Toda decision de permisos usa esta funcion."""
    return bool(getattr(user, "is_platform_admin", False)) and not getattr(user, "view_as", None)


def canonical_id(value: Any) -> str | None:
    if value is None:
        return None
    try:
        return str(uuid.UUID(str(value)))
    except (ValueError, AttributeError, TypeError):
        return None


def load_company_facts(db: Session, user, company_id: Any) -> CompanyFacts:
    cid = canonical_id(company_id)
    if cid is None:
        return CompanyFacts(
            company_id=str(company_id),
            exists=False,
            is_active=False,
            is_managed=False,
            membership_active=False,
            membership_role=None,
        )
    uid = str(user.id)

    cached = access_cache.get_access(uid, cid)
    if cached is not None:
        return CompanyFacts(
            company_id=cid,
            exists=True,
            is_active=bool(cached.get("company_active")),
            is_managed=bool(cached.get("is_managed")),
            membership_active=bool(cached.get("membership_active")),
            membership_role=cached.get("membership_role"),
        )

    company = db.get(models.Company, uuid.UUID(cid))
    if company is None:
        return CompanyFacts(
            company_id=cid,
            exists=False,
            is_active=False,
            is_managed=False,
            membership_active=False,
            membership_role=None,
        )
    member = (
        db.query(models.CompanyMember)
        .filter(models.CompanyMember.user_id == user.id, models.CompanyMember.company_id == company.id)
        .first()
    )
    membership_active = bool(member and member.is_active)
    role = access_policy.normalize_member_role(getattr(member.role, "value", member.role)) if member else None
    facts = {
        "company_active": bool(company.is_active),
        "is_managed": bool(company.is_managed),
        "membership_active": membership_active,
        "membership_role": role,
    }
    access_cache.set_access(uid, cid, facts)
    return CompanyFacts(
        company_id=cid,
        exists=True,
        is_active=facts["company_active"],
        is_managed=facts["is_managed"],
        membership_active=membership_active,
        membership_role=role,
    )


def authorize(
    db: Session,
    user: models.User,
    company_id: Any,
    *,
    min_role: str = access_policy.ROLE_WORKER,
    module: str | None = None,
) -> AccessContext:
    facts = load_company_facts(db, user, company_id)
    view_as = getattr(user, "view_as", None)
    role = access_policy.authorize_company(
        is_platform_admin=bool(getattr(user, "is_platform_admin", False)),
        view_as=view_as,
        token_company_id=canonical_id(getattr(user, "active_company_id", None)),
        facts=facts,
        min_role=min_role,
    )
    # Aislamiento por token: quien no es PA y tiene empresa activa (cid) no accede a otra empresa
    # hasta cambiar de scope, sea cual sea el rol minimo exigido.
    active_cid = canonical_id(getattr(user, "active_company_id", None))
    if not getattr(user, "is_platform_admin", False) and active_cid and active_cid != facts.company_id:
        raise PolicyError(403, access_policy.MSG_SWITCH_COMPANY)
    if module and role != access_policy.ROLE_PLATFORM_ADMIN:
        if not crud.user_has_module(db, str(user.id), facts.company_id, module):
            raise PolicyError(
                403, f"Tu cuenta no tiene acceso al módulo '{module}'. Contacta con el administrador."
            )
    return AccessContext(
        db=db,
        user=user,
        role=role,
        is_platform_admin=role == access_policy.ROLE_PLATFORM_ADMIN,
        is_managed=facts.is_managed,
        company_id=facts.company_id,
        is_read_only_view=bool(view_as),
    )


def require_company(min_role: str = access_policy.ROLE_WORKER, module: str | None = None):
    """Fabrica de dependencia que usa el path param `company_id: UUID`."""

    def dependency(
        company_id: UUID,
        db: Session = Depends(get_db),
        user: models.User = Depends(auth.get_verified_user),
    ) -> AccessContext:
        return authorize(db, user, company_id, min_role=min_role, module=module)

    return dependency


def require_platform_admin(user: models.User = Depends(auth.get_verified_user)) -> models.User:
    access_policy.require_platform_admin(acting_platform_admin(user))
    return user


def manages_user(db: Session, actor: models.User, target_user_id: Any) -> bool:
    """True si el actor es PA actuando o manager de una empresa donde el objetivo tiene membresia activa."""
    if acting_platform_admin(actor):
        return True
    active_cid = canonical_id(getattr(actor, "active_company_id", None))
    if not active_cid:
        return False
    try:
        authorize(db, actor, active_cid, min_role=access_policy.ROLE_MANAGER)
    except PolicyError:
        return False
    target = canonical_id(target_user_id)
    if target is None:
        return False
    membership = (
        db.query(models.CompanyMember)
        .filter(
            models.CompanyMember.user_id == uuid.UUID(target),
            models.CompanyMember.company_id == uuid.UUID(active_cid),
            models.CompanyMember.is_active == True,  # noqa: E712
        )
        .first()
    )
    return membership is not None


def require_active_member(db: Session, user_id: Any, company_id: Any) -> models.CompanyMember:
    uid, cid = canonical_id(user_id), canonical_id(company_id)
    member = None
    if uid and cid:
        member = (
            db.query(models.CompanyMember)
            .filter(
                models.CompanyMember.user_id == uuid.UUID(uid),
                models.CompanyMember.company_id == uuid.UUID(cid),
                models.CompanyMember.is_active == True,  # noqa: E712
            )
            .first()
        )
    if member is None:
        raise PolicyError(422, "El usuario no tiene una membresia activa en esta empresa")
    return member


def require_module(code_name: str):
    """Dependencia que exige el modulo activo para el usuario o su empresa activa. El PA actuando pasa siempre."""

    def dependency(
        current_user: models.User = Depends(auth.get_verified_user),
        db: Session = Depends(get_db),
    ) -> None:
        if acting_platform_admin(current_user):
            return
        company_id = canonical_id(getattr(current_user, "active_company_id", None))
        if not crud.user_has_module(db, str(current_user.id), company_id, code_name):
            raise PolicyError(
                403, f"Tu cuenta no tiene acceso al módulo '{code_name}'. Contacta con el administrador."
            )

    return dependency
