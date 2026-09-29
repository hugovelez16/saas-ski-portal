"""
Value Object TaxConfiguration: Gestiona porcentajes y deducciones de impuestos (IRPF, SS, Extras).
"""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional


@dataclass(frozen=True)
class TaxConfiguration:
    irpf_rate: Decimal
    social_security_rate: Decimal
    extra_rate: Decimal

    @classmethod
    def from_dict(
        cls,
        company_tax_config: Optional[Dict[str, Any]] = None,
        user_tax_overrides: Optional[Dict[str, Any]] = None,
    ) -> "TaxConfiguration":
        company_defaults = company_tax_config or {}
        overrides = user_tax_overrides or {}

        def _to_decimal(val, default=0.0) -> Decimal:
            if val is None or val == "":
                return Decimal(str(default))
            return Decimal(str(val))

        irpf_val = overrides.get("irpf")
        irpf = _to_decimal(irpf_val if irpf_val is not None else company_defaults.get("irpf_base", 0))

        ss_val = overrides.get("ss")
        ss = _to_decimal(ss_val if ss_val is not None else company_defaults.get("social_security", 0))

        extra_val = overrides.get("extra")
        extra = _to_decimal(extra_val if extra_val is not None else company_defaults.get("extra", 0))

        return cls(
            irpf_rate=irpf,
            social_security_rate=ss,
            extra_rate=extra,
        )

    @property
    def total_tax_rate(self) -> Decimal:
        return self.irpf_rate + self.social_security_rate + self.extra_rate
