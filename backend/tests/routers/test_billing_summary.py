"""
Resumen de facturacion (GET /work-logs/billing-summary) por HTTP.

Requiere PostgreSQL: la consulta usa la funcion SQL `get_billing_summary`. Se salta sin TEST_DATABASE_URL.
Los casos marcados con `# PR-03:` cambian respecto al codigo anterior.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import models
import pytest

from tests.factories import as_user

MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}
PA_CLAIMS = {"is_admin": True}

BILLING_PARAMS = {"start_date": "2026-07-01", "end_date": "2026-07-31"}


def _seed(db):
    """Empresa con un manager, un worker con un turno de 8 horas y un platform admin."""
    company = models.Company(name=f"Test Billing Company {uuid.uuid4().hex[:6]}")
    db.add(company)
    db.flush()

    user_manager = models.User(
        email=f"manager_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Manager",
        last_name="Test",
        role=models.UserRole.user,
    )
    db.add(user_manager)
    db.flush()

    user_worker = models.User(
        email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Worker",
        last_name="Test",
        role=models.UserRole.user,
    )
    db.add(user_worker)
    db.flush()

    membership1 = models.CompanyMember(
        user_id=user_manager.id, company_id=company.id, role=models.CompanyRole.manager, is_active=True
    )
    membership2 = models.CompanyMember(
        user_id=user_worker.id,
        company_id=company.id,
        role=models.CompanyRole.worker,
        is_active=True,
        rates_config={
            "particular": {
                "base_rate": 20.0,
                "is_gross": False,
                "tax_overrides": {"deduction_ss": 0.05, "deduction_irpf": 0.15},
            }
        },
    )
    db.add(membership1)
    db.add(membership2)
    db.flush()

    log = models.WorkLog(
        user_id=user_worker.id,
        company_id=company.id,
        start_date=date(2026, 7, 14),
        end_date=date(2026, 7, 14),
        duration=8.0,
        net_amount=160.0,
        gross_amount=200.0,
        type="particular",
    )
    db.add(log)
    db.flush()

    user_admin = models.User(
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Admin",
        last_name="Test",
        role=models.UserRole.admin,
    )
    db.add(user_admin)
    db.commit()

    return SimpleNamespace(
        company=company,
        user_manager=user_manager,
        user_worker=user_worker,
        user_admin=user_admin,
    )


@pytest.fixture
def billing(db):
    return _seed(db)


@pytest.mark.postgres
def test_manager_can_access_billing_summary(client, db, billing):
    as_user(client, billing.user_manager, billing.company, claims=MANAGER_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(billing.company.id), **BILLING_PARAMS},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2

    # Find the items by user_id
    worker_item = next((x for x in body if x["userId"] == str(billing.user_worker.id)), None)
    manager_item = next((x for x in body if x["userId"] == str(billing.user_manager.id)), None)

    assert worker_item is not None
    assert worker_item["type"] == "particular"
    assert worker_item["totalHours"] == 8.0
    assert worker_item["totalNet"] == 160.0
    assert worker_item["totalGross"] == 200.0
    assert worker_item["uniqueDays"] == 1
    assert worker_item["logsCount"] == 1

    assert manager_item is not None
    assert manager_item["type"] is None
    assert manager_item["totalHours"] == 0.0
    assert manager_item["totalNet"] == 0.0
    assert manager_item["totalGross"] == 0.0
    assert manager_item["uniqueDays"] == 0
    assert manager_item["logsCount"] == 0


@pytest.mark.postgres
def test_worker_cannot_access_billing_summary(client, db, billing):
    as_user(client, billing.user_worker, billing.company, claims=WORKER_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(billing.company.id), **BILLING_PARAMS},
    )

    assert resp.status_code == 403, resp.text


@pytest.mark.postgres
def test_admin_can_access_billing_summary(client, db, billing):
    as_user(client, billing.user_admin, claims=PA_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(billing.company.id), **BILLING_PARAMS},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert len(body) >= 2
