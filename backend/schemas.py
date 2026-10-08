"""
Pydantic Schemas Module.

This module defines the Pydantic models used for request validation and response serialization.
It ensures that data sent to and received from the API conforms to the expected structure.
"""

from datetime import date as dt_date
from datetime import datetime, time
from typing import Annotated, Any
from uuid import UUID

from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field


def to_camel(string: str) -> str:
    words = string.split("_")
    return words[0] + "".join(word.capitalize() for word in words[1:])


class CamelModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, from_attributes=True)


# Enums (mirroring models for validation)
# WorkLog types are now dynamic strings
class WorkLogBase(CamelModel):
    """Base schema for WorkLog data, containing common fields."""

    type: str
    start_date: dt_date = Field(..., alias="startDate")
    end_date: dt_date = Field(..., alias="endDate")
    start_time: time | None = Field(None, alias="startTime")
    end_time: time | None = Field(None, alias="endTime")
    duration: float | None = None
    net_amount: float | None = Field(None, alias="netAmount")
    gross_amount: float | None = Field(None, alias="grossAmount")
    extra_data: dict[str, Any] | None = Field(default={}, alias="extraData")
    description: str | None = None
    company_id: UUID | None = Field(None, alias="companyId")
    group_id: UUID | None = Field(None, alias="groupId")


class WorkLogCreate(WorkLogBase):
    """Schema for creating a new WorkLog entry."""

    user_id: UUID
    amount: float | None = None  # Allow manual amount override


class WorkLogBulkCreate(WorkLogBase):
    """Schema for creating multiple WorkLog entries at once."""

    user_ids: list[UUID] = Field(..., alias="userIds")
    amount: float | None = None


class WorkLogResponse(WorkLogBase):
    """Schema for WorkLog response data."""

    id: UUID
    user_id: UUID
    amount: float | None = None
    gross_amount: float | None = Field(None, alias="grossAmount")

    # SaaS Evolution: Historical snapshot (includes rate_applied inside snapshot["rate_applied"])
    calculation_snapshot: dict[str, Any] | None = Field(None, alias="calculationSnapshot")

    created_at: datetime
    updated_at: datetime


# UserDeviceResponse removed. Use SessionResponse instead.


class UserBase(CamelModel):
    """Base schema for User data, containing common fields."""

    email: EmailStr
    first_name: str | None = None
    last_name: str | None = None


class UserCreate(UserBase):
    """Schema for creating a new user (registration)."""

    password: str | None = None
    company_id: UUID | None = None
    send_email: bool = True


class UserResponse(UserBase):
    """Schema for User response data, excluding sensitive info like passwords."""

    id: UUID
    role: str
    is_active: bool
    is_manager: bool = False  # Computed
    is_active_worker: bool = False  # Computed
    must_change_password: bool = False
    is_2fa_enabled: bool = False  # TOTP status
    is_impersonated: bool = False  # SRE: Support impersonation UI
    is_platform_admin: bool = False
    active_company_id: UUID | None = None
    active_role: str | None = None
    default_company_id: UUID | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(CamelModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    role: str | None = None
    is_active: bool | None = None
    default_company_id: UUID | None = None


class UserSelfUpdate(CamelModel):
    first_name: str | None = None
    last_name: str | None = None
    default_company_id: UUID | None = None


class PasswordChange(CamelModel):
    current_password: str
    new_password: str


class UserCompanyRateBase(CamelModel):
    hourly_rate: float | None = 0.0
    daily_rate: float | None = 0.0
    coordination_rate: float | None = 0.0
    night_rate: float | None = 0.0
    is_gross: bool | None = False
    deduction_ss: float | None = None
    deduction_irpf: float | None = 0.0
    deduction_extra: float | None = 0.0


class UserCompanyRateCreate(UserCompanyRateBase):
    company_id: UUID


class UserCompanyRate(UserCompanyRateBase):
    user_id: UUID
    company_id: UUID
    updated_at: datetime

    class Config:
        from_attributes = True


class UserCompanyRateResponse(UserCompanyRate):
    user: UserResponse | None = None


class UpdateCompanyMembersOrder(CamelModel):
    user_ids: list[UUID] = Field(..., max_length=500)


class CompanyBase(CamelModel):
    name: str
    fiscal_id: str | None = None
    tax_config: dict[str, float] | None = Field(default={"social_security": 0.0, "irpf_base": 0.0}, alias="taxConfig")

    # SaaS Evolution: Dynamic shift definitions
    worklog_definitions: dict[str, Any] | None = Field(default={}, alias="worklogDefinitions")

    is_active: bool = Field(default=True, alias="isActive")
    is_managed: bool = Field(default=False, alias="isManaged")

    settings: dict[str, Any] | None = None


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CamelModel):
    name: str | None = None
    fiscal_id: str | None = None
    tax_config: dict[str, float] | None = Field(None, alias="taxConfig")
    worklog_definitions: dict[str, Any] | None = Field(None, alias="worklogDefinitions")
    is_active: bool | None = Field(None, alias="isActive")
    is_managed: bool | None = Field(None, alias="isManaged")
    settings: dict[str, Any] | None = None


class Company(CompanyBase):
    id: UUID
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class CompanyResponse(Company):
    is_active_member: bool | None = Field(True, alias="isActiveMember")
    role: str | None = None
    rates_config: dict[str, Any] | None = Field(None, alias="ratesConfig")


def default_role(v: Any) -> str:
    return v or "worker"


def default_is_active(v: Any) -> bool:
    return v if v is not None else True


class CompanyMemberBase(CamelModel):
    role: Annotated[str, BeforeValidator(default_role)] = "worker"
    is_active: Annotated[bool, BeforeValidator(default_is_active)] = True
    rates_config: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class CompanyMemberUpdate(CamelModel):
    role: str | None = None
    is_active: bool | None = None
    rates_config: dict[str, Any] | None = None
    settings: dict[str, Any] | None = None


class CompanyMemberResponse(CompanyMemberBase):
    user_id: UUID
    company_id: UUID
    joined_at: datetime
    user: UserResponse | None = None


class CompanyWithMembers(CompanyResponse):
    members: list[CompanyMemberResponse] = []


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


class TOTPDisable(CamelModel):
    code: str


class TokenData(CamelModel):
    user_id: str | None = None
    company_id: str | None = None
    company_role: str | None = None
    is_platform_admin: bool = False
    scope: str = "full"
    email: EmailStr | None = None
    admin_user_id: str | None = None


class SessionResponse(CamelModel):
    id: UUID
    device_name: str | None = None
    ip_address: str | None = None
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
    description: str | None = None
    is_active: bool = True
    target_scope: str = "both"  # "company" | "user" | "both"
    price_monthly: float | None = None


class AppModuleUpdate(CamelModel):
    """Schema para actualizar un módulo del catálogo."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    target_scope: str | None = None
    price_monthly: float | None = None


class AppModuleResponse(CamelModel):
    """Schema de respuesta de un módulo del catálogo."""

    id: UUID
    code_name: str
    name: str
    description: str | None = None
    is_active: bool
    target_scope: str
    price_monthly: float | None = None
    created_at: datetime
    updated_at: datetime


class ModuleSubscriptionCreate(CamelModel):
    """Schema para crear una suscripción a un módulo."""

    module_id: UUID = Field(..., alias="moduleId")
    company_id: UUID | None = Field(None, alias="companyId")
    user_id: UUID | None = Field(None, alias="userId")
    scope: str  # "company" | "user"
    status: str = "active"  # "active" | "trial" | "cancelled" | "expired"
    expires_at: datetime | None = Field(None, alias="expiresAt")
    notes: str | None = None


class ModuleSubscriptionUpdate(CamelModel):
    """Schema para actualizar el estado de una suscripción."""

    status: str | None = None
    expires_at: datetime | None = Field(None, alias="expiresAt")
    notes: str | None = None


class ModuleSubscriptionResponse(CamelModel):
    """Schema de respuesta de una suscripción."""

    id: UUID
    module_id: UUID = Field(..., alias="moduleId")
    company_id: UUID | None = Field(None, alias="companyId")
    user_id: UUID | None = Field(None, alias="userId")
    scope: str
    status: str
    expires_at: datetime | None = Field(None, alias="expiresAt")
    notes: str | None = None
    created_at: datetime
    updated_at: datetime
    module: AppModuleResponse | None = None
    company: CompanyResponse | None = None
    user: UserResponse | None = None


class BillingSummaryItemResponse(CamelModel):
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr
    type: str | None = None
    total_hours: float
    total_net: float
    total_gross: float
    unique_days: int
    logs_count: int
class DashboardPeriodMetrics(CamelModel):
    total_hours: float = 0.0
    total_net: float = 0.0
    total_gross: float = 0.0
    unique_days: int = 0
    total_logs: int = 0
    active_members_count: int = 0


class DashboardTodayMember(CamelModel):
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    role: str = "worker"
    hours: float = 0.0
    logs_count: int = 0


class DashboardTodayMetrics(CamelModel):
    today_hours: float = 0.0
    today_logs_count: int = 0
    today_active_members_count: int = 0
    today_active_members: list[DashboardTodayMember] = []


class DashboardTypeBreakdown(CamelModel):
    type: str
    label: str
    unit: str = "hours"
    hours: float = 0.0
    net: float = 0.0
    gross: float = 0.0
    count: int = 0


class DashboardDailyBreakdown(CamelModel):
    date: str
    day_of_week: int
    day_name: str
    hours: float = 0.0
    net: float = 0.0
    gross: float = 0.0
    count: int = 0


class DashboardWorkerSummary(CamelModel):
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    email: str | None = None
    role: str = "worker"
    sort_order: int = 1000
    is_active: bool = True
    total_hours: float = 0.0
    total_net: float = 0.0
    total_gross: float = 0.0
    unique_days: int = 0
    logs_count: int = 0
    types_breakdown: dict[str, float] = {}


class DashboardSummaryResponse(CamelModel):
    company_id: UUID
    company_name: str
    start_date: str
    end_date: str
    period_metrics: DashboardPeriodMetrics
    today_metrics: DashboardTodayMetrics
    type_breakdown: list[DashboardTypeBreakdown] = []
    daily_breakdown: list[DashboardDailyBreakdown] = []
    workers_summary: list[DashboardWorkerSummary] = []
