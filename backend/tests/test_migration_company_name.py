"""Migracion b7e1a0d10002 (longitud de companies.name) sobre PostgreSQL real (PR-06.1).

Requiere TEST_DATABASE_URL. El fixture `db` revierte la transaccion al final, asi que el
ALTER de la prueba (simular el esquema previo) y los datos no persisten.
"""

import importlib.util
from pathlib import Path

import models
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from scripts import repair_company_names
from tests.factories import make_company

pytestmark = pytest.mark.postgres

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "b7e1a0d10002_company_name_length.py"
)
LONG_NAME = "x" * 130


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_b7e1a0d10002", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(db, step: str):
    module = _load_migration()
    context = MigrationContext.configure(connection=db.connection())
    with Operations.context(context):
        getattr(module, step)()


def _name_max_length(db):
    return db.execute(
        text(
            "SELECT character_maximum_length FROM information_schema.columns "
            "WHERE table_name = 'companies' AND column_name = 'name'"
        )
    ).scalar()


def _simulate_pre_migration_schema(db):
    """Deja `companies.name` como VARCHAR sin longitud, el estado previo a b7e1a0d10002."""
    # La vista "Work Logs" lee companies.name y bloquea el ALTER; la migracion la recrea.
    db.execute(text('DROP VIEW IF EXISTS "Work Logs"'))
    db.execute(text("ALTER TABLE companies ALTER COLUMN name TYPE VARCHAR"))
    db.execute(
        text(
            'CREATE VIEW "Work Logs" AS SELECT wl.id, u.email AS worker_email, c.name AS company_name, '
            "wl.type, wl.start_date, wl.duration, wl.net_amount, wl.description, wl.user_id, wl.company_id "
            "FROM work_logs wl JOIN users u ON wl.user_id = u.id JOIN companies c ON wl.company_id = c.id"
        )
    )


def test_upgrade_aborts_without_changes_when_name_is_too_long(db):
    _simulate_pre_migration_schema(db)
    company = make_company(db, name=LONG_NAME)
    db.flush()

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    message = str(exc.value)
    assert "Hay 1 empresas con nombre no valido" in message
    assert str(company.id) in message
    assert "repair_company_names.py --apply" in message
    assert _name_max_length(db) is None
    db.expire_all()
    assert len(db.get(models.Company, company.id).name) == 130


def test_upgrade_passes_after_repair_script_and_downgrade_reverts(db, tmp_path):
    _simulate_pre_migration_schema(db)
    make_company(db, name=LONG_NAME)
    db.flush()

    repair_company_names.run(db, apply=True, backup_dir=tmp_path)
    _run(db, "upgrade")

    assert _name_max_length(db) == 120

    _run(db, "downgrade")

    assert _name_max_length(db) is None
