"""
CRUD Operations Module.

This module contains functions to interact with the database using the SQLAlchemy session.
It abstracts the database queries for creating, reading, updating, and deleting records.
"""

import json
import uuid
from datetime import date
from datetime import datetime as _dt
from typing import Any

import access_cache
import access_policy
import models
import schemas
import work_log_rules
from access_policy import PolicyError
from contracts import MissingWorklogUnitError, resolve_taxes
from redis_config import logger, redis_manager
from sqlalchemy import distinct, func, or_
from sqlalchemy.orm import Session, joinedload


def get_user_by_email(db: Session, email: str):
    """
    Retrieves a user from the database by their email address.

    Args:
        db (Session): The database session.
        email (str): The email address of the user to retrieve.

    Returns:
        models.User: The user object if found, otherwise None.
    """
    return db.query(models.User).filter(models.User.email == email).first()


def get_user(db: Session, user_id: str):
    return db.query(models.User).filter(models.User.id == user_id).first()


def get_users(db: Session, skip: int = 0, limit: int = 100):
    return db.query(models.User).offset(skip).limit(limit).all()


def create_user(db: Session, user: schemas.UserCreate):
    from auth import get_password_hash

    hashed_password = get_password_hash(user.password)
    # Basic name splitting logic or defaults
    first_name = user.first_name
    last_name = user.last_name

    # If schema has full_name but model needs split
    if hasattr(user, "full_name") and user.full_name:
        parts = user.full_name.split(" ", 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    db_user = models.User(email=user.email, hashed_password=hashed_password, first_name=first_name, last_name=last_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    return db_user


def update_user_status(db: Session, user_id: str, is_active: bool):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
    return user


MSG_NO_ACTIVE_MEMBERSHIP = "El usuario no tiene una membresia activa en esta empresa"


class MissingRateError(ValueError):
    """El turno no tiene tarifa aplicable ni importe manual (el router lo traduce a 400)."""


MSG_MANUAL_AMOUNT_CHOICE = (
    "Este turno tiene un importe manual: indica si se conserva el importe o se calcula por tarifa"
)


class ManualAmountChoiceError(ValueError):
    """Un turno manual cambia datos de calculo sin importe explicito ni recalculo (el router lo traduce a 409)."""


def get_company_member(db: Session, user_id: Any, company_id: Any, *, only_active: bool = False):
    try:
        cid = uuid.UUID(str(company_id)) if not isinstance(company_id, uuid.UUID) else company_id
        uid = uuid.UUID(str(user_id)) if not isinstance(user_id, uuid.UUID) else user_id
    except (ValueError, TypeError, AttributeError):
        return None
    query = db.query(models.CompanyMember).filter(
        models.CompanyMember.user_id == uid, models.CompanyMember.company_id == cid
    )
    if only_active:
        query = query.filter(models.CompanyMember.is_active == True)  # noqa: E712
    return query.first()


def get_worklog_unit(type_def: dict) -> str:
    unit = type_def.get("unit")
    if not unit:
        raise MissingWorklogUnitError("El tipo de turno no tiene unidad definida (unit)")
    return unit


def _safe_float(val, default=0.0):
    try:
        if val is None or val == "":
            return float(default)
        return float(val)
    except (ValueError, TypeError):
        return float(default)


def calculate_dynamic_work_log(log_data: dict, company_def: dict, user_rate: dict, company_tax_config: dict = None):
    """
    SaaS Evolution: Dynamic calculation engine.
    Calculates amounts based on company definitions and user rates stored in JSONB.

    Semantica de `is_gross` (P-10):
    - True: la tarifa es bruta; se descuentan todos los impuestos efectivos (empresa + overrides
      de miembro): neto = (base + extras) * (1 - suma de tasas).
    - False (o ausente): la tarifa es neta; no se deduce ningun impuesto y neto = base + extras.
      El bruto devuelto es solo informativo (neto / (1 - suma de tasas) si la suma es < 1).
    `settings.price_type` NO interviene aqui: solo decide la vista del dashboard.
    Un importe manual (`amount` / `net_amount`) no aplica impuestos.
    """
    # 1. Manual Amount Override
    manual_amount = log_data.get("amount")
    if manual_amount is None:
        manual_amount = log_data.get("net_amount")

    if manual_amount is not None:
        amount = _safe_float(manual_amount)
        return {
            "net_amount": amount,
            "gross_amount": amount,
            "rate_applied": 0.0,
            "duration": 0.0,
            "snapshot": {"type": "manual_override", "net_amount": amount},
        }

    # 2. Extract configuration
    unit = get_worklog_unit(company_def)
    base_rate = _safe_float(user_rate.get("base_rate", 0))
    is_gross = user_rate.get("is_gross", False)

    # Impuestos efectivos con claves libres (override de miembro > empresa)
    taxes = {
        name: _safe_float(rate)
        for name, rate in resolve_taxes(company_tax_config, user_rate.get("tax_overrides") or {}).items()
    }

    duration = 0.0

    # 3. Calculate Base Amount by Unit
    if unit == "hours":
        duration = _safe_float(log_data.get("duration_hours") or 0)
        if not duration and log_data.get("start_time") and log_data.get("end_time"):
            st = log_data["start_time"]
            et = log_data["end_time"]
            # Handles cross-day if needed, though usually same day
            start_h = st.hour + st.minute / 60.0
            end_h = et.hour + et.minute / 60.0
            diff = end_h - start_h
            if diff < 0:
                diff += 24.0
            duration = diff
        amount_base = duration * base_rate

    elif unit == "days":
        start_date = log_data.get("start_date")
        end_date = log_data.get("end_date")
        if start_date and end_date:
            delta = end_date - start_date
            duration = _safe_float(delta.days + 1)
            amount_base = duration * base_rate
        else:
            amount_base = 0.0
    else:  # fixed
        duration = 1.0
        amount_base = base_rate

    # 4. Handle Modifiers (Dynamic lookup in rate config)
    extras_total = 0.0
    applied_extras = {}
    user_extras = user_rate.get("extras", {})

    # Get extra inputs from extra_data
    log_extras = log_data.get("extra_data", {})
    log_options = log_extras.get("opciones", {})

    for extra_key, extra_val in user_extras.items():
        # If log has the key as True in extra_data['opciones']
        if log_options.get(extra_key) is True:
            # Extras can be fixed or per-unit
            val = _safe_float(extra_val.get("value", 0))
            if extra_val.get("per_unit") is True:
                extra_amt = val * duration
            else:
                extra_amt = val
            extras_total += extra_amt
            applied_extras[extra_key] = extra_amt

    # 5. Apply Taxes and handle Gross/Net modes
    total_tax_rate = sum(taxes.values())

    if is_gross:
        # Rate is Gross: Gross -> Net (se descuentan todos los impuestos efectivos)
        gross_total = amount_base + extras_total
        net_total = gross_total * (1.0 - total_tax_rate)
    else:
        # Rate is Net: no se deduce ningun impuesto; el bruto es informativo (Net -> Gross)
        net_total = amount_base + extras_total
        if total_tax_rate < 1.0:
            gross_total = net_total / (1.0 - total_tax_rate)
        else:
            gross_total = net_total  # Fallback

    # 6. Generate Structured Display Lines (Option A: Structured Snapshot)
    # These are used by the frontend to render the "ticket" with proper styling.
    display_lines = []

    # Base Income line
    base_label = f"{duration} {unit}"
    if unit == "hours":
        base_label = f"{round(duration, 2)}h x {base_rate}€/h"
    elif unit == "days":
        base_label = f"{round(duration, 1)}d x {base_rate}€/d"

    display_lines.append(
        {
            "type": "income",
            "label": base_label if is_gross else f"{base_label} (Neto)",
            "value": round(float(amount_base), 2),
        }
    )

    # Extras lines
    for ex_k, ex_v in applied_extras.items():
        display_lines.append({"type": "extra", "label": f"Extra: {ex_k}", "value": round(float(ex_v), 2)})

    # Gross Total line
    display_lines.append({"type": "subtotal", "label": "Total Bruto", "value": round(float(gross_total), 2)})

    # Taxes lines
    for tax_name, tax_rate in taxes.items():
        if tax_rate > 0:
            display_lines.append(
                {
                    "type": "tax",
                    "code": tax_name,
                    "label": f"{tax_name} ({round(tax_rate * 100, 2)}%)",
                    "value": -round(float(gross_total * tax_rate), 2),
                }
            )

    # Final Net line
    display_lines.append({"type": "total", "label": "Total Neto", "value": round(float(net_total), 2)})

    # 7. Build Snapshot
    snapshot = {
        "definition": company_def,
        "rate_applied": user_rate,
        "display_lines": display_lines,
        "calculations": {
            "base_amount": float(amount_base),
            "extras": applied_extras,
            "gross": float(gross_total),
            "net": float(net_total),
            "duration": float(duration),
            "unit": unit,
        },
        "tax_applied": taxes,
        "version": "2.3-free-taxes",
    }

    return {
        "net_amount": float(net_total),
        "gross_amount": float(gross_total),
        "rate_applied": float(base_rate),
        "duration": float(duration),
        "snapshot": snapshot,
    }


def _invalidate_company_rates(company_id: Any):
    """Helper to invalidate rates cache."""
    redis_manager.delete(f"company_rates:{company_id}")


def _overlap_warnings(db: Session, log: models.WorkLog, *, with_user_id: bool = False) -> list[dict]:
    """Avisos de solape (T7) de un turno guardado con otros del mismo usuario y empresa. Solo avisa, nunca rechaza."""
    others = (
        db.query(models.WorkLog)
        .filter(
            models.WorkLog.user_id == log.user_id,
            models.WorkLog.company_id == log.company_id,
            models.WorkLog.id != log.id,
            models.WorkLog.start_date <= log.end_date,
            models.WorkLog.end_date >= log.start_date,
        )
        .all()
    )
    fields = ("id", "start_date", "end_date", "start_time", "end_time")
    conflicting = work_log_rules.find_overlaps(
        {f: getattr(log, f) for f in fields}, [{f: getattr(o, f) for f in fields} for o in others]
    )
    if not conflicting:
        return []
    return [
        {
            "code": "overlap",
            "message": work_log_rules.OVERLAP_MESSAGE,
            "conflicting_log_ids": conflicting,
            "user_id": log.user_id if with_user_id else None,
        }
    ]


def create_work_log(db: Session, work_log: schemas.WorkLogCreate):
    """
    Creates a new work log entry using the dynamic calculation engine.
    """
    company_id = work_log.company_id
    user_id = str(work_log.user_id)

    # Get definitions and rates
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    member = get_company_member(db, user_id, str(company_id), only_active=True)

    if not company or not member:
        # Defensa en profundidad: el router ya exige membresia activa (T1)
        raise ValueError(MSG_NO_ACTIVE_MEMBERSHIP)
    defs = company.worklog_definitions or {}
    rates = member.rates_config or {}

    # Identify work type definition and rate
    work_type = work_log.type.value if hasattr(work_log.type, "value") else work_log.type
    type_def = defs.get(work_type, {"unit": "hours", "label": work_type})
    type_rate = rates.get(work_type, {})

    # Validation: Ensure rate is set (and non-zero) unless it's a manual override
    has_manual_override = getattr(work_log, "amount", None) is not None or work_log.net_amount is not None
    if not has_manual_override and _safe_float(type_rate.get("base_rate", 0)) <= 0:
        raise ValueError(
            f"No se ha encontrado un precio (rate) configurado para el tipo '{work_type}' para este usuario."
        )

    # Prepare DB Obj
    work_log_data = work_log.model_dump()
    work_log_data.pop("group_id", None)

    # Adjust end_date if it crosses midnight
    if get_worklog_unit(type_def) == "hours" and work_log_data.get("start_time") and work_log_data.get("end_time"):
        if work_log_data["end_time"] < work_log_data["start_time"]:
            from datetime import timedelta

            work_log_data["end_date"] = work_log_data["start_date"] + timedelta(days=1)

    # Use Dynamic Engine (passing the adjusted work_log_data)
    calc = calculate_dynamic_work_log(work_log_data, type_def, type_rate, company.tax_config if company else None)

    # Remove calculated and renamed fields
    for k in ["net_amount", "gross_amount", "rate_applied", "duration", "amount"]:
        work_log_data.pop(k, None)

    # El grupo solo lo genera el backend (bulk): se descarta un group_id colado en extra_data
    extra_data = dict(work_log_data.get("extra_data") or {})
    extra_data.pop("group_id", None)
    work_log_data["extra_data"] = extra_data

    db_work_log = models.WorkLog(
        **work_log_data,
        net_amount=calc["net_amount"],
        gross_amount=calc["gross_amount"],
        duration=calc["duration"],
        calculation_snapshot=calc["snapshot"],
    )

    db.add(db_work_log)
    db.commit()
    db.refresh(db_work_log)
    if db_work_log.company_id:
        invalidate_dashboard_summary(db_work_log.company_id)
    db_work_log.warnings = _overlap_warnings(db, db_work_log)
    return db_work_log


def create_work_log_bulk(db: Session, work_log_bulk: schemas.WorkLogBulkCreate):
    """
    Creates multiple work log entries for different users with the same group_id.
    """
    group_id = uuid.uuid4()
    company_id = work_log_bulk.company_id

    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    tax_config = company.tax_config if company else None
    defs = company.worklog_definitions or {} if company else {}

    # Identify work type definition
    work_type = work_log_bulk.type.value if hasattr(work_log_bulk.type, "value") else work_log_bulk.type
    type_def = defs.get(work_type, {"unit": "hours", "label": work_type})

    created_logs = []

    # Todo o nada: se comprueba a todos los usuarios antes de crear ningun turno
    members = {}
    user_ids = list(dict.fromkeys(work_log_bulk.user_ids))  # sin duplicados: un turno por usuario
    for user_id in user_ids:
        member = get_company_member(db, str(user_id), str(company_id), only_active=True)
        if member is None:
            raise ValueError(MSG_NO_ACTIVE_MEMBERSHIP)
        members[user_id] = member

    for user_id in user_ids:
        member = members[user_id]
        rates = member.rates_config or {}
        type_rate = rates.get(work_type, {})

        # Validation: Ensure rate is set (and non-zero) unless it's a manual override
        has_manual_override = getattr(work_log_bulk, "amount", None) is not None or work_log_bulk.net_amount is not None
        if not has_manual_override and _safe_float(type_rate.get("base_rate", 0)) <= 0:
            user_obj = db.query(models.User).filter(models.User.id == user_id).first()
            user_name = f"{user_obj.first_name} {user_obj.last_name}" if user_obj else str(user_id)
            raise ValueError(
                f"El usuario {user_name} no tiene un precio (rate) configurado para el tipo '{work_type}'."
            )

        # Build individual log data
        individual_log_data = work_log_bulk.model_dump(by_alias=False)
        individual_log_data.pop("user_ids", None)
        individual_log_data.pop("group_id", None)
        individual_log_data["user_id"] = user_id

        # Adjust end_date if it crosses midnight
        if (
            get_worklog_unit(type_def) == "hours"
            and individual_log_data.get("start_time")
            and individual_log_data.get("end_time")
        ):
            if individual_log_data["end_time"] < individual_log_data["start_time"]:
                from datetime import timedelta

                individual_log_data["end_date"] = individual_log_data["start_date"] + timedelta(days=1)

        # Use Dynamic Engine
        calc = calculate_dynamic_work_log(individual_log_data, type_def, type_rate, tax_config)

        # Prepare DB Obj
        # Remove calculated and renamed fields
        for k in ["net_amount", "gross_amount", "rate_applied", "duration", "amount"]:
            individual_log_data.pop(k, None)

        # group_id no es una columna: vive en extra_data y lo genera siempre el backend
        extra_data_val = dict(individual_log_data.get("extra_data") or {})
        extra_data_val["group_id"] = str(group_id)
        individual_log_data["extra_data"] = extra_data_val

        db_work_log = models.WorkLog(
            **individual_log_data,
            net_amount=calc["net_amount"],
            gross_amount=calc["gross_amount"],
            duration=calc["duration"],
            calculation_snapshot=calc["snapshot"],
        )

        db.add(db_work_log)
        created_logs.append(db_work_log)

    db.commit()
    for log in created_logs:
        db.refresh(log)

    if company_id:
        invalidate_dashboard_summary(company_id)

    if not created_logs:
        return None
    # La respuesta es el primer turno; lleva los avisos de todo el lote, cada uno con su userId
    created_logs[0].warnings = [w for log in created_logs for w in _overlap_warnings(db, log, with_user_id=True)]
    return created_logs[0]


def _filter_work_logs(
    db: Session,
    query,
    *,
    user_id: str = None,
    company_id: str = None,
    start_date: date = None,
    end_date: date = None,
    only_active_companies: bool = False,
):
    """Filtros comunes de turnos (listado, conteo y agregados). Rango con solape: end >= start y start <= end."""
    if only_active_companies:
        # Turnos sin empresa o de empresas activas (una empresa suspendida no expone sus turnos)
        active_company_ids = db.query(models.Company.id).filter(models.Company.is_active == True)
        query = query.filter(
            or_(models.WorkLog.company_id.is_(None), models.WorkLog.company_id.in_(active_company_ids))
        )
    if user_id:
        query = query.filter(models.WorkLog.user_id == user_id)
    if company_id:
        query = query.filter(models.WorkLog.company_id == company_id)

    if start_date:
        query = query.filter(models.WorkLog.end_date >= start_date)

    if end_date:
        query = query.filter(models.WorkLog.start_date <= end_date)
    return query


def get_daily_report_logs(db: Session, company_id: str, day: date):
    """Turnos de la empresa que cubren el dia (incluye los que cruzan medianoche), sin paginar."""
    query = _filter_work_logs(
        db, db.query(models.WorkLog), company_id=company_id, start_date=day, end_date=day
    )
    return query.order_by(models.WorkLog.start_time.asc(), models.WorkLog.id.asc()).all()


def get_work_logs(
    db: Session,
    skip: int = 0,
    limit: int = 100,
    user_id: str = None,
    company_id: str = None,
    start_date: date = None,
    end_date: date = None,
    only_active_companies: bool = False,
):
    query = _filter_work_logs(
        db,
        db.query(models.WorkLog),
        user_id=user_id,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        only_active_companies=only_active_companies,
    )

    return (
        query.order_by(models.WorkLog.start_date.desc(), models.WorkLog.start_time.desc(), models.WorkLog.id.desc())
        .offset(skip)
        .limit(limit)
        .all()
    )


def count_work_logs(
    db: Session,
    *,
    user_id: str = None,
    company_id: str = None,
    start_date: date = None,
    end_date: date = None,
    only_active_companies: bool = False,
) -> int:
    """Total de turnos que cumplen los mismos filtros que get_work_logs (sin paginar)."""
    query = _filter_work_logs(
        db,
        db.query(func.count(models.WorkLog.id)),
        user_id=user_id,
        company_id=company_id,
        start_date=start_date,
        end_date=end_date,
        only_active_companies=only_active_companies,
    )
    return int(query.scalar() or 0)


WORK_LOG_SUMMARY_CACHE_TTL = 300


def _work_log_summary_cache_key(company_id: str, user_id: str | None, start_date: date, end_date: date) -> str:
    # Prefijo dashboard_summary:{company_id}: para que invalidate_dashboard_summary lo borre al escribir turnos.
    return f"dashboard_summary:{company_id}:wls:{user_id or '-'}:{start_date.isoformat()}:{end_date.isoformat()}"


def get_work_log_summary(
    db: Session,
    *,
    company_id: str | None,
    user_id: str | None,
    start_date: date,
    end_date: date,
    only_active_companies: bool = False,
) -> dict:
    """
    Agregados de turnos en el rango (totales, por tipo, por dia y por usuario).
    Toda la agregacion se hace en SQL. Con company_id se usa cache Redis de 300 s.
    Devuelve tipos JSON-compatibles (fechas en ISO, UUID en str, numeros en float/int).
    """
    cache_key = None
    if company_id:
        cache_key = _work_log_summary_cache_key(str(company_id), str(user_id) if user_id else None, start_date, end_date)
        try:
            cached = redis_manager.get(cache_key)
            if cached:
                return json.loads(cached)
        except Exception as e:
            logger.error(f"Error leyendo cache de resumen de turnos: {e}")

    summary = _compute_work_log_summary(
        db,
        company_id=company_id,
        user_id=user_id,
        start_date=start_date,
        end_date=end_date,
        only_active_companies=only_active_companies,
    )

    if cache_key:
        try:
            redis_manager.set(cache_key, json.dumps(summary), ex=WORK_LOG_SUMMARY_CACHE_TTL)
        except Exception as e:
            logger.error(f"Error guardando cache de resumen de turnos: {e}")
    return summary


def _compute_work_log_summary(
    db: Session,
    *,
    company_id: str | None,
    user_id: str | None,
    start_date: date,
    end_date: date,
    only_active_companies: bool,
) -> dict:
    def _filtered(query):
        return _filter_work_logs(
            db,
            query,
            user_id=user_id,
            company_id=company_id,
            start_date=start_date,
            end_date=end_date,
            only_active_companies=only_active_companies,
        )

    logs = models.WorkLog
    sum_hours = func.sum(logs.duration)
    sum_net = func.sum(logs.net_amount)
    sum_gross = func.sum(logs.gross_amount)

    total_row = _filtered(
        db.query(
            func.count(logs.id),
            sum_hours,
            sum_net,
            sum_gross,
            func.count(distinct(logs.start_date)),
            func.count(distinct(logs.user_id)),
        ).select_from(logs)
    ).one()

    type_rows = (
        _filtered(db.query(logs.type, func.count(logs.id), sum_hours, sum_net, sum_gross).select_from(logs))
        .group_by(logs.type)
        .order_by(logs.type)
        .all()
    )

    day_rows = (
        _filtered(db.query(logs.start_date, func.count(logs.id), sum_hours, sum_net, sum_gross).select_from(logs))
        .group_by(logs.start_date)
        .order_by(logs.start_date)
        .all()
    )

    user_rows = (
        _filtered(
            db.query(
                logs.user_id,
                models.User.first_name,
                models.User.last_name,
                models.User.email,
                func.count(logs.id),
                sum_hours,
                sum_net,
                sum_gross,
                func.count(distinct(logs.start_date)),
            )
            .select_from(logs)
            .outerjoin(models.User, models.User.id == logs.user_id)
        )
        .group_by(logs.user_id, models.User.first_name, models.User.last_name, models.User.email)
        .order_by(models.User.last_name, models.User.first_name, logs.user_id)
        .all()
    )

    return {
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "totals": {
            "logs_count": int(total_row[0] or 0),
            "total_hours": float(total_row[1] or 0),
            "total_net": float(total_row[2] or 0),
            "total_gross": float(total_row[3] or 0),
            "unique_days": int(total_row[4] or 0),
            "active_users": int(total_row[5] or 0),
        },
        "by_type": [
            {
                "type": row[0],
                "logs_count": int(row[1] or 0),
                "hours": float(row[2] or 0),
                "net": float(row[3] or 0),
                "gross": float(row[4] or 0),
            }
            for row in type_rows
        ],
        "by_day": [
            {
                "date": row[0].isoformat(),
                "logs_count": int(row[1] or 0),
                "hours": float(row[2] or 0),
                "net": float(row[3] or 0),
                "gross": float(row[4] or 0),
            }
            for row in day_rows
        ],
        "by_user": [
            {
                "user_id": str(row[0]),
                "first_name": row[1],
                "last_name": row[2],
                "email": row[3],
                "logs_count": int(row[4] or 0),
                "hours": float(row[5] or 0),
                "net": float(row[6] or 0),
                "gross": float(row[7] or 0),
                "unique_days": int(row[8] or 0),
            }
            for row in user_rows
        ],
    }


def update_work_log(
    db: Session,
    work_log_id: str,
    work_log: schemas.WorkLogUpdate,
    *,
    company_id: Any,
    apply_to_group: bool = False,
    recalculate_with_current_rates: bool = False,
    keep_manual_amount: bool = False,
):
    """
    SaaS Evolution: Updates using the dynamic engine.
    Supports cascading updates for grouped logs.
    Solo toca turnos de `company_id`: devuelve None si el turno no existe o es de otra empresa.
    """
    db_work_log = (
        db.query(models.WorkLog)
        .filter(models.WorkLog.id == work_log_id, models.WorkLog.company_id == company_id)
        .first()
    )
    if not db_work_log:
        return None

    # If apply_to_group is true and we have a group_id (vive en extra_data, no es columna)
    group_id = db_work_log.extra_data.get("group_id") if db_work_log.extra_data else None

    if apply_to_group and group_id:
        # Turnos del mismo grupo Y de la misma empresa
        logs_in_group = (
            db.query(models.WorkLog)
            .filter(
                models.WorkLog.company_id == db_work_log.company_id,
                models.WorkLog.extra_data["group_id"].as_string() == str(group_id),
            )
            .all()
        )

        # Todo o nada: se valida cada turno del grupo antes de aplicar (y confirmar) ninguno
        payload = work_log.model_dump(exclude_unset=True)
        for log in logs_in_group:
            _check_update_dates(log, payload)

        # Todo o nada: ningun turno se confirma hasta que todos se han calculado; un fallo deshace el grupo entero
        primary_updated = None
        try:
            for log in logs_in_group:
                try:
                    updated = _update_single_work_log(
                        db,
                        log,
                        work_log,
                        recalculate_with_current_rates=recalculate_with_current_rates,
                        commit=False,
                        keep_manual_amount=keep_manual_amount,
                    )
                except ValueError as e:
                    owner = log.user
                    name = f"{owner.first_name} {owner.last_name}" if owner else str(log.user_id)
                    e.args = (f"{name}: {e}",)
                    raise
                if str(log.id) == work_log_id:
                    primary_updated = updated
            db.commit()
        except Exception:
            db.rollback()
            raise

        primary_updated = primary_updated or (logs_in_group[0] if logs_in_group else None)
        for log in logs_in_group:
            db.refresh(log)
        if db_work_log.company_id:
            invalidate_dashboard_summary(db_work_log.company_id)
        if primary_updated is not None:
            primary_updated.warnings = _overlap_warnings(db, primary_updated)
        return primary_updated

    return _update_single_work_log(
        db,
        db_work_log,
        work_log,
        recalculate_with_current_rates=recalculate_with_current_rates,
        keep_manual_amount=keep_manual_amount,
    )


def _check_update_dates(db_work_log: models.WorkLog, new_data: dict):
    """Una edicion parcial no puede dejar las fechas desordenadas. Solo se valida si el payload toca fechas,
    para no bloquear la edicion de otros campos en turnos antiguos."""
    if "start_date" not in new_data and "end_date" not in new_data:
        return
    start = new_data.get("start_date", db_work_log.start_date)
    end = new_data.get("end_date", db_work_log.end_date)
    if start > end:
        raise ValueError("start_date no puede ser posterior a end_date")


def _update_single_work_log(
    db: Session,
    db_work_log: models.WorkLog,
    work_log: schemas.WorkLogUpdate,
    *,
    recalculate_with_current_rates: bool = False,
    commit: bool = True,
    keep_manual_amount: bool = False,
):
    # Merge existing and new data
    current_data = {c.name: getattr(db_work_log, c.name) for c in db_work_log.__table__.columns}
    new_data = work_log.model_dump(exclude_unset=True)
    # Empresa y usuario no se pueden cambiar (T3); `amount` y `group_id` no son columnas
    for key in ("user_id", "company_id", "group_id"):
        new_data.pop(key, None)
    if "extra_data" in new_data:
        # El grupo no lo controla el cliente: se conserva el del turno
        extra = dict(new_data["extra_data"] or {})
        extra.pop("group_id", None)
        if (db_work_log.extra_data or {}).get("group_id"):
            extra["group_id"] = db_work_log.extra_data["group_id"]
        new_data["extra_data"] = extra
    merged_data = {**current_data, **new_data}
    _check_update_dates(db_work_log, new_data)

    # Los importes los fija el motor de calculo, nunca el cliente (salvo el importe manual explicito)
    snapshot = db_work_log.calculation_snapshot or {}
    was_manual = snapshot.get("type") == "manual_override"
    manual_value = new_data.get("amount") if new_data.get("amount") is not None else new_data.get("net_amount")
    if keep_manual_amount and was_manual:
        # "Conservar importe": cada turno manual (tambien en un grupo) mantiene el suyo; los calculados no se ven afectados
        manual_value = db_work_log.net_amount
    for key in ("amount", "net_amount", "gross_amount", "duration"):
        new_data.pop(key, None)

    type_changed = "type" in new_data and new_data["type"] != db_work_log.type
    # La columna es Numeric (Decimal): se compara redondeado a 2 decimales, no Decimal contra float
    explicit_manual = manual_value is not None and (
        was_manual
        or db_work_log.net_amount is None
        or round(float(manual_value), 2) != round(float(db_work_log.net_amount), 2)
    )

    inputs_changed = _recalc_inputs_changed(db_work_log, new_data)

    if was_manual and inputs_changed and not explicit_manual and not recalculate_with_current_rates:
        # Turno manual con datos de calculo modificados: el cliente debe elegir conservar el importe o calcular
        raise ManualAmountChoiceError(MSG_MANUAL_AMOUNT_CHOICE)

    if not (recalculate_with_current_rates or explicit_manual or inputs_changed):
        # T5: solo cambian campos sin efecto en el importe (p. ej. la descripcion): el snapshot no se toca
        for key, value in new_data.items():
            setattr(db_work_log, key, value)
        return _finish_updated_work_log(db, db_work_log, commit)

    owner_id = str(db_work_log.user_id)
    company_id = merged_data.get("company_id")
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    defs = company.worklog_definitions or {} if company else {}
    work_type = merged_data.get("type")

    if type_changed or recalculate_with_current_rates:
        # Tarifa, definicion e impuestos vigentes: exige membresia activa
        member = get_company_member(db, owner_id, str(company_id), only_active=True)
        if member is None:
            raise ValueError(MSG_NO_ACTIVE_MEMBERSHIP)
        type_def = defs.get(work_type, {"unit": "hours", "label": str(work_type)})
        type_rate = (member.rates_config or {}).get(work_type, {})
        tax_config = company.tax_config if company else None
    else:
        # Mismo tipo: se conservan la definicion, la tarifa y los impuestos con los que se guardo el turno.
        # Un snapshot sin esos datos (turno manual o antiguo) cae a los vigentes.
        member = get_company_member(db, owner_id, str(company_id))
        type_def = snapshot.get("definition") or defs.get(work_type, {"unit": "hours", "label": str(work_type)})
        type_rate = snapshot.get("rate_applied")
        if not isinstance(type_rate, dict):
            type_rate = (member.rates_config or {}).get(work_type, {}) if member else {}
        tax_applied = snapshot.get("tax_applied")
        tax_config = tax_applied if isinstance(tax_applied, dict) else (company.tax_config if company else None)

    if not explicit_manual and _safe_float(type_rate.get("base_rate", 0)) <= 0:
        raise MissingRateError(
            f"No se ha encontrado un precio (rate) configurado para el tipo '{work_type}' para este usuario."
        )

    # Adjust end_date if it crosses midnight
    if get_worklog_unit(type_def) == "hours" and merged_data.get("start_time") and merged_data.get("end_time"):
        if merged_data["end_time"] < merged_data["start_time"]:
            from datetime import timedelta

            merged_data["end_date"] = merged_data["start_date"] + timedelta(days=1)
            new_data["end_date"] = merged_data["end_date"]

    calc_input = {**merged_data, "amount": None, "net_amount": manual_value if explicit_manual else None}
    calc = calculate_dynamic_work_log(calc_input, type_def, type_rate, tax_config)

    for key, value in new_data.items():
        setattr(db_work_log, key, value)

    db_work_log.net_amount = calc["net_amount"]
    db_work_log.gross_amount = calc["gross_amount"]
    db_work_log.duration = calc["duration"]
    db_work_log.calculation_snapshot = calc["snapshot"]

    return _finish_updated_work_log(db, db_work_log, commit)


def _recalc_inputs_changed(db_work_log: models.WorkLog, new_data: dict) -> bool:
    """T5: True si la edicion toca algun dato que entra en el calculo del importe (con valor distinto al guardado)."""
    for field in ("type", "start_time", "end_time", "start_date", "end_date"):
        if field in new_data and new_data[field] != getattr(db_work_log, field):
            return True
    if "extra_data" in new_data:
        new_options = (new_data["extra_data"] or {}).get("opciones")
        if new_options != (db_work_log.extra_data or {}).get("opciones"):
            return True
    return False


def _finish_updated_work_log(db: Session, db_work_log: models.WorkLog, commit: bool) -> models.WorkLog:
    if not commit:
        # Edicion de grupo: el commit unico lo hace el llamador
        db.flush()
        return db_work_log
    db.commit()
    db.refresh(db_work_log)
    if db_work_log.company_id:
        invalidate_dashboard_summary(db_work_log.company_id)
    db_work_log.warnings = _overlap_warnings(db, db_work_log)
    return db_work_log


# --- Company Membership Logic ---


def join_company(db: Session, user_id: str, company_id: str):
    """
    Adds a user to a company or returns existing membership.
    """
    member = get_company_member(db, user_id, company_id)
    if not member:
        new_member = models.CompanyMember(
            user_id=user_id,
            company_id=company_id,
            role=models.CompanyRole.worker,
            is_active=True,
            rates_config={},  # Initialize empty dynamic rates
        )
        db.add(new_member)
        db.commit()
        db.refresh(new_member)
        _invalidate_company_rates(company_id)
        access_cache.invalidate_membership(user_id, company_id)
        return new_member

    # Healing: If existing member has NULL rates_config, fix it
    if member.rates_config is None:
        member.rates_config = {}
        db.commit()
        db.refresh(member)
        _invalidate_company_rates(company_id)

    return member


def get_manager_company_ids(db: Session, user_id: Any) -> set[str]:
    """Ids de las empresas activas donde el usuario tiene membresia activa de manager."""
    rows = (
        db.query(models.CompanyMember.company_id, models.CompanyMember.role)
        .join(models.Company)
        .filter(
            models.CompanyMember.user_id == user_id,
            models.CompanyMember.is_active == True,  # noqa: E712
            models.Company.is_active == True,  # noqa: E712
        )
        .all()
    )
    return {
        str(company_id)
        for company_id, role in rows
        if access_policy.normalize_member_role(getattr(role, "value", role)) == access_policy.ROLE_MANAGER
    }


def count_active_platform_admins(db: Session) -> int:
    """Cuenta los PA activos bloqueando sus filas (FOR UPDATE, orden por id).

    Debe llamarse dentro de la misma transaccion que la escritura posterior: el bloqueo se libera al commit.
    """
    rows = (
        db.query(models.User.id)
        .filter(models.User.role == models.UserRole.admin, models.User.is_active.is_(True))
        .order_by(models.User.id)
        .with_for_update()
        .all()
    )
    return len(rows)


def ensure_platform_admin_invariants(db: Session, actor, target, *, new_role: str | None, new_is_active: bool | None):
    """M9: el PA no puede desactivarse ni degradarse a si mismo, y la plataforma no puede quedarse sin PA activos.

    `new_role` y `new_is_active` a None significan "sin cambio".
    No hace commit: el llamador debe escribir y confirmar en la misma transaccion para que el bloqueo sea efectivo.
    """
    deactivates = new_is_active is False
    removes_admin_role = new_role is not None and new_role != models.UserRole.admin.value

    if actor.id == target.id:
        if deactivates:
            raise PolicyError(403, "No puedes desactivar tu propia cuenta")
        if removes_admin_role:
            raise PolicyError(403, "No puedes cambiar tu propio rol de plataforma")
        return

    target_is_active_admin = target.role == models.UserRole.admin and bool(target.is_active)
    if target_is_active_admin and (deactivates or removes_admin_role):
        if count_active_platform_admins(db) - 1 < 1:
            raise PolicyError(409, "La plataforma no puede quedarse sin administradores")


def delete_work_log(db: Session, work_log_id: str, *, company_id: Any):
    """Borra un turno solo si es de `company_id`; devuelve None si no existe o es de otra empresa."""
    db_work_log = (
        db.query(models.WorkLog)
        .filter(models.WorkLog.id == work_log_id, models.WorkLog.company_id == company_id)
        .first()
    )
    if db_work_log:
        db.delete(db_work_log)
        db.commit()
    return db_work_log


# UserDevice management removed. Sessions are now managed via UserSession in auth.py


def get_company(db: Session, company_id: Any):
    try:
        cid = uuid.UUID(str(company_id)) if not isinstance(company_id, uuid.UUID) else company_id
    except (ValueError, TypeError, AttributeError):
        return None
    return db.query(models.Company).filter(models.Company.id == cid).first()


def update_user(db: Session, user_id: Any, user: schemas.UserUpdate):
    from uuid import UUID

    try:
        uid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
    except ValueError:
        return None

    db_user = db.query(models.User).filter(models.User.id == uid).first()
    if db_user:
        # Use model_dump(exclude_unset=True) to get only provided fields
        update_data = user.model_dump(exclude_unset=True)
        for key, value in update_data.items():
            if value is None and key in ["role", "is_active"]:
                continue  # Hardening: do not allow setting role or is_active to NULL

            if key == "role" and value:
                # Convert string role to UserRole enum
                try:
                    setattr(db_user, key, models.UserRole(value))
                except ValueError:
                    logger.warning("Invalid role value for user update")
            else:
                setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user


# ─── Module & Subscription CRUD ────────────────────────────────────────────


def get_modules(db: Session, include_inactive: bool = False):
    """Lista todos los módulos del catálogo."""
    query = db.query(models.AppModule)
    if not include_inactive:
        query = query.filter(models.AppModule.is_active == True)
    return query.order_by(models.AppModule.name).all()


def get_module_by_id(db: Session, module_id: str):
    return db.query(models.AppModule).filter(models.AppModule.id == module_id).first()


def get_module_by_code(db: Session, code_name: str):
    return db.query(models.AppModule).filter(models.AppModule.code_name == code_name).first()


def create_module(db: Session, data: schemas.AppModuleCreate):
    db_module = models.AppModule(**data.model_dump())
    db.add(db_module)
    db.commit()
    db.refresh(db_module)
    return db_module


def update_module(db: Session, module_id: str, data: schemas.AppModuleUpdate):
    db_module = db.query(models.AppModule).filter(models.AppModule.id == module_id).first()
    if not db_module:
        return None
    update_data = data.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(db_module, key, value)
    db.commit()
    db.refresh(db_module)
    return db_module


_LIVE_SUBSCRIPTION_STATUSES = ("active", "trial")


def _ensure_no_live_duplicate(db: Session, module_id, company_id, user_id, exclude_id=None) -> None:
    """409 si ya hay otra suscripcion active/trial del mismo modulo para la misma empresa o usuario."""
    query = db.query(models.ModuleSubscription.id).filter(
        models.ModuleSubscription.module_id == module_id,
        models.ModuleSubscription.status.in_([models.SubscriptionStatus(s) for s in _LIVE_SUBSCRIPTION_STATUSES]),
        or_(models.ModuleSubscription.expires_at.is_(None), models.ModuleSubscription.expires_at > _dt.utcnow()),
    )
    if company_id is not None:
        query = query.filter(models.ModuleSubscription.company_id == company_id)
    else:
        query = query.filter(models.ModuleSubscription.user_id == user_id)
    if exclude_id is not None:
        query = query.filter(models.ModuleSubscription.id != exclude_id)
    if query.first() is not None:
        subject = "La empresa" if company_id is not None else "El usuario"
        raise PolicyError(409, f"{subject} ya tiene este modulo activo")


def create_subscription(db: Session, data: schemas.ModuleSubscriptionCreate):
    """Crea una suscripción. Valida que solo company_id O user_id esté presente."""
    if data.company_id and data.user_id:
        raise ValueError("Una suscripción no puede tener company_id y user_id a la vez.")
    if not data.company_id and not data.user_id:
        raise ValueError("Una suscripción debe tener company_id o user_id.")

    module = get_module_by_id(db, str(data.module_id))
    if module is not None and module.target_scope in ("company", "user") and module.target_scope != data.scope:
        raise PolicyError(422, f"El módulo solo admite suscripciones con scope '{module.target_scope}'.")
    if data.status in _LIVE_SUBSCRIPTION_STATUSES:
        _ensure_no_live_duplicate(db, data.module_id, data.company_id, data.user_id)

    db_sub = models.ModuleSubscription(
        module_id=data.module_id,
        company_id=data.company_id,
        user_id=data.user_id,
        scope=models.SubscriptionScope(data.scope),
        status=models.SubscriptionStatus(data.status),
        expires_at=data.expires_at,
        notes=data.notes,
    )
    db.add(db_sub)
    db.commit()
    db.refresh(db_sub)
    return db_sub


def update_subscription(db: Session, sub_id: str, data: schemas.ModuleSubscriptionUpdate):
    db_sub = db.query(models.ModuleSubscription).filter(models.ModuleSubscription.id == sub_id).first()
    if not db_sub:
        return None
    update_data = data.model_dump(exclude_unset=True, by_alias=False)
    new_status = update_data.get("status")
    if new_status in _LIVE_SUBSCRIPTION_STATUSES and new_status != db_sub.status.value:
        _ensure_no_live_duplicate(db, db_sub.module_id, db_sub.company_id, db_sub.user_id, exclude_id=db_sub.id)
    for key, value in update_data.items():
        if key == "status" and value:
            setattr(db_sub, key, models.SubscriptionStatus(value))
        else:
            setattr(db_sub, key, value)
    db.commit()
    db.refresh(db_sub)
    return db_sub


def delete_subscription(db: Session, sub_id: str):
    db_sub = db.query(models.ModuleSubscription).filter(models.ModuleSubscription.id == sub_id).first()
    if db_sub:
        db.delete(db_sub)
        db.commit()
    return db_sub


def user_has_module(db: Session, user_id: str, company_id: str | None, code_name: str) -> bool:
    """
    Comprueba si un usuario tiene acceso a un módulo.
    Prioridad:
      1. ¿Tiene el usuario una suscripción activa (personal)?
      2. ¿Tiene la empresa del usuario una suscripción activa?
    Una suscripción está activa si status == "active" o "trial"
    Y no ha expirado (expires_at is NULL o expires_at > now).
    """
    now = _dt.utcnow()
    active_statuses = [models.SubscriptionStatus.active, models.SubscriptionStatus.trial]

    # Buscar el módulo
    module = get_module_by_code(db, code_name)
    if not module or not module.is_active:
        return False

    # 1. Suscripción personal del usuario
    user_sub = (
        db.query(models.ModuleSubscription)
        .filter(
            models.ModuleSubscription.user_id == user_id,
            models.ModuleSubscription.module_id == module.id,
            models.ModuleSubscription.status.in_(active_statuses),
            or_(models.ModuleSubscription.expires_at.is_(None), models.ModuleSubscription.expires_at > now),
        )
        .first()
    )

    if user_sub:
        return True

    # 2. Suscripción de empresa (se ignora si la empresa esta suspendida)
    if company_id:
        company = db.query(models.Company).filter(models.Company.id == company_id).first()
        if company is None or not company.is_active:
            return False
        company_sub = (
            db.query(models.ModuleSubscription)
            .filter(
                models.ModuleSubscription.company_id == company_id,
                models.ModuleSubscription.module_id == module.id,
                models.ModuleSubscription.status.in_(active_statuses),
                or_(models.ModuleSubscription.expires_at.is_(None), models.ModuleSubscription.expires_at > now),
            )
            .first()
        )
        if company_sub:
            return True

    return False
def invalidate_dashboard_summary(company_id: Any):
    """
    Invalidates cached dashboard summary keys for a company.
    """
    if not company_id:
        return
    try:
        cid_str = str(company_id)
        redis_manager.delete_pattern(f"dashboard_summary:{cid_str}:*")
        logger.info(f"Invalidated dashboard summary cache for company {cid_str}")
    except Exception as e:
        logger.error(f"Error invalidating dashboard summary cache: {e}")


def get_dashboard_summary(
    db: Session,
    company_id: Any,
    start_date: date | None = None,
    end_date: date | None = None
) -> dict:
    """
    Calculates aggregated metrics for the manager dashboard.
    """
    cid = uuid.UUID(str(company_id)) if not isinstance(company_id, uuid.UUID) else company_id
    company = db.query(models.Company).filter(models.Company.id == cid).first()
    if not company:
        raise ValueError("Company not found")

    today = date.today()
    defs = company.worklog_definitions or {}

    # 1. Fetch all members (active and inactive, T11) ordered by sort_order
    members = db.query(models.CompanyMember).options(
        joinedload(models.CompanyMember.user)
    ).filter(
        models.CompanyMember.company_id == cid
    ).order_by(
        models.CompanyMember.sort_order.asc(),
        models.CompanyMember.joined_at.asc()
    ).all()

    # 2. Fetch period work logs
    query = db.query(models.WorkLog).options(
        joinedload(models.WorkLog.user)
    ).filter(models.WorkLog.company_id == cid)

    if start_date:
        query = query.filter(models.WorkLog.end_date >= start_date)
    if end_date:
        query = query.filter(models.WorkLog.start_date <= end_date)

    period_logs = query.all()

    # 3. Fetch today's logs specifically
    today_logs = db.query(models.WorkLog).options(
        joinedload(models.WorkLog.user)
    ).filter(
        models.WorkLog.company_id == cid,
        models.WorkLog.start_date <= today,
        models.WorkLog.end_date >= today
    ).all()

    # 4. Compute Period Metrics
    total_hours = 0.0
    total_net = 0.0
    total_gross = 0.0
    unique_days_set = set()
    active_users_set = set()

    type_stats: dict[str, dict] = {}
    daily_stats: dict[str, dict] = {}
    user_period_stats: dict[str, dict] = {}

    for log in period_logs:
        uid_str = str(log.user_id)
        active_users_set.add(uid_str)

        dur = float(log.duration or 0.0)
        net = float(log.net_amount or 0.0)
        gross = float(log.gross_amount or 0.0)

        total_hours += dur
        total_net += net
        total_gross += gross

        # Unique days
        if log.start_date:
            unique_days_set.add(str(log.start_date))

        # Type Breakdown
        w_type = log.type or "particular"
        if w_type not in type_stats:
            t_def = defs.get(w_type, {})
            type_stats[w_type] = {
                "type": w_type,
                "label": t_def.get("label", w_type.capitalize()),
                "unit": t_def.get("unit", "hours"),
                "hours": 0.0,
                "net": 0.0,
                "gross": 0.0,
                "count": 0
            }
        type_stats[w_type]["hours"] += dur
        type_stats[w_type]["net"] += net
        type_stats[w_type]["gross"] += gross
        type_stats[w_type]["count"] += 1

        # Daily Breakdown
        d_str = str(log.start_date)
        if d_str not in daily_stats:
            d_obj = log.start_date
            # Day names in Spanish
            d_names = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
            dow = d_obj.weekday()
            daily_stats[d_str] = {
                "date": d_str,
                "day_of_week": dow,
                "day_name": d_names[dow],
                "hours": 0.0,
                "net": 0.0,
                "gross": 0.0,
                "count": 0
            }
        daily_stats[d_str]["hours"] += dur
        daily_stats[d_str]["net"] += net
        daily_stats[d_str]["gross"] += gross
        daily_stats[d_str]["count"] += 1

        # User stats
        if uid_str not in user_period_stats:
            user_period_stats[uid_str] = {
                "hours": 0.0,
                "net": 0.0,
                "gross": 0.0,
                "days": set(),
                "count": 0,
                "types": {}
            }
        user_period_stats[uid_str]["hours"] += dur
        user_period_stats[uid_str]["net"] += net
        user_period_stats[uid_str]["gross"] += gross
        user_period_stats[uid_str]["days"].add(str(log.start_date))
        user_period_stats[uid_str]["count"] += 1
        user_period_stats[uid_str]["types"][w_type] = user_period_stats[uid_str]["types"].get(w_type, 0.0) + dur

    # 5. Compute Today's Metrics
    today_hours = 0.0
    today_user_map: dict[str, dict] = {}

    for log in today_logs:
        uid_str = str(log.user_id)
        dur = float(log.duration or 0.0)
        today_hours += dur

        if uid_str not in today_user_map:
            u = log.user
            today_user_map[uid_str] = {
                "user_id": log.user_id,
                "first_name": u.first_name if u else None,
                "last_name": u.last_name if u else None,
                "email": u.email if u else None,
                "role": "worker",
                "hours": 0.0,
                "logs_count": 0
            }
        today_user_map[uid_str]["hours"] += dur
        today_user_map[uid_str]["logs_count"] += 1

    # Attach member roles for today's active members
    for m in members:
        uid_str = str(m.user_id)
        if uid_str in today_user_map:
            today_user_map[uid_str]["role"] = m.role.value if hasattr(m.role, "value") else str(m.role)

    today_active_members = list(today_user_map.values())

    # 6. Workers Summary respecting strict sort_order
    workers_summary = []
    for m in members:
        uid_str = str(m.user_id)
        u = m.user
        u_stats = user_period_stats.get(uid_str, {
            "hours": 0.0,
            "net": 0.0,
            "gross": 0.0,
            "days": set(),
            "count": 0,
            "types": {}
        })

        workers_summary.append({
            "user_id": m.user_id,
            "first_name": u.first_name if u else None,
            "last_name": u.last_name if u else None,
            "email": u.email if u else None,
            "role": m.role.value if hasattr(m.role, "value") else str(m.role),
            "sort_order": m.sort_order if m.sort_order is not None else 1000,
            "is_active": m.is_active,
            "total_hours": round(u_stats["hours"], 2),
            "total_net": round(u_stats["net"], 2),
            "total_gross": round(u_stats["gross"], 2),
            "unique_days": len(u_stats["days"]),
            "logs_count": u_stats["count"],
            "types_breakdown": {k: round(v, 2) for k, v in u_stats["types"].items()}
        })

    # Sort daily breakdown by date
    sorted_daily = sorted(daily_stats.values(), key=lambda x: x["date"])

    return {
        "company_id": company.id,
        "company_name": company.name,
        "start_date": str(start_date) if start_date else "",
        "end_date": str(end_date) if end_date else "",
        "period_metrics": {
            "total_hours": round(total_hours, 2),
            "total_net": round(total_net, 2),
            "total_gross": round(total_gross, 2),
            "unique_days": len(unique_days_set),
            "total_logs": len(period_logs),
            "active_members_count": len(active_users_set)
        },
        "today_metrics": {
            "today_hours": round(today_hours, 2),
            "today_logs_count": len(today_logs),
            "today_active_members_count": len(today_active_members),
            "today_active_members": today_active_members
        },
        "type_breakdown": list(type_stats.values()),
        "daily_breakdown": sorted_daily,
        "workers_summary": workers_summary
    }


def get_audit_logs(
    db: Session,
    *,
    company_id: Any = None,
    actor_user_id: Any = None,
    target_user_id: Any = None,
    action: str | None = None,
    from_date: _dt | None = None,
    to_date: _dt | None = None,
    limit: int = 50,
    offset: int = 0,
) -> tuple[int, list[models.AuditLog]]:
    query = db.query(models.AuditLog)
    if company_id is not None:
        query = query.filter(models.AuditLog.company_id == company_id)
    if actor_user_id is not None:
        query = query.filter(models.AuditLog.actor_user_id == actor_user_id)
    if target_user_id is not None:
        query = query.filter(models.AuditLog.target_user_id == target_user_id)
    if action is not None:
        query = query.filter(models.AuditLog.action == action)
    if from_date is not None:
        query = query.filter(models.AuditLog.created_at >= from_date)
    if to_date is not None:
        query = query.filter(models.AuditLog.created_at <= to_date)

    total = query.count()
    rows = (
        query.order_by(models.AuditLog.created_at.desc(), models.AuditLog.id.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    return total, rows
