"""Tests del registro de auditoria: helper `audit.record_audit` y `routers.work_logs.record_impersonation_audit`.

Los imports del helper se hacen dentro de cada test para que un fallo de importacion no oculte
los fallos propios de los tests de endpoint y de impersonacion.
"""

import uuid
from datetime import date
from types import SimpleNamespace

import main
import models
import pytest
from auth import get_verified_user
from routers.work_logs import record_impersonation_audit

from tests.factories import make_user


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
    assert row.admin_user_id == admin.id
    assert row.actor_user_id == admin.id


def test_impersonation_audit_sets_actor(db):
    admin = make_user(db, role="admin")
    impersonated = make_user(db)

    current_user = SimpleNamespace(
        id=impersonated.id,
        token_scope="impersonated",
        admin_user_id=str(admin.id),
    )

    record_impersonation_audit(db, current_user, "accion", {"clave": "valor"})

    row = db.query(models.AuditLog).filter(models.AuditLog.action == "accion").one()
    assert row.admin_user_id == admin.id
    assert row.actor_user_id == admin.id
