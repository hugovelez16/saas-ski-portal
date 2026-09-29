from fastapi import APIRouter, Depends, HTTPException, status, Request, Response
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from uuid import UUID
from datetime import timedelta, datetime
from typing import List

import auth, crud, models, schemas
from database import get_db

router = APIRouter()

@router.post("/token", response_model=schemas.Token)
async def login_for_access_token(
    response: Response,
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(), 
    db: Session = Depends(get_db)
):
    """
    Step 1: Validate email/password.
    If 2FA is enabled, return provisional token.
    Otherwise, create session and return full tokens.
    """
    user = crud.get_user_by_email(db, form_data.username)
    if not user or not auth.verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    
    # Check if 2FA is required
    if user.is_2fa_enabled:
        # Issue provisional token (short lived, specific scope)
        provisional_token = auth.create_access_token(
            data={"sub": str(user.id), "scope": "2fa_pending"},
            expires_delta=timedelta(minutes=5)
        )
        # Set provisional access token as cookie
        response.set_cookie(
            key="access_token",
            value=provisional_token,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=300 # 5 mins
        )
        return {
            "access_token": "cookie", # Signal that it's in a cookie
            "token_type": "bearer",
            "requires_2fa": True
        }

    # No 2FA: Create full session with default scope
    access_token, refresh_token = auth.generate_user_tokens(db, user)
    
    # Store session in DB
    auth.create_session(
        db, 
        user_id=str(user.id), 
        refresh_token=refresh_token,
        device_name=request.headers.get("user-agent"),
        ip_address=request.client.host
    )
    
    # Set HttpOnly Cookies for both tokens
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return {
        "access_token": "cookie", 
        "token_type": "bearer",
        "requires_2fa": False
    }

@router.post("/verify-2fa", response_model=schemas.Token)
async def verify_2fa(
    data: schemas.Verify2FA, 
    response: Response,
    request: Request,
    db: Session = Depends(get_db), 
    current_user: models.User = Depends(auth.get_current_user)
):
    """
    Verify TOTP code and issue final tokens.
    """
    if not current_user.is_2fa_enabled or not current_user.otp_secret:
        raise HTTPException(status_code=400, detail="2FA not enabled for this user")
    
    # Decrypt secret
    decrypted_secret = auth.decrypt_secret(current_user.otp_secret)
    
    if not auth.verify_totp_code(decrypted_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    # Issue Full Tokens with default scope
    access_token, refresh_token = auth.generate_user_tokens(db, current_user)
    
    # Create Session
    auth.create_session(
        db, 
        user_id=str(current_user.id), 
        refresh_token=refresh_token,
        device_name=request.headers.get("user-agent"),
        ip_address=request.client.host
    )

    # Cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return {
        "access_token": "cookie", 
        "token_type": "bearer",
        "requires_2fa": False
    }

@router.post("/refresh-token")
async def refresh_access_token(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    refresh_token = request.cookies.get("refresh_token")
    if not refresh_token:
        raise HTTPException(status_code=401, detail="Refresh token missing")
    
    session = auth.get_session_by_token(db, refresh_token)
    if not session:
        raise HTTPException(status_code=401, detail="Invalid or revoked session")
    
    # Verify JWT integrity & expiry
    try:
        payload = auth.jwt.decode(refresh_token, auth.PUBLIC_KEY, algorithms=[auth.ALGORITHM])
        if payload.get("type") != "refresh":
             raise auth.JWTError()
        user_id = payload.get("sub")
    except auth.JWTError:
        auth.revoke_session(db, refresh_token)
        raise HTTPException(status_code=401, detail="Token expired or corrupted")
    
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=401, detail="User not found")

    new_access_token, _ = auth.generate_user_tokens(db, user)
    
    # Set as cookie
    response.set_cookie(
        key="access_token",
        value=new_access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    
    return {"access_token": "cookie", "token_type": "bearer"}

@router.post("/logout")
async def logout(
    request: Request,
    response: Response,
    db: Session = Depends(get_db)
):
    # 1. Get tokens from cookies
    access_token = request.cookies.get("access_token")
    refresh_token = request.cookies.get("refresh_token")
    
    # 2. Blacklist Access Token (if exists)
    if access_token:
        auth.blacklist_token(access_token)
        
    # 3. Revoke Session in DB (if exists)
    if refresh_token:
        auth.revoke_session(db, refresh_token)
        
    # 4. Clear Cookies
    response.delete_cookie("access_token")
    response.delete_cookie("refresh_token")
    response.delete_cookie("admin_access_token") # Also clear backups if any
    response.delete_cookie("admin_refresh_token")
    
    return {"message": "Logged out successfully"}

@router.post("/auth/switch-scope", response_model=schemas.Token)
async def switch_scope(
    data: schemas.TokenData, 
    response: Response,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """
    SaaS: Switch active company and role context.
    Issues NEW JWT cookies.
    """
    # Platform Admins can switch to ANY company and ANY role, OR reset to pure admin
    if current_user.role == models.UserRole.admin:
        if not data.company_id:
            # Special case: Reset to Admin ONLY context
            access_token, refresh_token = auth.generate_user_tokens(
                db, current_user, company_id=None, role=None, force_none=True,
                scope=getattr(current_user, "token_scope", None)
            )
        else:
            requested_role = data.company_role or "manager"
            access_token, refresh_token = auth.generate_user_tokens(
                db, current_user, company_id=data.company_id, role=requested_role,
                scope=getattr(current_user, "token_scope", None)
            )
    else:
        # Verify membership and role for regular users
        if not data.company_id:
            raise HTTPException(status_code=400, detail="company_id is required")
            
        membership = db.query(models.CompanyMember).filter(
            models.CompanyMember.user_id == current_user.id,
            models.CompanyMember.company_id == data.company_id,
            models.CompanyMember.is_active == True
        ).first()
        
        if not membership:
            raise HTTPException(status_code=403, detail="You are not a member of this company")
            
        requested_role = data.company_role or "worker"
        if requested_role == "manager":
            if membership.role not in [models.CompanyRole.admin, models.CompanyRole.manager]:
                raise HTTPException(status_code=403, detail="Insufficient permissions for manager scope")
            
        access_token, refresh_token = auth.generate_user_tokens(
            db, current_user, company_id=data.company_id, role=requested_role,
            scope=getattr(current_user, "token_scope", None)
        )
    
    response.set_cookie(
        key="access_token", value=access_token, httponly=True, secure=True, samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token", value=refresh_token, httponly=True, secure=True, samesite="lax",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    
    return {"access_token": "cookie", "token_type": "bearer", "requires_2fa": False}

@router.post("/admin/stop-impersonation")
async def stop_impersonation(
    request: Request,
    response: Response
):
    """
    SRE: Restore Admin session from backup cookies.
    """
    admin_access = request.cookies.get("admin_access_token")
    admin_refresh = request.cookies.get("admin_refresh_token")
    
    if not admin_access or not admin_refresh:
        # If no backup, just logout
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")
        return {"message": "Impersonation ended (no backup found)"}
        
    # Restore main cookies from backups
    response.set_cookie(
        key="access_token",
        value=admin_access,
        httponly=True,
        secure=True, 
        samesite="lax",
        max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )
    response.set_cookie(
        key="refresh_token",
        value=admin_refresh,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )
    
    # Clear backups
    response.delete_cookie("admin_access_token")
    response.delete_cookie("admin_refresh_token")
    
    return {"message": "Returned to admin session"}

@router.post("/admin/impersonate/{user_id}", response_model=schemas.Token)
async def impersonate_user(
    user_id: UUID,
    response: Response,
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """
    Impersonation: Global admin can log in as any user.
    """
    if not getattr(current_user, "is_platform_admin", False):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Only global administrators can impersonate users"
        )
    
    target_user = db.query(models.User).filter(models.User.id == user_id).first()
    if not target_user:
        raise HTTPException(status_code=404, detail="Target user not found")
    
    # Backup current admin session before impersonating
    current_access = request.cookies.get("access_token")
    current_refresh = request.cookies.get("refresh_token")
    
    # Generate Hardened Tokens for the target user
    access_token, _ = auth.generate_user_tokens(db, target_user)
    
    # Re-decode to update scope and exp
    payload = auth.jwt.decode(access_token, auth.PRIVATE_KEY, algorithms=[auth.ALGORITHM])
    payload.update({
        "scope": "impersonated",
        "admin_user_id": str(current_user.id),
        "exp": datetime.utcnow() + timedelta(minutes=10)
    })
    access_token = auth.jwt.encode(payload, auth.PRIVATE_KEY, algorithm=auth.ALGORITHM)
    refresh_token = auth.create_refresh_token(data={"sub": str(target_user.id)})
    
    # Set Backup Cookies ONLY if we are starting a primary impersonation (not nested)
    if current_access and current_refresh and not request.cookies.get("admin_refresh_token"):
        response.set_cookie(
            key="admin_access_token",
            value=current_access,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=auth.ACCESS_TOKEN_EXPIRE_MINUTES * 60
        )
        response.set_cookie(
            key="admin_refresh_token",
            value=current_refresh,
            httponly=True,
            secure=True,
            samesite="lax",
            max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
        )
    
    # Create Session for the target user (marked as impersonated in audit)
    auth.create_session(
        db, 
        user_id=str(target_user.id), 
        refresh_token=refresh_token,
        device_name=f"IMPERSONATED by Admin ({current_user.email})",
        ip_address=request.client.host
    )
    
    # Set Cookies
    response.set_cookie(
        key="access_token",
        value=access_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=600 # 10 mins
    )
    response.set_cookie(
        key="refresh_token",
        value=refresh_token,
        httponly=True,
        secure=True,
        samesite="lax",
        max_age=auth.REFRESH_TOKEN_EXPIRE_DAYS * 86400
    )

    return {
        "access_token": "cookie", 
        "token_type": "bearer",
        "requires_2fa": False
    }

@router.post("/2fa/setup", response_model=schemas.TOTPSetupResponse)
async def setup_2fa(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """Generates a new TOTP secret for the user (not active yet)."""
    secret = auth.generate_totp_secret()
    current_user.otp_secret = auth.encrypt_secret(secret)
    current_user.is_2fa_enabled = False # Not enabled until verified
    db.commit()
    
    uri = auth.get_totp_uri(secret, current_user.email)
    return {"secret": secret, "qr_code_uri": uri}

@router.post("/2fa/activate")
async def activate_2fa(
    data: schemas.TOTPActivate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """Verifies the first code and enables 2FA."""
    if not current_user.otp_secret:
        raise HTTPException(status_code=400, detail="2FA setup not initiated")
    
    decrypted_secret = auth.decrypt_secret(current_user.otp_secret)
    if not auth.verify_totp_code(decrypted_secret, data.code):
        raise HTTPException(status_code=400, detail="Invalid verification code")
    
    current_user.is_2fa_enabled = True
    db.commit()
    return {"message": "2FA activated successfully"}

@router.post("/2fa/disable")
async def disable_2fa(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """Disables 2FA (Requires verified user)."""
    current_user.is_2fa_enabled = False
    current_user.otp_secret = None
    db.commit()
    return {"message": "2FA disabled"}

@router.get("/sessions", response_model=List[schemas.SessionResponse])
async def list_sessions(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """Lists all active sessions for the user."""
    return [s for s in current_user.sessions if s.is_active]

@router.delete("/sessions/{session_id}")
async def revoke_session(
    session_id: str,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user)
):
    """Revokes a specific session."""
    session = db.query(models.UserSession).filter(
        models.UserSession.id == session_id,
        models.UserSession.user_id == current_user.id
    ).first()
    
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    session.is_active = False
    db.commit()
    return {"message": "Session revoked"}

@router.post("/auth/forgot-password")
async def forgot_password(
    data: schemas.PasswordResetRequest,
    db: Session = Depends(get_db)
):
    import email_utils
    user = crud.get_user_by_email(db, data.email)
    if not user:
        # Avoid user enumeration by returning 200 anyway
        return {"message": "If the email exists, a reset link has been sent."}
    
    # Generate token
    token = auth.create_reset_token(user.email)
    
    # Send email
    try:
        await email_utils.send_password_reset_email(user.email, token)
    except Exception as e:
        print(f"Error sending password reset email: {e}")
        raise HTTPException(status_code=500, detail="Failed to send password reset email.")
        
    return {"message": "If the email exists, a reset link has been sent."}

@router.post("/auth/reset-password")
async def reset_password(
    data: schemas.PasswordResetConfirm,
    db: Session = Depends(get_db)
):
    email = auth.verify_reset_token(data.token)
    if not email:
        raise HTTPException(status_code=400, detail="Invalid or expired reset token.")
        
    user = crud.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found.")
        
    # Update password and disable must_change_password
    user.hashed_password = auth.get_password_hash(data.new_password)
    user.must_change_password = False
    db.commit()
    
    # Invalidate reset token to prevent replay attacks
    auth.consume_reset_token(data.token)
    
    return {"message": "Password updated successfully."}
