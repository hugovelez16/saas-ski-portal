"""
Pruebas HTTP de GET /companies/{company_id}/daily-report (PR-14, T10) y de la retirada de la vista
de empresa para el worker con modulo en GET /work-logs y GET /companies/detailed.

Decision P-14: el JSON del worker NO contiene las claves netAmount ni grossAmount (ausentes, no null).
"""

from datetime import date, time

import models

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

MODULE_CODE = "worker_daily_report"
DAY = date(2026, 1, 10)
PA_CLAIMS = {"is_admin": True}
MSG_NO_MODULE = "Tu cuenta no tiene acceso al módulo 'worker_daily_report'. Contacta con el administrador."
AMOUNT_KEYS = ("netAmount", "grossAmount")


def _ensure_module(db) -> models.AppModule:
    module = db.query(models.AppModule).filter(models.AppModule.code_name == MODULE_CODE).first()
    if module is None:
        module = models.AppModule(code_name=MODULE_CODE, name="Parte diario", is_active=True)
        db.add(module)
        db.commit()
        db.refresh(module)
    return module


def _subscribe(db, company):
    db.add(
        models.ModuleSubscription(
            module_id=_ensure_module(db).id,
            company_id=company.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
        )
    )
    db.commit()


def _setup(db, *, subscribed: bool = True):
    company = make_company(
        db,
        worklog_definitions={
            "particular": {"unit": "hours", "label": "Particular", "fields": []},
            "colectivo": {"unit": "days", "label": "Colectivo", "fields": []},
        },
    )
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    other_worker = make_user(db)
    make_member(db, other_worker, company, role="worker")
    if subscribed:
        _subscribe(db, company)
    return company, manager, worker, other_worker


def _url(company) -> str:
    return f"/companies/{company.id}/daily-report"


def _log_ids(resp) -> set[str]:
    return {item["id"] for item in resp.json()["logs"]}


def test_worker_with_module_sees_whole_company_without_amount_keys(client, db):
    company, manager, worker, other_worker = _setup(db)
    log_own = make_work_log(db, worker, company, start_date=DAY)
    log_other = make_work_log(db, other_worker, company, start_date=DAY)
    log_manager = make_work_log(db, manager, company, start_date=DAY)
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert _log_ids(resp) == {str(log_own.id), str(log_other.id), str(log_manager.id)}
    assert {m["userId"] for m in body["members"]} == {str(manager.id), str(worker.id), str(other_worker.id)}
    assert body["companyId"] == str(company.id)
    assert body["date"] == DAY.isoformat()
    for log in body["logs"]:
        for key in AMOUNT_KEYS:
            assert key not in log, f"{key} no debe aparecer en el JSON del worker"


def test_worker_response_has_no_amount_keys_anywhere(client, db):
    company, _, worker, _ = _setup(db)
    make_work_log(db, worker, company, start_date=DAY, net_amount=123.45)
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    assert "netAmount" not in resp.text
    assert "grossAmount" not in resp.text
    assert "net_amount" not in resp.text
    assert "gross_amount" not in resp.text
    assert "123.45" not in resp.text


def test_manager_with_module_gets_amount_keys(client, db):
    company, manager, worker, _ = _setup(db)
    make_work_log(db, worker, company, start_date=DAY, net_amount=40.0)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    logs = resp.json()["logs"]
    assert len(logs) == 1
    for key in AMOUNT_KEYS:
        assert key in logs[0]
    assert logs[0]["netAmount"] == 40.0


def test_pa_acting_gets_amount_keys_without_module(client, db):
    company, _, worker, _ = _setup(db, subscribed=False)
    make_work_log(db, worker, company, start_date=DAY)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    logs = resp.json()["logs"]
    assert len(logs) == 1
    for key in AMOUNT_KEYS:
        assert key in logs[0]


def test_pa_view_as_worker_gets_no_amount_keys(client, db):
    company, _, worker, _ = _setup(db)
    make_work_log(db, worker, company, start_date=DAY, net_amount=77.7)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    assert len(resp.json()["logs"]) == 1
    assert "netAmount" not in resp.text
    assert "grossAmount" not in resp.text
    assert "77.7" not in resp.text


def test_pa_view_as_manager_gets_amount_keys(client, db):
    company, _, worker, _ = _setup(db)
    make_work_log(db, worker, company, start_date=DAY)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    for key in AMOUNT_KEYS:
        assert key in resp.json()["logs"][0]


def test_worker_without_module_is_forbidden(client, db):
    company, _, worker, _ = _setup(db, subscribed=False)
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 403
    assert resp.json()["detail"] == MSG_NO_MODULE


def test_manager_without_module_is_forbidden(client, db):
    company, manager, _, _ = _setup(db, subscribed=False)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 403
    assert resp.json()["detail"] == MSG_NO_MODULE


def test_suspended_company_blocks_non_pa(client, db):
    company, manager, worker, _ = _setup(db)
    company.is_active = False
    db.commit()

    for user, role in ((worker, "worker"), (manager, "manager")):
        as_user(client, user, company, claims={"role": role})
        resp = client.get(_url(company), params={"date": DAY.isoformat()})
        assert resp.status_code == 403, resp.text


def test_other_company_member_cannot_read(client, db):
    company, _, _, _ = _setup(db)
    other_company = make_company(db)
    outsider = make_user(db)
    make_member(db, outsider, other_company, role="manager")
    _subscribe(db, other_company)
    as_user(client, outsider, other_company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 403, resp.text


def test_malformed_date_is_422(client, db):
    company, manager, _, _ = _setup(db)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": "10-01-2026"})

    assert resp.status_code == 422


def test_date_defaults_to_today(client, db):
    company, manager, worker, _ = _setup(db)
    log_today = make_work_log(db, worker, company, start_date=date.today())
    make_work_log(db, worker, company, start_date=date(2020, 1, 1))
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company))

    assert resp.status_code == 200, resp.text
    assert resp.json()["date"] == date.today().isoformat()
    assert _log_ids(resp) == {str(log_today.id)}


def test_log_crossing_midnight_appears_next_day(client, db):
    company, manager, worker, _ = _setup(db)
    log = make_work_log(
        db,
        worker,
        company,
        start_date=date(2026, 1, 9),
        end_date=date(2026, 1, 10),
        start_time=time(22, 0),
        end_time=time(2, 0),
    )
    as_user(client, manager, company, claims={"role": "manager"})

    for day in ("2026-01-09", "2026-01-10"):
        resp = client.get(_url(company), params={"date": day})
        assert resp.status_code == 200, resp.text
        assert str(log.id) in _log_ids(resp)
    resp = client.get(_url(company), params={"date": "2026-01-11"})
    assert str(log.id) not in _log_ids(resp)


def test_inactive_member_with_log_appears_as_inactive(client, db):
    company, manager, _, _ = _setup(db)
    former = make_user(db)
    make_member(db, former, company, role="worker", is_active=False)
    log = make_work_log(db, former, company, start_date=DAY)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    members = {m["userId"]: m for m in resp.json()["members"]}
    assert members[str(former.id)]["isActive"] is False
    assert str(log.id) in _log_ids(resp)


def test_work_types_expose_full_definition(client, db):
    company, manager, _, _ = _setup(db)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    assert resp.json()["workTypes"]["colectivo"] == {"label": "Colectivo", "unit": "days", "fields": []}


def test_logs_include_company_id(client, db):
    company, _, worker, _ = _setup(db)
    make_work_log(db, worker, company, start_date=DAY)
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    assert {log["companyId"] for log in resp.json()["logs"]} == {str(company.id)}


def test_logs_of_other_company_are_not_included(client, db):
    company, manager, worker, _ = _setup(db)
    other_company = make_company(db)
    make_member(db, worker, other_company, role="worker")
    foreign_log = make_work_log(db, worker, other_company, start_date=DAY)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.get(_url(company), params={"date": DAY.isoformat()})

    assert resp.status_code == 200, resp.text
    assert str(foreign_log.id) not in _log_ids(resp)


# --- Retirada de la vista de empresa del worker con modulo ---


def test_work_logs_worker_with_module_sees_only_own(client, db):
    company, _, worker, other_worker = _setup(db)
    own = make_work_log(db, worker, company, start_date=DAY)
    other = make_work_log(db, other_worker, company, start_date=DAY)
    as_user(client, worker, company, claims={"role": "worker"})

    for params in ({}, {"company_id": str(company.id)}):
        resp = client.get("/work-logs", params=params)
        assert resp.status_code == 200, resp.text
        ids = {item["id"] for item in resp.json()}
        assert str(own.id) in ids
        assert str(other.id) not in ids
