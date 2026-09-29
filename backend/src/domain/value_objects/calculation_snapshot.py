"""
Value Object CalculationSnapshot: Encapsula el desglose auditado del calculo salarial y fiscal.
"""
from dataclasses import dataclass, field
from decimal import Decimal
from typing import List, Dict, Any


@dataclass(frozen=True)
class DisplayLine:
    type: str
    label: str
    value: float
    code: str = ""

    def to_dict(self) -> Dict[str, Any]:
        res: Dict[str, Any] = {
            "type": self.type,
            "label": self.label,
            "value": self.value,
        }
        if self.code:
            res["code"] = self.code
        return res


@dataclass(frozen=True)
class CalculationSnapshot:
    gross_amount: Decimal
    net_amount: Decimal
    rate_applied: Decimal
    duration: float
    display_lines: List[DisplayLine] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "version": "2.2-structured-snapshot",
            "lines": [line.to_dict() for line in self.display_lines],
            "metadata": self.metadata,
        }
