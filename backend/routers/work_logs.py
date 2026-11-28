from datetime import date, timedelta
from uuid import UUID

import access_policy
import auth
import crud
import models
import schemas
from access_policy import PolicyError
from contracts import MissingWorklogDatesError, MissingWorklogUnitError
from database import get_db
from fastapi import APIRouter, Body, Depends, HTTPException, Query, Response
from sqlalchemy.orm import Session

from routers import deps

router = APIRouter(prefix="/work-logs", tags=["work-logs"])

_COMPANY_VIEW_ROLES = (access_policy.ROLE_MANAGER, access_policy.ROLE_PLATFORM_ADMIN)

# Rango permitido para GET /work-logs/summary: desde 2000-01-01 hasta hoy + 730 dias
_SUMMARY_MIN_DATE = date(2000, 1, 1)
_SUMMARY_MAX_AHEAD_DAYS = 730


def record_impersonation_audit(db: Session, current_user: models.User, action: str, extra_data: dict = None):
    """Retirada (R-AUD-26): las escrituras de turnos durante suplantacion ya no se registran."""
    return None


@router.post("", response_model=schemas.WorkLogResponse)
def create_work_log(
    work_log: schemas.WorkLogCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Create a new work log entry.
    """
    ctx = deps.authorize(db, current_user, work_log.company_id, min_role=access_policy.ROLE_WORKER)

    # T2: worker solo en empresa autonoma y para si mismo; manager y PA siempre
    access_policy.can_write_work_log(
        role=ctx.role, is_managed=ctx.is_managed, is_owner=str(work_log.user_id) == str(current_user.id)
    )
    # T1: el usuario del turno debe ser miembro activo de la empresa (tambien para el PA)
    deps.require_active_member(db, work_log.user_id, work_log.company_id)

    try:
        new_log = crud.create_work_log(db=db, work_log=work_log)
        return new_log
    except (MissingWorklogUnitError, MissingWorklogDatesError):
        raise
    except (crud.MissingRateError, crud.UnknownWorkLogTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/bulk", response_model=schemas.WorkLogResponse)
def create_work_log_bulk(
    work_log_bulk: schemas.WorkLogBulkCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Create multiple work log entries at once (for managers).
    """
    deps.authorize(db, current_user, work_log_bulk.company_id, min_role=access_policy.ROLE_MANAGER)

    # T1: un solo usuario invalido rechaza todo el lote antes de crear ningun turno
    for user_id in work_log_bulk.user_ids:
        deps.require_active_member(db, user_id, work_log_bulk.company_id)

    try:
        logs = crud.create_work_log_bulk(db=db, work_log_bulk=work_log_bulk)
        return logs  # Returns the first one created as a representative
    except (MissingWorklogUnitError, MissingWorklogDatesError):
        raise
    except (crud.MissingRateError, crud.UnknownWorkLogTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


def _resolve_work_log_scope(
    db: Session,
    current_user: models.User,
    company_id: UUID | None,
    user_id: UUID | None,
    start_date: date | None,
    end_date: date | None,
) -> tuple[UUID | None, UUID | None, bool]:
    """
    Resuelve la visibilidad de turnos del usuario actual.
    Devuelve (empresa objetivo, usuario filtrado o None para todos, solo empresas activas).
    Compartido por GET /work-logs y GET /work-logs/summary.
    """
    only_active_companies = False

    if deps.acting_platform_admin(current_user):
        # Admin can do anything
        target_company_id = company_id or getattr(current_user, "active_company_id", None)
        if user_id:
            final_user_id = user_id
        elif not company_id and not start_date and not end_date:
            final_user_id = current_user.id  # Default to self if ABSOLUTELY no filters
        else:
            final_user_id = None
    else:
        effective_company_id = company_id or getattr(current_user, "active_company_id", None)
        if effective_company_id:
            ctx = deps.authorize(db, current_user, effective_company_id, min_role=access_policy.ROLE_WORKER)
            target_company_id = ctx.company_id
            if ctx.role in _COMPANY_VIEW_ROLES:
                final_user_id = user_id  # None: todos los usuarios de la empresa
            elif user_id and user_id != current_user.id:
                raise PolicyError(403, access_policy.MSG_FORBIDDEN)
            else:
                final_user_id = current_user.id
        else:
            target_company_id = None
            if user_id and user_id != current_user.id:
                raise PolicyError(403, access_policy.MSG_FORBIDDEN)
            final_user_id = current_user.id
            only_active_companies = True

    return target_company_id, final_user_id, only_active_companies


@router.get("", response_model=list[schemas.WorkLogResponse])
def read_work_logs(
    response: Response,
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=2000),  # Tope [P-12]: las sumas se piden a /work-logs/summary
    user_id: UUID = None,  # Optional filter via query param
    company_id: UUID = None,  # Optional filter via query param
    start_date: date = None,
    end_date: date = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Retrieve work logs.
    Users can only see their own. Managers (and platform admins) see the whole company and can filter by user_id.
    El parte diario de empresa para el worker es GET /companies/{id}/daily-report.
    La cabecera X-Total-Count indica el total de turnos que cumplen los filtros (sin skip/limit).
    """
    target_company_id, final_user_id, only_active_companies = _resolve_work_log_scope(
        db, current_user, company_id, user_id, start_date, end_date
    )

    filters = {
        "user_id": str(final_user_id) if final_user_id else None,
        "company_id": str(target_company_id) if target_company_id else None,
        "start_date": start_date,
        "end_date": end_date,
        "only_active_companies": only_active_companies,
    }
    work_logs = crud.get_work_logs(db, skip=skip, limit=limit, **filters)
    response.headers["X-Total-Count"] = str(crud.count_work_logs(db, **filters))
    return work_logs


def _validate_summary_date_range(start_date: date, end_date: date) -> None:
    """Valida coherencia y limites del rango de fechas para resumenes e informes."""
    if start_date > end_date:
        raise HTTPException(status_code=422, detail="start_date no puede ser posterior a end_date")
    max_end_date = date.today() + timedelta(days=_SUMMARY_MAX_AHEAD_DAYS)
    if not (
        _SUMMARY_MIN_DATE <= start_date <= max_end_date and _SUMMARY_MIN_DATE <= end_date <= max_end_date
    ):
        raise HTTPException(
            status_code=422,
            detail=f"Las fechas deben estar entre {_SUMMARY_MIN_DATE.isoformat()} y {max_end_date.isoformat()}",
        )


@router.get("/summary", response_model=schemas.WorkLogSummaryResponse)
def get_work_logs_summary(
    start_date: date,
    end_date: date,
    company_id: UUID | None = None,
    user_id: UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Agregados de turnos en un rango de fechas: totales, por tipo, por dia y por usuario.
    Misma visibilidad que GET /work-logs: los workers solo obtienen sus propios datos.
    """
    _validate_summary_date_range(start_date, end_date)

    target_company_id, final_user_id, only_active_companies = _resolve_work_log_scope(
        db, current_user, company_id, user_id, start_date, end_date
    )
    if target_company_id is None and deps.acting_platform_admin(current_user):
        # Sin empresa el PA agregaria toda la plataforma (con importes y emails): se exige empresa explicita
        raise HTTPException(status_code=422, detail="company_id es obligatorio para el administrador de plataforma")

    summary = crud.get_work_log_summary(
        db,
        company_id=str(target_company_id) if target_company_id else None,
        user_id=str(final_user_id) if final_user_id else None,
        start_date=start_date,
        end_date=end_date,
        only_active_companies=only_active_companies,
    )
    return schemas.WorkLogSummaryResponse(**summary)


@router.get("/reports", response_model=schemas.WorkLogReportResponse)
def get_work_logs_report(
    start_date: date,
    end_date: date,
    company_id: UUID | None = None,
    user_id: UUID | None = None,
    skip: int = Query(0, ge=0),
    limit: int = Query(500, ge=1, le=2000),
    include_logs: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Datos del modulo de pago Informes (R-MOD-15, R-ACC-24): devuelve el resumen y las filas
    paginadas exigiendo suscripcion vigente al modulo 'reports' en la empresa (salvo PA actuando).
    """
    _validate_summary_date_range(start_date, end_date)

    effective_company_id = company_id or getattr(current_user, "active_company_id", None)
    if effective_company_id is None:
        if deps.acting_platform_admin(current_user):
            raise HTTPException(status_code=422, detail="company_id es obligatorio para el administrador de plataforma")
        raise PolicyError(403, access_policy.MSG_NO_ACCESS)

    ctx = deps.authorize(
        db,
        current_user,
        effective_company_id,
        min_role=access_policy.ROLE_WORKER,
        module="reports",
    )

    if ctx.role in _COMPANY_VIEW_ROLES:
        final_user_id = user_id
    elif user_id and str(user_id) != str(current_user.id):
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)
    else:
        final_user_id = current_user.id

    summary = crud.get_work_log_summary(
        db,
        company_id=str(ctx.company_id),
        user_id=str(final_user_id) if final_user_id else None,
        start_date=start_date,
        end_date=end_date,
        only_active_companies=False,
    )

    if include_logs:
        filters = {
            "user_id": str(final_user_id) if final_user_id else None,
            "company_id": str(ctx.company_id),
            "start_date": start_date,
            "end_date": end_date,
            "only_active_companies": False,
        }
        items = crud.get_work_logs(db, skip=skip, limit=limit, **filters)
        total = crud.count_work_logs(db, **filters)
    else:
        items = []
        total = int(summary["totals"]["logs_count"])

    return schemas.WorkLogReportResponse(
        items=items,
        total=total,
        summary=schemas.WorkLogSummaryResponse(**summary),
    )


@router.get("/billing-summary", response_model=list[schemas.BillingSummaryItemResponse])
def get_billing_summary(
    company_id: UUID,
    start_date: date,
    end_date: date,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Get billing summary for a company, aggregated by user and work log type, using the PostgreSQL database function.
    Only managers of the company or platform admins can access this.
    """
    deps.authorize(db, current_user, company_id, min_role=access_policy.ROLE_MANAGER)

    from sqlalchemy import text

    query = text("""
        SELECT user_id, first_name, last_name, email, type,
               total_hours, total_net, total_gross, unique_days, logs_count,
               is_active, user_total_net
        FROM get_billing_summary(:company_id, :start_date, :end_date)
    """)
    result = db.execute(
        query, {"company_id": str(company_id), "start_date": start_date, "end_date": end_date}
    ).fetchall()

    summary = []
    for row in result:
        summary.append(
            schemas.BillingSummaryItemResponse(
                user_id=row.user_id,
                first_name=row.first_name,
                last_name=row.last_name,
                email=row.email,
                type=row.type,
                total_hours=float(row.total_hours or 0.0),
                total_net=float(row.total_net or 0.0),
                total_gross=float(row.total_gross or 0.0),
                unique_days=int(row.unique_days or 0),
                logs_count=int(row.logs_count or 0),
                is_active=bool(row.is_active),
                user_total_net=float(row.user_total_net or 0.0),
            )
        )
    return summary


def _work_log_not_found(current_user: models.User) -> Exception:
    """Anti-enumeracion [P-5]: quien no es PA recibe el mismo 403 para un turno inexistente que para uno ajeno."""
    if deps.acting_platform_admin(current_user):
        return HTTPException(status_code=404, detail="Work log not found")
    return PolicyError(403, access_policy.MSG_NO_ACCESS)


def _authorize_work_log_write(db: Session, current_user: models.User, log: models.WorkLog) -> str:
    """Valida que el usuario puede escribir sobre el turno y devuelve su rol efectivo."""
    is_owner = str(log.user_id) == str(current_user.id)
    if log.company_id is None:
        # Turno sin empresa: solo el PA o el propietario
        if deps.acting_platform_admin(current_user):
            return access_policy.ROLE_PLATFORM_ADMIN
        if not is_owner:
            raise PolicyError(403, access_policy.MSG_FORBIDDEN)
        return access_policy.ROLE_WORKER

    ctx = deps.authorize(db, current_user, log.company_id, min_role=access_policy.ROLE_WORKER)
    access_policy.can_write_work_log(role=ctx.role, is_managed=ctx.is_managed, is_owner=is_owner)
    return ctx.role


@router.delete("/{work_log_id}")
def delete_work_log(
    work_log_id: UUID, db: Session = Depends(get_db), current_user: models.User = Depends(auth.get_verified_user)
):
    log = db.query(models.WorkLog).filter(models.WorkLog.id == work_log_id).first()
    if not log:
        raise _work_log_not_found(current_user)

    _authorize_work_log_write(db, current_user, log)

    company_id = log.company_id
    crud.delete_work_log(db, str(work_log_id), company_id=company_id)
    if company_id:
        crud.invalidate_dashboard_summary(company_id)
    return {"ok": True}


@router.post("/{work_log_id}/recalculate-preview", response_model=schemas.WorkLogRecalculatePreviewResponse)
def preview_work_log_recalculation(
    work_log_id: UUID,
    work_log: schemas.WorkLogUpdate | None = Body(default=None),
    apply_to_group: bool = False,
    recalculate_with_current_rates: bool = True,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    """
    Previsualiza el importe actual frente al nuevo antes de confirmar un recalculo con tarifa vigente
    o un cambio de tipo de turno (R-TUR-20, R-TUR-21), sin persistir cambios.
    """
    log = db.query(models.WorkLog).filter(models.WorkLog.id == work_log_id).first()
    if not log:
        raise _work_log_not_found(current_user)

    role = _authorize_work_log_write(db, current_user, log)

    if apply_to_group and role not in _COMPANY_VIEW_ROLES:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    if recalculate_with_current_rates and role not in _COMPANY_VIEW_ROLES:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    payload = work_log or schemas.WorkLogUpdate()
    if (payload.user_id is not None and str(payload.user_id) != str(log.user_id)) or (
        payload.company_id is not None and str(payload.company_id) != str(log.company_id)
    ):
        raise PolicyError(422, "No se puede cambiar la empresa ni el usuario de un turno")

    try:
        preview = crud.preview_work_log_recalculation(
            db,
            str(work_log_id),
            payload,
            company_id=log.company_id,
            apply_to_group=apply_to_group,
            recalculate_with_current_rates=recalculate_with_current_rates,
        )
    except (MissingWorklogUnitError, MissingWorklogDatesError):
        raise
    except (crud.MissingRateError, crud.UnknownWorkLogTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    if preview is None:
        raise _work_log_not_found(current_user)

    return schemas.WorkLogRecalculatePreviewResponse(**preview)


@router.put("/{work_log_id}", response_model=schemas.WorkLogResponse)
def update_work_log(
    work_log_id: UUID,
    work_log: schemas.WorkLogUpdate,
    apply_to_group: bool = False,
    recalculate_with_current_rates: bool = False,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(auth.get_verified_user),
):
    log = db.query(models.WorkLog).filter(models.WorkLog.id == work_log_id).first()
    if not log:
        raise _work_log_not_found(current_user)

    role = _authorize_work_log_write(db, current_user, log)

    # Only managers/admins can apply to group
    if apply_to_group and role not in _COMPANY_VIEW_ROLES:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    # R-TUR-20: recalcular con la tarifa vigente solo lo piden manager y PA
    if recalculate_with_current_rates and role not in _COMPANY_VIEW_ROLES:
        raise PolicyError(403, access_policy.MSG_FORBIDDEN)

    # R-TUR-02: empresa y usuario de un turno no cambian; se aceptan solo si coinciden con los actuales
    if (work_log.user_id is not None and str(work_log.user_id) != str(log.user_id)) or (
        work_log.company_id is not None and str(work_log.company_id) != str(log.company_id)
    ):
        raise PolicyError(422, "No se puede cambiar la empresa ni el usuario de un turno")

    try:
        updated_log = crud.update_work_log(
            db,
            str(work_log_id),
            work_log,
            company_id=log.company_id,
            apply_to_group=apply_to_group,
            recalculate_with_current_rates=recalculate_with_current_rates,
        )
    except (MissingWorklogUnitError, MissingWorklogDatesError):
        raise
    except (crud.MissingRateError, crud.UnknownWorkLogTypeError) as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))
    if updated_log is None:
        raise _work_log_not_found(current_user)

    return updated_log
