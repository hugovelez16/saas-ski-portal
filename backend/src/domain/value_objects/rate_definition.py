"""
Value Object RateDefinition: Define la estructura de tarifa aplicable a un trabajador.
"""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class RateExtra:
    name: str
    value: Decimal
    per_unit: bool


@dataclass(frozen=True)
class RateDefinition:
    base_rate: Decimal
    is_gross: bool
    extras: Dict[str, RateExtra] = field(default_factory=dict)
    tax_overrides: Dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, rate_dict: Optional[Dict[str, Any]] = None) -> "RateDefinition":
        data = rate_dict or {}
        base_rate_raw = data.get("base_rate", 0)
        base_rate = Decimal(str(base_rate_raw if base_rate_raw is not None and base_rate_raw != "" else 0))
        is_gross = bool(data.get("is_gross", False))

        extras_dict: Dict[str, RateExtra] = {}
        raw_extras = data.get("extras", {})
        if isinstance(raw_extras, dict):
            for k, v in raw_extras.items():
                if isinstance(v, dict):
                    val = Decimal(str(v.get("value", 0) or 0))
                    per_unit = bool(v.get("per_unit", False))
                    extras_dict[k] = RateExtra(name=k, value=val, per_unit=per_unit)

        return cls(
            base_rate=base_rate,
            is_gross=is_gross,
            extras=extras_dict,
            tax_overrides=data.get("tax_overrides", {}) or {},
        )
