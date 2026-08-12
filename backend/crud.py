"""
CRUD Operations Module.

This module contains functions to interact with the database using the SQLAlchemy session.
It abstracts the database queries for creating, reading, updating, and deleting records.
"""
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_
import models, schemas, auth
from sqlalchemy.orm.attributes import flag_modified
import uuid
from datetime import date, datetime
from typing import Any, Dict, List, Optional
import json
from pydantic import TypeAdapter
from redis_config import redis_manager, logger



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
    if hasattr(user, 'full_name') and user.full_name:
        parts = user.full_name.split(' ', 1)
        first_name = parts[0]
        last_name = parts[1] if len(parts) > 1 else ""

    db_user = models.User(email=user.email, hashed_password=hashed_password, first_name=first_name, last_name=last_name)
    db.add(db_user)
    db.commit()
    db.refresh(db_user)

    # Auto-join "Personal" company
    personal_company = db.query(models.Company).filter(models.Company.name == "Personal").first()
    if personal_company:
        new_member = models.CompanyMember(
            user_id=db_user.id,
            company_id=personal_company.id,
            role=models.CompanyRole.worker,
            is_active=True # Auto-active for Personal
        )
        db.add(new_member)
        db_user.default_company_id = personal_company.id
        db.commit()
        db.refresh(db_user)
        _invalidate_company_rates(personal_company.id)
        
    return db_user

def update_user_status(db: Session, user_id: str, is_active: bool):
    user = db.query(models.User).filter(models.User.id == user_id).first()
    if user:
        user.is_active = is_active
        db.commit()
        db.refresh(user)
    return user

def get_company_member(db: Session, user_id: str, company_id: str):
    return db.query(models.CompanyMember).filter(
        models.CompanyMember.user_id == user_id,
        models.CompanyMember.company_id == company_id
    ).first()

def get_worklog_unit(type_def: dict) -> str:
    unit = type_def.get("unit")
    if not unit:
        unit = "days" if type_def.get("is_range") else "hours"
    return unit

def calculate_dynamic_work_log(log_data: dict, company_def: dict, user_rate: dict, company_tax_config: dict = None):
    """
    SaaS Evolution: Dynamic calculation engine.
    Calculates amounts based on company definitions and user rates stored in JSONB.
    """
    # 1. Manual Amount Override
    if log_data.get('net_amount') is not None:
        amount = float(log_data['net_amount'])
        return {
            "net_amount": amount,
            "gross_amount": amount,
            "rate_applied": 0.0,
            "duration": 0.0,
            "snapshot": {"type": "manual_override", "net_amount": amount}
        }

    # 2. Extract configuration
    unit = get_worklog_unit(company_def)
    base_rate = float(user_rate.get("base_rate", 0))
    is_gross = user_rate.get("is_gross", False)
    
    # Tax configuration (Priority: rate override > company default > 0)
    user_overrides = user_rate.get("tax_overrides", {})
    company_defaults = company_tax_config if company_tax_config else {}
    
    irpf_val = user_overrides.get("irpf")
    irpf = float(irpf_val if irpf_val is not None else company_defaults.get("irpf_base", 0))
    
    ss_val = user_overrides.get("ss")
    ss = float(ss_val if ss_val is not None else company_defaults.get("social_security", 0))
    
    extra_val = user_overrides.get("extra")
    extra = float(extra_val if extra_val is not None else company_defaults.get("extra", 0))
    
    duration = 0.0
    
    # 3. Calculate Base Amount by Unit
    if unit == "hours":
        duration = float(log_data.get('duration_hours') or 0)
        if not duration and log_data.get('start_time') and log_data.get('end_time'):
            st = log_data['start_time']
            et = log_data['end_time']
            # Handles cross-day if needed, though usually same day
            start_h = st.hour + st.minute / 60.0
            end_h = et.hour + et.minute / 60.0
            diff = end_h - start_h
            if diff < 0: diff += 24.0
            duration = diff
        amount_base = duration * base_rate
        
    elif unit == "days":
        start_date = log_data.get('start_date')
        end_date = log_data.get('end_date')
        if start_date and end_date:
            delta = end_date - start_date
            duration = float(delta.days + 1)
            amount_base = duration * base_rate
        else:
            amount_base = 0.0
    else: # fixed
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
            val = float(extra_val.get("value", 0))
            if extra_val.get("per_unit") is True:
                extra_amt = val * duration
            else:
                extra_amt = val
            extras_total += extra_amt
            applied_extras[extra_key] = extra_amt

    # 5. Apply Taxes and handle Gross/Net modes
    total_tax_rate = irpf + ss + extra
    
    if is_gross:
        # Rate is Gross: Gross -> Net
        gross_total = amount_base + extras_total
        net_total = gross_total * (1.0 - total_tax_rate)
    else:
        # Rate is Net: Net -> Gross (Reverse Tax)
        net_total = amount_base + extras_total
        if total_tax_rate < 1.0:
            gross_total = net_total / (1.0 - total_tax_rate)
        else:
            gross_total = net_total # Fallback
            
    # 6. Generate Structured Display Lines (Option A: Structured Snapshot)
    # These are used by the frontend to render the "ticket" with proper styling.
    display_lines = []
    
    # Base Income line
    base_label = f"{duration} {unit}"
    if unit == "hours": base_label = f"{round(duration, 2)}h x {base_rate}€/h"
    elif unit == "days": base_label = f"{round(duration, 1)}d x {base_rate}€/d"
    
    display_lines.append({
        "type": "income",
        "label": base_label if is_gross else f"{base_label} (Neto)",
        "value": round(float(amount_base), 2)
    })
    
    # Extras lines
    for ex_k, ex_v in applied_extras.items():
        display_lines.append({
            "type": "extra",
            "label": f"Extra: {ex_k}",
            "value": round(float(ex_v), 2)
        })
        
    # Gross Total line
    display_lines.append({
        "type": "subtotal",
        "label": "Total Bruto",
        "value": round(float(gross_total), 2)
    })
    
    # Taxes lines
    if ss > 0:
        display_lines.append({
            "type": "tax",
            "code": "ss",
            "label": f"Seguridad Social ({round(ss*100, 2)}%)",
            "value": -round(float(gross_total * ss), 2)
        })
    if irpf > 0:
        display_lines.append({
            "type": "tax",
            "code": "irpf",
            "label": f"IRPF ({round(irpf*100, 2)}%)",
            "value": -round(float(gross_total * irpf), 2)
        })
    if extra > 0:
        display_lines.append({
            "type": "tax",
            "code": "other",
            "label": f"Otros ({round(extra*100, 2)}%)",
            "value": -round(float(gross_total * extra), 2)
        })
        
    # Final Net line
    display_lines.append({
        "type": "total",
        "label": "Total Neto",
        "value": round(float(net_total), 2)
    })

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
            "unit": unit
        },
        "version": "2.2-structured-snapshot"
    }

    return {
        "net_amount": float(net_total),
        "gross_amount": float(gross_total),
        "rate_applied": float(base_rate),
        "duration": float(duration),
        "snapshot": snapshot
    }


def get_company_rates(db: Session, company_id: str):
    """
    SaaS Evolution: Gets rates from the members table instead of the deprecated rates table.
    Includes Redis caching with Failover.
    """
    cache_key = f"company_rates:{company_id}"
    
    # 1. Try Cache
    cached_data = redis_manager.get(cache_key)
    if cached_data:
        try:
            return json.loads(cached_data)
        except Exception as e:
            logger.error(f"Failed to decode rates cache for {company_id}: {e}")

    # 2. Db Fetch
    members = db.query(models.CompanyMember) \
             .options(joinedload(models.CompanyMember.user)) \
             .filter(models.CompanyMember.company_id == company_id).all()
    
    # 3. Serialize and Store
    try:
        # We use CompanyMemberResponse schema for consistent serialization (handles UUIDs/Dates)
        adapter = TypeAdapter(List[schemas.CompanyMemberResponse])
        serialized = adapter.dump_python(members, mode='json')
        redis_manager.set(cache_key, json.dumps(serialized), ex=3600)
    except Exception as e:
        logger.error(f"Failed to cache rates for {company_id}: {e}")

    return members

def _invalidate_company_rates(company_id: Any):
    """Helper to invalidate rates cache."""
    redis_manager.delete(f"company_rates:{company_id}")


def create_work_log(db: Session, work_log: schemas.WorkLogCreate):
    """
    Creates a new work log entry using the dynamic calculation engine.
    """
    company_id = work_log.company_id
    user_id = str(work_log.user_id)
    
    # Get definitions and rates
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    member = get_company_member(db, user_id, str(company_id))
    
    if not company or not member:
        # Fallback or error handling - for now, basic defaults if missing
        defs = {}
        rates = {}
    else:
        defs = company.worklog_definitions or {}
        rates = member.rates_config or {}

    # Identify work type definition and rate
    work_type = work_log.type.value if hasattr(work_log.type, 'value') else work_log.type
    type_def = defs.get(work_type, {"unit": "hours", "label": work_type})
    type_rate = rates.get(work_type, {})
    
    # Validation: Ensure rate is set (and non-zero) unless it's a manual override
    if work_log.net_amount is None and float(type_rate.get("base_rate", 0)) <= 0:
        raise ValueError(f"No se ha encontrado un precio (rate) configurado para el tipo '{work_type}' para este usuario.")

    # Prepare DB Obj
    work_log_data = work_log.model_dump()

    # Adjust end_date if it crosses midnight
    if get_worklog_unit(type_def) == "hours" and work_log_data.get('start_time') and work_log_data.get('end_time'):
        if work_log_data['end_time'] < work_log_data['start_time']:
            from datetime import timedelta
            work_log_data['end_date'] = work_log_data['start_date'] + timedelta(days=1)

    # Use Dynamic Engine (passing the adjusted work_log_data)
    calc = calculate_dynamic_work_log(work_log_data, type_def, type_rate, company.tax_config if company else None)

    # Remove calculated and renamed fields
    for k in ['net_amount', 'gross_amount', 'rate_applied', 'duration', 'amount']:
        work_log_data.pop(k, None)

    # Handle group_id which is not a dedicated column
    group_id = work_log_data.pop('group_id', None)
    extra_data = work_log_data.get('extra_data') or {}
    if group_id:
        extra_data['group_id'] = str(group_id)
    work_log_data['extra_data'] = extra_data

    db_work_log = models.WorkLog(
        **work_log_data,
        net_amount=calc["net_amount"],
        gross_amount=calc["gross_amount"],
        duration=calc["duration"],
        calculation_snapshot=calc["snapshot"]
    )
    
    db.add(db_work_log)
    db.commit()
    db.refresh(db_work_log)
    return db_work_log

def create_work_log_bulk(db: Session, work_log_bulk: schemas.WorkLogBulkCreate):
    """
    Creates multiple work log entries for different users with the same group_id.
    """
    group_id = work_log_bulk.group_id or uuid.uuid4()
    company_id = work_log_bulk.company_id
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    tax_config = company.tax_config if company else None
    defs = company.worklog_definitions or {} if company else {}
    
    # Identify work type definition
    work_type = work_log_bulk.type.value if hasattr(work_log_bulk.type, 'value') else work_log_bulk.type
    type_def = defs.get(work_type, {"unit": "hours", "label": work_type})
    
    created_logs = []
    
    for user_id in work_log_bulk.user_ids:
        member = get_company_member(db, str(user_id), str(company_id))
        rates = member.rates_config or {} if member else {}
        type_rate = rates.get(work_type, {})
        
        # Validation: Ensure rate is set (and non-zero) unless it's a manual override
        if work_log_bulk.net_amount is None and float(type_rate.get("base_rate", 0)) <= 0:
            user_obj = db.query(models.User).filter(models.User.id == user_id).first()
            user_name = f"{user_obj.first_name} {user_obj.last_name}" if user_obj else str(user_id)
            raise ValueError(f"El usuario {user_name} no tiene un precio (rate) configurado para el tipo '{work_type}'.")
        
        # Build individual log data
        individual_log_data = work_log_bulk.model_dump(by_alias=False)
        individual_log_data.pop('user_ids', None)
        individual_log_data['user_id'] = user_id
        individual_log_data['group_id'] = group_id
        
        # Adjust end_date if it crosses midnight
        if get_worklog_unit(type_def) == "hours" and individual_log_data.get('start_time') and individual_log_data.get('end_time'):
            if individual_log_data['end_time'] < individual_log_data['start_time']:
                from datetime import timedelta
                individual_log_data['end_date'] = individual_log_data['start_date'] + timedelta(days=1)

        # Use Dynamic Engine
        calc = calculate_dynamic_work_log(individual_log_data, type_def, type_rate, tax_config)
        
        # Prepare DB Obj
        # Remove calculated and renamed fields
        for k in ['net_amount', 'gross_amount', 'rate_applied', 'duration', 'amount']:
            individual_log_data.pop(k, None)
            
        # Handle group_id which is not a dedicated column
        group_id_val = individual_log_data.pop('group_id', None)
        extra_data_val = individual_log_data.get('extra_data') or {}
        if group_id_val:
            extra_data_val['group_id'] = str(group_id_val)
        individual_log_data['extra_data'] = extra_data_val
            
        db_work_log = models.WorkLog(
            **individual_log_data,
            net_amount=calc["net_amount"],
            gross_amount=calc["gross_amount"],
            duration=calc["duration"],
            calculation_snapshot=calc["snapshot"]
        )
        
        db.add(db_work_log)
        created_logs.append(db_work_log)
    
    db.commit()
    for log in created_logs:
        db.refresh(log)
    
    return created_logs[0] if created_logs else None 

def get_work_logs(db: Session, skip: int = 0, limit: int = 100, user_id: str = None, company_id: str = None, start_date: date = None, end_date: date = None):
    query = db.query(models.WorkLog)
    if user_id:
        query = query.filter(models.WorkLog.user_id == user_id)
    if company_id:
        query = query.filter(models.WorkLog.company_id == company_id)
    
    if start_date:
        query = query.filter(models.WorkLog.end_date >= start_date)
    
    if end_date:
        query = query.filter(models.WorkLog.start_date <= end_date)

    return query.order_by(models.WorkLog.start_date.desc(), models.WorkLog.start_time.desc()).offset(skip).limit(limit).all()

def update_work_log(db: Session, work_log_id: str, work_log: schemas.WorkLogCreate, apply_to_group: bool = False):
    """
    SaaS Evolution: Updates using the dynamic engine.
    Supports cascading updates for grouped logs.
    """
    db_work_log = db.query(models.WorkLog).filter(models.WorkLog.id == work_log_id).first()
    if not db_work_log:
        return None
    
    # If apply_to_group is true and we have a group_id
    group_id = getattr(db_work_log, 'group_id', None) or (db_work_log.extra_data.get('group_id') if db_work_log.extra_data else None)
    
    if apply_to_group and group_id:
        # Find all logs in the group
        import sqlalchemy
        logs_in_group = db.query(models.WorkLog).filter(
            or_(
                models.WorkLog.group_id == group_id,
                models.WorkLog.extra_data['group_id'].astext == str(group_id)
            )
        ).all()
        
        primary_updated = None
        for log in logs_in_group:
            updated = _update_single_work_log(db, log, work_log)
            if str(log.id) == work_log_id:
                primary_updated = updated
        
        return primary_updated or (logs_in_group[0] if logs_in_group else None)
    
    return _update_single_work_log(db, db_work_log, work_log)

def _update_single_work_log(db: Session, db_work_log: models.WorkLog, work_log: schemas.WorkLogCreate):
    # Merge existing and new data
    current_data = {c.name: getattr(db_work_log, c.name) for c in db_work_log.__table__.columns}
    new_data = work_log.model_dump(exclude_unset=True)
    merged_data = {**current_data, **new_data}
    
    # Recalculate
    owner_id = str(db_work_log.user_id)
    company_id = merged_data.get('company_id')
    
    company = db.query(models.Company).filter(models.Company.id == company_id).first()
    member = get_company_member(db, owner_id, str(company_id))
    
    defs = company.worklog_definitions or {} if company else {}
    rates = member.rates_config or {} if member else {}
    
    work_type = merged_data.get('type')
    type_def = defs.get(work_type, {"unit": "hours", "label": str(work_type)})
    type_rate = rates.get(work_type, {})
    
    # Force recalculation if net_amount not in NEW data
    if 'net_amount' not in new_data:
        merged_data.pop('net_amount', None)

    # Adjust end_date if it crosses midnight
    if get_worklog_unit(type_def) == "hours" and merged_data.get('start_time') and merged_data.get('end_time'):
        if merged_data['end_time'] < merged_data['start_time']:
            from datetime import timedelta
            merged_data['end_date'] = merged_data['start_date'] + timedelta(days=1)
            new_data['end_date'] = merged_data['end_date']

    calc = calculate_dynamic_work_log(merged_data, type_def, type_rate, company.tax_config if company else None)
    
    # Apply changes
    for key, value in new_data.items():
        setattr(db_work_log, key, value)
        
    db_work_log.net_amount = calc["net_amount"]
    db_work_log.gross_amount = calc["gross_amount"]
    db_work_log.duration = calc["duration"]
    db_work_log.calculation_snapshot = calc["snapshot"]
    
    db.commit()
    db.refresh(db_work_log)
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
            rates_config={} # Initialize empty dynamic rates
        )
         db.add(new_member)
         db.commit()
         db.refresh(new_member)
         _invalidate_company_rates(company_id)
         return new_member
    
    # Healing: If existing member has NULL rates_config, fix it
    if member.rates_config is None:
        member.rates_config = {}
        db.commit()
        db.refresh(member)
        _invalidate_company_rates(company_id)
    
    return member


def get_user_companies(db: Session, user_id: str, include_inactive: bool = False):
    """Get companies the user is a member of (joined), merging member-specific settings."""
    query = db.query(models.CompanyMember).filter(
        models.CompanyMember.user_id == user_id
    )
    if not include_inactive:
        query = query.filter(models.CompanyMember.is_active == True)
        
    members = query.all()
    
    results = []
    for m in members:
        company = m.company
        if not company: continue
        
        c_settings = company.settings if isinstance(company.settings, dict) else {}
        m_settings = m.settings if isinstance(m.settings, dict) else {}
        
        effective = c_settings.copy()
        effective.update(m_settings)
        
        # Construct response object (dict compatible with Pydantic)
        results.append({
            "id": company.id,
            "name": company.name,
            "fiscal_id": company.fiscal_id,
            "tax_config": company.tax_config,
            "worklog_definitions": company.worklog_definitions,
            "created_at": company.created_at,
            "updated_at": company.updated_at,
            "settings": effective,
            "role": m.role.value if hasattr(m.role, 'value') else m.role,
            "is_active_member": m.is_active,
            "rates_config": m.rates_config
        })
    return results

def get_company_members(db: Session, company_id: str, is_active: bool = None):
    query = db.query(models.CompanyMember).filter(models.CompanyMember.company_id == company_id)
    if is_active is not None:
        query = query.filter(models.CompanyMember.is_active == is_active)
    return query.order_by(models.CompanyMember.sort_order.asc(), models.CompanyMember.joined_at.asc()).all()

def update_company_members_order(db: Session, company_id: str, user_ids: list[str]):
    for index, user_id in enumerate(user_ids):
        member = db.query(models.CompanyMember).filter(
            models.CompanyMember.company_id == company_id,
            models.CompanyMember.user_id == user_id
        ).first()
        if member:
            member.sort_order = index
    db.commit()

def update_company_member_status(db: Session, company_id: str, user_id: str, is_active: bool):
    member = db.query(models.CompanyMember).filter(
        models.CompanyMember.company_id == company_id,
        models.CompanyMember.user_id == user_id
    ).first()
    
    if member:
        member.is_active = is_active
        
        # If deactivating, check if this company was the user's default company
        if not is_active:
            user = db.query(models.User).filter(models.User.id == member.user_id).first()
            if user and user.default_company_id and str(user.default_company_id) == str(member.company_id):
                # Find the next active membership
                next_active = db.query(models.CompanyMember).filter(
                    models.CompanyMember.user_id == member.user_id,
                    models.CompanyMember.company_id != member.company_id,
                    models.CompanyMember.is_active == True
                ).first()
                user.default_company_id = next_active.company_id if next_active else None
                
        db.commit()
        db.refresh(member)
        _invalidate_company_rates(company_id)
    return member

def update_company_member(db: Session, company_id: Any, user_id: Any, member_update: schemas.CompanyMemberUpdate):
    # Ensure UUIDs
    from uuid import UUID
    try:
        cid = UUID(str(company_id)) if not isinstance(company_id, UUID) else company_id
        uid = UUID(str(user_id)) if not isinstance(user_id, UUID) else user_id
    except ValueError:
        return None

    member = db.query(models.CompanyMember).filter(
        models.CompanyMember.company_id == cid,
        models.CompanyMember.user_id == uid
    ).first()
    
    if member:
        # Use model_dump(exclude_unset=True)
        update_data = member_update.model_dump(exclude_unset=True, by_alias=False)
        
        for key, value in update_data.items():
            if value is None and key in ["role", "is_active"]:
                continue # Hardening: do not allow setting role or is_active to NULL

            if key == "role" and value:
                try:
                    setattr(member, key, models.CompanyRole(value))
                except ValueError:
                    print(f"WARNING: Invalid company role value: {value}")
            else:
                setattr(member, key, value)
            if key in ["settings", "rates_config"]:
                 flag_modified(member, key)
                 
        # Protection: if is_active is set to False, reassign user's default_company_id
        if update_data.get("is_active") == False:
            user = db.query(models.User).filter(models.User.id == member.user_id).first()
            if user and user.default_company_id and str(user.default_company_id) == str(member.company_id):
                next_active = db.query(models.CompanyMember).filter(
                    models.CompanyMember.user_id == member.user_id,
                    models.CompanyMember.company_id != member.company_id,
                    models.CompanyMember.is_active == True
                ).first()
                user.default_company_id = next_active.company_id if next_active else None

        db.commit()
        db.refresh(member)
        _invalidate_company_rates(company_id)
    return member


def delete_work_log(db: Session, work_log_id: str):
    db_work_log = db.query(models.WorkLog).filter(models.WorkLog.id == work_log_id).first()
    if db_work_log:
        db.delete(db_work_log)
        db.commit()
    return db_work_log

# UserDevice management removed. Sessions are now managed via UserSession in auth.py


def create_company(db: Session, company: schemas.CompanyCreate):
    db_company = models.Company(**company.dict())
    db.add(db_company)
    db.commit()
    db.refresh(db_company)
    return db_company

def get_company(db: Session, company_id: str):
    return db.query(models.Company).filter(models.Company.id == company_id).first()

def update_company(db: Session, company_id: str, company: schemas.CompanyUpdate):
    db_company = db.query(models.Company).filter(models.Company.id == company_id).first()
    if db_company:
        # Use model_dump(by_alias=False) to ensure we get snake_case property names for setattr
        update_data = company.model_dump(exclude_unset=True, by_alias=False)
        print(f"DEBUG: Updating company {company_id} with data: {update_data}")
        for key, value in update_data.items():
            if hasattr(db_company, key):
                setattr(db_company, key, value)
                if key in ["settings", "tax_config", "worklog_definitions"]:
                    flag_modified(db_company, key)
            else:
                print(f"WARNING: Unknown field {key} for Company update")
        db.commit()
        db.refresh(db_company)
    return db_company

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
                continue # Hardening: do not allow setting role or is_active to NULL

            if key == "role" and value:
                # Convert string role to UserRole enum
                try:
                    setattr(db_user, key, models.UserRole(value))
                except ValueError:
                    print(f"WARNING: Invalid role value: {value}")
            else:
                setattr(db_user, key, value)
        db.commit()
        db.refresh(db_user)
    return db_user


# ─── Module & Subscription CRUD ────────────────────────────────────────────

from datetime import datetime as _dt

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

def get_subscriptions(db: Session, company_id: str = None, user_id: str = None):
    """Lista suscripciones filtrables por empresa o usuario."""
    query = db.query(models.ModuleSubscription)
    if company_id:
        query = query.filter(models.ModuleSubscription.company_id == company_id)
    if user_id:
        query = query.filter(models.ModuleSubscription.user_id == user_id)
    return query.order_by(models.ModuleSubscription.created_at.desc()).all()

def create_subscription(db: Session, data: schemas.ModuleSubscriptionCreate):
    """Crea una suscripción. Valida que solo company_id O user_id esté presente."""
    if data.company_id and data.user_id:
        raise ValueError("Una suscripción no puede tener company_id y user_id a la vez.")
    if not data.company_id and not data.user_id:
        raise ValueError("Una suscripción debe tener company_id o user_id.")

    db_sub = models.ModuleSubscription(
        module_id=data.module_id,
        company_id=data.company_id,
        user_id=data.user_id,
        scope=models.SubscriptionScope(data.scope),
        status=models.SubscriptionStatus(data.status),
        expires_at=data.expires_at,
        notes=data.notes
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

def user_has_module(db: Session, user_id: str, company_id: Optional[str], code_name: str) -> bool:
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
    user_sub = db.query(models.ModuleSubscription).filter(
        models.ModuleSubscription.user_id == user_id,
        models.ModuleSubscription.module_id == module.id,
        models.ModuleSubscription.status.in_(active_statuses),
        or_(
            models.ModuleSubscription.expires_at.is_(None),
            models.ModuleSubscription.expires_at > now
        )
    ).first()

    if user_sub:
        return True

    # 2. Suscripción de empresa
    if company_id:
        company_sub = db.query(models.ModuleSubscription).filter(
            models.ModuleSubscription.company_id == company_id,
            models.ModuleSubscription.module_id == module.id,
            models.ModuleSubscription.status.in_(active_statuses),
            or_(
                models.ModuleSubscription.expires_at.is_(None),
                models.ModuleSubscription.expires_at > now
            )
        ).first()
        if company_sub:
            return True

    return False

