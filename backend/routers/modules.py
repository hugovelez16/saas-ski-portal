"""
Módulos y Suscripciones SaaS.

Gestión del catálogo de módulos de la plataforma y las suscripciones
de empresa a dichos módulos.
"""

from datetime import UTC, datetime
from uuid import UUID

import access_policy
import auth
import crud
import models
import schemas
from access_policy import PolicyError
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import JSONResponse
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from routers import deps

router = APIRouter(prefix="/modules", tags=["modules"])


# ─── Catálogo de Módulos ─────────────────────────────────────────────────────


@router.get("", response_model=list[schemas.AppModuleResponse])
def list_modules(
    include_inactive: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """Lista todos los módulos disponibles. Admin puede ver también los inactivos."""
    if include_inactive and not deps.acting_platform_admin(current_user):
        include_inactive = False  # Non-admin cannot see inactive
    return crud.get_modules(db, include_inactive=include_inactive)


@router.post("", response_model=schemas.AppModuleResponse)
def create_module(
    data: schemas.AppModuleCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    """Crea un nuevo módulo en el catálogo (Platform Admin)."""
    existing = crud.get_module_by_code(db, data.code_name)
    if existing:
        raise HTTPException(status_code=400, detail=f"Ya existe un módulo con el código '{data.code_name}'.")

    return crud.create_module(db, data)


@router.put("/{module_id}", response_model=schemas.AppModuleResponse)
def update_module(
    module_id: str,
    data: schemas.AppModuleUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    """Actualiza un módulo del catálogo (Platform Admin)."""
    updated = crud.update_module(db, module_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return updated


# ─── Suscripciones ──────────────────────────────────────────────────────────


@router.get("/subscriptions", response_model=None)
def list_subscriptions(
    company_id: str | None = None,
    module_id: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Lista suscripciones de empresa.
    Platform Admin puede ver todas.
    Manager puede ver las de su empresa activa, con la empresa embebida reducida a `id` y `name`.
    """
    acting_pa = deps.acting_platform_admin(current_user)
    if not acting_pa:
        # Non-admin can only see subscriptions for their own active company
        active_cid = getattr(current_user, "active_company_id", None)
        if not active_cid:
            raise PolicyError(403, access_policy.MSG_FORBIDDEN)
        ctx = deps.authorize(db, current_user, active_cid, min_role=access_policy.ROLE_MANAGER)
        company_id = ctx.company_id

    subs = (
        db.query(models.ModuleSubscription)
        .options(
            joinedload(models.ModuleSubscription.module),
            joinedload(models.ModuleSubscription.company),
        )
        .filter(
            (models.ModuleSubscription.company_id == company_id) if company_id else True,
            (models.ModuleSubscription.module_id == module_id) if module_id else True,
        )
        .order_by(models.ModuleSubscription.created_at.desc())
        .all()
    )

    schema = schemas.ModuleSubscriptionResponse if acting_pa else schemas.ModuleSubscriptionManagerResponse
    return JSONResponse([schema.model_validate(sub).model_dump(mode="json", by_alias=True) for sub in subs])


@router.post("/subscriptions", response_model=schemas.ModuleSubscriptionResponse)
def create_subscription(
    data: schemas.ModuleSubscriptionCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    """Crea una suscripción de empresa a un módulo activo (Platform Admin)."""
    module = crud.get_module_by_id(db, str(data.module_id))
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")

    try:
        sub = crud.create_subscription(db, data)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    db.refresh(sub)
    return sub


@router.put("/subscriptions/{sub_id}", response_model=schemas.ModuleSubscriptionResponse)
def update_subscription(
    sub_id: str,
    data: schemas.ModuleSubscriptionUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    """Actualiza el estado/expiración de una suscripción (Platform Admin)."""
    updated = crud.update_subscription(db, sub_id, data)
    if not updated:
        raise HTTPException(status_code=404, detail="Suscripción no encontrada.")
    return updated


# ─── Módulos del Usuario Actual ──────────────────────────────────────────────


@router.get("/me", response_model=list[schemas.AppModuleResponse])
def get_my_modules(
    company_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Devuelve la lista de módulos activos de la empresa activa (R-MOD-16, R-MOD-17).
    Sin empresa en contexto, o si la empresa está suspendida, devuelve [].
    """
    is_admin = deps.acting_platform_admin(current_user)

    effective_company_id = None
    if company_id and not is_admin:
        # Empresa explicita: exige acceso (membresia activa). Si esta suspendida, devuelve []
        facts = deps.load_company_facts(db, current_user, company_id)
        if not (facts.exists and facts.membership_active and not facts.is_active):
            effective_company_id = deps.authorize(
                db, current_user, company_id, min_role=access_policy.ROLE_WORKER
            ).company_id
    else:
        raw_company_id = company_id or getattr(current_user, "active_company_id", None)
        if raw_company_id:
            facts = deps.load_company_facts(db, current_user, raw_company_id)
            has_access = facts.membership_active or is_admin
            if facts.exists and facts.is_active and has_access:
                effective_company_id = facts.company_id

    if not effective_company_id:
        return []

    now = datetime.now(UTC)
    active_statuses = [models.SubscriptionStatus.active, models.SubscriptionStatus.trial]
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

    seen = set()
    result = []
    for sub in subs:
        if sub.module and sub.module.is_active and sub.module.id not in seen:
            seen.add(sub.module.id)
            result.append(sub.module)

    return result


@router.get("/{module_id}", response_model=schemas.AppModuleResponse)
def get_module(
    module_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(deps.require_platform_admin)
):
    """Obtiene un módulo específico por su ID (Platform Admin)."""
    module = crud.get_module_by_id(db, module_id)
    if not module:
        raise HTTPException(status_code=404, detail="Módulo no encontrado.")
    return module
