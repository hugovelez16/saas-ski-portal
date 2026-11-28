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
    assert worker_item["isActive"] is True

    assert manager_item is not None
    assert manager_item["type"] is None
    assert manager_item["totalHours"] == 0.0
    assert manager_item["totalNet"] == 0.0
    assert manager_item["totalGross"] == 0.0
    assert manager_item["uniqueDays"] == 0
    assert manager_item["logsCount"] == 0
    assert manager_item["isActive"] is True


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


@pytest.mark.postgres
def test_billing_summary_includes_inactive_members_only_with_logs_in_period(client, db, billing):
    """R-TAR-29: miembros inactivos con turnos en el periodo se incluyen marcados como inactivos."""
    inactive_with_logs = models.User(
        email=f"inact_logs_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Inactivo",
        last_name="ConTurnos",
        role=models.UserRole.user,
    )
    inactive_without_logs = models.User(
        email=f"inact_empty_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Inactivo",
        last_name="SinTurnos",
        role=models.UserRole.user,
    )
    db.add_all([inactive_with_logs, inactive_without_logs])
    db.flush()

    db.add_all([
        models.CompanyMember(
            user_id=inactive_with_logs.id,
            company_id=billing.company.id,
            role=models.CompanyRole.worker,
            is_active=False,
        ),
        models.CompanyMember(
            user_id=inactive_without_logs.id,
            company_id=billing.company.id,
            role=models.CompanyRole.worker,
            is_active=False,
        ),
    ])
    db.add(
        models.WorkLog(
            user_id=inactive_with_logs.id,
            company_id=billing.company.id,
            start_date=date(2026, 7, 15),
            end_date=date(2026, 7, 15),
            duration=4.0,
            net_amount=80.0,
            gross_amount=100.0,
            type="particular",
        )
    )
    # Turno fuera del periodo para el inactivo sin turnos en julio
    db.add(
        models.WorkLog(
            user_id=inactive_without_logs.id,
            company_id=billing.company.id,
            start_date=date(2026, 6, 15),
            end_date=date(2026, 6, 15),
            duration=2.0,
            net_amount=40.0,
            gross_amount=50.0,
            type="particular",
        )
    )
    db.commit()

    as_user(client, billing.user_manager, billing.company, claims=MANAGER_CLAIMS)
    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(billing.company.id), **BILLING_PARAMS},
    )

    assert resp.status_code == 200, resp.text
    by_uid = {item["userId"]: item for item in resp.json()}
    assert str(inactive_with_logs.id) in by_uid
    assert by_uid[str(inactive_with_logs.id)]["isActive"] is False
    assert by_uid[str(inactive_with_logs.id)]["totalHours"] == 4.0
    assert by_uid[str(inactive_with_logs.id)]["totalGross"] == 100.0
    assert str(inactive_without_logs.id) not in by_uid


@pytest.mark.postgres
def test_billing_summary_groups_net_by_worker_and_effective_tax_set(client, db, billing):
    """R-TAR-27, R-TAR-30: el neto agrupado por trabajador y conjunto efectivo de impuestos."""
    worker2 = models.User(
        email=f"w_tax_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="dummy_password",
        first_name="Agrupado",
        last_name="Test",
        role=models.UserRole.user,
    )
    db.add(worker2)
    db.flush()
    db.add(
        models.CompanyMember(
            user_id=worker2.id,
            company_id=billing.company.id,
            role=models.CompanyRole.worker,
            is_active=True,
        )
    )
    # 10 turnos de 1.01 bruto con IRPF 15%: suma agrupada = 10.10 * 0.85 = 8.585 -> 8.59
    for _ in range(10):
        db.add(
            models.WorkLog(
                user_id=worker2.id,
                company_id=billing.company.id,
                start_date=date(2026, 7, 20),
                end_date=date(2026, 7, 20),
                duration=1.0,
                gross_amount=1.01,
                net_amount=0.86,
                type="particular",
                calculation_snapshot={
                    "rate_applied": {"base_rate": 1.01, "is_gross": True},
                    "tax_applied": {"IRPF": 0.15},
                },
            )
        )
    # 1 turno de otro tipo con el mismo impuesto (10.03 * 0.85):
    # agrupado por trabajador: (10.10 + 10.03) * 0.85 = 20.13 * 0.85 = 17.1105 -> 17.11
    db.add(
        models.WorkLog(
            user_id=worker2.id,
            company_id=billing.company.id,
            start_date=date(2026, 7, 21),
            end_date=date(2026, 7, 21),
            duration=1.0,
            gross_amount=10.03,
            net_amount=8.53,
            type="tutorial",
            calculation_snapshot={
                "rate_applied": {"base_rate": 10.03, "is_gross": True},
                "tax_applied": {"IRPF": 0.15},
            },
        )
    )
    db.commit()

    as_user(client, billing.user_manager, billing.company, claims=MANAGER_CLAIMS)
    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(billing.company.id), **BILLING_PARAMS},
    )
    assert resp.status_code == 200, resp.text
    rows = [item for item in resp.json() if item["userId"] == str(worker2.id)]
    by_type = {item["type"]: item for item in rows}
    assert by_type["particular"]["totalNet"] == 8.59
    assert by_type["particular"]["totalGross"] == 10.10
    assert by_type["tutorial"]["totalNet"] == 8.53
    assert by_type["particular"]["userTotalNet"] == 17.11
    assert by_type["tutorial"]["userTotalNet"] == 17.11
