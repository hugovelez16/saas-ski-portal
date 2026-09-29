"""
Módulos y Suscripciones SaaS.

Gestión del catálogo de módulos de la plataforma y las suscripciones
de empresa o usuario a dichos módulos.
"""

from datetime import datetime
from uuid import UUID

import auth
import crud
import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

router = APIRouter(prefix="/modules", tags=["modules"])


# ─── Helpers ────────────────────────────────────────────────────────────────


def _require_admin(current_user: models.User):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(
            status_code=403, detail="Solo el administrador de la plataforma puede realizar esta acción."
        )


# ─── Catálogo de Módulos ─────────────────────────────────────────────────────


@router.get("", response_model=list[schemas.AppModuleResponse])
def list_modules(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Lista todos los módulos disponibles. Admin puede ver también los inactivos."""
    if include_inactive and not getattr(current_user, "is_platform_admin", False):
        include_inactive = False  # Non-admin cannot see inactive
    return crud.get_modules(db, include_inactive=include_inactive)


@router.post("", response_model=schemas.AppModuleResponse)
def create_module(
    data: schemas.AppModuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Crea un nuevo módulo en el catálogo (Platform Admin)."""
    _require_admin(current_user)

    existing = crud.get_module_by_code(db, data.code_name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un módulo con el código '{data.code_name}'.")

    return crud.create_module(db, data)


@router.put("/{module_id}", response_model=schemas.AppModuleResponse)
def update_module(
    module_id: str,
    data: schemas.AppModuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Actualiza un módulo del catálogo (Platform Admin)."""
    _require_admin(current_user)

    updated = crud.update_module(db, module_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return updated


# ─── Suscripciones ──────────────────────────────────────────────────────────


@router.get("/subscriptions", response_model=list[schemas.ModuleSubscriptionResponse])
def list_subscriptions(
    company_id: str | None = None,
    user_id: str | None = None,
    module_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Lista suscripciones.
    Platform Admin puede ver todas.
    Manager puede ver las de su empresa activa.
    """
    is_admin = getattr(current_user, "is_platform_admin", False)
    active_cid = str(getattr(current_user, "active_company_id", None) or "")
    active_role = getattr(current_user, "active_role", None)

    if not is_admin:
        # Non-admin can only see subscriptions for their own active company
        if active_role != "manager" or not active_cid:
            raise HTTPException(status_code=403, detail="No autorizado.")
        company_id = active_cid
        user_id = None  # Managers cannot filter by user_id

    subs = (
        db.query(models.ModuleSubscription)
        .options(
            joinedload(models.ModuleSubscription.module),
            joinedload(models.ModuleSubscription.company),
            joinedload(models.ModuleSubscription.user),
        )
        .filter(
            (models.ModuleSubscription.company_id == company_id) if company_id else True,
            (models.ModuleSubscription.user_id == user_id) if user_id else True,
            (models.ModuleSubscription.module_id == module_id) if module_id else True,
        )
        .order_by(models.ModuleSubscription.created_at.desc())
        .all()
    )

    return subs


@router.post("/subscriptions", response_model=schemas.ModuleSubscriptionResponse)
def create_subscription(
    data: schemas.ModuleSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Crea una suscripción a un módulo (Platform Admin)."""
    _require_admin(current_user)

    # Verify module exists
    module = crud.get_module_by_id(db, str(data.module_id))
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    try:
        sub = crud.create_subscription(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Reload with module relation
    db.refresh(sub)
    return sub


@router.put("/subscriptions/{sub_id}", response_model=schemas.ModuleSubscriptionResponse)
def update_subscription(
    sub_id: str,
    data: schemas.ModuleSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Actualiza el estado/expiración de una suscripción (Platform Admin)."""
    _require_admin(current_user)

    updated = crud.update_subscription(db, sub_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada.")
    return updated


@router.delete("/subscriptions/{sub_id}")
def delete_subscription(
    sub_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)
):
    """Elimina una suscripción (Platform Admin)."""
    _require_admin(current_user)

    deleted = crud.delete_subscription(db, sub_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada.")
    return {"ok": True}


# ─── Módulos del Usuario Actual ──────────────────────────────────────────────


@router.get("/me", response_model=list[schemas.AppModuleResponse])
def get_my_modules(
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Devuelve la lista de módulos activos a los que el usuario actual tiene acceso
    (bien por suscripción personal o por suscripción de su empresa activa/proveída).
    Útil para que el frontend sepa qué funciones mostrar.
    """
    is_admin = getattr(current_user, "is_platform_admin", False)

    if company_id and not is_admin:
        # Verify active member
        membership = (
            db.query(models.CompanyMember)
            .filter(
                models.CompanyMember.user_id == current_user.id,
                models.CompanyMember.company_id == company_id,
                models.CompanyMember.is_active == True,
            )
            .first()
        )
        if not membership:
            raise HTTPException(status_code=403, detail="No autorizado.")

    effective_company_id = company_id if company_id else getattr(current_user, "active_company_id", None)
    if effective_company_id:
        effective_company_id = str(effective_company_id)

    from sqlalchemy import or_

    now = datetime.utcnow()
    active_statuses = [models.SubscriptionStatus.active, models.SubscriptionStatus.trial]

    if is_admin:
        if not effective_company_id:
            # Platform Admin sin contexto de empresa tiene acceso a todos los módulos activos
            return crud.get_modules(db, include_inactive=False)

        # Platform Admin con contexto de empresa: solo módulos suscritos por la empresa
        subs = (
            db.query(models.ModuleSubscription)
            .options(joinedload(models.ModuleSubscription.module))
            .filter(
                models.ModuleSubscription.company_id == effective_company_id,
                models.ModuleSubscription.status.in_(active_statuses),
                or_(models.ModuleSubscription.expires_at.is_(None), models.ModuleSubscription.expires_at > now),
            )
            .all()
        )
    else:
        user_id = str(current_user.id)
        # Subs activas del usuario o de su empresa
        filters = [
            models.ModuleSubscription.status.in_(active_statuses),
            or_(models.ModuleSubscription.expires_at.is_(None), models.ModuleSubscription.expires_at > now),
        ]

        user_or_company_filters = [models.ModuleSubscription.user_id == user_id]
        if effective_company_id:
            user_or_company_filters.append(models.ModuleSubscription.company_id == effective_company_id)

        filters.append(or_(*user_or_company_filters))

        subs = (
            db.query(models.ModuleSubscription)
            .options(joinedload(models.ModuleSubscription.module))
            .filter(*filters)
            .all()
        )

    # Devolver los módulos únicos (puede haber sub personal + sub empresa del mismo módulo)
    seen = set()
    result = []
    for sub in subs:
        if sub.module and sub.module.is_active and sub.module.id not in seen:
            seen.add(sub.module.id)
            result.append(sub.module)

    return result


@router.get("/{module_id}", response_model=schemas.AppModuleResponse)
def get_module(
    module_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)
):
    """Obtiene un módulo específico por su ID (Platform Admin)."""
    _require_admin(current_user)
    module = crud.get_module_by_id(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return module
