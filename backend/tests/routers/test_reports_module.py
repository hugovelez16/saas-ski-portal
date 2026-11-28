"""
Pruebas HTTP del endpoint dedicado de Informes (GET /work-logs/reports, R-MOD-15, R-ACC-24)
y verificacion de que turnos normales y billing basico no exigen los modulos reports ni billing.
"""

from datetime import UTC, date, datetime, timedelta

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

REPORTS_CODE = "reports"
BILLING_CODE = "billing"
DAY = date(2026, 2, 15)
REPORT_PARAMS = {"start_date": "2026-02-01", "end_date": "2026-02-28"}
PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}
MSG_NO_REPORTS = "Tu cuenta no tiene acceso al módulo 'reports'. Contacta con el administrador."


def _ensure_module(db, code_name: str, *, name: str = "Informes", is_active: bool = True) -> models.AppModule:
    module = db.query(models.AppModule).filter(models.AppModule.code_name == code_name).first()
    if module is None:
        module = models.AppModule(code_name=code_name, name=name, is_active=is_active)
        db.add(module)
    else:
        module.is_active = is_active
    db.commit()
    db.refresh(module)
    return module


def _subscribe_company(
    db,
    company: models.Company,
    code_name: str = REPORTS_CODE,
    *,
    status: models.SubscriptionStatus = models.SubscriptionStatus.active,
    expires_at: datetime | None = None,
    module_active: bool = True,
) -> models.ModuleSubscription:
    module = _ensure_module(db, code_name, is_active=module_active)
    sub = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=status,
        expires_at=expires_at,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def _setup(db, *, subscribed: bool = False):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    other_worker = make_user(db)
    make_member(db, other_worker, company, role="worker")
    if subscribed:
        _subscribe_company(db, company)
    return company, manager, worker, other_worker


def test_worker_without_reports_module_gets_403(client, db):
    company, _, worker, _ = _setup(db, subscribed=False)
    make_work_log(db, worker, company, start_date=DAY)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_REPORTS


def test_manager_without_reports_module_gets_403(client, db):
    company, manager, worker, _ = _setup(db, subscribed=False)
    make_work_log(db, worker, company, start_date=DAY)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_REPORTS


@pytest.mark.parametrize(
    "sub_kwargs",
    [
        pytest.param({"status": models.SubscriptionStatus.cancelled}, id="cancelled"),
        pytest.param({"status": models.SubscriptionStatus.expired}, id="expired"),
        pytest.param({"expires_at": datetime.now(UTC) - timedelta(days=1)}, id="past_expiry"),
        pytest.param({"module_active": False}, id="inactive_module"),
    ],
)
def test_non_vigente_reports_subscription_gets_403(client, db, sub_kwargs):
    company, manager, _, _ = _setup(db, subscribed=False)
    _subscribe_company(db, company, **sub_kwargs)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_REPORTS


def test_suspended_company_with_reports_module_gets_403(client, db):
    company, manager, _, _ = _setup(db, subscribed=True)
    company.is_active = False
    db.commit()
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 403, resp.text


def test_worker_with_reports_module_sees_only_own_logs(client, db):
    company, manager, worker, other_worker = _setup(db, subscribed=True)
    own_log = make_work_log(db, worker, company, start_date=DAY, net_amount=45.0)
    other_log = make_work_log(db, other_worker, company, start_date=DAY, net_amount=60.0)
    manager_log = make_work_log(db, manager, company, start_date=DAY, net_amount=80.0)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 1
    assert [item["id"] for item in body["items"]] == [str(own_log.id)]
    assert body["summary"]["totals"]["logsCount"] == 1
    assert body["summary"]["totals"]["totalNet"] == pytest.approx(45.0)
    assert str(other_log.id) not in resp.text
    assert str(manager_log.id) not in resp.text


def test_worker_with_reports_module_cannot_filter_another_user(client, db):
    company, _, worker, other_worker = _setup(db, subscribed=True)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs/reports", params={**REPORT_PARAMS, "user_id": str(other_worker.id)})

    assert resp.status_code == 403, resp.text


def test_manager_with_reports_module_sees_company_and_can_filter_user(client, db):
    company, manager, worker, other_worker = _setup(db, subscribed=True)
    _subscribe_company(
        db,
        make_company(db),
        status=models.SubscriptionStatus.trial,
    )
    log_w = make_work_log(db, worker, company, start_date=DAY, net_amount=40.0)
    log_o = make_work_log(db, other_worker, company, start_date=DAY, net_amount=60.0)
    log_m = make_work_log(db, manager, company, start_date=DAY, net_amount=20.0)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp_all = client.get("/work-logs/reports", params=REPORT_PARAMS)
    assert resp_all.status_code == 200, resp_all.text
    body_all = resp_all.json()
    assert body_all["total"] == 3
    assert {item["id"] for item in body_all["items"]} == {str(log_w.id), str(log_o.id), str(log_m.id)}
    assert body_all["summary"]["totals"]["logsCount"] == 3
    assert body_all["summary"]["totals"]["totalNet"] == pytest.approx(120.0)

    resp_filtered = client.get("/work-logs/reports", params={**REPORT_PARAMS, "user_id": str(worker.id)})
    assert resp_filtered.status_code == 200, resp_filtered.text
    body_filtered = resp_filtered.json()
    assert body_filtered["total"] == 1
    assert [item["id"] for item in body_filtered["items"]] == [str(log_w.id)]

    resp_summary_only = client.get("/work-logs/reports", params={**REPORT_PARAMS, "include_logs": "false"})
    assert resp_summary_only.status_code == 200, resp_summary_only.text
    assert resp_summary_only.json()["items"] == []
    assert resp_summary_only.json()["total"] == 3
    assert resp_summary_only.json()["summary"]["totals"]["logsCount"] == 3


def test_manager_with_trial_reports_subscription_gets_200(client, db):
    company, manager, worker, _ = _setup(db, subscribed=False)
    _subscribe_company(db, company, status=models.SubscriptionStatus.trial)
    make_work_log(db, worker, company, start_date=DAY)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 200, resp.text
    assert resp.json()["total"] == 1


def test_pa_acting_gets_200_without_reports_module(client, db):
    company, _, worker, other_worker = _setup(db, subscribed=False)
    log_w = make_work_log(db, worker, company, start_date=DAY, net_amount=50.0)
    log_o = make_work_log(db, other_worker, company, start_date=DAY, net_amount=70.0)
    pa = make_user(db, role="admin")
    as_user(client, pa, claims=PA_CLAIMS)

    resp = client.get("/work-logs/reports", params={**REPORT_PARAMS, "company_id": str(company.id)})

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["total"] == 2
    assert {item["id"] for item in body["items"]} == {str(log_w.id), str(log_o.id)}
    assert body["summary"]["totals"]["totalNet"] == pytest.approx(120.0)


def test_pa_acting_without_company_id_gets_422(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims=PA_CLAIMS)

    resp = client.get("/work-logs/reports", params=REPORT_PARAMS)

    assert resp.status_code == 422


def test_pa_view_as_respects_reports_module_and_worker_scope(client, db):
    company, _, worker, other_worker = _setup(db, subscribed=False)
    pa = make_user(db, role="admin")
    make_work_log(db, worker, company, start_date=DAY)
    make_work_log(db, other_worker, company, start_date=DAY)
    pa_log = make_work_log(db, pa, company, start_date=DAY)

    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})
    resp_forbidden = client.get("/work-logs/reports", params=REPORT_PARAMS)
    assert resp_forbidden.status_code == 403

    _subscribe_company(db, company)
    resp_worker = client.get("/work-logs/reports", params=REPORT_PARAMS)
    assert resp_worker.status_code == 200, resp_worker.text
    assert [item["id"] for item in resp_worker.json()["items"]] == [str(pa_log.id)]


def test_regular_work_logs_and_summary_keep_working_without_reports_module(client, db):
    company, manager, worker, _ = _setup(db, subscribed=False)
    make_work_log(db, worker, company, start_date=DAY, net_amount=35.0)

    for user, claims in ((worker, WORKER_CLAIMS), (manager, MANAGER_CLAIMS)):
        as_user(client, user, company, claims=claims)
        resp_list = client.get("/work-logs", params={"company_id": str(company.id)})
        resp_summary = client.get("/work-logs/summary", params={**REPORT_PARAMS, "company_id": str(company.id)})
        assert resp_list.status_code == 200, resp_list.text
        assert resp_summary.status_code == 200, resp_summary.text


def test_billing_summary_does_not_require_billing_module(client, db, monkeypatch):
    """La facturacion basica no es un modulo de pago (R-MOD-04, R-TAR-25)."""
    company, manager, _, _ = _setup(db, subscribed=False)
    _ensure_module(db, BILLING_CODE, name="Facturacion", is_active=True)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    class _FakeResult:
        def fetchall(self):
            return []

    original_execute = db.execute

    def _selective_execute(statement, *args, **kwargs):
        if "get_billing_summary" in str(statement):
            return _FakeResult()
        return original_execute(statement, *args, **kwargs)

    monkeypatch.setattr(db, "execute", _selective_execute)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(company.id), "start_date": "2026-02-01", "end_date": "2026-02-28"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == []
