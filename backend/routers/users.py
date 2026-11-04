import logging
from uuid import UUID

import access_policy
import auth
import crud
import email_utils
import models
import schemas
from access_policy import PolicyError
from database import get_db
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from routers import deps

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["users"])


@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
    token: str = Depends(auth.get_token_from_request),
):
    # Detect impersonation from JWT scope
    is_impersonated = False
    if token:
        try:
            payload = auth.jwt.decode(token, auth.PUBLIC_KEY, algorithms=[auth.ALGORITHM])
            if payload.get("scope") == "impersonated":
                is_impersonated = True
        except Exception:
            pass

    # Compute flags (is_manager and is_active_worker)
    memberships = (
        db.query(models.CompanyMember)
        .filter(models.CompanyMember.user_id == current_user.id, models.CompanyMember.is_active == True)
        .all()
    )

    current_user.is_manager = any(m.role in [models.CompanyRole.manager, models.CompanyRole.admin] for m in memberships)
    current_user.is_active_worker = len(memberships) > 0

    # Construct response with impersonated flag and active context
    user_data = schemas.UserResponse.model_validate(current_user)
    user_data.is_impersonated = is_impersonated

    # Attach transient context from auth logic
    user_data.is_platform_admin = getattr(current_user, "is_platform_admin", False)
    user_data.active_company_id = getattr(current_user, "active_company_id", None)
    user_data.active_role = getattr(current_user, "active_role", None)
    user_data.view_as = getattr(current_user, "view_as", None)
    user_data.is_read_only_view = bool(user_data.view_as)

    return user_data


@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    if not deps.manages_user(db, current_user, user_id):
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)
    user = crud.get_user(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user


@router.get("", response_model=list[schemas.UserResponse])
def read_users(
    skip: int = 0,
    limit: int = 100,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    users = crud.get_users(db, skip=skip, limit=limit)
    return users


@router.post("", response_model=schemas.UserResponse)
async def create_user_admin(
    user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(deps.require_platform_admin)
):
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    # Option A: Random unusable Password
    import secrets

    unusable_password = secrets.token_urlsafe(32)
    user.password = unusable_password  # Override with random secure string

    created_user = crud.create_user(db=db, user=user)

    # Set must_change_password
    created_user.must_change_password = True
    db.commit()

    # Send Email
    if user.send_email:
        reset_token = auth.create_reset_token(user.email)
        await email_utils.send_welcome_email(user.email, reset_token)

    # Company Linkage
    if user.company_id:
        crud.join_company(db, str(created_user.id), str(user.company_id))

    return created_user


@router.put("/{user_id}/status")
def toggle_user_status(
    user_id: UUID,
    is_active: bool,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    target = crud.get_user(db, str(user_id))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    crud.ensure_platform_admin_invariants(db, current_user, target, new_role=None, new_is_active=is_active)

    user = crud.update_user_status(db, user_id=str(user_id), is_active=is_active)
    return {"message": "Status updated", "is_active": user.is_active}


@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(
    user: schemas.UserSelfUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    # Solo los campos enviados; un nombre null o ausente no borra el valor actual (M4)
    data = user.model_dump(exclude_unset=True)
    for name_field in ("first_name", "last_name"):
        if data.get(name_field) is None:
            data.pop(name_field, None)
    db_user = crud.update_user(db, str(current_user.id), schemas.UserUpdate(**data))
    return db_user


@router.post("/me/change-password")
def change_password(
    data: schemas.PasswordChange,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    # Verify current password
    if not auth.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")

    # Update password
    current_user.hashed_password = auth.get_password_hash(data.new_password)
    current_user.must_change_password = False

    db.commit()
    return {"message": "Password updated successfully"}


@router.post("/{user_id}/reset-password-email")
async def reset_password_via_email(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(deps.require_platform_admin)
):
    """
    Platform admin only: Reset user password to a random one and email it.
    """
    user = crud.get_user(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Update User
    user.must_change_password = True
    db.commit()

    # Send Email
    try:
        reset_token = auth.create_reset_token(user.email)
        await email_utils.send_password_reset_email(user.email, reset_token)
    except Exception:
        logger.warning("Error sending password reset email to user %s", user.id)
        raise HTTPException(status_code=500, detail="Failed to send email.")

    return {"message": "Password reset and email sent"}


@router.post("/{user_id}/reset-2fa")
def reset_user_2fa(
    user_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(deps.require_platform_admin)
):
    """
    Platform admin only: disable 2FA for a user who lost access to their authenticator app.
    Revokes the user's active sessions and leaves an audit entry. The user can enrol 2FA again afterwards.
    """
    user = crud.get_user(db, str(user_id))
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    if not user.is_2fa_enabled and not user.otp_secret:
        raise HTTPException(status_code=400, detail="2FA not enabled for this user")

    user.is_2fa_enabled = False
    user.otp_secret = None

    db.query(models.UserSession).filter(
        models.UserSession.user_id == user.id, models.UserSession.is_active.is_(True)
    ).update({"is_active": False}, synchronize_session=False)

    db.add(
        models.AuditLog(
            action="2fa_reset",
            impersonated_user_id=user.id,
            admin_user_id=current_user.id,
            actor_user_id=current_user.id,
            extra_data={"target_email": user.email},
        )
    )
    db.commit()

    # Un reset deja al usuario sin bloqueo por intentos fallidos previos
    auth.redis_manager.delete(f"2fa_fail_{user.id}")

    return {"message": "2FA reset"}


@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(
    user_id: UUID,
    user: schemas.UserUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(deps.require_platform_admin),
):
    target = crud.get_user(db, str(user_id))
    if not target:
        raise HTTPException(status_code=404, detail="User not found")
    crud.ensure_platform_admin_invariants(
        db, current_user, target, new_role=user.role, new_is_active=user.is_active
    )

    db_user = crud.update_user(db, str(user_id), user)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user
