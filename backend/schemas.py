"""
Pydantic Schemas Module.

This module defines the Pydantic models used for request validation and response serialization.
It ensures that data sent to and received from the API conforms to the expected structure.
"""

import json
import math
from datetime import date as dt_date
from datetime import datetime, time, timedelta
from typing import Annotated, Any, Literal
from uuid import UUID

from contracts import TaxConfig, validate_tax_overrides
from pydantic import BaseModel, BeforeValidator, ConfigDict, EmailStr, Field, field_validator, model_validator


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


MIN_WORKLOG_DATE = dt_date(2000, 1, 1)
MAX_WORKLOG_FUTURE_DAYS = 730


def _validate_worklog_dates(start: dt_date | None, end: dt_date | None) -> None:
    """Rango de fechas de un turno: ordenadas y entre 2000-01-01 y hoy + 730 dias."""
    max_date = dt_date.today() + timedelta(days=MAX_WORKLOG_FUTURE_DAYS)
    for value in (start, end):
        if value is not None and not (MIN_WORKLOG_DATE <= value <= max_date):
            raise ValueError(f"Las fechas deben estar entre {MIN_WORKLOG_DATE.isoformat()} y {max_date.isoformat()}")
    if start is not None and end is not None and start > end:
        raise ValueError("start_date no puede ser posterior a end_date")


class WorkLogInput(WorkLogBase):
    """Reglas de entrada de turnos. No se aplican a WorkLogResponse para no romper la lectura de turnos antiguos."""

    duration: float | None = Field(None, ge=0)
    net_amount: float | None = Field(None, alias="netAmount", ge=0)
    gross_amount: float | None = Field(None, alias="grossAmount", ge=0)
    amount: float | None = Field(None, ge=0)  # Allow manual amount override

    @model_validator(mode="after")
    def _check_dates(self):
        _validate_worklog_dates(self.start_date, self.end_date)
        return self

    @model_validator(mode="after")
    def _check_company(self):
        if self.company_id is None:
            raise ValueError("company_id es obligatorio")
        return self


class WorkLogCreate(WorkLogInput):
    """Schema for creating a new WorkLog entry. El `groupId` del cliente se ignora (lo genera el backend)."""

    user_id: UUID


class WorkLogBulkCreate(WorkLogInput):
    """Schema for creating multiple WorkLog entries at once."""

    user_ids: list[UUID] = Field(..., alias="userIds", min_length=1, max_length=500)


class WorkLogUpdate(CamelModel):
    """Edicion de un turno: campos opcionales. `user_id` y `company_id` solo se aceptan si no cambian."""

    type: str | None = None
    start_date: dt_date | None = Field(None, alias="startDate")
    end_date: dt_date | None = Field(None, alias="endDate")
    start_time: time | None = Field(None, alias="startTime")
    end_time: time | None = Field(None, alias="endTime")
    duration: float | None = Field(None, ge=0)
    net_amount: float | None = Field(None, alias="netAmount", ge=0)
    gross_amount: float | None = Field(None, alias="grossAmount", ge=0)
    amount: float | None = Field(None, ge=0)
    extra_data: dict[str, Any] | None = Field(None, alias="extraData")
    description: str | None = None
    user_id: UUID | None = Field(None, alias="userId")
    company_id: UUID | None = Field(None, alias="companyId")

    @model_validator(mode="after")
    def _check_required_not_null(self):
        # Un null explicito en un campo obligatorio del turno no es una edicion valida
        for name in ("type", "start_date", "end_date"):
            if name in self.model_fields_set and getattr(self, name) is None:
                raise ValueError(f"{name} no puede ser nulo")
        return self

    @model_validator(mode="after")
    def _check_dates(self):
        _validate_worklog_dates(self.start_date, self.end_date)
        return self


class WorkLogResponse(WorkLogBase):
    """Schema for WorkLog response data."""

    id: UUID
    user_id: UUID
    amount: float | None = None
    gross_amount: float | None = Field(None, alias="grossAmount")
    group_id: UUID | None = Field(None, alias="groupId")

    # SaaS Evolution: Historical snapshot (includes rate_applied inside snapshot["rate_applied"])
    calculation_snapshot: dict[str, Any] | None = Field(None, alias="calculationSnapshot")

    created_at: datetime
    updated_at: datetime

    @model_validator(mode="after")
    def _fill_group_id(self):
        """El grupo vive en extra_data, no es columna."""
        if self.group_id is None and self.extra_data and self.extra_data.get("group_id"):
            try:
                self.group_id = UUID(str(self.extra_data["group_id"]))
            except ValueError:
                pass
        return self


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
    view_as: str | None = None
    is_read_only_view: bool = False
    created_at: datetime

    class Config:
        from_attributes = True


class UserUpdate(CamelModel):
    first_name: str | None = None
    last_name: str | None = None
    email: EmailStr | None = None
    role: Literal["admin", "user"] | None = None
    is_active: bool | None = None


class UserSelfUpdate(CamelModel):
    first_name: str | None = None
    last_name: str | None = None


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


COMPANY_NAME_MAX = 120


def normalize_company_name(v: str | None) -> str:
    """Quita los espacios sobrantes y exige entre 1 y COMPANY_NAME_MAX caracteres."""
    if v is None:
        raise ValueError("El nombre de la empresa es obligatorio")
    name = v.strip()
    if not 1 <= len(name) <= COMPANY_NAME_MAX:
        raise ValueError(f"El nombre debe tener entre 1 y {COMPANY_NAME_MAX} caracteres")
    return name


# Tope del JSON de `settings` y `worklog_definitions`: cada edicion se copia entera a la auditoria.
COMPANY_JSON_MAX_BYTES = 65536


def limit_company_json(v: dict[str, Any] | None) -> dict[str, Any] | None:
    if v is not None and len(json.dumps(v, default=str).encode("utf-8")) > COMPANY_JSON_MAX_BYTES:
        raise ValueError(f"El contenido supera el maximo de {COMPANY_JSON_MAX_BYTES} bytes")
    return v


class CompanyBase(CamelModel):
    name: str
    # Obligatorio y estricto en escritura ({} es valido). Las respuestas lo relajan en `Company`.
    tax_config: TaxConfig = Field(alias="taxConfig")

    # SaaS Evolution: Dynamic shift definitions
    worklog_definitions: dict[str, Any] | None = Field(default={}, alias="worklogDefinitions")

    is_active: bool = Field(default=True, alias="isActive")
    is_managed: bool = Field(default=False, alias="isManaged")

    settings: dict[str, Any] | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "worklog_definitions")
    @classmethod
    def _limit_json(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return limit_company_json(v)


class CompanyCreate(CompanyBase):
    pass


class CompanyUpdate(CamelModel):
    name: str | None = None
    tax_config: TaxConfig | None = Field(None, alias="taxConfig")
    worklog_definitions: dict[str, Any] | None = Field(None, alias="worklogDefinitions")
    is_active: bool | None = Field(None, alias="isActive")
    is_managed: bool | None = Field(None, alias="isManaged")
    settings: dict[str, Any] | None = None
    # Solo para auditoria (motivo de suspension, etc.). No se persiste en la empresa.
    reason: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str | None) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "worklog_definitions")
    @classmethod
    def _limit_json(cls, v: dict[str, Any] | None) -> dict[str, Any] | None:
        return limit_company_json(v)

    @field_validator("is_active", "is_managed")
    @classmethod
    def _reject_null_flag(cls, v: bool | None) -> bool | None:
        # Evita un 500 por violar NOT NULL: si el campo viene en la peticion debe ser true/false.
        if v is None:
            raise ValueError("Debe ser true o false")
        return v


class Company(CompanyBase):
    # Lectura tolerante: filas existentes con tax_config NULL o cualquier dict.
    tax_config: dict[str, float] | None = Field(None, alias="taxConfig")
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


class CompanyMemberResponse(CompanyMemberBase):
    user_id: UUID
    company_id: UUID
    joined_at: datetime
    user: UserResponse | None = None


class AddMemberRequest(CamelModel):
    email: EmailStr


class MemberRoleUpdate(CamelModel):
    role: Literal["worker", "manager"]


class MemberRatesUpdate(CamelModel):
    rates_config: dict[str, dict[str, Any]]

    @field_validator("rates_config")
    @classmethod
    def _base_rates_are_non_negative(cls, value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        for shift_key, shift in value.items():
            if "base_rate" not in shift:
                continue
            base_rate = shift["base_rate"]
            if isinstance(base_rate, bool) or not isinstance(base_rate, (int, float)):
                raise ValueError(f"base_rate de '{shift_key}' debe ser un numero")
            if not math.isfinite(base_rate) or base_rate < 0:
                raise ValueError(f"base_rate de '{shift_key}' debe ser un numero mayor o igual que 0")
        return value

    @field_validator("rates_config")
    @classmethod
    def _tax_overrides_are_valid(cls, value: dict[str, dict[str, Any]]) -> dict[str, dict[str, Any]]:
        for shift_key, shift in value.items():
            if not isinstance(shift, dict) or "tax_overrides" not in shift:
                continue
            try:
                validate_tax_overrides(shift["tax_overrides"])
            except ValueError as exc:
                raise ValueError(f"tax_overrides de '{shift_key}' no es valido: {exc}") from exc
        return value


class MemberSettingsUpdate(CamelModel):
    settings: dict[str, Any]


class MemberDeleteResponse(CamelModel):
    deleted: bool
    deactivated: bool
    reason: str | None = None


class CompanyWithMembers(CompanyResponse):
    members: list[CompanyMemberResponse] = []


class Token(CamelModel):
    access_token: str
    token_type: str
    requires_2fa: bool = False


class Verify2FA(CamelModel):
    code: str
    company_id: UUID | None = None


class SwitchScopeRequest(CamelModel):
    """Cuerpo de POST /auth/switch-scope. El rol de la membresia se lee de BD; no se acepta del cliente."""

    company_id: UUID | None = None
    view_as: Literal["worker", "manager"] | None = None


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


ModuleTargetScope = Literal["company", "user", "both"]
SubscriptionScopeValue = Literal["company", "user"]
SubscriptionStatusValue = Literal["active", "trial", "cancelled", "expired"]


class AppModuleCreate(CamelModel):
    """Schema para crear un módulo en el catálogo (solo Platform Admin)."""

    code_name: str
    name: str
    description: str | None = None
    is_active: bool = True
    target_scope: ModuleTargetScope = "both"
    price_monthly: float | None = None


class AppModuleUpdate(CamelModel):
    """Schema para actualizar un módulo del catálogo."""

    name: str | None = None
    description: str | None = None
    is_active: bool | None = None
    target_scope: ModuleTargetScope | None = None
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
    scope: SubscriptionScopeValue
    status: SubscriptionStatusValue = "active"
    expires_at: datetime | None = Field(None, alias="expiresAt")
    notes: str | None = None

    @model_validator(mode="after")
    def _scope_matches_target(self):
        """El scope exige su destino y excluye el otro."""
        if self.scope == "company" and (self.company_id is None or self.user_id is not None):
            raise ValueError("Una suscripción de empresa requiere companyId y no admite userId.")
        if self.scope == "user" and (self.user_id is None or self.company_id is not None):
            raise ValueError("Una suscripción de usuario requiere userId y no admite companyId.")
        return self


class ModuleSubscriptionUpdate(CamelModel):
    """Schema para actualizar el estado de una suscripción."""

    status: SubscriptionStatusValue | None = None
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


# ─── Parte diario (PR-14) ──────────────────────────────────────────────────


class DailyReportMember(CamelModel):
    user_id: UUID
    first_name: str | None = None
    last_name: str | None = None
    role: str
    is_active: bool
    sort_order: int


class DailyReportLogWorker(CamelModel):
    """Turno del parte diario sin importes: es el que recibe el worker [P-14]."""

    id: UUID
    user_id: UUID
    company_id: UUID | None = None
    type: str
    start_date: dt_date
    end_date: dt_date
    start_time: time | None = None
    end_time: time | None = None
    duration: float | None = None
    description: str | None = None


class DailyReportLogFull(DailyReportLogWorker):
    net_amount: float | None = None
    gross_amount: float | None = None


class DailyReportWorkerResponse(CamelModel):
    company_id: UUID
    date: dt_date
    members: list[DailyReportMember]
    work_types: dict[str, dict[str, Any]]
    logs: list[DailyReportLogWorker]


class DailyReportFullResponse(CamelModel):
    company_id: UUID
    date: dt_date
    members: list[DailyReportMember]
    work_types: dict[str, dict[str, Any]]
    logs: list[DailyReportLogFull]


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


# --- Agregados de turnos (PR-07): GET /work-logs/summary ---


class WorkLogTotals(CamelModel):
    logs_count: int
    total_hours: float
    total_net: float
    total_gross: float
    unique_days: int
    active_users: int


class WorkLogTypeTotals(CamelModel):
    type: str
    logs_count: int
    hours: float
    net: float
    gross: float


class WorkLogDayTotals(CamelModel):
    date: dt_date
    logs_count: int
    hours: float
    net: float
    gross: float


class WorkLogUserTotals(CamelModel):
    user_id: UUID
    first_name: str | None
    last_name: str | None
    email: str | None
    logs_count: int
    hours: float
    net: float
    gross: float
    unique_days: int


class WorkLogSummaryResponse(CamelModel):
    start_date: dt_date
    end_date: dt_date
    totals: WorkLogTotals
    by_type: list[WorkLogTypeTotals]
    by_day: list[WorkLogDayTotals]
    by_user: list[WorkLogUserTotals]


class AuditLogItem(CamelModel):
    id: UUID
    action: str
    created_at: datetime
    actor_user_id: UUID | None
    actor_email: str | None
    company_id: UUID | None
    target_user_id: UUID | None
    old_value: dict[str, Any] | None
    new_value: dict[str, Any] | None
    reason: str | None
    extra_data: dict[str, Any] | None


class AuditLogPage(CamelModel):
    total: int
    items: list[AuditLogItem]
