"""
Pydantic Schemas Module.

This module defines the Pydantic models used for request validation and response serialization.
It ensures that data sent to and received from the API conforms to the expected structure.
"""
from pydantic import BaseModel, EmailStr, Field, ConfigDict, BeforeValidator
from typing import Optional, List, Dict, Any, Annotated
from datetime import date as dt_date, time, datetime
from uuid import UUID
from enum import Enum

def to_camel(string: str) -> str:
    words = string.split('_')
    return words[0] + ''.join(word.capitalize() for word in words[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(
        alias_generator=to_camel,
        populate_by_name=True,
        from_attributes=True
    )

# Enums (mirroring models for validation)
# WorkLog types are now dynamic strings
class WorkLogBase(CamelModel):
    """Base schema for WorkLog data, containing common fields."""
    type: str
    start_date: dt_date = Field(..., alias="startDate")
    end_date: dt_date = Field(..., alias="endDate")
    start_time: Optional[time] = Field(None, alias="startTime")
    end_time: Optional[time] = Field(None, alias="endTime")
    duration: Optional[float] = None
    net_amount: Optional[float] = Field(None, alias="netAmount")
    gross_amount: Optional[float] = Field(None, alias="grossAmount")
    extra_data: Optional[Dict[str, Any]] = Field(default={}, alias="extraData")
    description: Optional[str] = None
    company_id: Optional[UUID] = Field(None, alias="companyId")
    group_id: Optional[UUID] = Field(None, alias="groupId")

class WorkLogCreate(WorkLogBase):
    """Schema for creating a new WorkLog entry."""
    user_id: UUID
    amount: Optional[float] = None # Allow manual amount override

class WorkLogBulkCreate(WorkLogBase):
    """Schema for creating multiple WorkLog entries at once."""
    user_ids: List[UUID] = Field(..., alias="userIds")
    amount: Optional[float] = None

class WorkLogResponse(WorkLogBase):
    """Schema for WorkLog response data."""
    id: UUID
    user_id: UUID
    amount: Optional[float] = None
    gross_amount: Optional[float] = Field(None, alias="grossAmount")

    # SaaS Evolution: Historical snapshot (includes rate_applied inside snapshot["rate_applied"])
    calculation_snapshot: Optional[Dict[str, Any]] = Field(None, alias="calculationSnapshot")
    
    created_at: datetime
    updated_at: datetime


# UserDeviceResponse removed. Use SessionResponse instead.

class UserBase(CamelModel):
    """Base schema for User data, containing common fields."""
    email: EmailStr
    first_name: Optional[str] = None
    last_name: Optional[str] = None

class UserCreate(UserBase):
    """Schema for creating a new user (registration)."""
    password: Optional[str] = None
    company_id: Optional[UUID] = None
    send_email: bool = True

class UserResponse(UserBase):
    """Schema for User response data, excluding sensitive info like passwords."""
    id: UUID
    role: str
    is_active: bool
    is_manager: bool = False # Computed
    is_active_worker: bool = False # Computed
    must_change_password: bool = False
    is_2fa_enabled: bool = False # TOTP status
    is_impersonated: bool = False # SRE: Support impersonation UI
    is_platform_admin: bool = False
    active_company_id: Optional[UUID] = None
    active_role: Optional[str] = None
    default_company_id: Optional[UUID] = None
    created_at: datetime
    
    class Config:
        from_attributes = True

class UserUpdate(CamelModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: Optional[EmailStr] = None
    role: Optional[str] = None
    is_active: Optional[bool] = None
    default_company_id: Optional[UUID] = None

class UserSelfUpdate(CamelModel):
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    default_company_id: Optional[UUID] = None

class PasswordChange(CamelModel):
    current_password: str
    new_password: str


class UserCompanyRateBase(CamelModel):
    hourly_rate: Optional[float] = 0.0
    daily_rate: Optional[float] = 0.0
    coordination_rate: Optional[float] = 0.0
    night_rate: Optional[float] = 0.0
    is_gross: Optional[bool] = False
    deduction_ss: Optional[float] = None
    deduction_irpf: Optional[float] = 0.0
    deduction_extra: Optional[float] = 0.0

class UserCompanyRateCreate(UserCompanyRateBase):
    company_id: UUID

class UserCompanyRate(UserCompanyRateBase):
    user_id: UUID
    company_id: UUID
    updated_at: datetime
    
    class Config:
        from_attributes = True

class UserCompanyRateResponse(UserCompanyRate):
    pass
    user: Optional[UserResponse] = None

class UpdateCompanyMembersOrder(CamelModel):
    user_ids: List[str]

class CompanyBase(CamelModel):
    name: str
    fiscal_id: Optional[str] = None
    tax_config: Optional[Dict[str, float]] = Field(default={"social_security": 0.0, "irpf_base": 0.0}, alias="taxConfig")
    
    # SaaS Evolution: Dynamic shift definitions
    worklog_definitions: Optional[Dict[str, Any]] = Field(default={}, alias="worklogDefinitions")
    
    settings: Optional[Dict[str, Any]] = None

class CompanyCreate(CompanyBase):
    pass

class CompanyUpdate(CamelModel):
    name: Optional[str] = None
    fiscal_id: Optional[str] = None
    tax_config: Optional[Dict[str, float]] = Field(None, alias="taxConfig")
    worklog_definitions: Optional[Dict[str, Any]] = Field(None, alias="worklogDefinitions")
    settings: Optional[Dict[str, Any]] = None

class Company(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime
    
    class Config:
        from_attributes = True

class CompanyResponse(Company):
    is_active_member: Optional[bool] = Field(True, alias="isActiveMember")
    role: Optional[str] = None
    rates_config: Optional[Dict[str, Any]] = Field(None, alias="ratesConfig")


def default_role(v: Any) -> str:
    return v or "worker"

def default_is_active(v: Any) -> bool:
    return v if v is not None else True

class CompanyMemberBase(CamelModel):
    role: Annotated[str, BeforeValidator(default_role)] = "worker"
    is_active: Annotated[bool, BeforeValidator(default_is_active)] = True
    rates_config: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class CompanyMemberUpdate(CamelModel):
    role: Optional[str] = None
    is_active: Optional[bool] = None
    rates_config: Optional[Dict[str, Any]] = None
    settings: Optional[Dict[str, Any]] = None

class CompanyMemberResponse(CompanyMemberBase):
    user_id: UUID
    company_id: UUID
    joined_at: datetime
    user: Optional[UserResponse] = None

class CompanyWithMembers(CompanyResponse):
    members: List[CompanyMemberResponse] = []


class Token(CamelModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False

class Verify2FA(CamelModel):
    code: str

class TOTPSetupResponse(CamelModel):
    secret: str
    qr_code_uri: str

class TOTPActivate(CamelModel):
    code: str


class TokenData(CamelModel):
    user_id: Optional[str] = None
    company_id: Optional[str] = None
    company_role: Optional[str] = None
    is_platform_admin: bool = False
    scope: str = "full"
    email: Optional[EmailStr] = None
    admin_user_id: Optional[str] = None

class SessionResponse(CamelModel):
    id: UUID
    device_name: Optional[str] = None
    ip_address: Optional[str] = None
    is_active: bool
    last_active: datetime
    created_at: datetime

class PasswordResetRequest(CamelModel):
    email: EmailStr

class PasswordResetConfirm(CamelModel):
    token: str
    new_password: str


# ─── Módulos y Suscripciones ───────────────────────────────────────────────

class AppModuleCreate(CamelModel):
    """Schema para crear un módulo en el catálogo (solo Platform Admin)."""
    code_name: str
    name: str
    description: Optional[str] = None
    is_active: bool = True
    target_scope: str = "both"  # "company" | "user" | "both"
    price_monthly: Optional[float] = None

class AppModuleUpdate(CamelModel):
    """Schema para actualizar un módulo del catálogo."""
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None
    target_scope: Optional[str] = None
    price_monthly: Optional[float] = None

class AppModuleResponse(CamelModel):
    """Schema de respuesta de un módulo del catálogo."""
    id: UUID
    code_name: str
    name: str
    description: Optional[str] = None
    is_active: bool
    target_scope: str
    price_monthly: Optional[float] = None
    created_at: datetime
    updated_at: datetime


class ModuleSubscriptionCreate(CamelModel):
    """Schema para crear una suscripción a un módulo."""
    module_id: UUID = Field(..., alias="moduleId")
    company_id: Optional[UUID] = Field(None, alias="companyId")
    user_id: Optional[UUID] = Field(None, alias="userId")
    scope: str  # "company" | "user"
    status: str = "active"  # "active" | "trial" | "cancelled" | "expired"
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    notes: Optional[str] = None

class ModuleSubscriptionUpdate(CamelModel):
    """Schema para actualizar el estado de una suscripción."""
    status: Optional[str] = None
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    notes: Optional[str] = None

class ModuleSubscriptionResponse(CamelModel):
    """Schema de respuesta de una suscripción."""
    id: UUID
    module_id: UUID = Field(..., alias="moduleId")
    company_id: Optional[UUID] = Field(None, alias="companyId")
    user_id: Optional[UUID] = Field(None, alias="userId")
    scope: str
    status: str
    expires_at: Optional[datetime] = Field(None, alias="expiresAt")
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    module: Optional[AppModuleResponse] = None
    company: Optional[CompanyResponse] = None
    user: Optional[UserResponse] = None


class BillingSummaryItemResponse(CamelModel):
    user_id: UUID
    first_name: Optional[str] = None
    last_name: Optional[str] = None
    email: EmailStr
    type: Optional[str] = None
    total_hours: float
    total_net: float
    total_gross: float
    unique_days: int
    logs_count: int



