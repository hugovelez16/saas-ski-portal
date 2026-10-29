"""Migracion b7e1a0d10006 (borrar companies.fiscal_id) sobre PostgreSQL real (PR-23.1).

Requiere TEST_DATABASE_URL, con la base migrada hasta el head (donde la columna ya no existe).
El fixture `db` revierte la transaccion al final: la columna que cada test recrea para simular
el esquema previo, las vistas y los datos no persisten.
"""

import importlib.util
from pathlib import Path

import models
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import text

from scripts import repair_fiscal_id
from tests.factories import make_company

pytestmark = pytest.mark.postgres

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "b7e1a0d10006_drop_companies_fiscal_id.py"
)
COMPANIES = sa.table(
    "companies",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("fiscal_id", sa.String()),
)


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_b7e1a0d10006", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(db, step: str):
    module = _load_migration()
    context = MigrationContext.configure(connection=db.connection())
    with Operations.context(context):
        getattr(module, step)()


def _has_column(db) -> bool:
    return bool(
        db.execute(
            text(
                "SELECT 1 FROM information_schema.columns "
                "WHERE table_name = 'companies' AND column_name = 'fiscal_id'"
            )
        ).first()
    )


def _legacy_company(db, fiscal_id):
    company = make_company(db)
    db.flush()
    db.execute(sa.update(COMPANIES).where(COMPANIES.c.id == company.id).values(fiscal_id=fiscal_id))
    return company


@pytest.fixture(autouse=True)
def _legacy_schema(db):
    """Esquema previo a la migracion: companies con la columna fiscal_id."""
    db.execute(text("ALTER TABLE companies ADD COLUMN fiscal_id VARCHAR"))


def test_upgrade_aborts_with_real_value_and_without_env(db, monkeypatch):
    monkeypatch.delenv("FISCAL_ID_EXPORTED", raising=False)
    _legacy_company(db, "B12345678")
    _legacy_company(db, "A87654321")

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    message = str(exc.value)
    assert "Hay 2 empresas con fiscal_id real" in message
    assert "repair_fiscal_id.py --apply" in message
    assert "FISCAL_ID_EXPORTED=1" in message
    assert _has_column(db)


@pytest.mark.parametrize("value", ["0", "true", "", " 1"])
def test_upgrade_only_accepts_exactly_one(db, monkeypatch, value):
    monkeypatch.setenv("FISCAL_ID_EXPORTED", value)
    _legacy_company(db, "B12345678")

    with pytest.raises(RuntimeError):
        _run(db, "upgrade")

    assert _has_column(db)


def test_upgrade_passes_with_real_value_when_exported(db, monkeypatch):
    monkeypatch.setenv("FISCAL_ID_EXPORTED", "1")
    _legacy_company(db, "B12345678")

    _run(db, "upgrade")

    assert not _has_column(db)


def test_upgrade_passes_without_env_when_only_seed_null_or_empty(db, monkeypatch):
    monkeypatch.delenv("FISCAL_ID_EXPORTED", raising=False)
    _legacy_company(db, "B00000000")
    _legacy_company(db, "  B00000000 ")
    _legacy_company(db, None)
    _legacy_company(db, "")
    _legacy_company(db, "   ")

    _run(db, "upgrade")

    assert not _has_column(db)


def test_migration_and_script_agree_on_what_is_real(db, monkeypatch):
    monkeypatch.delenv("FISCAL_ID_EXPORTED", raising=False)
    for value in ("B12345678", "B00000000", None, "", "  "):
        _legacy_company(db, value)

    exported = repair_fiscal_id.run(db, apply=False, backup_dir=None).changes

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")
    assert f"Hay {len(exported)} empresas con fiscal_id real" in str(exc.value)


def test_upgrade_aborts_naming_a_view_that_reads_fiscal_id(db, monkeypatch):
    monkeypatch.setenv("FISCAL_ID_EXPORTED", "1")
    db.execute(text('CREATE VIEW "Ficha Empresa" AS SELECT c.id, c.name, c.fiscal_id FROM companies c'))

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    assert "Ficha Empresa" in str(exc.value)
    assert "companies.fiscal_id" in str(exc.value)
    assert _has_column(db)


def test_upgrade_keeps_views_that_do_not_read_fiscal_id(db, monkeypatch):
    monkeypatch.setenv("FISCAL_ID_EXPORTED", "1")
    db.execute(text('CREATE VIEW "Nombres Empresa" AS SELECT c.id, c.name FROM companies c'))
    db.execute(text('GRANT SELECT ON "Nombres Empresa" TO PUBLIC'))
    work_logs_before = db.execute(text("SELECT pg_get_viewdef('\"Work Logs\"'::regclass)")).scalar()
    companies = db.execute(text("SELECT count(*) FROM companies")).scalar()

    _run(db, "upgrade")

    assert not _has_column(db)
    assert db.execute(text('SELECT count(*) FROM "Nombres Empresa"')).scalar() == companies
    assert db.execute(text("SELECT pg_get_viewdef('\"Work Logs\"'::regclass)")).scalar() == work_logs_before


def test_downgrade_recreates_an_empty_nullable_column(db, monkeypatch):
    monkeypatch.setenv("FISCAL_ID_EXPORTED", "1")
    company = _legacy_company(db, "B12345678")
    _run(db, "upgrade")

    _run(db, "downgrade")

    assert _has_column(db)
    nullable = db.execute(
        text(
            "SELECT is_nullable FROM information_schema.columns "
            "WHERE table_name = 'companies' AND column_name = 'fiscal_id'"
        )
    ).scalar()
    assert nullable == "YES"
    assert db.execute(sa.select(COMPANIES.c.fiscal_id).where(COMPANIES.c.id == company.id)).scalar() is None


def test_company_model_has_no_fiscal_id_column():
    assert "fiscal_id" not in models.Company.__table__.columns
    assert not hasattr(models.Company, "fiscal_id")
