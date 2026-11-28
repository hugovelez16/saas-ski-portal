"""Entidad de dominio CompanyInvitation: invitacion por correo de un solo uso para unirse a una empresa."""

import hashlib
import secrets
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Optional

INVITATION_TTL_DAYS = 7


def normalize_invitation_email(email: str) -> str:
    """Normaliza un correo de invitacion a minusculas sin espacios sobrantes."""
    return email.strip().lower()


def hash_invitation_token(raw_token: str) -> str:
    """Devuelve el hash SHA-256 hexadecimal del token de invitacion."""
    return hashlib.sha256(raw_token.encode("utf-8")).hexdigest()


def generate_invitation_token() -> tuple[str, str]:
    """Genera un par (token_en_claro, token_hash_sha256) criptograficamente seguro."""
    raw_token = secrets.token_urlsafe(32)
    return raw_token, hash_invitation_token(raw_token)


def ensure_utc(dt: datetime) -> datetime:
    """Devuelve una fecha consciente en UTC (compatibilidad con SQLite si viene naive)."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


@dataclass
class CompanyInvitation:
    company_id: str
    email: str
    token_hash: str
    invited_by_user_id: str
    expires_at: datetime
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    accepted_at: Optional[datetime] = None
    accepted_by_user_id: Optional[str] = None
    cancelled_at: Optional[datetime] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @classmethod
    def default_expires_at(cls, now: Optional[datetime] = None) -> datetime:
        base = ensure_utc(now) if now is not None else datetime.now(UTC)
        return base + timedelta(days=INVITATION_TTL_DAYS)

    def is_expired(self, now: Optional[datetime] = None) -> bool:
        ref = ensure_utc(now) if now is not None else datetime.now(UTC)
        return ensure_utc(self.expires_at) <= ref

    def status_at(self, now: Optional[datetime] = None) -> str:
        if self.cancelled_at is not None:
            return "cancelled"
        if self.accepted_at is not None:
            return "accepted"
        if self.is_expired(now):
            return "expired"
        return "pending"
