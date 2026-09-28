from typing import Any

import auth
import crud
import models
from database import get_db
from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session


def check_manager_access(db: Session, manager: models.User, target_user_id: str) -> bool:
    """
    Check if manager has active manager scope for target user's company.
    """
    is_platform_admin = getattr(manager, "is_platform_admin", False)
    if is_platform_admin:
        return True

    active_cid = getattr(manager, "active_company_id", None)
    active_role = getattr(manager, "active_role", None)

    if not active_cid or active_role != "manager":
        return False

    # Check if target_user is a member of THIS active company
    access = db.query(models.CompanyMember).filter(
        models.CompanyMember.user_id == target_user_id,
        models.CompanyMember.company_id == active_cid,
        models.CompanyMember.is_active == True
    ).first()

    return bool(access)

def is_manager_of_company(db: Session, user: models.User, company_id: Any) -> bool:
    """
    Check if user has active manager scope in the specified company.
    """
    if getattr(user, "is_platform_admin", False):
        return True

    active_cid = getattr(user, "active_company_id", None)
    active_role = getattr(user, "active_role", None)

    if str(active_cid) == str(company_id) and active_role == "manager":
        return True

    return False


def require_module(code_name: str):
    """
    FastAPI dependency factory. Bloquea el acceso a un endpoint si el
    usuario actual (o su empresa activa) no tiene activo el módulo indicado.

    Uso:
        @router.get("/some-feature")
        def my_endpoint(
            db: Session = Depends(get_db),
            current_user: models.User = Depends(auth.get_verified_user),
            _: None = Depends(require_module("export_pdf"))
        ):
            ...
    """
    def dependency(
        current_user: models.User = Depends(auth.get_verified_user),
        db: Session = Depends(get_db)
    ):
        # Platform Admin siempre tiene acceso a todo
        if getattr(current_user, "is_platform_admin", False):
            return

        user_id = str(current_user.id)
        active_cid = getattr(current_user, "active_company_id", None)
        company_id = str(active_cid) if active_cid else None

        has_access = crud.user_has_module(db, user_id, company_id, code_name)
        if not has_access:
            raise HTTPException(
                status_code=403,
                detail=f"Tu cuenta no tiene acceso al módulo '{code_name}'. Contacta con el administrador."
            )

    return dependency

