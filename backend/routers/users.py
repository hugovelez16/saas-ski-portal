from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from sqlalchemy.orm import Session
from typing import List, Any
from uuid import UUID
import random
import string

import crud, models, schemas, auth, email_utils
from database import get_db
from routers.utils import check_manager_access

router = APIRouter(prefix="/users", tags=["users"])

@router.post("/", response_model=schemas.UserCreate)
def create_user(user: schemas.UserCreate, db: Session = Depends(get_db)):
    """
    Register a new user.
    """
    db_user = auth.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    return crud.create_user(db=db, user=user)

@router.get("/me", response_model=schemas.UserResponse)
def read_users_me(
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_verified_user),
    token: str = Depends(auth.get_token_from_request)
):
    # Detect impersonation from JWT scope
    is_impersonated = False
    if token:
        try:
            payload = auth.jwt.decode(token, auth.PUBLIC_KEY, algorithms=[auth.ALGORITHM])
            if payload.get("scope") == "impersonated":
                is_impersonated = True
        except:
            pass


    # Compute flags (is_manager and is_active_worker)
    memberships = db.query(models.CompanyMember).filter(
        models.CompanyMember.user_id == current_user.id,
        models.CompanyMember.is_active == True
    ).all()
    
    current_user.is_manager = any(m.role in [models.CompanyRole.manager, models.CompanyRole.admin] for m in memberships)
    current_user.is_active_worker = len(memberships) > 0

    # Construct response with impersonated flag and active context
    user_data = schemas.UserResponse.model_validate(current_user)
    user_data.is_impersonated = is_impersonated
    
    # Attach transient context from auth logic
    user_data.is_platform_admin = getattr(current_user, "is_platform_admin", False)
    user_data.active_company_id = getattr(current_user, "active_company_id", None)
    user_data.active_role = getattr(current_user, "active_role", None)
    
    return user_data

@router.get("/me/companies", response_model=List[schemas.CompanyResponse])
def read_user_companies(db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    """
    Get companies the current user is a member of.
    """
    if getattr(current_user, "is_platform_admin", False):
        companies = db.query(models.Company).all()
        results = []
        for company in companies:
            results.append({
                "id": company.id,
                "name": company.name,
                "fiscal_id": company.fiscal_id,
                "tax_config": company.tax_config,
                "worklog_definitions": company.worklog_definitions,
                "created_at": company.created_at,
                "updated_at": company.updated_at,
                "settings": company.settings if isinstance(company.settings, dict) else {},
                "role": "admin"
            })
        return results
    return crud.get_user_companies(db, str(current_user.id))

@router.get("/{user_id}", response_model=schemas.UserResponse)
def read_user(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    is_platform_admin = getattr(current_user, "is_platform_admin", False)
    if not is_platform_admin and not check_manager_access(db, current_user, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return user

@router.get("", response_model=List[schemas.UserResponse])
def read_users(skip: int = 0, limit: int = 100, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    users = crud.get_users(db, skip=skip, limit=limit)
    return users

@router.post("", response_model=schemas.UserResponse)
async def create_user_admin(user: schemas.UserCreate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    db_user = crud.get_user_by_email(db, email=user.email)
    if db_user:
        raise HTTPException(status_code=400, detail="Email already registered")
    
    # Option A: Random unusable Password
    import secrets
    unusable_password = secrets.token_urlsafe(32)
    user.password = unusable_password # Override with random secure string
    
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
        created_user.default_company_id = user.company_id
        db.commit()
    
    return created_user

@router.put("/{user_id}/status")
def toggle_user_status(user_id: str, is_active: bool, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    user = crud.update_user_status(db, user_id=user_id, is_active=is_active)
    if not user:
         raise HTTPException(status_code=404, detail="User not found")
    return {"message": "Status updated", "is_active": user.is_active}

@router.put("/me", response_model=schemas.UserResponse)
def update_user_me(user: schemas.UserSelfUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    # Create a full UserUpdate object but only with allowed fields
    db_user = crud.update_user(db, str(current_user.id), schemas.UserUpdate(**user.dict()))
    return db_user

@router.post("/me/change-password")
def change_password(data: schemas.PasswordChange, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    # Verify current password
    if not auth.verify_password(data.current_password, current_user.hashed_password):
        raise HTTPException(status_code=400, detail="Incorrect current password")
    
    # Update password
    current_user.hashed_password = auth.get_password_hash(data.new_password)
    current_user.must_change_password = False
    
    db.commit()
    return {"message": "Password updated successfully"}

@router.post("/{user_id}/reset-password-email")
async def reset_password_via_email(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    """
    Admin only: Reset user password to a random one and email it.
    """
    if not getattr(current_user, "is_platform_admin", False):
        # Manager check
        is_manager = check_manager_access(db, current_user, user_id)
        if not is_manager:
             raise HTTPException(status_code=403, detail="Not authorized")

    user = crud.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
        
    # Update User
    user.must_change_password = True
    db.commit()
    
    # Send Email
    try:
        reset_token = auth.create_reset_token(user.email)
        await email_utils.send_password_reset_email(user.email, reset_token)
    except Exception as e:
        print(f"Error sending email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send email.")
        
    return {"message": "Password reset and email sent"}

@router.put("/{user_id}", response_model=schemas.UserResponse)
def update_user(user_id: str, user: schemas.UserUpdate, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(status_code=403, detail="Not authorized")
    db_user = crud.update_user(db, user_id, user)
    if not db_user:
        raise HTTPException(status_code=404, detail="User not found")
    return db_user

@router.get("/{user_id}/companies", response_model=List[schemas.CompanyResponse])
def read_user_companies_admin(user_id: str, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)):
    is_platform_admin = getattr(current_user, "is_platform_admin", False)
    if not is_platform_admin and not check_manager_access(db, current_user, user_id):
        raise HTTPException(status_code=403, detail="Not authorized")
    return crud.get_user_companies(db, user_id, include_inactive=True)
