"""Esquemas de v2: snake_case sin alias [Q-2]. Las entradas validan con `contracts.py`, igual que v1."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from application.use_cases.company.common import CompanyView, CompanyWithMembers, MemberDetail
from application.use_cases.company.invitations import AcceptInvitationResult, InvitationView, PreviewInvitationResult
from contracts import (
    MEMBER_SETTINGS_ALLOWED_KEYS,
    CompanySettings,
    PlatformSettings,
    RatesConfig,
    TaxConfig,
    WorklogDefinitions,
    validate_allowed_email_domain,
    validate_member_settings,
)
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from schemas import limit_company_json, normalize_company_name, read_company_platform_settings, read_company_settings


class V2Model(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# --- Entrada ---


class CompanyCreateV2(V2Model):
    name: str
    # Obligatorio y estricto en escritura ({} es valido).
    tax_config: TaxConfig
    worklog_definitions: WorklogDefinitions = Field(default_factory=lambda: WorklogDefinitions({}))
    is_active: bool = True
    is_managed: bool = False
    settings: CompanySettings | None = None
    platform_settings: PlatformSettings | None = None

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "platform_settings", "worklog_definitions", mode="before")
    @classmethod
    def _limit_json(cls, v: Any) -> Any:
        return limit_company_json(v)


class CompanyUpdateV2(V2Model):
    name: str | None = None
    tax_config: TaxConfig | None = None
    worklog_definitions: WorklogDefinitions | None = None
    is_active: bool | None = None
    is_managed: bool | None = None
    settings: CompanySettings | None = None
    platform_settings: PlatformSettings | None = None
    # Solo para auditoria (motivo de suspension, etc.). No se persiste en la empresa.
    reason: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str | None) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "platform_settings", "worklog_definitions", mode="before")
    @classmethod
    def _limit_json(cls, v: Any) -> Any:
        return limit_company_json(v)

    @field_validator("is_active", "is_managed")
    @classmethod
    def _reject_null_flag(cls, v: bool | None) -> bool | None:
        # Evita un 500 por violar NOT NULL: si el campo viene en la peticion debe ser true/false.
        if v is None:
            raise ValueError("Debe ser true o false")
        return v

    @field_validator("tax_config", "worklog_definitions", "settings", "platform_settings", mode="before")
    @classmethod
    def _reject_null_json(cls, v: Any) -> Any:
        # Un null explicito llegaria a la persistencia como None y provocaria un 500: se omite el campo para no cambiarlo.
        if v is None:
            raise ValueError("No puede ser null: omite el campo para no modificarlo")
        return v


class CompanyManagerUpdateV2(V2Model):
    """Edicion de ajustes de empresa por el manager (R-EMP-08, R-ACC-72, R-ACC-73)."""

    model_config = ConfigDict(from_attributes=True, extra="forbid")

    tax_config: TaxConfig | None = None
    worklog_definitions: WorklogDefinitions | None = None
    settings: CompanySettings | None = None

    @field_validator("settings", "worklog_definitions", mode="before")
    @classmethod
    def _limit_json(cls, v: Any) -> Any:
        return limit_company_json(v)

    @field_validator("tax_config", "worklog_definitions", "settings", mode="before")
    @classmethod
    def _reject_null_json(cls, v: Any) -> Any:
        if v is None:
            raise ValueError("No puede ser null: omite el campo para no modificarlo")
        return v


# --- Salida ---


class UserBriefV2(V2Model):
    id: UUID
    email: str
    first_name: str | None = None
    last_name: str | None = None
    is_active: bool


class CompanyMemberV2(V2Model):
    user_id: UUID
    company_id: UUID
    role: str
    is_active: bool
    sort_order: int
    rates_config: dict[str, Any]
    settings: dict[str, Any]
    joined_at: datetime | None = None
    user: UserBriefV2 | None = None


class CompanyFull(V2Model):
    id: UUID
    name: str
    is_active: bool
    is_managed: bool
    tax_config: dict[str, Any]
    worklog_definitions: dict[str, Any]
    settings: dict[str, Any]
    platform_settings: dict[str, Any]
    created_at: datetime | None = None
    updated_at: datetime | None = None


class CompanyManagerSettingsOut(V2Model):
    """Ajustes de empresa visibles y editables por el manager (R-EMP-08, R-EMP-45, R-ACC-72)."""

    tax_config: dict[str, float] = {}
    worklog_definitions: dict[str, Any] = {}
    settings: dict[str, Any]


class WorklogDefinitionUsageOut(V2Model):
    """Uso en BD de un tipo de turno (para permitir borrado seguro o solo desactivacion, R-EMP-41)."""

    work_logs_count: int = 0
    member_rates_count: int = 0


class CompanyFullWithMembership(CompanyFull):
    """Vista completa de `/users/{id}/companies`: la empresa mas la membresia del usuario consultado."""

    role: str | None = None
    is_active_member: bool
    rates_config: dict[str, Any] | None = None


class CompanyFullWithMembers(CompanyFull):
    members: list[CompanyMemberV2] = []


class MemberOut(CompanyMemberV2):
    """Membresia de los endpoints `/companies/{id}/members` y `/rates`: anade `updated_at` a la de `include=members`."""

    updated_at: datetime | None = None


class MemberDeleteOut(V2Model):
    deleted: bool
    deactivated: bool
    reason: str | None = None


class MemberAddIn(V2Model):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _validate_email_domain(cls, value: EmailStr) -> str:
        return validate_allowed_email_domain(str(value))


class MemberStatusIn(V2Model):
    is_active: bool


class MemberRoleIn(V2Model):
    # El rol `admin` de membresia esta reservado.
    role: Literal["worker", "manager"]


class MemberRatesIn(V2Model):
    rates_config: RatesConfig


class MemberSettingsIn(V2Model):
    settings: dict[str, Any]

    @field_validator("settings")
    @classmethod
    def _validate_settings(cls, value: dict[str, Any]) -> dict[str, Any]:
        # Lista blanca de claves de usuario y tamano maximo (M2).
        return validate_member_settings(value)


class MemberOrderIn(V2Model):
    user_ids: list[UUID] = Field(..., max_length=500)


class InvitationCreateIn(V2Model):
    email: EmailStr

    @field_validator("email")
    @classmethod
    def _validate_email_domain(cls, value: EmailStr) -> str:
        return validate_allowed_email_domain(str(value))


class InvitationAcceptIn(V2Model):
    token: str = Field(..., min_length=1, max_length=512)


class InvitationOut(V2Model):
    id: UUID
    company_id: UUID
    email: str
    status: Literal["pending", "accepted", "cancelled", "expired"]
    invited_by_user_id: UUID
    invited_by_name: str | None = None
    expires_at: datetime
    accepted_at: datetime | None = None
    cancelled_at: datetime | None = None
    created_at: datetime | None = None


class InvitationPreviewOut(V2Model):
    company_id: UUID
    company_name: str
    status: Literal["pending"]
    expires_at: datetime


class InvitationAcceptOut(V2Model):
    company_id: UUID
    company_name: str
    membership: MemberOut


class CompanyReduced(V2Model):
    """Vista reducida: no expone is_active, settings ni platform_settings (R-ACC-55, R-EMP-49)."""

    id: UUID
    name: str
    is_managed: bool
    role: str | None = None
    is_active_member: bool
    rates_config: dict[str, Any] | None = None
    worklog_definitions: dict[str, Any] = {}
    tax_config: dict[str, float] = {}


class MyCompanyOut(V2Model):
    """Selector de empresas (`GET /v2/me/companies`): solo id, name y role (R-ACC-81)."""

    id: UUID
    name: str
    role: str


def my_company_out(view: CompanyView) -> MyCompanyOut:
    role = view.member.role.value if view.member is not None else view.role
    return MyCompanyOut(id=view.company.id, name=view.company.name, role=role or "worker")


# --- Conversion desde el dominio ---


def _full_fields(company) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "is_active": company.is_active,
        "is_managed": company.is_managed,
        "tax_config": company.tax_config or {},
        "worklog_definitions": company.worklog_definitions or {},
        "settings": read_company_settings(company.settings),
        "platform_settings": read_company_platform_settings(getattr(company, "platform_settings", None)),
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }


def company_manager_settings_out(company) -> CompanyManagerSettingsOut:
    return CompanyManagerSettingsOut(
        tax_config=company.tax_config or {},
        worklog_definitions=company.worklog_definitions or {},
        settings=read_company_settings(company.settings),
    )


def company_full(company) -> CompanyFull:
    return CompanyFull(**_full_fields(company))


def company_full_with_membership(view: CompanyView) -> CompanyFullWithMembership:
    member = view.member
    fields = _full_fields(view.company)
    # A los settings de empresa se suman las claves permitidas del miembro.
    raw_member = member.settings if member is not None and isinstance(member.settings, dict) else {}
    fields["settings"] = {
        **fields["settings"],
        **{key: value for key, value in raw_member.items() if key in MEMBER_SETTINGS_ALLOWED_KEYS},
    }
    return CompanyFullWithMembership(
        **fields,
        role=member.role.value if member is not None else view.role,
        is_active_member=member.is_active if member is not None else True,
        rates_config=member.rates_config if member is not None else None,
    )


def company_reduced(view: CompanyView) -> CompanyReduced:
    company, member = view.company, view.member
    role = (member.role.value if member is not None else view.role)
    return CompanyReduced(
        id=company.id,
        name=company.name,
        is_managed=bool(company.is_managed),
        role=role,
        is_active_member=member.is_active if member is not None else True,
        rates_config=member.rates_config if member is not None else None,
        worklog_definitions=company.worklog_definitions or {},
        tax_config=company.tax_config or {},
    )


def _member_v2(detail: MemberDetail) -> CompanyMemberV2:
    member, user = detail.member, detail.user
    return CompanyMemberV2(
        user_id=member.user_id,
        company_id=member.company_id,
        role=member.role.value,
        is_active=member.is_active,
        sort_order=member.sort_order,
        rates_config=member.rates_config or {},
        settings=member.settings or {},
        joined_at=member.joined_at,
        user=UserBriefV2(
            id=user.id,
            email=user.email,
            first_name=user.first_name,
            last_name=user.last_name,
            is_active=user.is_active,
        )
        if user is not None
        else None,
    )


def member_out(detail: MemberDetail) -> MemberOut:
    return MemberOut(**_member_v2(detail).model_dump(), updated_at=detail.member.updated_at)


def company_full_with_members(item: CompanyWithMembers) -> CompanyFullWithMembers:
    return CompanyFullWithMembers(**_full_fields(item.company), members=[_member_v2(m) for m in item.members])


def invitation_out(view: InvitationView) -> InvitationOut:
    inv = view.invitation
    return InvitationOut(
        id=inv.id,
        company_id=inv.company_id,
        email=inv.email,
        status=inv.status_at(),
        invited_by_user_id=inv.invited_by_user_id,
        invited_by_name=view.invited_by_name,
        expires_at=inv.expires_at,
        accepted_at=inv.accepted_at,
        cancelled_at=inv.cancelled_at,
        created_at=inv.created_at,
    )


def invitation_preview_out(preview: PreviewInvitationResult) -> InvitationPreviewOut:
    return InvitationPreviewOut(
        company_id=preview.company.id,
        company_name=preview.company.name,
        status="pending",
        expires_at=preview.invitation.expires_at,
    )


def invitation_accept_out(result: AcceptInvitationResult) -> InvitationAcceptOut:
    return InvitationAcceptOut(
        company_id=result.company.id,
        company_name=result.company.name,
        membership=member_out(result.detail),
    )
