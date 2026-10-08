"""
Entidad de Dominio WorkLog: Representa el registro de una jornada, turno o clase.
"""

from dataclasses import dataclass, field
from datetime import date, datetime, time
from typing import Any, Dict, Optional

from domain.value_objects.calculation_snapshot import CalculationSnapshot
from domain.value_objects.money import Money


@dataclass
class WorkLog:
    id: str
    user_id: str
    company_id: str
    type: str
    start_date: date
    end_date: Optional[date] = None
    start_time: Optional[time] = None
    end_time: Optional[time] = None
    duration_hours: Optional[float] = None
    description: Optional[str] = None
    gross_amount: Money = field(default_factory=Money.zero)
    net_amount: Money = field(default_factory=Money.zero)
    extra_data: Dict[str, Any] = field(default_factory=dict)
    calculation_snapshot: Optional[CalculationSnapshot] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    @property
    def group_id(self) -> Optional[str]:
        return self.extra_data.get("group_id")
