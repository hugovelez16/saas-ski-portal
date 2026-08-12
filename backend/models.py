from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey, Numeric, Date, Time, Text, Enum, Integer
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
import uuid
from datetime import datetime
import enum
from database import Base

class UserRole(str, enum.Enum):
    admin = "admin" # System Creator / Super Admin
    user = "user" # Regular User

class CompanyRole(str, enum.Enum):
    admin = "admin" # Deprecated or specific high-level company admin
    manager = "manager" # Supervisor/Boss
    worker = "worker" # Regular Employee

# WorkLog types are now dynamic and defined per company in JSONB

# RequestStatus was replaced by MemberStatus for company joins

class User(Base):
    """
    User Model.
    
    Represents a registered user in the system.
    """
    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String, unique=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    first_name = Column(String)
    last_name = Column(String)
    role = Column(Enum(UserRole), default=UserRole.user)
    is_active = Column(Boolean, default=True) # System Login Access
    default_company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)

    # Auth & Security
    must_change_password = Column(Boolean, default=False)
    
    # TOTP 2FA Evolution
    is_2fa_enabled = Column(Boolean, default=False)
    otp_secret = Column(String, nullable=True) # Should be encrypted in production

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    default_company = relationship("Company", foreign_keys=[default_company_id])

    work_logs = relationship("WorkLog", back_populates="user")
    company_memberships = relationship("CompanyMember", back_populates="user")
    sessions = relationship("UserSession", back_populates="user")

# Legacy UserDevice model removed in favor of UserSession

# MemberStatus enum removed in favor of simple is_active boolean

class Company(Base):
    __tablename__ = "companies"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    fiscal_id = Column(String)
    
    # SaaS Evolution: Dynamic tax/deduction configuration
    tax_config = Column(JSONB, default={"social_security": 0.0648})
    # Structure example: { "social_security": 0.0648, "irpf_base": 0.15 }
    
    # SaaS Evolution: Dynamic shift definitions
    worklog_definitions = Column(JSONB, default={}) 
    # Structure example: { "particular": { "unit": "hours", "label": "Particular", "fields": [...] } }
    
    settings = Column(JSONB, default={}) # Global company settings
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    members = relationship("CompanyMember", back_populates="company")
    work_logs = relationship("WorkLog", back_populates="company")
    # user_rates = relationship("UserCompanyRate", back_populates="company") # Deprecated

class CompanyMember(Base):
    __tablename__ = "company_members"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), primary_key=True)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), primary_key=True)
    role = Column(Enum(CompanyRole), nullable=False, default=CompanyRole.worker, server_default="worker")
    is_active = Column(Boolean, nullable=False, default=True, server_default="true") 
    sort_order = Column(Integer, default=1000, server_default="1000")
    
    # SaaS Evolution: The "Contract" - user rates for THIS specific company
    rates_config = Column(JSONB, default={})
    # Structure example: { "particular": { "base_rate": 25.0, "is_gross": true, "tax_overrides": {...} } }

    settings = Column(JSONB, default={}) # User-specific UI/Feature overrides
    joined_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="company_memberships")
    company = relationship("Company", back_populates="members")

# UserCompanyRate was removed in favor of dynamic JSONB rates_config in CompanyMember

class WorkLog(Base):
    __tablename__ = "work_logs"

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
    gross_amount = Column(Numeric(10, 2), default=0.0)
    
    extra_data = Column(JSONB, default={}) # Stores dynamic extras: {"has_night": true, etc.}
    
    description = Column(Text, nullable=True)
    
    # SaaS Evolution: Historical integrity snapshot
    calculation_snapshot = Column(JSONB, nullable=True)
    # Stores a copy of rates, definitions and logic used for this calculation.
    
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", back_populates="work_logs")
    company = relationship("Company", back_populates="work_logs")

# AccessRequest is deprecated. Admin adds users or users join companies.


class UserSession(Base):
    """
    Session Management for advanced security and remote revocation.
    """
    __tablename__ = "user_sessions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    
    refresh_token = Column(String, unique=True, nullable=False)
    device_name = Column(String, nullable=True)
    ip_address = Column(String, nullable=True)
    
    is_active = Column(Boolean, default=True)
    last_active = Column(DateTime, default=datetime.utcnow)
    created_at = Column(DateTime, default=datetime.utcnow)

    user = relationship("User", back_populates="sessions")


class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    action = Column(String, nullable=False)
    impersonated_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    admin_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=False)
    extra_data = Column(JSONB, default={})
    created_at = Column(DateTime, default=datetime.utcnow)


class SubscriptionScope(str, enum.Enum):
    company = "company"  # Suscripción asignada a toda una empresa
    user = "user"        # Suscripción asignada a un usuario individual

class SubscriptionStatus(str, enum.Enum):
    active = "active"
    trial = "trial"
    cancelled = "cancelled"
    expired = "expired"

class AppModule(Base):
    """
    Catálogo de módulos/funcionalidades disponibles en la plataforma.
    Solo el Platform Admin puede crear/editar módulos.
    """
    __tablename__ = "app_modules"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code_name = Column(String, unique=True, nullable=False)  # e.g. "worker_daily_report", "export_pdf"
    name = Column(String, nullable=False)                    # Display name
    description = Column(Text, nullable=True)
    is_active = Column(Boolean, default=True)               # Is the module available to subscribe to?

    # Which scopes can subscribe to this module?
    # "both" means company OR user can subscribe.
    # "company" means only company-level subs.
    # "user" means only user-level subs.
    target_scope = Column(String, default="both")  # "company" | "user" | "both"

    # Future: pricing info (not used yet)
    price_monthly = Column(Numeric(10, 2), nullable=True)

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    subscriptions = relationship("ModuleSubscription", back_populates="module")


class ModuleSubscription(Base):
    """
    Suscripción activa a un módulo.
    Puede ser de empresa (company_id != NULL, user_id == NULL)
    o de usuario (user_id != NULL, company_id == NULL).
    """
    __tablename__ = "module_subscriptions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    module_id = Column(UUID(as_uuid=True), ForeignKey("app_modules.id"), nullable=False)

    # Exactly ONE of these must be set (enforced at application level)
    company_id = Column(UUID(as_uuid=True), ForeignKey("companies.id"), nullable=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    scope = Column(Enum(SubscriptionScope), nullable=False)
    status = Column(Enum(SubscriptionStatus), nullable=False, default=SubscriptionStatus.active)

    # Optional expiry (NULL = never expires)
    expires_at = Column(DateTime, nullable=True)

    notes = Column(Text, nullable=True)  # Admin notes (e.g. "Regalo promo", "Pago Stripe #123")

    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    module = relationship("AppModule", back_populates="subscriptions")
    company = relationship("Company")
    user = relationship("User")

