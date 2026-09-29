"""
Value Object WorkDuration: Modela la duracion de una jornada o servicio.
"""

from dataclasses import dataclass
from datetime import date, time
from enum import Enum
from typing import Optional


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
                start_h = start_time.hour + start_time.minute / 60.0
                end_h = end_time.hour + end_time.minute / 60.0
                diff = end_h - start_h
                if diff < 0:
                    diff += 24.0
                return cls(unit=WorkUnit.HOURS, value=round(diff, 2))
            return cls(unit=WorkUnit.HOURS, value=0.0)

        elif unit == WorkUnit.DAYS:
            if start_date is not None and end_date is not None:
                delta = (end_date - start_date).days + 1
                return cls(unit=WorkUnit.DAYS, value=float(max(delta, 1)))
            return cls(unit=WorkUnit.DAYS, value=1.0)

        else:
            return cls(unit=WorkUnit.FIXED, value=1.0)
