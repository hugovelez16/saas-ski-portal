"""Seccion Modulos y suscripciones de la API v2 de administracion (`/api/v2/admin/modules...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.

El orden de registro importa: `/modules/subscriptions` debe ir antes de `/modules/{module_id}`.
"""

import crud
import models
import schemas as legacy_schemas
from database import get_db
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session, joinedload

from routers import deps
from routers import modules as modules_router

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


@router.get("/modules", response_model=list[legacy_schemas.AppModuleResponse])
def list_modules_admin(include_inactive: bool = True, db: Session = Depends(get_db)):
    return crud.get_modules(db, include_inactive=include_inactive)


@router.post("/modules", response_model=legacy_schemas.AppModuleResponse)
def create_module_admin(
    data: legacy_schemas.AppModuleCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.create_module(data=data, db=db, current_user=actor)


@router.get("/modules/subscriptions", response_model=list[legacy_schemas.ModuleSubscriptionResponse])
def list_subscriptions_admin(
    company_id: str | None = None,
    module_id: str | None = None,
    db: Session = Depends(get_db),
):
    return (
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


@router.post("/modules/subscriptions", response_model=legacy_schemas.ModuleSubscriptionResponse)
def create_subscription_admin(
    data: legacy_schemas.ModuleSubscriptionCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.create_subscription(data=data, db=db, current_user=actor)


@router.put("/modules/subscriptions/{sub_id}", response_model=legacy_schemas.ModuleSubscriptionResponse)
def update_subscription_admin(
    sub_id: str,
    data: legacy_schemas.ModuleSubscriptionUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.update_subscription(sub_id=sub_id, data=data, db=db, current_user=actor)


@router.get("/modules/{module_id}", response_model=legacy_schemas.AppModuleResponse)
def get_module_admin(
    module_id: str,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.get_module(module_id=module_id, db=db, current_user=actor)


@router.put("/modules/{module_id}", response_model=legacy_schemas.AppModuleResponse)
def update_module_admin(
    module_id: str,
    data: legacy_schemas.AppModuleUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return modules_router.update_module(module_id=module_id, data=data, db=db, current_user=actor)
