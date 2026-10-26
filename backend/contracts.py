"""
Contratos de validacion compartidos (PR-10: impuestos con claves libres).

`TaxConfig` valida la configuracion de impuestos de una empresa (nombre libre -> tasa 0..1),
`validate_tax_overrides` valida los overrides de impuestos de un miembro y `resolve_taxes`
combina ambos para obtener los impuestos efectivos.
"""

import math
from typing import Any

from pydantic import RootModel, field_validator

TAX_NAME_MAX = 50
TAX_MAX_ENTRIES = 20


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
