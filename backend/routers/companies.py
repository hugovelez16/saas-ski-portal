import json
from datetime import date
from uuid import UUID

import access_cache
import access_policy
import auth
import crud
import models
import schemas
from access_policy import PolicyError
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, Query
from redis_config import redis_manager
from sqlalchemy.orm import Session, joinedload

from routers import deps

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[schemas.CompanyResponse])
def read_companies(
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    query = db.query(models.Company)
    if not deps.acting_platform_admin(current_user):
        # Solo listar empresas donde el usuario tenga membresia activa o esten activas
        user_memberships = (
            db.query(models.CompanyMember)
            .filter(models.CompanyMember.user_id == current_user.id, models.CompanyMember.is_active == True)
            .all()
        )
        company_ids = [m.company_id for m in user_memberships]
        query = query.filter(models.Company.id.in_(company_ids), models.Company.is_active == True)
    companies = query.offset(skip).limit(limit).all()
    return companies


@router.post("", response_model=schemas.CompanyResponse)
def create_company(
    company: schemas.CompanyCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    return crud.create_company(db, company)


@router.put("/{company_id}", response_model=schemas.CompanyResponse)
def update_company(
    company_id: UUID,
    company: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    if not ctx.is_platform_admin:
        # Security: Non-platform admins cannot modify is_active or is_managed
        update_data = company.model_dump(exclude_unset=True)
        if any(k in update_data for k in ["is_active", "isActive", "is_managed", "isManaged"]):
            raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    updated_company = crud.update_company(db, str(company_id), company)
    return updated_company


@router.get("/detailed", response_model=list[schemas.CompanyWithMembers])
def read_companies_detailed(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    # If platform admin (actuando), return all
    if deps.acting_platform_admin(current_user):
        return db.query(models.Company).options(joinedload(models.Company.members)).all()

    # If not admin, check for permissions
    # 1. Supervisor permissions: manager of the company the token points to
    active_cid = deps.canonical_id(getattr(current_user, "active_company_id", None))
    supervisor_memberships = (
        db.query(models.CompanyMember)
        .join(models.Company)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.role.in_([models.CompanyRole.manager, models.CompanyRole.admin]),
            models.CompanyMember.is_active == True,
            models.Company.is_active == True,
        )
        .all()
    )

    allowed_company_ids = {m.company_id for m in supervisor_memberships if active_cid and str(m.company_id) == active_cid}

    # 2. Worker Daily Report permissions
    # Check if user is a member of any company that has this feature enabled
    user_memberships = (
        db.query(models.CompanyMember)
        .options(joinedload(models.CompanyMember.company))
        .join(models.Company)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.is_active == True,
            models.Company.is_active == True,
        )
        .all()
    )

    for m in user_memberships:
        company = m.company  # The Company relationship
        # Con empresa activa en el token no se exponen otras empresas
        if active_cid and str(m.company_id) != active_cid:
            continue
        if company and company.is_active:
            has_wr = crud.user_has_module(db, str(current_user.id), str(company.id), "worker_daily_report")
            if has_wr:
                allowed_company_ids.add(company.id)

    if allowed_company_ids:
        companies = (
            db.query(models.Company)
            .options(joinedload(models.Company.members))
            .filter(models.Company.id.in_(allowed_company_ids), models.Company.is_active == True)
            .all()
        )
        return companies

    raise PolicyError(403, access_policy.MSG_FORBIDDEN)


@router.get("/{company_id}/members", response_model=list[schemas.CompanyMemberResponse])
def read_company_members(
    company_id: UUID,
    status: str = None,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Get members of a company.
    """
    return crud.get_company_members(db, str(company_id), status)


@router.put("/{company_id}/members/order", response_model=dict)
def update_members_order(
    company_id: UUID,
    order_data: schemas.UpdateCompanyMembersOrder,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Update the sort order of company members.
    """
    crud.update_company_members_order(db, str(company_id), order_data.user_ids)
    return {"message": "Order updated successfully"}


@router.post("/{company_id}/members/add", response_model=schemas.CompanyMemberResponse)
def add_company_member(
    company_id: UUID,
    member_data: schemas.TokenData,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Admin: Add a user to a company directly by email (bypass request).
    """
    user_to_add = crud.get_user_by_email(db, member_data.email)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User email not found")

    # Check if exists
    existing = crud.join_company(db, str(user_to_add.id), str(company_id))

    # If it was inactive or just created, force active and ensure role is set (healing)
    needs_update = False
    if not existing.is_active:
        existing.is_active = True
        needs_update = True

    if not existing.role:  # Heal potential legacy NULLs
        existing.role = models.CompanyRole.worker
        needs_update = True

    if existing.rates_config is None:  # Heal missing JSONB field
        existing.rates_config = {}
        needs_update = True

    if needs_update:
        db.commit()
        db.refresh(existing)
        access_cache.invalidate_membership(existing.user_id, existing.company_id)

    return existing


@router.put("/{company_id}/members/{user_id}/status", response_model=schemas.CompanyMemberResponse)
def update_member_status(
    company_id: UUID,
    user_id: UUID,
    status: str,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Approve/Reject company membership.
    """
    member = crud.update_company_member_status(db, str(company_id), str(user_id), status)
    if not member:
        raise HTTPException(status_code=404, detail="Member request not found")

    return member


@router.get("/{company_id}", response_model=schemas.CompanyResponse)
def read_company(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company("worker")),
):
    if ctx.company is None:
        raise PolicyError(403, access_policy.MSG_NO_ACCESS)
    return ctx.company


@router.get("/{company_id}/rates-v2", response_model=list[schemas.CompanyMemberResponse])
def read_company_rates(
    company_id: UUID,
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
    db: Session = Depends(get_db),
):
    return crud.get_company_rates(db, str(company_id))


@router.put("/{company_id}/members/{user_id}", response_model=schemas.CompanyMemberResponse)
def update_company_member(
    company_id: UUID,
    user_id: UUID,
    member_data: schemas.CompanyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
    ctx: deps.AccessContext = Depends(deps.require_company("worker")),
):
    company = ctx.company
    is_platform_admin = ctx.is_platform_admin
    is_manager = ctx.role in (access_policy.ROLE_MANAGER, access_policy.ROLE_PLATFORM_ADMIN)
    is_self = user_id == current_user.id

    if not is_manager and not is_self:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    cid = str(company_id)
    uid = str(user_id)
    target_member = crud.get_company_member(db, uid, cid)
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    requester_membership = (
        db.query(models.CompanyMember)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.company_id == company_id,
            models.CompanyMember.is_active == True,
        )
        .first()
    )
    is_company_admin = is_platform_admin or (
        requester_membership and requester_membership.role == models.CompanyRole.admin
    )

    # 1. Role Change Restrictions:
    # Only company admin or platform admin can change roles. Managers CANNOT change roles.
    if member_data.role is not None:
        target_role_str = target_member.role.value if hasattr(target_member.role, "value") else str(target_member.role)
        if member_data.role != target_role_str:
            if not is_company_admin:
                raise HTTPException(
                    status_code=403,
                    detail="Solo los administradores de la empresa o de la plataforma pueden modificar el rol de un miembro",
                )

    # 2. Managed Company Restrictions:
    # In managed mode (is_managed == True), workers cannot edit their own rates_config or role.
    if company.is_managed and is_self and not is_company_admin and not is_manager:
        if member_data.rates_config is not None:
            raise HTTPException(
                status_code=403, detail="En empresas gestionadas las tarifas son fijadas por los administradores"
            )
        if member_data.role is not None:
            raise HTTPException(
                status_code=403, detail="En empresas gestionadas los trabajadores no pueden modificar su rol"
            )

    # 3. Security: Non-managers and non-admins cannot alter role or membership status
    if not is_manager and not is_company_admin:
        member_data = schemas.CompanyMemberUpdate(
            ratesConfig=None if (company.is_managed and not is_company_admin) else member_data.rates_config,
            settings=member_data.settings,
        )

    member = crud.update_company_member(db, cid, uid, member_data)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member


@router.get("/{company_id}/dashboard-summary", response_model=schemas.DashboardSummaryResponse)
def get_company_dashboard_summary(
    company_id: UUID,
    start_date: date | None = None,
    end_date: date | None = None,
    db: Session = Depends(get_db),
    ctx: deps.AccessContext = Depends(deps.require_company("manager")),
):
    """
    Retorna el resumen analitico y operativo para el dashboard de gestores,
    integrando cache en Redis y agregacion optimizada.
    """
    cid = str(company_id)

    # Redis Cache Key
    cache_key = f"dashboard_summary:{cid}:{start_date or ''}:{end_date or ''}"
    cached_data = redis_manager.get(cache_key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except Exception:
            pass

    try:
        summary_data = crud.get_dashboard_summary(db=db, company_id=cid, start_date=start_date, end_date=end_date)
        try:
            serialized = schemas.DashboardSummaryResponse(**summary_data).model_dump(mode="json", by_alias=True)
            redis_manager.set(cache_key, json.dumps(serialized), ex=300)
        except Exception:
            pass

        return summary_data
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
