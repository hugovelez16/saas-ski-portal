"""Tests del registro de auditoria: helper `audit.record_audit` y `routers.work_logs.record_impersonation_audit`.

Los imports del helper se hacen dentro de cada test para que un fallo de importacion no oculte
los fallos propios de los tests de endpoint y de impersonacion.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import auth as auth_module
import main
import models
import pytest
import seed
from auth import get_verified_user
from routers.work_logs import record_impersonation_audit
from scripts.grant_platform_admin import grant_platform_admin
from scripts.grant_platform_admin import main as grant_pa_main

from tests.factories import as_user, make_company, make_member, make_user


def test_record_audit_adds_row_without_commit(db):
    from audit import AuditAction, record_audit

    admin = make_user(db, role="admin")

    # Se usa un SAVEPOINT en lugar de db.rollback(): con PostgreSQL la sesion de test va dentro de
    # una transaccion externa y un rollback completo la cerraria, filtrando datos a la BD de test.
    nested = db.begin_nested()
    record_audit(db, action=AuditAction.COMPANY_CREATED, actor_id=admin.id)
    nested.rollback()

    # Sin commit, la fila pendiente no debe persistir tras el rollback.
    assert db.query(models.AuditLog).all() == []

    record_audit(db, action=AuditAction.COMPANY_CREATED, actor_id=admin.id)
    db.commit()

    assert len(db.query(models.AuditLog).all()) == 1


def test_record_audit_serializes_uuid_and_dates(db):
    from audit import AuditAction, record_audit

    admin = make_user(db, role="admin")
    company_id = uuid.uuid4()

    record_audit(
        db,
        action=AuditAction.COMPANY_CREATED,
        actor_id=admin.id,
        old_value={"company_id": company_id},
        new_value={"valid_from": date(2026, 1, 10)},
    )
    db.commit()

    row = db.query(models.AuditLog).one()
    db.refresh(row)

    # Los valores se guardan como JSON, por lo que UUID y fecha llegan como string.
    assert row.old_value["company_id"] == str(company_id)
    assert row.new_value["valid_from"] == "2026-01-10"


@pytest.mark.postgres  # Falla en SQLite: str en columna UUID (el id llega como str desde la ruta).
def test_existing_2fa_reset_sets_actor(db, client):
    admin = make_user(db, role="admin")
    admin.is_platform_admin = True
    target = make_user(db)
    target.is_2fa_enabled = True
    target.otp_secret = "secreto-de-prueba"
    db.commit()

    main.app.dependency_overrides[get_verified_user] = lambda: admin

    response = client.post(f"/users/{target.id}/reset-2fa")
    assert response.status_code == 200

    row = db.query(models.AuditLog).filter(models.AuditLog.action == "2fa_reset").one()
    assert row.actor_user_id == admin.id
    assert row.target_user_id == target.id


def test_impersonation_audit_no_longer_writes_work_log_events(db):
    admin = make_user(db, role="admin")
    impersonated = make_user(db)

    current_user = SimpleNamespace(
        id=impersonated.id,
        token_scope="impersonated",
        admin_user_id=str(admin.id),
    )

    record_impersonation_audit(db, current_user, "create_work_log", {"clave": "valor"})

    assert db.query(models.AuditLog).all() == []


def test_user_status_changed_emits_audit_in_same_transaction(db, client):
    pa = make_user(db, role="admin")
    target = make_user(db, is_active=True)
    as_user(client, pa)

    resp = client.put(f"/users/{target.id}/status", params={"is_active": "false"})
    assert resp.status_code == 200, resp.text

    logs = db.query(models.AuditLog).filter(models.AuditLog.action == "user.status_changed").all()
    assert len(logs) == 1
    assert logs[0].actor_user_id == pa.id
    assert logs[0].target_user_id == target.id
    assert logs[0].old_value == {"is_active": True}
    assert logs[0].new_value == {"is_active": False}

    # Sin cambio de estado no se emite un segundo evento
    resp_noop = client.put(f"/users/{target.id}/status", params={"is_active": "false"})
    assert resp_noop.status_code == 200
    assert db.query(models.AuditLog).filter(models.AuditLog.action == "user.status_changed").count() == 1

    # Reactivacion via v2/admin
    resp_reactivate = client.put(f"/v2/admin/users/{target.id}/status", params={"is_active": "true"})
    assert resp_reactivate.status_code == 200
    logs = (
        db.query(models.AuditLog)
        .filter(models.AuditLog.action == "user.status_changed")
        .order_by(models.AuditLog.created_at.asc(), models.AuditLog.id.asc())
        .all()
    )
    assert len(logs) == 2
    assert logs[1].old_value == {"is_active": False}
    assert logs[1].new_value == {"is_active": True}


def test_user_status_changed_not_emitted_when_invariant_blocks(db, client):
    pa = make_user(db, role="admin")
    as_user(client, pa)

    resp = client.put(f"/users/{pa.id}/status", params={"is_active": "false"})
    assert resp.status_code == 403
    assert db.query(models.AuditLog).filter(models.AuditLog.action == "user.status_changed").count() == 0


def test_user_status_changed_emitted_on_put_user(db, client):
    pa = make_user(db, role="admin")
    target = make_user(db, is_active=True)
    as_user(client, pa)

    resp = client.put(f"/users/{target.id}", json={"isActive": False})
    assert resp.status_code == 200, resp.text

    log = db.query(models.AuditLog).filter(models.AuditLog.action == "user.status_changed").one()
    assert log.actor_user_id == pa.id
    assert log.target_user_id == target.id
    assert log.old_value == {"is_active": True}
    assert log.new_value == {"is_active": False}


def test_impersonation_started_and_ended_emit_audit(db, client):
    pa = make_user(db, role="admin")
    target = make_user(db)
    as_user(client, pa)

    imp_resp = client.post(f"/admin/impersonate/{target.id}")
    assert imp_resp.status_code == 200, imp_resp.text

    started = db.query(models.AuditLog).filter(models.AuditLog.action == "impersonation.started").one()
    assert started.actor_user_id == pa.id
    assert started.target_user_id == target.id

    client.cookies.set("access_token", imp_resp.cookies.get("access_token"))
    client.cookies.set("refresh_token", imp_resp.cookies.get("refresh_token"))
    stop_resp = client.post("/admin/stop-impersonation")
    assert stop_resp.status_code == 200, stop_resp.text

    ended = db.query(models.AuditLog).filter(models.AuditLog.action == "impersonation.ended").one()
    assert ended.actor_user_id == pa.id
    assert ended.target_user_id == target.id


def test_stop_impersonation_records_ended_even_when_token_expired(db, client):
    from datetime import UTC, datetime, timedelta

    pa = make_user(db, role="admin")
    target = make_user(db)
    expired_token = auth_module.create_access_token(
        data={"sub": str(target.id), "scope": "impersonated", "admin_user_id": str(pa.id)},
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    client.cookies.clear()
    client.cookies.set("access_token", expired_token)

    resp = client.post("/admin/stop-impersonation")
    assert resp.status_code == 200

    ended = db.query(models.AuditLog).filter(models.AuditLog.action == "impersonation.ended").one()
    assert ended.actor_user_id == pa.id
    assert ended.target_user_id == target.id


def test_stop_impersonation_without_impersonation_writes_no_audit(db, client):
    pa = make_user(db, role="admin")
    as_user(client, pa)

    resp = client.post("/admin/stop-impersonation")
    assert resp.status_code == 200
    assert db.query(models.AuditLog).filter(models.AuditLog.action == "impersonation.ended").count() == 0


def test_seed_records_platform_admin_granted(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", "seed-pa@vesotel.com")
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", "PasswordSeguro123!")
    monkeypatch.setenv("INITIAL_COMPANY_NAME", "Demo Seed Audit")
    db.query(models.User).filter(models.User.role == models.UserRole.admin).update({"role": models.UserRole.user})
    db.flush()

    assert seed.seed_initial_data(db) is True

    admin = db.query(models.User).filter_by(email="seed-pa@vesotel.com").one()
    log = db.query(models.AuditLog).filter(models.AuditLog.action == "user.platform_admin_granted").one()
    assert log.target_user_id == admin.id
    assert log.new_value == {"role": "admin"}
    assert log.extra_data["source"] == "seed"


def test_grant_platform_admin_command_audits_and_validates(db, monkeypatch):
    user = make_user(db, email="nuevo-pa@vesotel.com")

    promoted, granted = grant_platform_admin(db, email="NUEVO-PA@vesotel.com", reason="Alta operativa")
    assert granted is True
    assert promoted.role == models.UserRole.admin

    log = db.query(models.AuditLog).filter(models.AuditLog.action == "user.platform_admin_granted").one()
    assert log.target_user_id == user.id
    assert log.old_value == {"role": "user"}
    assert log.new_value == {"role": "admin"}
    assert log.reason == "Alta operativa"
    assert log.extra_data["source"] == "cli"

    # Idempotente: segunda ejecucion no duplica el evento
    _, granted_again = grant_platform_admin(db, email="nuevo-pa@vesotel.com")
    assert granted_again is False
    assert db.query(models.AuditLog).filter(models.AuditLog.action == "user.platform_admin_granted").count() == 1

    # Rechaza usuario con membresias (R-ACC-26)
    company = make_company(db)
    member_user = make_user(db, email="con-empresa@vesotel.com")
    make_member(db, member_user, company)
    with pytest.raises(ValueError):
        grant_platform_admin(db, email="con-empresa@vesotel.com")

    # CLI main() con usuario inexistente devuelve 1
    monkeypatch.setattr("database.SessionLocal", lambda: db)
    monkeypatch.setattr(db, "close", lambda: None)
    assert grant_pa_main(["--email", "no-existe@vesotel.com"]) == 1
