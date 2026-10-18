"""
Resumen del dashboard de empresa (GET /companies/{cid}/dashboard-summary) por HTTP.

Los casos marcados con `# PR-03:` cambian respecto al codigo anterior.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import models
import pytest

from tests.factories import as_user

MSG_NO_ACCESS = "No tienes acceso a esta empresa"

MANAGER_CLAIMS = {"role": "manager"}


def _seed(db):
    """Datos de partida del dashboard: una empresa, cuatro usuarios, tres miembros y dos turnos de hoy."""
    company = models.Company(
        name=f"Test Dashboard Company {uuid.uuid4().hex[:6]}",
        worklog_definitions={
            "particular": {"unit": "hours", "label": "Particular"},
            "tutorial": {"unit": "days", "label": "Tutorial"},
        },
    )
    db.add(company)
    db.flush()

    manager_user = models.User(
        email=f"mgr_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="hashed_pass_test",
        first_name="Carlos",
        last_name="Manager",
        role=models.UserRole.user,
    )
    worker_user1 = models.User(
        email=f"w1_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="hashed_pass_test",
        first_name="Ana",
        last_name="Monitora",
        role=models.UserRole.user,
    )
    worker_user2 = models.User(
        email=f"w2_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="hashed_pass_test",
        first_name="David",
        last_name="Profesor",
        role=models.UserRole.user,
    )
    unauthorized_user = models.User(
        email=f"unauth_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="hashed_pass_test",
        first_name="Pedro",
        last_name="Ajeno",
        role=models.UserRole.user,
    )
    db.add_all([manager_user, worker_user1, worker_user2, unauthorized_user])
    db.flush()

    # Memberships con sort_order estricto
    mem_manager = models.CompanyMember(
        user_id=manager_user.id,
        company_id=company.id,
        role=models.CompanyRole.manager,
        is_active=True,
        sort_order=1,
    )
    mem_worker1 = models.CompanyMember(
        user_id=worker_user1.id,
        company_id=company.id,
        role=models.CompanyRole.worker,
        is_active=True,
        sort_order=10,
    )
    mem_worker2 = models.CompanyMember(
        user_id=worker_user2.id,
        company_id=company.id,
        role=models.CompanyRole.worker,
        is_active=True,
        sort_order=20,
    )
    db.add_all([mem_manager, mem_worker1, mem_worker2])
    db.flush()

    today = date.today()
    log_today_w1 = models.WorkLog(
        user_id=worker_user1.id,
        company_id=company.id,
        type="particular",
        start_date=today,
        end_date=today,
        duration=3.0,
        net_amount=75.0,
        gross_amount=90.0,
    )
    log_today_w2 = models.WorkLog(
        user_id=worker_user2.id,
        company_id=company.id,
        type="particular",
        start_date=today,
        end_date=today,
        duration=2.0,
        net_amount=50.0,
        gross_amount=60.0,
    )
    db.add_all([log_today_w1, log_today_w2])
    db.commit()

    return SimpleNamespace(
        company=company,
        manager_user=manager_user,
        worker_user1=worker_user1,
        worker_user2=worker_user2,
        unauthorized_user=unauthorized_user,
    )


@pytest.fixture
def dashboard(db):
    return _seed(db)


def test_get_dashboard_summary_metrics(client, db, dashboard):
    as_user(client, dashboard.manager_user, dashboard.company, claims=MANAGER_CLAIMS)
    today = date.today()

    resp = client.get(
        f"/companies/{dashboard.company.id}/dashboard-summary",
        params={"start_date": today.isoformat(), "end_date": today.isoformat()},
    )

    assert resp.status_code == 200, resp.text
    summary = resp.json()

    # Check today metrics
    assert summary["todayMetrics"]["todayHours"] == 5.0
    assert summary["todayMetrics"]["todayLogsCount"] == 2
    assert summary["todayMetrics"]["todayActiveMembersCount"] == 2

    # Check period metrics
    assert summary["periodMetrics"]["totalHours"] == 5.0
    assert summary["periodMetrics"]["totalNet"] == 125.0
    assert summary["periodMetrics"]["totalGross"] == 150.0

    # Check workers summary follows sort order (manager=1, worker1=10, worker2=20)
    workers = summary["workersSummary"]
    assert len(workers) == 3
    assert workers[0]["userId"] == str(dashboard.manager_user.id)
    assert workers[1]["userId"] == str(dashboard.worker_user1.id)
    assert workers[2]["userId"] == str(dashboard.worker_user2.id)


def test_unauthorized_access_denied(client, db, dashboard):
    as_user(client, dashboard.unauthorized_user, dashboard.company, claims={"role": "worker"})
    today = date.today()

    resp = client.get(
        f"/companies/{dashboard.company.id}/dashboard-summary",
        params={"start_date": today.isoformat(), "end_date": today.isoformat()},
    )

    # PR-03: sin membresia la empresa responde 403 con MSG_NO_ACCESS (mensaje de access_policy).
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS
