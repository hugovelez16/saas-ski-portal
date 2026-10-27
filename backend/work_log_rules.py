"""Reglas puras de turnos (sin acceso a base de datos)."""

from datetime import datetime, time

OVERLAP_MESSAGE = "Este turno se solapa con otro del mismo trabajador"


def _interval(log: dict) -> tuple[datetime, datetime]:
    start = datetime.combine(log["start_date"], log.get("start_time") or time.min)
    end = datetime.combine(log["end_date"], log.get("end_time") or time.max)
    return start, end


def find_overlaps(candidate: dict, existing: list[dict]) -> list[str]:
    """
    Devuelve los ids de los turnos de `existing` que se solapan con `candidate`.

    Cada turno es un dict con `start_date`, `end_date`, `start_time`, `end_time` (y `id` en los existentes).
    Sin hora de inicio el turno empieza a las 00:00; sin hora de fin acaba al final del dia. Dos turnos solapan
    si a.start < b.end y b.start < a.end, asi que los contiguos (fin == inicio) no solapan. Un existente con el
    mismo `id` que el candidato se ignora (editar un turno no lo solapa consigo mismo).
    """
    cand_start, cand_end = _interval(candidate)
    cand_id = candidate.get("id")
    overlaps = []
    for other in existing:
        if cand_id is not None and str(other.get("id")) == str(cand_id):
            continue
        other_start, other_end = _interval(other)
        if cand_start < other_end and other_start < cand_end:
            overlaps.append(other["id"])
    return overlaps
