import enum
import uuid
from datetime import UTC, datetime

from database import Base
from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    Time,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import relationship, validates


def _utcnow() -> datetime:
    return datetime.now(UTC)


class UserRole(str, enum.Enum):
    admin = "admin"  # System Creator / Super Admin
    user = "user"  # Regular User


class CompanyRole(str, enum.Enum):
    admin = "admin"  # Deprecated or specific high-level company admin
    manager = "manager"  # Supervisor/Boss
    worker = "worker"  # Regular Employee


# WorkLog types are now dynamic and defined per company in JSONB

# RequestStatus was replaced by MemberStatus for company joins


class User(Base):
    """
    User Model.

    Represents a registered user in the system.
    """

    __tablename__ = "users"
    __table_args__ = (Index("uq_users_email_lower", text("lower(email)"), unique=True),)

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.user, server_default="user")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")  # System Login Access

    # Auth & Security
    must_change_password = Column(Boolean, nullable=False, default=False, server_default="false")

    # TOTP 2FA Evolution
    is_2fa_enabled = Column(Boolean, nullable=False, default=False, server_default="false")
    otp_secret = Column(String, nullable=True)  # Cifrado con Fernet (ENCRYPTION_KEY) via auth.encrypt_secret

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    work_logs = relationship("WorkLog", back_populates="user")
    company_memberships = relationship("CompanyMember", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")

    @validates("email")
    def _normalize_email(self, _key: str, value: str | None) -> str | None:
        return value.strip().lower() if isinstance(value, str) else value


# Legacy UserDevice model removed in favor of UserSession

# MemberStatus enum removed in favor of simple is_active boolean


class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String(120), nullable=False)

    # SaaS Evolution: Dynamic tax/deduction configuration
    tax_config = Column(JSONB, nullable=True)
    # Structure example: { "IRPF": 0.15, "Seguridad Social": 0.0648 } (nombre libre -> tasa 0..1; {} o NULL = sin impuestos)

    # SaaS Evolution: Dynamic shift definitions
    worklog_definitions = Column(JSONB, default=dict)
    # Structure example: { "particular": { "unit": "hours", "label": "Particular", "fields": [...] } }

    is_active = Column(Boolean, default=True, server_default="true", nullable=False)
    is_managed = Column(Boolean, default=False, server_default="false", nullable=False)

    settings = Column(JSONB, default=dict)  # Global company settings
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    members = relationship(
        "CompanyMember",
        back_populates="company",
        order_by="CompanyMember.sort_order.asc(), CompanyMember.joined_at.asc()",
    )
    work_logs = relationship("WorkLog", back_populates="company")
    # user_rates = relationship("UserCompanyRate", back_populates="company") # Deprecated


class CompanyMember(Base):
    __tablename__ = "company_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True, index=True)
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.worker, server_default="worker")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    sort_order = Column(Integer, default=1000, server_default="1000")

    # SaaS Evolution: The "Contract" - user rates for THIS specific company
    rates_config = Column(JSONB, default=dict)
    # Structure example: { "particular": { "base_rate": 25.0, "is_gross": true, "tax_overrides": {...} } }

    settings = Column(JSONB, default=dict)  # User-specific UI/Feature overrides
    joined_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="company_memberships")
    company = relationship("Company", back_populates="members")


# UserCompanyRate was removed in favor of dynamic JSONB rates_config in CompanyMember


class WorkLog(Base):
    __tablename__ = "work_logs"
    __table_args__ = (
        Index("ix_work_logs_company_start_date", "company_id", "start_date"),
        Index("ix_work_logs_user_start_date", "user_id", "start_date"),
        CheckConstraint("end_date >= start_date", name="ck_work_logs_end_date_gte_start_date"),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)

    type = Column(String, nullable=False)

    start_date = Column(Date, nullable=False)
    end_date = Column(Date, nullable=False)

    start_time = Column(Time, nullable=True)
    end_time = Column(Time, nullable=True)

    duration = Column(Numeric(10, 2), nullable=True)

    net_amount = Column(Numeric(10, 2), nullable=True)
    gross_amount = Column(Numeric(10, 2), nullable=False, default=0.0, server_default="0")

    extra_data = Column(JSONB, default=dict)  # Stores dynamic extras: {"has_night": true, etc.}

    description = Column(Text, nullable=True)

    # SaaS Evolution: Historical integrity snapshot
    calculation_snapshot = Column(JSONB, nullable=True)
    # Stores a copy of rates, definitions and logic used for this calculation.

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    user = relationship("User", back_populates="work_logs")
    company = relationship("Company", back_populates="work_logs")


# AccessRequest is deprecated. Admin adds users or users join companies.


class UserSession(Base):
    """
    Session Management for advanced security and remote revocation.
    """

    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False, index=True)

    refresh_token_hash = Column(String(64), unique=True, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=True)
    revoked_at = Column(DateTime(timezone=True), nullable=True)
    device_name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)

    is_active = Column(Boolean, nullable=False, default=True, server_default="true")
    last_active = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    __table_args__ = (Index("ix_audit_logs_company_created", "company_id", "created_at"),)
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String, nullable=False, index=True)
    actor_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    company_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    target_user_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    old_value = Column(JSONB, nullable=True)
    new_value = Column(JSONB, nullable=True)
    reason = Column(Text, nullable=True)
    extra_data = Column(JSONB, default=dict)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )


class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trial = "trial"
    cancelled = "cancelled"
    expired = "expired"


class AppModule(Base):
    """
    Catalogo de modulos/funcionalidades disponibles en la plataforma.
    Solo el Platform Admin puede crear/editar modulos.
    """

    __tablename__ = "app_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_name = Column(String, unique=True, nullable=False)  # e.g. "worker_daily_report", "reports"
    name = Column(String, nullable=False)  # Display name
    description = Column(Text, nullable=True)
    is_active = Column(
        Boolean, nullable=False, default=True, server_default="true"
    )  # Is the module available to subscribe to?

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    subscriptions = relationship("ModuleSubscription", back_populates="module")


class ModuleSubscription(Base):
    """Suscripcion de una empresa a un modulo del catalogo."""

    __tablename__ = "module_subscriptions"
    __table_args__ = (
        CheckConstraint("company_id IS NOT NULL", name="ck_module_subscriptions_company_id_not_null"),
        Index(
            "uq_module_subscriptions_active_company",
            "module_id",
            "company_id",
            unique=True,
            postgresql_where=text("status = 'active'"),
            sqlite_where=text("status = 'active'"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("app_modules.id"), nullable=False)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=False, index=True)

    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.active)

    # Optional expiry (NULL = never expires)
    expires_at = Column(DateTime(timezone=True), nullable=True)

    notes = Column(Text, nullable=True)  # Admin notes (e.g. "Regalo promo", "Pago Stripe #123")

    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    module = relationship("AppModule", back_populates="subscriptions")
    company = relationship("Company")


class CompanyInvitation(Base):
    """Invitacion de un solo uso por correo electronico para unirse a una empresa como miembro."""

    __tablename__ = "company_invitations"
    __table_args__ = (
        Index("ix_company_invitations_company_id", "company_id"),
        Index(
            "uq_company_invitations_pending_company_email",
            "company_id",
            text("lower(email)"),
            unique=True,
            postgresql_where=text("accepted_at IS NULL AND cancelled_at IS NULL"),
            sqlite_where=text("accepted_at IS NULL AND cancelled_at IS NULL"),
        ),
    )

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id", ondelete="CASCADE"), nullable=False)
    email = Column(String(320), nullable=False)
    token_hash = Column(String(64), unique=True, nullable=False)
    invited_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    accepted_at = Column(DateTime(timezone=True), nullable=True)
    accepted_by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    cancelled_at = Column(DateTime(timezone=True), nullable=True)
    created_at = Column(
        DateTime(timezone=True), nullable=False, default=_utcnow, server_default=text("CURRENT_TIMESTAMP")
    )
    updated_at = Column(
        DateTime(timezone=True),
        nullable=False,
        default=_utcnow,
        onupdate=_utcnow,
        server_default=text("CURRENT_TIMESTAMP"),
    )

    company = relationship("Company")
    invited_by = relationship("User", foreign_keys=[invited_by_user_id])
    accepted_by = relationship("User", foreign_keys=[accepted_by_user_id])

    @validates("email")
    def _normalize_email(self, _key: str, value: str | None) -> str | None:
        return value.strip().lower() if isinstance(value, str) else value
