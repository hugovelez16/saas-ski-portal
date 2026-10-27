"""
Contratos de validacion compartidos (PR-10: impuestos con claves libres).

`TaxConfig` valida la configuracion de impuestos de una empresa (nombre libre -> tasa 0..1),
`validate_tax_overrides` valida los overrides de impuestos de un miembro y `resolve_taxes`
combina ambos para obtener los impuestos efectivos.
"""

import json
import logging
import math
from typing import Annotated, Any, Literal

from pydantic import BaseModel, ConfigDict, Field, RootModel, Strict, ValidationError, field_validator

logger = logging.getLogger(__name__)


class MissingWorklogUnitError(ValueError):
    """El tipo de turno no tiene `unit` en su definicion. Se traduce a HTTP 422 en main.py."""


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
        return result

    def as_dict(self) -> dict[str, float]:
        return dict(self.root)


def validate_tax_overrides(value: dict | None) -> dict | None:
    """Valida overrides de impuestos de un miembro: None, o nombre -> (None | tasa 0..1)."""
    if value is None:
        return None
    if not isinstance(value, dict):
        raise ValueError("tax_overrides debe ser un objeto o null")
    for raw_name, rate in value.items():
        name = _validate_tax_name(raw_name)
        if rate is not None:
            _validate_tax_rate(name, rate)
    return value


def resolve_taxes(company_tax_config: dict | None, tax_overrides: dict | None) -> dict[str, float]:
    """Impuestos efectivos: empresa + overrides de miembro (un override None no sustituye)."""
    return {**(company_tax_config or {}), **{k: v for k, v in (tax_overrides or {}).items() if v is not None}}


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


class BusinessLogic(BaseModel):
    """Reglas de negocio de la empresa (clave `business_logic` de CompanySettings)."""

    model_config = ConfigDict(extra="forbid")

    price_type: Literal["net", "gross"] = "net"
    """Tipo: Literal["net", "gross"]. Default "net".
    Solo afecta a la vista del dashboard (P-10); no cambia ningun calculo del backend."""


class WorkerExperience(BaseModel):
    """Experiencia de registro de jornadas para trabajadores (clave `worker_experience`)."""

    model_config = ConfigDict(extra="forbid")

    input_mode: Literal["manual_single", "timer", "bulk"] = "manual_single"
    """Tipo: Literal["manual_single", "timer", "bulk"]. Default "manual_single".
    Modo de introduccion de jornadas que muestra la interfaz al trabajador."""

    allow_manual_amount: bool = False
    """Tipo: bool. Default False.
    Si es True, el trabajador puede introducir el importe manualmente."""


class UiLabels(BaseModel):
    """Etiquetas personalizables de la interfaz (dentro de `ui_customization.labels`)."""

    model_config = ConfigDict(extra="forbid")

    worklog: str | None = Field(None, max_length=60)
    """Tipo: str | None, maximo 60 caracteres. Default None (etiqueta por defecto del producto)."""

    client: str | None = Field(None, max_length=60)
    """Tipo: str | None, maximo 60 caracteres. Default None (etiqueta por defecto del producto)."""


class UiCustomization(BaseModel):
    """Personalizacion visual de la empresa (clave `ui_customization`)."""

    model_config = ConfigDict(extra="forbid")

    labels: UiLabels = Field(default_factory=UiLabels)
    """Tipo: UiLabels. Default: UiLabels sin etiquetas personalizadas."""


class CompanySettings(BaseModel):
    """
    Configuracion global de una empresa (columna `companies.settings`).

    Las claves desconocidas se rechazan al validar (extra="forbid"); al leer
    desde BD se usa `from_db`, que las descarta con un warning.
    """

    model_config = ConfigDict(extra="forbid")

    business_logic: BusinessLogic = Field(default_factory=BusinessLogic)
    """Clave `business_logic`. Tipo: BusinessLogic. Default: BusinessLogic(price_type="net").
    Reglas de negocio; `price_type` solo afecta a la vista del dashboard (P-10)."""

    worker_experience: WorkerExperience = Field(default_factory=WorkerExperience)
    """Clave `worker_experience`. Tipo: WorkerExperience. Default: input_mode="manual_single", allow_manual_amount=False.
    Comportamiento de registro de jornadas para trabajadores."""

    ui_customization: UiCustomization = Field(default_factory=UiCustomization)
    """Clave `ui_customization`. Tipo: UiCustomization. Default: sin etiquetas personalizadas.
    Personalizacion de textos de la interfaz."""

    modules: dict[str, bool] = Field(default_factory=dict)
    """Clave `modules`. Tipo: dict[str, bool]. Default: {}.
    Activacion de modulos de la empresa por codigo de modulo."""

    allowed_rates: list[str] | None = None
    """Clave `allowed_rates`. Tipo: list[str] | None. Default: None (sin restriccion).
    Tipos de turno que puede usar la empresa; None no restringe."""

    @classmethod
    def from_db(cls, raw: dict | None) -> "CompanySettings":
        """
        Lectura tolerante del JSONB de BD. Nunca lanza excepcion:
        - las claves desconocidas (tambien dentro de subobjetos) se descartan con warning;
        - un valor de tipo invalido cae al default de ese campo con warning.
        """
        if not raw:
            return cls()
        return _tolerant_build(cls, raw, "settings")

    def ui_view(self) -> dict[str, Any]:
        """Parte de interfaz para la vista reducida (PR-13)."""
        return {
            "worker_experience": self.worker_experience.model_dump(),
            "ui_customization": self.ui_customization.model_dump(),
            "modules": dict(self.modules),
            "business_logic": {"price_type": self.business_logic.price_type},
        }


class WorklogDefinition(BaseModel):
    """Definicion de un tipo de turno (valor de `companies.worklog_definitions`)."""

    model_config = ConfigDict(extra="allow")

    unit: Literal["hours", "days", "fixed"]
    label: str = Field(min_length=1, max_length=60)
    fields: list[dict[str, Any]] = Field(default_factory=list)


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
