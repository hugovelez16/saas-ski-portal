from datetime import date
from uuid import UUID

import auth
import crud
import models
import schemas
from database import get_db
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from routers.utils import check_manager_access, is_manager_of_company

router = APIRouter(prefix="/work-logs", tags=["work-logs"])

def record_impersonation_audit(db: Session, current_user: models.User, action: str, extra_data: dict = None):
    if getattr(current_user, "token_scope", None) == "impersonated":
        admin_user_id = getattr(current_user, "admin_user_id", None)
        if admin_user_id:
            audit_entry = models.AuditLog(
                action=action,
                impersonated_user_id=current_user.id,
                admin_user_id=UUID(admin_user_id) if isinstance(admin_user_id, str) else admin_user_id,
                extra_data=extra_data or {}
            )
            db.add(audit_entry)
            db.commit()

@router.post("", response_model=schemas.WorkLogResponse)
def create_work_log(work_log: schemas.WorkLogCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    """
    Create a new work log entry.
    """
    company = crud.get_company(db, str(work_log.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    # Verify current_user.id matches work_log.user_id or user is manager/admin of the target company
    if str(work_log.user_id) != str(current_user.id):
        if not is_manager_of_company(db, current_user, work_log.company_id):
             raise HTTPException(status_code=403, detail="Cannot create work logs for other users")

    try:
        new_log = crud.create_work_log(db=db, work_log=work_log)
        record_impersonation_audit(
            db,
            current_user,
            action="create_work_log",
            extra_data={"work_log_id": str(new_log.id), "user_id": str(work_log.user_id)}
        )
        return new_log
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/bulk", response_model=schemas.WorkLogResponse)
def create_work_log_bulk(
    work_log_bulk: schemas.WorkLogBulkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """
    Create multiple work log entries at once (for managers).
    """
    company = crud.get_company(db, str(work_log_bulk.company_id))
    if not company:
        raise HTTPException(status_code=404, detail="Company not found")

    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin
    if not is_platform_admin and not company.is_active:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    # Authorization check: must be manager of the company
    if not is_manager_of_company(db, current_user, work_log_bulk.company_id):
         raise HTTPException(status_code=403, detail="Only managers can create bulk work logs")

    try:
        logs = crud.create_work_log_bulk(db=db, work_log_bulk=work_log_bulk)
        if logs:
            record_impersonation_audit(
                db,
                current_user,
                action="create_work_log_bulk",
                extra_data={
                    "company_id": str(work_log_bulk.company_id),
                    "user_ids": [str(uid) for uid in work_log_bulk.user_ids],
                    "group_id": logs.extra_data.get("group_id") if logs.extra_data else None
                }
            )
        return logs # Returns the first one created as a representative
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("", response_model=list[schemas.WorkLogResponse])
def read_work_logs(
    skip: int = 0,
    limit: int = 100,
    user_id: UUID = None, # Optional filter via query param
    company_id: UUID = None, # Optional filter via query param
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """
    Retrieve work logs.
    Users can only see their own. Admins can filter by user_id or see their own if not specified.
    Supervisors can filter by company_id for their companies.
    """
    target_user_id = current_user.id
    target_company_id = company_id or getattr(current_user, "active_company_id", None)

    # Permission Logic
    if getattr(current_user, "is_platform_admin", False):
        # Admin can do anything
        if user_id:
            target_user_id = user_id
        else:
            target_user_id = None
            # Existing behavior: target_user_id = current_user.id
            if not company_id and not user_id and not start_date and not end_date:
               target_user_id = current_user.id # Default to self if ABSOLUTELY no filters

        final_user_id = target_user_id

    else:
        # Check for Supervisor Permission dynamically (as "supervisor" role doesn't exist on User model)
        # Check if user is manager/admin of the requested company OR if they are checking availability for a user in their managed company
        is_supervisor_request = False

        if company_id:
             if is_manager_of_company(db, current_user, UUID(company_id) if isinstance(company_id, str) else company_id):
                 is_supervisor_request = True
                 target_user_id = None # See all logs for this company
                 if user_id:
                     target_user_id = user_id # Filter specific user in this company
             else:
                 # Check if the company has worker_daily_report enabled and the user is an active member
                 membership = db.query(models.CompanyMember).filter(
                     models.CompanyMember.user_id == current_user.id,
                     models.CompanyMember.company_id == company_id,
                     models.CompanyMember.is_active == True
                 ).first()

                 if membership:
                     if crud.user_has_module(db, str(current_user.id), str(company_id), "worker_daily_report"):
                         is_supervisor_request = True
                         target_user_id = None
                         if user_id:
                             target_user_id = user_id

        if is_supervisor_request:
              final_user_id = target_user_id
        else:
            # Regular user or Manager accessing outside their scope
            # Check generically if manager manages this user via any company
            if user_id and str(user_id) != str(current_user.id):
                 if check_manager_access(db, current_user, str(user_id)):
                     final_user_id = user_id
                 else:
                     raise HTTPException(status_code=403, detail="Not authorized to view other users' logs")
            else:
                 final_user_id = current_user.id

    work_logs = crud.get_work_logs(
        db,
        skip=skip,
        limit=limit,
        user_id=str(final_user_id) if final_user_id else None,
        company_id=target_company_id,
        start_date=start_date,
        end_date=end_date
    )
    return work_logs

@router.get("/billing-summary", response_model=list[schemas.BillingSummaryItemResponse])
def get_billing_summary(
    company_id: UUID,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """
    Get billing summary for a company, aggregated by user and work log type, using the PostgreSQL database function.
    Only managers of the company or platform admins can access this.
    """
    if not getattr(current_user, "is_platform_admin", False):
        if not is_manager_of_company(db, current_user, company_id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Only managers of this company or platform admins can access the billing summary."
            )

    from sqlalchemy import text
    query = text("""
        SELECT user_id, first_name, last_name, email, type,
               total_hours, total_net, total_gross, unique_days, logs_count
        FROM get_billing_summary(:company_id, :start_date, :end_date)
    """)
    result = db.execute(query, {
        "company_id": str(company_id),
        "start_date": start_date,
        "end_date": end_date
    }).fetchall()

    summary = []
    for row in result:
        summary.append(schemas.BillingSummaryItemResponse(
            user_id=row.user_id,
            first_name=row.first_name,
            last_name=row.last_name,
            email=row.email,
            type=row.type,
            total_hours=float(row.total_hours or 0.0),
            total_net=float(row.total_net or 0.0),
            total_gross=float(row.total_gross or 0.0),
            unique_days=int(row.unique_days or 0),
            logs_count=int(row.logs_count or 0)
        ))
    return summary

@router.delete("/{work_log_id}")
def delete_work_log(work_log_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    wid = UUID(str(work_log_id)) if not isinstance(work_log_id, UUID) else work_log_id
    log = db.query(models.WorkLog).filter(models.WorkLog.id == wid).first()
    if not log:
         raise HTTPException(status_code=404, detail="Work log not found")

    company = crud.get_company(db, str(log.company_id))
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin

    if company and not company.is_active and not is_platform_admin:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    is_owner = str(log.user_id) == str(current_user.id)
    is_manager = is_manager_of_company(db, current_user, log.company_id)

    if not is_owner and not is_manager and not is_platform_admin:
         raise HTTPException(status_code=403, detail="Not authorized")

    if company and company.is_managed and not is_manager and not is_platform_admin:
        raise HTTPException(status_code=403, detail="En empresas gestionadas los trabajadores no pueden eliminar turnos directamente")

    record_impersonation_audit(
        db,
        current_user,
        action="delete_work_log",
        extra_data={"work_log_id": work_log_id, "user_id": str(log.user_id)}
    )
    crud.delete_work_log(db, work_log_id)
    return {"ok": True}

@router.put("/{work_log_id}", response_model=schemas.WorkLogResponse)
def update_work_log(
    work_log_id: str,
    work_log: schemas.WorkLogCreate,
    apply_to_group: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    # Verify ownership or management
    wid = UUID(str(work_log_id)) if not isinstance(work_log_id, UUID) else work_log_id
    log = db.query(models.WorkLog).filter(models.WorkLog.id == wid).first()
    if not log:
         raise HTTPException(status_code=404, detail="Work log not found")

    company = crud.get_company(db, str(log.company_id))
    is_platform_admin = getattr(current_user, "is_platform_admin", False) or current_user.role == models.UserRole.admin

    if company and not company.is_active and not is_platform_admin:
        raise HTTPException(status_code=403, detail="Empresa inactiva o suspendida")

    is_owner = str(log.user_id) == str(current_user.id)
    is_manager = is_manager_of_company(db, current_user, log.company_id)

    if not is_owner and not is_manager and not is_platform_admin:
         raise HTTPException(status_code=403, detail="Not authorized")

    if company and company.is_managed and not is_manager and not is_platform_admin:
        raise HTTPException(status_code=403, detail="En empresas gestionadas los trabajadores no pueden modificar turnos directamente")

    # Only managers/admins can apply to group
    if apply_to_group and not is_manager and not is_platform_admin:
        raise HTTPException(status_code=403, detail="Only managers can perform cascading updates")

    updated_log = crud.update_work_log(db, work_log_id, work_log, apply_to_group=apply_to_group)

    record_impersonation_audit(
        db,
        current_user,
        action="update_work_log",
        extra_data={"work_log_id": work_log_id, "user_id": str(updated_log.user_id), "apply_to_group": apply_to_group}
    )

    return updated_log
