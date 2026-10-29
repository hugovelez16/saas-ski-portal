"""Esquemas de v2: snake_case sin alias [Q-2]. Las entradas validan con `contracts.py`, igual que v1."""

from datetime import datetime
from typing import Any, Literal
from uuid import UUID

from application.use_cases.company.common import CompanyView, CompanyWithMembers, MemberDetail
from contracts import (
    MEMBER_SETTINGS_ALLOWED_KEYS,
    CompanySettings,
    RatesConfig,
    TaxConfig,
    WorklogDefinitions,
    validate_member_settings,
)
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from schemas import limit_company_json, normalize_company_name, read_company_settings


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

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "worklog_definitions", mode="before")
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
    # Solo para auditoria (motivo de suspension, etc.). No se persiste en la empresa.
    reason: str | None = Field(None, max_length=500)

    @field_validator("name")
    @classmethod
    def _validate_name(cls, v: str | None) -> str:
        return normalize_company_name(v)

    @field_validator("settings", "worklog_definitions", mode="before")
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

    @field_validator("tax_config", "worklog_definitions", "settings", mode="before")
    @classmethod
    def _reject_null_json(cls, v: Any) -> Any:
        # Un null explicito llegaria a la persistencia como None y provocaria un 500: se omite el campo para no cambiarlo.
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
    created_at: datetime | None = None
    updated_at: datetime | None = None


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


class CompanyReduced(V2Model):
    """Vista reducida: no expone is_active, allowed_rates ni cost_markup."""

    id: UUID
    name: str
    is_managed: bool
    role: str | None = None
    is_active_member: bool
    rates_config: dict[str, Any] | None = None
    worklog_definitions: dict[str, Any] = {}
    tax_config: dict[str, float] = {}
    settings: dict[str, Any]


# --- Conversion desde el dominio ---


def _reduced_settings(company_settings: Any, member_settings: Any) -> dict[str, Any]:
    merged_company = read_company_settings(company_settings)
    raw_member = member_settings if isinstance(member_settings, dict) else {}
    merged = {
        **merged_company,
        **{key: value for key, value in raw_member.items() if key in MEMBER_SETTINGS_ALLOWED_KEYS},
    }
    member_part = {key: value for key, value in merged.items() if key in MEMBER_SETTINGS_ALLOWED_KEYS}
    company_part = {key: value for key, value in merged.items() if key not in MEMBER_SETTINGS_ALLOWED_KEYS}
    return {**CompanySettings.from_db(company_part).ui_view(), **member_part}


def _full_fields(company) -> dict[str, Any]:
    return {
        "id": company.id,
        "name": company.name,
        "is_active": company.is_active,
        "is_managed": company.is_managed,
        "tax_config": company.tax_config or {},
        "worklog_definitions": company.worklog_definitions or {},
        "settings": read_company_settings(company.settings),
        "created_at": company.created_at,
        "updated_at": company.updated_at,
    }


def company_full(company) -> CompanyFull:
    return CompanyFull(**_full_fields(company))


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
        settings=_reduced_settings(company.settings, member.settings if member is not None else None),
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
