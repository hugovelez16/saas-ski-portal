"""
Value Object WorkDuration: Modela la duracion de una jornada o servicio.
"""

from dataclasses import dataclass
from datetime import date, time
from decimal import ROUND_HALF_UP, Decimal
from enum import Enum
from typing import Optional

from contracts import MissingWorklogDatesError


class WorkUnit(str, Enum):
    HOURS = "hours"
    DAYS = "days"
    FIXED = "fixed"


@dataclass(frozen=True)
class WorkDuration:
    """Duracion de trabajo calculada segun unidad, horas o rango de fechas."""

    unit: WorkUnit
    value: float

    @classmethod
    def calculate(
        cls,
        unit: WorkUnit,
        duration_hours: Optional[float] = None,
        start_time: Optional[time] = None,
        end_time: Optional[time] = None,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> "WorkDuration":
        if unit == WorkUnit.HOURS:
            if duration_hours is not None and duration_hours > 0:
                return cls(unit=WorkUnit.HOURS, value=float(duration_hours))
            if start_time is not None and end_time is not None:
                start_minutes = Decimal(start_time.hour * 60 + start_time.minute) + Decimal(start_time.second) / Decimal(
                    60
                )
                end_minutes = Decimal(end_time.hour * 60 + end_time.minute) + Decimal(end_time.second) / Decimal(60)
                diff = (end_minutes - start_minutes) / Decimal(60)
                if diff < Decimal("0"):
                    diff += Decimal("24")
                return cls(unit=WorkUnit.HOURS, value=float(diff.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)))
            return cls(unit=WorkUnit.HOURS, value=0.0)

        elif unit == WorkUnit.DAYS:
            if start_date is None or end_date is None:
                raise MissingWorklogDatesError("Un turno con unidad 'days' requiere fecha de inicio y de fin")
            delta = (end_date - start_date).days + 1
            return cls(unit=WorkUnit.DAYS, value=float(max(delta, 1)))

        else:
            return cls(unit=WorkUnit.FIXED, value=1.0)
