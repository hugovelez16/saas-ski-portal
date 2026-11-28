"""Seccion Usuarios y suplantacion de la API v2 de administracion (`/api/v2/admin/users...`).

Guarda unica en la entrada del router (`deps.require_platform_admin`, R-ACC-25): ninguna ruta
interna repite comprobaciones inline de PA.
"""

from uuid import UUID

import crud
import models
import schemas as legacy_schemas
from application.use_cases.company.list_user_companies import ListUserCompaniesUseCase
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from routers import auth as auth_router
from routers import deps
from routers import users as users_router
from routers.v2 import deps as v2_deps
from routers.v2 import schemas

router = APIRouter(
    prefix="/admin",
    tags=["v2-admin"],
    dependencies=[Depends(deps.require_platform_admin)],
)


@router.get("/users", response_model=list[legacy_schemas.UserResponse])
def list_users_admin(skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    return crud.get_users(db, skip=skip, limit=limit)


@router.post("/users", response_model=legacy_schemas.UserResponse)
async def create_user_admin_route(
    user: legacy_schemas.UserCreate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return await users_router.create_user_admin(user=user, db=db, current_user=actor)


@router.get("/users/{user_id}", response_model=legacy_schemas.UserResponse)
def read_user_admin(user_id: UUID, db: Session = Depends(get_db)):
    user = crud.get_user(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.put("/users/{user_id}", response_model=legacy_schemas.UserResponse)
def update_user_admin_route(
    user_id: UUID,
    user: legacy_schemas.UserUpdate,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.update_user(user_id=user_id, user=user, db=db, current_user=actor)


@router.put("/users/{user_id}/status")
def toggle_user_status_admin_route(
    user_id: UUID,
    is_active: bool,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.toggle_user_status(user_id=user_id, is_active=is_active, db=db, current_user=actor)


@router.post("/users/{user_id}/reset-password-email")
async def reset_password_email_admin_route(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return await users_router.reset_password_via_email(user_id=user_id, db=db, current_user=actor)


@router.post("/users/{user_id}/reset-2fa")
def reset_2fa_admin_route(
    user_id: UUID,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return users_router.reset_user_2fa(user_id=user_id, db=db, current_user=actor)


@router.get("/users/{user_id}/companies", response_model=list[schemas.CompanyFullWithMembership])
async def read_user_companies_admin(
    user_id: UUID,
    company_repo=Depends(v2_deps.get_company_repository),
    member_repo=Depends(v2_deps.get_member_repository),
):
    views = await ListUserCompaniesUseCase(company_repo, member_repo).execute(
        user_id=str(user_id), include_inactive=True
    )
    return [schemas.company_full_with_membership(view) for view in views]


@router.post("/impersonate/{user_id}", response_model=legacy_schemas.Token)
async def impersonate_user_admin(
    user_id: UUID,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    actor: models.User = Depends(deps.require_platform_admin),
):
    return auth_router.execute_impersonate_user(
        user_id=user_id, response=response, request=request, db=db, current_user=actor
    )
