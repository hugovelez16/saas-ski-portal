"""
Contratos de validacion compartidos (PR-10: impuestos con claves libres).

`TaxConfig` valida la configuracion de impuestos de una empresa (nombre libre -> tasa 0..1),
`validate_tax_overrides` valida los overrides de impuestos de un miembro y `resolve_taxes`
combina ambos para obtener los impuestos efectivos.
"""

import json
import logging
import math
from collections.abc import Iterable
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, Strict, ValidationError, field_validator, model_validator

logger = logging.getLogger(__name__)


class MissingWorklogUnitError(ValueError):
    """El tipo de turno no tiene `unit` en su definicion. Se traduce a HTTP 422 en main.py."""


class MissingWorklogDatesError(ValueError):
    """Un turno con unidad `days` no tiene fecha de inicio o de fin (R-TUR-12). Se traduce a HTTP 422 en main.py."""


TAX_NAME_MAX = 50
TAX_MAX_ENTRIES = 20

WORKLOG_KEY_MAX = 50
RATES_CONFIG_MAX_KEYS = 50
RATES_CONFIG_MAX_BYTES = 65536
MEMBER_SETTINGS_MAX_BYTES = 8192
# TEMPORAL (O10): allow_tutorial y allow_coordination solo estan para que
# frontend/src/components/admin/member-settings-dialog.tsx siga guardando. Eliminarlas de esta
# lista cuando se retire ese dialogo (bloque F6/O10, settings de membresia).
MEMBER_SETTINGS_ALLOWED_KEYS = frozenset({"notifications", "ui_preferences", "allow_tutorial", "allow_coordination"})

# Numero finito, no booleano (Strict), >= 0. allow_inf_nan=False rechaza NaN e infinitos.
NonNegativeFiniteFloat = Annotated[float, Strict(), Field(ge=0, allow_inf_nan=False)]


def _validate_tax_name(name: Any) -> str:
    if not isinstance(name, str):
        raise ValueError("El nombre del impuesto debe ser texto")
    clean = name.strip()
    if not 1 <= len(clean) <= TAX_NAME_MAX:
        raise ValueError(f"El nombre del impuesto debe tener entre 1 y {TAX_NAME_MAX} caracteres")
    return clean


def _validate_tax_rate(name: str, value: Any) -> float | int:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"La tasa de '{name}' debe ser un numero")
    if not math.isfinite(value) or not 0 <= value <= 1:
        raise ValueError(f"La tasa de '{name}' debe estar entre 0 y 1")
    return value


def _to_decimal_safe(value: Any) -> Decimal:
    """Convierte un valor numerico o texto en Decimal finito (0 si es nulo o invalido)."""
    if value is None or value == "" or isinstance(value, bool):
        return Decimal("0")
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    return dec if dec.is_finite() else Decimal("0")


def _validate_tax_sum(rates: Iterable[float | int]) -> None:
    """R-TAR-16: la suma de tasas efectivas no puede superar 1 (100%)."""
    total = sum((Decimal(str(rate)) for rate in rates), Decimal("0"))
    if total > Decimal("1"):
        raise ValueError("La suma de los impuestos efectivos no puede superar 1 (100%)")


class TaxConfig(RootModel[dict[str, float]]):
    """Impuestos de empresa: nombre libre (1..50 caracteres) -> tasa entre 0 y 1, maximo 20 entradas."""

    @field_validator("root", mode="before")
    @classmethod
    def _validate_root(cls, value: Any) -> dict[str, float]:
        if not isinstance(value, dict):
            raise ValueError("taxConfig debe ser un objeto nombre -> tasa")
        if len(value) > TAX_MAX_ENTRIES:
            raise ValueError(f"taxConfig admite como maximo {TAX_MAX_ENTRIES} impuestos")
        result: dict[str, float] = {}
        for raw_name, raw_rate in value.items():
            name = _validate_tax_name(raw_name)
            if name in result:
                raise ValueError(f"Impuesto duplicado: '{name}'")
            result[name] = _validate_tax_rate(name, raw_rate)
        _validate_tax_sum(result.values())
        return result

    def as_dict(self) -> dict[str, float]:
        return dict(self.root)


def validate_tax_overrides(
    value: dict | None,
    *,
    company_tax_config: dict | None = None,
    is_managed: bool | None = None,
    existing_overrides: dict | None = None,
) -> dict | None:
    """Valida overrides de impuestos de un miembro: None, o nombre -> (None | tasa 0..1).

    - Rechaza duplicados tras `strip()` y tasas cuya suma efectiva supere 1 (R-TAR-16).
    - En empresa gestionada (`is_managed=True`), rechaza nombres inexistentes en `company_tax_config`
      salvo impuestos propios ya existentes sin modificar (R-ACC-74, R-TAR-08).
    """
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("tax_overrides debe ser un objeto o null")

    seen: set[str] = set()
    normalized: dict[str, float | int | None] = {}
    for raw_name, rate in value.items():
        name = _validate_tax_name(raw_name)
        if name in seen:
            raise ValueError(f"Impuesto duplicado: '{name}'")
        seen.add(name)
        if rate is not None:
            _validate_tax_rate(name, rate)
        normalized[name] = rate

    if is_managed is True:
        company_keys = {k.strip() for k in (company_tax_config or {}) if isinstance(k, str)}
        existing: dict[str, Any] = {}
        if isinstance(existing_overrides, dict):
            for raw_k, raw_v in existing_overrides.items():
                if isinstance(raw_k, str):
                    existing[raw_k.strip()] = raw_v
        for name, rate in normalized.items():
            if name not in company_keys:
                if name in existing and rate == existing[name]:
                    continue
                if name in existing:
                    raise ValueError(f"En empresa gestionada no se puede editar el impuesto propio '{name}'")
                raise ValueError(f"El impuesto '{name}' no existe en la configuracion de la empresa")

    effective = resolve_taxes(company_tax_config, normalized)
    _validate_tax_sum(effective.values())
    return value


def resolve_taxes(company_tax_config: dict | None, tax_overrides: dict | None) -> dict[str, float]:
    """Impuestos efectivos: empresa + overrides de miembro (un override None no sustituye)."""
    return {**(company_tax_config or {}), **{k: v for k, v in (tax_overrides or {}).items() if v is not None}}


def _extract_snapshot_tax_info(snapshot: Any) -> tuple[bool, tuple[tuple[str, Decimal], ...] | None, Decimal]:
    """Extrae si aplica calculo agrupado por impuestos y su clave canonica a partir de `calculation_snapshot`."""
    if not isinstance(snapshot, dict):
        return False, None, Decimal("0")
    tax_applied = snapshot.get("tax_applied")
    if not isinstance(tax_applied, dict):
        return False, None, Decimal("0")

    rate_applied = snapshot.get("rate_applied")
    metadata = snapshot.get("metadata")
    if isinstance(rate_applied, dict):
        is_gross = bool(rate_applied.get("is_gross", False))
    elif isinstance(metadata, dict):
        is_gross = bool(metadata.get("is_gross", False))
    else:
        is_gross = True

    if not is_gross:
        return False, None, Decimal("0")

    normalized: list[tuple[str, Decimal]] = []
    for key, raw_rate in sorted(tax_applied.items()):
        rate = _to_decimal_safe(raw_rate)
        if rate != Decimal("0"):
            normalized.append((str(key), rate))
    tax_sum = sum((rate for _, rate in normalized), Decimal("0"))
    return True, tuple(normalized), tax_sum


def compute_grouped_net_total(items: Iterable[tuple[Any, Any, Any, Any]]) -> Decimal:
    """Calcula el total neto agrupando por trabajador y conjunto efectivo de impuestos (R-TAR-27, R-TAR-30).

    Cada elemento de `items` es `(user_id, gross_amount, net_amount, calculation_snapshot)`.
    Para turnos con tarifa bruta y `tax_applied` en el snapshot, suma el bruto del grupo
    `(user_id, conjunto_impuestos)`, aplica la retencion una sola vez y redondea con `ROUND_HALF_UP`.
    Para turnos con tarifa neta (R-TAR-13) o sin `tax_applied` en el snapshot, suma `net_amount`.
    """
    gross_groups: dict[tuple[str, tuple[tuple[str, Decimal], ...]], tuple[Decimal, Decimal]] = {}
    fallback_net = Decimal("0")

    for user_id, gross_amount, net_amount, snapshot in items:
        use_grouped, tax_key, tax_sum = _extract_snapshot_tax_info(snapshot)
        if not use_grouped or tax_key is None:
            fallback_net += _to_decimal_safe(net_amount)
            continue

        group_key = (str(user_id), tax_key)
        gross_dec = _to_decimal_safe(gross_amount)
        prev_gross, _ = gross_groups.get(group_key, (Decimal("0"), tax_sum))
        gross_groups[group_key] = (prev_gross + gross_dec, tax_sum)

    total = fallback_net.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) if fallback_net else Decimal("0.00")
    for group_gross, tax_sum in gross_groups.values():
        factor = max(Decimal("0"), Decimal("1") - tax_sum)
        group_net = (group_gross * factor).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        total += group_net
    return total.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def _json_size_bytes(value: Any) -> int:
    """Tamano en bytes del JSON serializado. Rechaza NaN/infinitos y valores no serializables."""
    try:
        return len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode("utf-8"))
    except (TypeError, ValueError) as exc:
        raise ValueError("El contenido debe ser JSON valido, sin NaN ni infinitos") from exc


def _tolerant_build(model_cls: type[BaseModel], raw: Any, path: str) -> BaseModel:
    """
    Construye `model_cls` desde datos crudos de BD sin lanzar excepciones.

    Descarta claves desconocidas (recursivo en subobjetos) con warning y sustituye por el default
    cada campo cuyo valor no valida, tambien con warning. `path` identifica el campo en los logs.
    """
    if not isinstance(raw, dict):
        logger.warning("Valor no valido en %s, se usa el valor por defecto", path)
        return model_cls()
    values: dict[str, Any] = {}
    for key, value in raw.items():
        field_path = f"{path}.{key}"
        field = model_cls.model_fields.get(key)
        if field is None:
            logger.warning("Clave de settings desconocida descartada: %s", field_path)
            continue
        annotation = field.annotation
        if isinstance(annotation, type) and issubclass(annotation, BaseModel):
            value = _tolerant_build(annotation, value, field_path)
        elif key == "modules" and isinstance(value, dict):
            # Filtrado por entrada: una bandera invalida no hace perder el resto de modulos.
            flags: dict[str, Any] = {}
            for name, flag in value.items():
                if isinstance(flag, bool):
                    flags[name] = flag
                else:
                    logger.warning("Valor no valido en %s.%s, se descarta la entrada", field_path, name)
            value = flags
        try:
            model_cls.model_validate({key: value})
        except (ValidationError, TypeError, ValueError):
            logger.warning("Valor no valido en %s, se usa el valor por defecto", field_path)
            continue
        values[key] = value
    return model_cls.model_validate(values)


class CompanySettings(BaseModel):
    """Configuracion de empresa editable por el manager y el PA (columna `companies.settings`).

    Las claves desconocidas se rechazan al validar (extra="forbid"); al leer
    desde BD se usa `from_db`, que las descarta con un warning.
    """

    model_config = ConfigDict(extra="forbid")

    default_is_gross: bool = False
    """Valor de bruto/neto por defecto que se copia a los miembros nuevos (R-EMP-45, R-EMP-46)."""

    @classmethod
    def from_db(cls, raw: dict | None) -> "CompanySettings":
        """Lectura tolerante del JSONB de BD. Nunca lanza excepcion."""
        if not raw:
            return cls()
        if isinstance(raw, dict) and "_platform" in raw:
            raw = {k: v for k, v in raw.items() if k != "_platform"}
            if not raw:
                return cls()
        return _tolerant_build(cls, raw, "settings")


PLAN_PRESETS: dict[str, tuple[int | None, int | None]] = {
    "pista_verde": (10, 1),
    "pista_azul": (25, 2),
    "pista_roja": (50, None),
}


class PlatformLimits(BaseModel):
    """Limites de plan de una empresa gestionados solo por el PA (R-EMP-45)."""

    model_config = ConfigDict(extra="forbid")

    max_monitors: int | None = Field(None, ge=0)
    max_managers: int | None = Field(None, ge=0)


class PlatformSettings(BaseModel):
    """Ajustes de plataforma de una empresa: plan, limites y modulos (solo PA, R-EMP-45, R-EMP-49)."""

    model_config = ConfigDict(extra="forbid")

    plan: str | None = Field(None, min_length=1, max_length=60)
    limits: PlatformLimits = Field(default_factory=PlatformLimits)
    modules: dict[str, bool] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _apply_plan_preset(self) -> "PlatformSettings":
        """Aplica los topes de monitores y responsables de planes comerciales (R-MOD-22)."""
        if self.plan in PLAN_PRESETS:
            max_monitors, max_managers = PLAN_PRESETS[self.plan]
            self.limits = PlatformLimits(max_monitors=max_monitors, max_managers=max_managers)
        return self

    @classmethod
    def from_db(cls, raw: dict | None) -> "PlatformSettings":
        """Lectura tolerante del bloque de plataforma. Nunca lanza excepcion."""
        if not raw:
            return cls()
        return _tolerant_build(cls, raw, "platform_settings")


class WorklogDefinition(BaseModel):
    """Definicion de un tipo de turno (valor de `companies.worklog_definitions`)."""

    model_config = ConfigDict(extra="forbid")

    unit: Literal["hours", "days", "fixed"]
    label: str = Field(min_length=1, max_length=60)
    options: list[str] = Field(default_factory=list)
    is_active: Annotated[bool, Strict()] = True

    @field_validator("options")
    @classmethod
    def _validate_options(cls, value: list[str]) -> list[str]:
        cleaned: list[str] = []
        seen: set[str] = set()
        for raw in value:
            if not isinstance(raw, str):
                raise ValueError("Cada opcion debe ser texto")
            opt = raw.strip()
            if not 1 <= len(opt) <= WORKLOG_KEY_MAX:
                raise ValueError(f"Cada opcion debe tener entre 1 y {WORKLOG_KEY_MAX} caracteres")
            if opt not in seen:
                seen.add(opt)
                cleaned.append(opt)
        return cleaned


class WorklogDefinitions(RootModel[dict[str, WorklogDefinition]]):
    """Tipos de turno de la empresa: clave (1..50 caracteres) -> WorklogDefinition."""

    @field_validator("root", mode="after")
    @classmethod
    def _validate_keys(cls, value: dict[str, WorklogDefinition]) -> dict[str, WorklogDefinition]:
        for key in value:
            if not 1 <= len(key) <= WORKLOG_KEY_MAX:
                raise ValueError(f"La clave de tipo de turno debe tener entre 1 y {WORKLOG_KEY_MAX} caracteres")
        return value


class ExtraEntry(BaseModel):
    """Extra de una tarifa (valor de `RateEntry.extras`)."""

    value: NonNegativeFiniteFloat
    """Tipo: float >= 0, finito, no booleano. Sin default: obligatorio."""

    per_unit: bool = False
    """Tipo: bool. Default False. Si es True, el extra se aplica por unidad."""


class RateEntry(BaseModel):
    """Tarifa de un miembro para un tipo de turno (valor de `CompanyMember.rates_config`)."""

    model_config = ConfigDict(extra="allow")

    base_rate: NonNegativeFiniteFloat = 0.0
    """Tipo: float >= 0, finito, no booleano. Default 0.0."""

    is_gross: bool = False
    """Tipo: bool. Default False. Indica si base_rate es bruta."""

    tax_overrides: dict[str, float | None] | None = Field(default_factory=dict)
    """Tipo: dict[str, float | None] | None. Default {}. Nombre de impuesto -> tasa 0..1 o None (no sustituye); null equivale a sin overrides (igual que en PR-10)."""

    extras: dict[str, ExtraEntry] = Field(default_factory=dict)
    """Tipo: dict[str, ExtraEntry]. Default {}. Extras por nombre."""

    @field_validator("tax_overrides", mode="before")
    @classmethod
    def _validate_tax_overrides(cls, value: Any) -> Any:
        validate_tax_overrides(value)
        return value


class RatesConfig(RootModel[dict[str, RateEntry]]):
    """Tarifas de un miembro: tipo de turno -> RateEntry. Maximo 50 claves y 65536 bytes de JSON."""

    @field_validator("root", mode="before")
    @classmethod
    def _validate_root(cls, value: Any) -> Any:
        if not isinstance(value, dict):
            raise ValueError("rates_config debe ser un objeto tipo -> tarifa")
        if len(value) > RATES_CONFIG_MAX_KEYS:
            raise ValueError(f"rates_config admite como maximo {RATES_CONFIG_MAX_KEYS} tipos de turno")
        if _json_size_bytes(value) > RATES_CONFIG_MAX_BYTES:
            raise ValueError(f"rates_config supera el tamano maximo de {RATES_CONFIG_MAX_BYTES} bytes")
        return value


def validate_member_settings(value: dict) -> dict:
    """Valida `CompanyMember.settings`: solo claves de la lista blanca y tamano maximo en bytes."""
    if not isinstance(value, dict):
        raise ValueError("settings debe ser un objeto")
    unknown = sorted(str(key) for key in value if key not in MEMBER_SETTINGS_ALLOWED_KEYS)
    if unknown:
        raise ValueError(f"Claves no permitidas en settings de miembro: {', '.join(unknown)}")
    if _json_size_bytes(value) > MEMBER_SETTINGS_MAX_BYTES:
        raise ValueError(f"settings de miembro supera el tamano maximo de {MEMBER_SETTINGS_MAX_BYTES} bytes")
    return value


RESERVED_EMAIL_TLDS = frozenset({"invalid", "test", "local"})


def validate_allowed_email_domain(email: str) -> str:
    """Rechaza dominios reservados (.invalid, .test, .local) conforme a R-ACC-69."""
    domain = email.strip().lower().rsplit("@", 1)[-1]
    tld = domain.rsplit(".", 1)[-1] if "." in domain else ""
    if tld in RESERVED_EMAIL_TLDS:
        raise ValueError("El dominio del correo no es valido (.invalid, .test y .local no estan permitidos)")
    return email
