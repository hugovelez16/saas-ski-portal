"""
Authentication Module.

This module handles password hashing, token creation/verification, and current user retrieval.
It uses OAuth2 with Password Flow and JWT tokens.
"""
import os
import secrets
from datetime import datetime, timedelta

import crud
import models
import pyotp
import schemas
from cryptography.fernet import Fernet
from database import get_db
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from passlib.context import CryptContext
from redis_config import redis_manager
from sqlalchemy.orm import Session

# Cryptographic Configuration
# RS256 (Asymmetric) is used for signing and verification.
# The private key signs the token; the public key verifies it.
ALGORITHM = "RS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 30

# Load RSA Keys
KEYS_DIR = os.path.join(os.path.dirname(__file__), "keys")
try:
    with open(os.path.join(KEYS_DIR, "public_key.pem"), "r") as f:
        PUBLIC_KEY = f.read()

    with open(os.path.join(KEYS_DIR, "private_key.pem"), "rb") as f:
        private_key_data = f.read()

    from cryptography.hazmat.backends import default_backend
    from cryptography.hazmat.primitives import serialization

    passphrase = os.getenv("JWT_PRIVATE_KEY_PASSPHRASE")
    private_key_obj = serialization.load_pem_private_key(
        private_key_data,
        password=passphrase.encode() if passphrase else None,
        backend=default_backend()
    )

    PRIVATE_KEY = private_key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption()
    ).decode("utf-8")
except (FileNotFoundError, ValueError, TypeError):
    # Fallback for dev/CI if keys don't exist yet or decryption fails
    PRIVATE_KEY = os.getenv("PRIVATE_KEY", "")
    PUBLIC_KEY = os.getenv("PUBLIC_KEY", "")
    if not PRIVATE_KEY and not PUBLIC_KEY:
        try:
            print("RSA keys not found or failed to load. Generating a new key pair for local development...")
            from cryptography.hazmat.backends import default_backend
            from cryptography.hazmat.primitives import serialization
            from cryptography.hazmat.primitives.asymmetric import rsa

            # Generate new RSA key pair
            private_key_obj = rsa.generate_private_key(
                public_exponent=65537,
                key_size=2048,
                backend=default_backend()
            )

            # Serialize key pair (unencrypted for easy local development)
            pem_private = private_key_obj.private_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PrivateFormat.PKCS8,
                encryption_algorithm=serialization.NoEncryption()
            )
            pem_public = private_key_obj.public_key().public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo
            )

            # Write key pair back to disk to persist across hot-reloads if writable
            try:
                os.makedirs(KEYS_DIR, exist_ok=True)
                with open(os.path.join(KEYS_DIR, "private_key.pem"), "wb") as f:
                    f.write(pem_private)
                with open(os.path.join(KEYS_DIR, "public_key.pem"), "wb") as f:
                    f.write(pem_public)
                print("Successfully auto-generated RSA key pair for local development (saved under keys/).")
            except Exception as write_err:
                print(f"Warning: Could not save RSA keys to disk ({write_err}). Using in-memory keys for this session.")

            PRIVATE_KEY = pem_private.decode("utf-8")
            PUBLIC_KEY = pem_public.decode("utf-8")
        except Exception as gen_err:
            raise RuntimeError(f"Failed to generate RSA key: {gen_err}")


# Encryption key for OTP secrets
_encryption_key_env = os.getenv("ENCRYPTION_KEY")
if not _encryption_key_env:
    ENCRYPTION_KEY = Fernet.generate_key().decode()
else:
    if len(_encryption_key_env) == 64:
        try:
            import base64
            raw_key = bytes.fromhex(_encryption_key_env)
            ENCRYPTION_KEY = base64.urlsafe_b64encode(raw_key).decode()
        except ValueError:
            ENCRYPTION_KEY = _encryption_key_env
    else:
        ENCRYPTION_KEY = _encryption_key_env

try:
    fernet = Fernet(ENCRYPTION_KEY.encode())
except Exception as e:
    print(f"Warning: Invalid ENCRYPTION_KEY ({e}). Generating a new ephemeral Fernet key for local development.")
    ENCRYPTION_KEY = Fernet.generate_key().decode()
    fernet = Fernet(ENCRYPTION_KEY.encode())

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token", auto_error=False)

def get_token_from_request(request: Request):
    """
    Extracts token from HttpOnly cookie (preferred) or Authorization header.
    """
    token = request.cookies.get("access_token")
    if not token:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            token = auth_header.split(" ")[1]
    return token

def encrypt_secret(secret: str) -> str:
    return fernet.encrypt(secret.encode()).decode()

def decrypt_secret(encrypted_secret: str) -> str:
    return fernet.decrypt(encrypted_secret.encode()).decode()

def verify_password(plain_password, hashed_password):
    """Verifies a plain:hashed password match."""
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password):
    """Generates a Bcrypt hash for a password."""
    return pwd_context.hash(password)

def create_access_token(data: dict, expires_delta: timedelta | None = None):
    """Creates a JWT access token with an expiration time."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    # Added jti for revocation support
    to_encode.update({"exp": expire, "iat": now, "type": "access", "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)

def create_refresh_token(data: dict):
    """Creates a long-lived JWT refresh token."""
    to_encode = data.copy()
    now = datetime.utcnow()
    expire = now + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS)
    to_encode.update({"exp": expire, "iat": now, "type": "refresh", "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)

_consumed_reset_jtis = set()

def create_reset_token(email: str) -> str:
    """Creates a short-lived JWT reset token (valid for 30 minutes)."""
    to_encode = {"sub": email, "type": "reset"}
    now = datetime.utcnow()
    expire = now + timedelta(minutes=30)
    to_encode.update({"exp": expire, "iat": now, "jti": secrets.token_hex(16)})
    return jwt.encode(to_encode, PRIVATE_KEY, algorithm=ALGORITHM)

def verify_reset_token(token: str) -> str | None:
    """Verifies the reset token, ensuring it has not been consumed yet."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        if payload.get("type") != "reset":
            return None
        jti = payload.get("jti")
        if not jti:
            return None
        # Check Redis if available
        try:
            from redis_config import redis_manager
            redis_client = redis_manager.get_client()
            if redis_client and redis_client.get(f"revoked_reset_jti:{jti}"):
                return None
        except Exception:
            pass
        if jti in _consumed_reset_jtis:
            return None
        return payload.get("sub")
    except JWTError:
        return None

def consume_reset_token(token: str) -> bool:
    """Marks a reset token as consumed so it cannot be replayed."""
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        if not jti:
            return False
        _consumed_reset_jtis.add(jti)
        try:
            from redis_config import redis_manager
            redis_client = redis_manager.get_client()
            if redis_client:
                redis_client.setex(f"revoked_reset_jti:{jti}", 3600, "consumed")
        except Exception:
            pass
        return True
    except JWTError:
        return False

def generate_user_tokens(db: Session, user: models.User, company_id: str | None = None, role: str | None = None, force_none: bool = False, scope: str | None = None):
    """
    SRE: Enhanced token generation with platform and company context.
    If company_id or role are not provided, it selects defaults based on user profile and memberships.
    If force_none is True, it allows cid/role to be None (only for platform admins).
    """
    is_platform_admin = user.role == models.UserRole.admin

    # SaaS Logic: Platform Admins start in neutral context by default unless a company is explicitly requested
    if is_platform_admin and (force_none or not company_id):
        active_cid = company_id
        active_role = role
    else:
        active_cid = company_id or (str(user.default_company_id) if user.default_company_id else None)
        active_role = role

        # Selection logic if not explicitly provided
        if not active_cid or not active_role:
            # Try to find membership for default or any company
            query = db.query(models.CompanyMember).filter(
                models.CompanyMember.user_id == user.id,
                models.CompanyMember.is_active == True
            )

            if active_cid:
                membership = query.filter(models.CompanyMember.company_id == active_cid).first()
                if not membership:
                    membership = query.first()
            else:
                membership = query.first()

            if membership:
                active_cid = str(membership.company_id)
                if not active_role:
                    # admin/manager roles -> manager scope
                    if membership.role in [models.CompanyRole.admin, models.CompanyRole.manager]:
                        active_role = "manager"
                    else:
                        active_role = "worker"

    # Token Data
    data = {
        "sub": str(user.id),
        "is_admin": is_platform_admin,
        "cid": active_cid,
        "role": active_role,
        "scope": scope or "full"
    }

    access_token = create_access_token(data=data)
    refresh_token = create_refresh_token(data={"sub": str(user.id)})
    return access_token, refresh_token

async def get_current_user(token: str = Depends(get_token_from_request), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")

        if user_id is None:
            raise credentials_exception

        # SRE Improvement: Check Blacklist in Redis
        if jti and redis_manager.get(f"bl_{jti}"):
            raise credentials_exception

        token_data = schemas.TokenData(
            user_id=user_id,
            company_id=payload.get("cid"),
            company_role=payload.get("role"),
            is_platform_admin=payload.get("is_admin", False),
            scope=payload.get("scope", "full"),
            admin_user_id=payload.get("admin_user_id")
        )
    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception

    # Attach active context to user object (transient)
    user.active_company_id = token_data.company_id
    user.active_role = token_data.company_role
    user.is_platform_admin = token_data.is_platform_admin
    user.token_scope = token_data.scope
    user.admin_user_id = token_data.admin_user_id

    return user

async def get_verified_user(token: str = Depends(get_token_from_request), db: Session = Depends(get_db)):
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token missing",
            headers={"WWW-Authenticate": "Bearer"},
        )
    """
    Returns user only if token is fully authenticated (not 2fa_pending).
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    two_fa_exception = HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="2FA Verification Required",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        user_id: str = payload.get("sub")
        jti: str = payload.get("jti")
        scope: str = payload.get("scope", "")

        if user_id is None:
            raise credentials_exception

        # SRE Improvement: Check Blacklist in Redis
        if jti and redis_manager.get(f"bl_{jti}"):
            raise credentials_exception

        if scope == "2fa_pending":
             raise two_fa_exception

        token_data = schemas.TokenData(
            user_id=user_id,
            company_id=payload.get("cid"),
            company_role=payload.get("role"),
            is_platform_admin=payload.get("is_admin", False),
            scope=payload.get("scope", "full"),
            admin_user_id=payload.get("admin_user_id")
        )
    except JWTError:
        raise credentials_exception

    user = crud.get_user(db, user_id=token_data.user_id)
    if user is None:
        raise credentials_exception

    # Attach active context to user object (transient)
    user.active_company_id = token_data.company_id
    user.active_role = token_data.company_role
    user.is_platform_admin = token_data.is_platform_admin
    user.token_scope = token_data.scope
    user.admin_user_id = token_data.admin_user_id

    return user

# --- TOTP 2FA Logic ---

def generate_totp_secret() -> str:
    return pyotp.random_base32()

def get_totp_uri(secret: str, email: str, issuer_name: str = "Vesotel System") -> str:
    return pyotp.totp.TOTP(secret).provisioning_uri(name=email, issuer_name=issuer_name)

def verify_totp_code(secret: str, code: str) -> bool:
    totp = pyotp.totp.TOTP(secret)
    return totp.verify(code)

# --- Session Management ---

def create_session(db: Session, user_id: str, refresh_token: str, device_name: str = None, ip_address: str = None):
    session = models.UserSession(
        user_id=user_id,
        refresh_token=refresh_token,
        device_name=device_name,
        ip_address=ip_address,
        last_active=datetime.utcnow()
    )
    db.add(session)
    db.commit()
    return session

def get_session_by_token(db: Session, refresh_token: str):
    return db.query(models.UserSession).filter(
        models.UserSession.refresh_token == refresh_token,
        models.UserSession.is_active == True
    ).first()

def revoke_session(db: Session, refresh_token: str):
    session = get_session_by_token(db, refresh_token)
    if session:
        session.is_active = False
        db.commit()
    return session

def blacklist_token(token: str):
    """
    Blacklists an access token in Redis until it expires.
    """
    try:
        payload = jwt.decode(token, PUBLIC_KEY, algorithms=[ALGORITHM])
        jti = payload.get("jti")
        exp = payload.get("exp")
        if jti and exp:
            now = datetime.utcnow().timestamp()
            ttl = int(exp - now)
            if ttl > 0:
                redis_manager.set(f"bl_{jti}", "1", ex=ttl)
    except JWTError:
        pass

# TOTP is now the primary 2FA method. Legacy email-based 2FA logic removed.

# Legacy Device Token logic removed in favor of UserSession
