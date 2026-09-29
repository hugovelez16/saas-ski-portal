from uuid import UUID

import auth
import crud
import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session, joinedload

from routers.utils import is_manager_of_company

router = APIRouter(prefix="/companies", tags=["companies"])


@router.get("", response_model=list[schemas.CompanyResponse])
def read_companies(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    query = db.query(models.Company)
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    if not is_platform_admin:
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
    current_user: models.User = Depends(auth.get_verified_user),
):
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    if not is_platform_admin:
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.create_company(db, company)


@router.put("/{company_id}", response_model=schemas.CompanyResponse)
def update_company(
    company_id: str,
    company: schemas.CompanyUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin

    db_company = crud.get_company(db, company_id)
    if not db_company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin:
        if not db_company.is_active:
            raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")
        if not is_manager_of_company(db, current_user, company_id):
            print(f"Access denied for user {current_user.email} on company {company_id}")
            raise HTTPException(status_code=403, detail="Not authorized to update this company")

        # Security: Non-platform admins cannot modify is_active or is_managed
        update_data = company.model_dump(exclude_unset=True)
        if any(k in update_data for k in ["is_active", "isActive", "is_managed", "isManaged"]):
            raise HTTPException(
                status_code=403,
                detail="Solo administradores de plataforma pueden modificar el estado o modo de la empresa",
            )

    updated_company = crud.update_company(db, company_id, company)
    return updated_company


@router.get("/detailed", response_model=list[schemas.CompanyWithMembers])
def read_companies_detailed(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    # If platform admin, return all
    if is_platform_admin:
        return db.query(models.Company).options(joinedload(models.Company.members)).all()

    # If not admin, check for permissions
    # 1. Supervisor permissions (manager/admin of specific companies)
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

    allowed_company_ids = {m.company_id for m in supervisor_memberships}

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

    raise HTTPException(status_code=403, detail="Not authorized")


@router.get("/{company_id}/members", response_model=list[schemas.CompanyMemberResponse])
def read_company_members(
    company_id: str,
    status: str = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Get members of a company.
    """
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    if not is_manager_of_company(db, current_user, company_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.get_company_members(db, company_id, status)


@router.put("/{company_id}/members/order", response_model=dict)
def update_members_order(
    company_id: str,
    order_data: schemas.UpdateCompanyMembersOrder,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Update the sort order of company members.
    """
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    if not is_manager_of_company(db, current_user, company_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    crud.update_company_members_order(db, company_id, order_data.user_ids)
    return {"message": "Order updated successfully"}


@router.post("/{company_id}/members/add", response_model=schemas.CompanyMemberResponse)
def add_company_member(
    company_id: str,
    member_data: schemas.TokenData,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Admin: Add a user to a company directly by email (bypass request).
    """
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    if not is_manager_of_company(db, current_user, company_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    user_to_add = crud.get_user_by_email(db, member_data.email)
    if not user_to_add:
        raise HTTPException(status_code=404, detail="User email not found")

    # Check if exists
    existing = crud.join_company(db, str(user_to_add.id), company_id)

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

    return existing


@router.put("/{company_id}/members/{user_id}/status", response_model=schemas.CompanyMemberResponse)
def update_member_status(
    company_id: str,
    user_id: str,
    status: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    """
    Approve/Reject company membership.
    """
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    if not is_manager_of_company(db, current_user, company_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    member = crud.update_company_member_status(db, company_id, user_id, status)
    if not member:
        raise HTTPException(status_code=404, detail="Member request not found")

    return member


@router.get("/{company_id}", response_model=schemas.CompanyResponse)
def read_company(
    company_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    # Access control
    if is_platform_admin:
        return company

    cid = UUID(str(company_id)) if not isinstance(company_id, UUID) else company_id
    membership = (
        db.query(models.CompanyMember)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.company_id == cid,
            models.CompanyMember.is_active == True,
        )
        .first()
    )

    if not membership:
        raise HTTPException(status_code=403, detail="Not authorized")

    return company


@router.get("/{company_id}/rates-v2", response_model=list[schemas.CompanyMemberResponse])
def read_company_rates(
    company_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_current_user)
):
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    # Allow Admin or Manager of this company
    if not is_manager_of_company(db, current_user, company_id):
        raise HTTPException(status_code=403, detail="Not authorized")

    return crud.get_company_rates(db, company_id)


@router.put("/{company_id}/members/{user_id}", response_model=schemas.CompanyMemberResponse)
def update_company_member(
    company_id: str,
    user_id: str,
    member_data: schemas.CompanyMemberUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_current_user),
):
    company = crud.get_company(db, company_id)
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    is_manager = is_manager_of_company(db, current_user, company_id)
    is_self = str(user_id) == str(current_user.id)

    # DEBUG
    print(
        f"DEBUG: update_company_member - company_id={company_id}, user_id={user_id}, current_user_id={current_user.id}, is_manager={is_manager}, is_self={is_self}"
    )

    if not is_platform_admin and not is_manager and not is_self:
        raise HTTPException(
            status_code=403,
            detail=f"Not authorized. is_manager={is_manager}, is_self={is_self}, user_id={user_id}, current_user_id={current_user.id}",
        )

    target_member = crud.get_company_member(db, user_id, company_id)
    if not target_member:
        raise HTTPException(status_code=404, detail="Member not found")

    cid = UUID(str(company_id)) if not isinstance(company_id, UUID) else company_id
    requester_membership = (
        db.query(models.CompanyMember)
        .filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.company_id == cid,
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

    member = crud.update_company_member(db, company_id, user_id, member_data)
    if not member:
        raise HTTPException(status_code=404, detail="Member not found")
    return member
