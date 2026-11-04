"""
Value Object TaxConfiguration: impuestos efectivos con claves libres (empresa + overrides de miembro).
"""

from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, Optional


def _to_decimal(val: Any) -> Decimal:
    """Como `crud._safe_float`: un valor vacio o no numerico (dato heredado sucio) cuenta como 0."""
    if val is None or val == "":
        return Decimal("0")
    try:
        result = Decimal(str(val))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0")
    return result if result.is_finite() else Decimal("0")


@dataclass(frozen=True)
class TaxConfiguration:
    taxes: Dict[str, Decimal] = field(default_factory=dict)

    @classmethod
    def from_dict(
        cls,
        company_tax_config: Optional[Dict[str, Any]] = None,
        user_tax_overrides: Optional[Dict[str, Any]] = None,
    ) -> "TaxConfiguration":
        """Equivale a `contracts.resolve_taxes`: un override con valor None no sustituye al de la empresa."""
        effective = {
            **(company_tax_config or {}),
            **{name: rate for name, rate in (user_tax_overrides or {}).items() if rate is not None},
        }
        return cls(taxes={name: _to_decimal(rate) for name, rate in effective.items()})

    @property
    def total_tax_rate(self) -> Decimal:
        return sum(self.taxes.values(), Decimal("0"))
