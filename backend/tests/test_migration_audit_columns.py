"""Migracion b7e1a0d10013 (eliminar admin_user_id e impersonated_user_id de audit_logs)."""

import importlib.util
import uuid
from pathlib import Path

import models
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from tests.factories import make_user

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "b7e1a0d10013_drop_legacy_audit_columns.py"
)

AUDIT_LOGS = sa.table(
    "audit_logs",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("action", sa.String()),
    sa.column("actor_user_id", sa.Uuid(as_uuid=True)),
    sa.column("target_user_id", sa.Uuid(as_uuid=True)),
    sa.column("admin_user_id", sa.Uuid(as_uuid=True)),
    sa.column("impersonated_user_id", sa.Uuid(as_uuid=True)),
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_b7e1a0d10013", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(db, step: str):
    module = _load_migration()
    context = MigrationContext.configure(connection=db.connection())
    with Operations.context(context):
        getattr(module, step)()


def _has_column(db, column: str) -> bool:
    return bool(
        db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'audit_logs' AND column_name = :col"
            ),
            {"col": column},
        ).first()
    )


def test_audit_log_model_has_no_legacy_columns():
    cols = models.AuditLog.__table__.columns
    assert "admin_user_id" not in cols
    assert "impersonated_user_id" not in cols
    assert not hasattr(models.AuditLog, "admin_user_id")
    assert not hasattr(models.AuditLog, "impersonated_user_id")


@pytest.mark.postgres
def test_upgrade_preserves_legacy_ids_and_drops_columns(db):
    db.execute(text("ALTER TABLE audit_logs ADD COLUMN impersonated_user_id UUID REFERENCES users(id)"))
    db.execute(text("ALTER TABLE audit_logs ADD COLUMN admin_user_id UUID REFERENCES users(id)"))

    pa = make_user(db, role="admin")
    victim = make_user(db)
    row_id = uuid.uuid4()
    db.execute(
        sa.insert(AUDIT_LOGS).values(
            id=row_id,
            action="2fa_reset",
            actor_user_id=None,
            target_user_id=None,
            admin_user_id=pa.id,
            impersonated_user_id=victim.id,
        )
    )

    _run(db, "upgrade")

    assert not _has_column(db, "admin_user_id")
    assert not _has_column(db, "impersonated_user_id")
    migrated = db.execute(
        text("SELECT actor_user_id, target_user_id FROM audit_logs WHERE id = :id"),
        {"id": row_id},
    ).mappings().one()
    assert migrated["actor_user_id"] == pa.id
    assert migrated["target_user_id"] == victim.id

    _run(db, "downgrade")

    assert _has_column(db, "admin_user_id")
    assert _has_column(db, "impersonated_user_id")
    restored = db.execute(
        text("SELECT admin_user_id, impersonated_user_id FROM audit_logs WHERE id = :id"),
        {"id": row_id},
    ).mappings().one()
    assert restored["admin_user_id"] == pa.id
    assert restored["impersonated_user_id"] == victim.id


@pytest.mark.postgres
def test_upgrade_aborts_if_view_depends_on_legacy_audit_column(db):
    db.execute(text("ALTER TABLE audit_logs ADD COLUMN impersonated_user_id UUID REFERENCES users(id)"))
    db.execute(text("ALTER TABLE audit_logs ADD COLUMN admin_user_id UUID REFERENCES users(id)"))
    db.execute(text('CREATE VIEW "Vista Audit Legacy" AS SELECT id, admin_user_id FROM audit_logs'))

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    assert "Vista Audit Legacy" in str(exc.value)
    assert "audit_logs.admin_user_id" in str(exc.value)
    assert _has_column(db, "admin_user_id")
