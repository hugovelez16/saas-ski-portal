"""
Gobierno de empresas (PR-03) por HTTP: cambios de rol y tarifas de miembros, empresas suspendidas,
y escritura de turnos en empresas gestionadas.

Los casos marcados con `# PR-03:` cambian respecto al codigo anterior: el mensaje de error de
empresa gestionada sale ahora de `access_policy`.
"""

import uuid
from types import SimpleNamespace

import models
import pytest

from tests.factories import as_user

MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_MANAGED_READONLY = "En empresas gestionadas solo el equipo gestor puede modificar turnos y tarifas"

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}


def _seed(db):
    """Datos de partida del escenario de gobierno. Devuelve los objetos en un namespace."""
    platform_admin = models.User(
        id=uuid.uuid4(),
        email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="pw",
        first_name="Platform",
        last_name="Admin",
        role=models.UserRole.admin,
        is_active=True,
    )
    manager_user = models.User(
        id=uuid.uuid4(),
        email=f"manager_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="pw",
        first_name="Manager",
        last_name="User",
        role=models.UserRole.user,
        is_active=True,
    )
    worker_user = models.User(
        id=uuid.uuid4(),
        email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="pw",
        first_name="Worker",
        last_name="User",
        role=models.UserRole.user,
        is_active=True,
    )
    other_worker = models.User(
        id=uuid.uuid4(),
        email=f"other_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password="pw",
        first_name="Other",
        last_name="Worker",
        role=models.UserRole.user,
        is_active=True,
    )

    managed_company = models.Company(id=uuid.uuid4(), name="Managed Corp", is_active=True, is_managed=True)
    autonomous_company = models.Company(
        id=uuid.uuid4(), name="Autonomous Freelancers", is_active=True, is_managed=False
    )
    inactive_company = models.Company(id=uuid.uuid4(), name="Suspended Company", is_active=False, is_managed=False)

    db.add_all(
        [
            platform_admin,
            manager_user,
            worker_user,
            other_worker,
            managed_company,
            autonomous_company,
            inactive_company,
        ]
    )
    db.commit()

    m_manager = models.CompanyMember(
        company_id=managed_company.id,
        user_id=manager_user.id,
        role=models.CompanyRole.manager,
        is_active=True,
    )
    m_worker = models.CompanyMember(
        company_id=managed_company.id,
        user_id=worker_user.id,
        role=models.CompanyRole.worker,
        is_active=True,
        rates_config={"particular": 30.0},
    )
    m_other = models.CompanyMember(
        company_id=managed_company.id,
        user_id=other_worker.id,
        role=models.CompanyRole.worker,
        is_active=True,
    )
    m_auto_worker = models.CompanyMember(
        company_id=autonomous_company.id,
        user_id=worker_user.id,
        role=models.CompanyRole.worker,
        is_active=True,
        rates_config={"particular": 25.0},
    )
    m_inactive_worker = models.CompanyMember(
        company_id=inactive_company.id,
        user_id=worker_user.id,
        role=models.CompanyRole.worker,
        is_active=True,
    )
    db.add_all([m_manager, m_worker, m_other, m_auto_worker, m_inactive_worker])
    db.commit()

    return SimpleNamespace(
        platform_admin=platform_admin,
        manager_user=manager_user,
        worker_user=worker_user,
        other_worker=other_worker,
        managed_company=managed_company,
        autonomous_company=autonomous_company,
        inactive_company=inactive_company,
    )


@pytest.fixture
def world(db):
    return _seed(db)


def test_manager_cannot_change_member_role(client, db, world):
    """Un manager de empresa no debe poder ascender o cambiar el rol de un miembro."""
    as_user(client, world.manager_user, world.managed_company, claims=MANAGER_CLAIMS)

    resp = client.put(
        f"/companies/{world.managed_company.id}/members/{world.other_worker.id}",
        json={"role": "admin"},
    )

    assert resp.status_code == 403, resp.text
    assert "Solo los administradores" in resp.json()["detail"]


def test_platform_admin_can_change_member_role(client, db, world):
    """Un admin de plataforma si debe poder cambiar el rol de un miembro."""
    as_user(client, world.platform_admin, claims=PA_CLAIMS)

    resp = client.put(
        f"/companies/{world.managed_company.id}/members/{world.other_worker.id}",
        json={"role": "admin"},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "admin"


def test_worker_cannot_edit_rates_in_managed_company(client, db, world):
    """En una empresa gestionada (is_managed=True), un trabajador no puede modificar sus tarifas."""
    as_user(client, world.worker_user, world.managed_company, claims=WORKER_CLAIMS)

    resp = client.put(
        f"/companies/{world.managed_company.id}/members/{world.worker_user.id}",
        json={"ratesConfig": {"particular": 50.0}},
    )

    assert resp.status_code == 403, resp.text
    assert "tarifas son fijadas por los administradores" in resp.json()["detail"]


def test_worker_can_edit_rates_in_autonomous_company(client, db, world):
    """En una empresa autonoma (is_managed=False), el trabajador si puede modificar sus tarifas."""
    as_user(client, world.worker_user, world.autonomous_company, claims=WORKER_CLAIMS)

    resp = client.put(
        f"/companies/{world.autonomous_company.id}/members/{world.worker_user.id}",
        json={"ratesConfig": {"particular": 45.0}},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json()["ratesConfig"] == {"particular": 45.0}


def test_inactive_company_blocks_access_to_non_admin(client, db, world):
    """Una empresa inactiva (is_active=False) rechaza el acceso a usuarios no plataforma."""
    as_user(client, world.worker_user, world.inactive_company, claims=WORKER_CLAIMS)

    resp = client.get(f"/companies/{world.inactive_company.id}")

    assert resp.status_code == 403, resp.text
    assert MSG_SUSPENDED in resp.json()["detail"]


def test_inactive_company_allows_access_to_platform_admin(client, db, world):
    """Un admin de plataforma si puede acceder a una empresa inactiva."""
    as_user(client, world.platform_admin, claims=PA_CLAIMS)

    resp = client.get(f"/companies/{world.inactive_company.id}")

    assert resp.status_code == 200, resp.text
    assert resp.json()["id"] == str(world.inactive_company.id)


def test_cannot_create_work_log_in_inactive_company(client, db, world):
    """No se pueden crear turnos de trabajo en empresas inactivas."""
    as_user(client, world.worker_user, world.inactive_company, claims=WORKER_CLAIMS)

    resp = client.post(
        "/work-logs",
        json={
            "type": "particular",
            "startDate": "2026-09-28",
            "endDate": "2026-09-28",
            "duration": 2.0,
            "companyId": str(world.inactive_company.id),
            "userId": str(world.worker_user.id),
        },
    )

    assert resp.status_code == 403, resp.text
    assert MSG_SUSPENDED in resp.json()["detail"]


def test_worker_cannot_edit_or_delete_shifts_in_managed_company(client, db, world):
    """En una empresa gestionada, un trabajador no puede modificar ni borrar turnos directamente."""
    # Creamos un turno en managed_company directamente en BD
    log = models.WorkLog(
        id=uuid.uuid4(),
        company_id=world.managed_company.id,
        user_id=world.worker_user.id,
        type="particular",
        start_date=models.datetime.utcnow().date(),
        end_date=models.datetime.utcnow().date(),
        duration=2.0,
    )
    db.add(log)
    db.commit()

    as_user(client, world.worker_user, world.managed_company, claims=WORKER_CLAIMS)

    # Intentar borrar como trabajador
    resp = client.delete(f"/work-logs/{log.id}")

    # PR-03: el mensaje de empresa gestionada sale de access_policy (MSG_MANAGED_READONLY).
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_MANAGED_READONLY

    # Intentar actualizar como trabajador
    body = {
        "companyId": str(world.managed_company.id),
        "userId": str(world.worker_user.id),
        "type": "particular",
        "startDate": "2026-09-28",
        "endDate": "2026-09-28",
        "duration": 3.0,
    }
    resp = client.put(f"/work-logs/{log.id}", json=body)

    # PR-03: el mensaje de empresa gestionada sale de access_policy (MSG_MANAGED_READONLY).
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_MANAGED_READONLY
