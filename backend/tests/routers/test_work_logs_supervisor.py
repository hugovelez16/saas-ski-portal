"""
Pruebas HTTP de la vista de supervisor de GET /work-logs (PR-03): manager que ve la empresa,
worker con modulo worker_daily_report y filtros por empresa y usuario.

Los casos marcados con `# PR-03:` describen un comportamiento que cambia respecto a la
expectativa anterior: la empresa efectiva es la explicita o la del claim `cid` del token.
"""

from datetime import date

import models

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

LOG_DATE = date(2026, 7, 14)
MODULE_CODE = "worker_daily_report"


def _ids(resp):
    return {item["id"] for item in resp.json()}


def _ensure_module(db, code_name: str) -> models.AppModule:
    module = db.query(models.AppModule).filter(models.AppModule.code_name == code_name).first()
    if not module:
        module = models.AppModule(code_name=code_name, name="Worker Daily Report", is_active=True)
        db.add(module)
        db.commit()
        db.refresh(module)
    return module


def _setup(db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    log_manager = make_work_log(db, manager, company, start_date=LOG_DATE)
    log_worker = make_work_log(db, worker, company, start_date=LOG_DATE)
    return company, manager, worker, log_manager, log_worker


def test_supervisor_with_explicit_company_id(client, db):
    """
    If company_id is explicitly passed, a manager should see logs for all users.
    """
    company, manager, _, log_manager, log_worker = _setup(db)
    as_user(client, manager, company)

    resp = client.get("/work-logs", params={"company_id": str(company.id)})

    assert resp.status_code == 200, resp.text
    log_ids = _ids(resp)
    assert str(log_manager.id) in log_ids
    assert str(log_worker.id) in log_ids


def test_supervisor_with_implicit_company_id(client, db):
    """
    If company_id is NOT passed, the effective company is the one in the token (cid).
    """
    company, manager, _, log_manager, log_worker = _setup(db)
    as_user(client, manager, company)

    resp = client.get("/work-logs")

    # PR-03: con cid en el token la empresa es efectiva aunque no se pase company_id; el manager ve
    # los turnos de todos los usuarios de la empresa (antes solo veia los propios).
    assert resp.status_code == 200, resp.text
    log_ids = _ids(resp)
    assert str(log_manager.id) in log_ids
    assert str(log_worker.id) in log_ids


def test_worker_with_daily_report_module_explicit_company_id(client, db):
    """
    Check if a worker can read company logs if worker_daily_report module is subscribed,
    but only when company_id is explicitly provided.
    """
    company, _, worker, log_manager, log_worker = _setup(db)

    # Check if a module named "worker_daily_report" exists in app_modules (or create one if it doesn't)
    module = _ensure_module(db, MODULE_CODE)

    # Add a models.ModuleSubscription for the company to that module
    subscription = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        scope=models.SubscriptionScope.company,
        status=models.SubscriptionStatus.active,
    )
    db.add(subscription)
    db.commit()

    # Call GET /work-logs as worker passing company_id explicitly.
    # Verify they receive all logs (both log_manager and log_worker)
    as_user(client, worker, company)
    resp_explicit = client.get("/work-logs", params={"company_id": str(company.id)})
    assert resp_explicit.status_code == 200, resp_explicit.text
    log_ids_explicit = _ids(resp_explicit)
    assert str(log_manager.id) in log_ids_explicit
    assert str(log_worker.id) in log_ids_explicit

    # Call GET /work-logs as worker without company_id (cid del token = empresa efectiva).
    # PR-03: el modulo worker_daily_report mantiene la vista de empresa tambien con cid en el token;
    # antes solo veia sus propios turnos.
    resp_implicit = client.get("/work-logs")
    assert resp_implicit.status_code == 200, resp_implicit.text
    log_ids_implicit = _ids(resp_implicit)
    assert str(log_manager.id) in log_ids_implicit
    assert str(log_worker.id) in log_ids_implicit
