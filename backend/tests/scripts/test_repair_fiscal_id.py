"""Tests de scripts.repair_fiscal_id (PR-23.R, fixtures de tests/conftest.py).

`models.Company` ya no tiene `fiscal_id`: cada test recrea la columna con un ALTER para reproducir
el esquema previo a la migracion b7e1a0d10006. Los ficheros se escriben en tmp_path, siempre fuera
del arbol del repositorio.
"""

import json
import os
import stat

import pytest
import sqlalchemy as sa
from scripts.repair_common import BACKEND_DIR
from scripts.repair_fiscal_id import SEED_VALUE, main, run

from tests.factories import make_company

COMPANIES = sa.table(
    "companies",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("fiscal_id", sa.String()),
)

# main() abre su propia sesion (database.SessionLocal): con PostgreSQL no veria los datos ni la
# columna creados sin commit dentro de la transaccion del test.
only_sqlite = pytest.mark.skipif(
    bool(os.getenv("TEST_DATABASE_URL")),
    reason="main() abre su propia sesion; se prueba con SQLite",
)


@pytest.fixture(autouse=True)
def _legacy_column(db):
    db.execute(sa.text("ALTER TABLE companies ADD COLUMN fiscal_id VARCHAR"))
    db.commit()


def _company(db, name, fiscal_id):
    company = make_company(db, name=name)
    db.flush()
    db.execute(sa.update(COMPANIES).where(COMPANIES.c.id == company.id).values(fiscal_id=fiscal_id))
    db.commit()
    return company


def _fiscal_ids(db):
    db.expire_all()
    return dict(db.execute(sa.select(COMPANIES.c.id, COMPANIES.c.fiscal_id)).all())


def _exports(directory):
    return sorted(directory.glob("fiscal_id_export_*.json"))


def test_dry_run_cuenta_reales_y_semilla_sin_escribir(db, tmp_path):
    _company(db, "Real", "B12345678")
    _company(db, "Semilla", SEED_VALUE)
    backup = tmp_path / "backups"

    report = run(db, apply=False, backup_dir=backup)

    assert [change["company_name"] for change in report.changes] == ["Real"]
    assert {"real": 1, "semilla": 1} in report.informational
    assert report.backup_files == []
    assert report.exit_code() == 0
    assert not backup.exists()


def test_apply_exporta_solo_reales_y_marca_los_de_semilla(db, tmp_path):
    real = _company(db, "Real", "B12345678")
    seed = _company(db, "Semilla", SEED_VALUE)
    _company(db, "Con espacios", "  A87654321  ")

    report = run(db, apply=True, backup_dir=tmp_path)

    assert len(report.backup_files) == 1
    exported = json.loads(report.backup_files[0].read_text(encoding="utf-8"))
    by_id = {entry["company_id"]: entry for entry in exported}
    assert len(exported) == 3
    assert by_id[str(real.id)] == {"company_id": str(real.id), "company_name": "Real", "fiscal_id": "B12345678"}
    assert by_id[str(seed.id)] == {
        "company_id": str(seed.id),
        "company_name": "Semilla",
        "fiscal_id": SEED_VALUE,
        "seed_value": True,
    }
    assert sum("seed_value" not in entry for entry in exported) == 2
    assert report.exit_code() == 0


def test_nulos_y_cadenas_vacias_se_ignoran(db, tmp_path):
    _company(db, "Nulo", None)
    _company(db, "Vacio", "")
    _company(db, "Espacios", "   ")

    report = run(db, apply=True, backup_dir=tmp_path)

    assert report.changes == []
    assert json.loads(report.backup_files[0].read_text(encoding="utf-8")) == []
    assert {"real": 0, "semilla": 0} in report.informational


def test_el_fichero_queda_fuera_del_repo_con_permisos_0600(db, tmp_path):
    _company(db, "Real", "B12345678")

    report = run(db, apply=True, backup_dir=tmp_path / "repairs")

    path = report.backup_files[0]
    assert path.name.startswith("fiscal_id_export_") and path.suffix == ".json"
    assert BACKEND_DIR.parent not in path.resolve().parents
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_apply_no_modifica_la_bd_y_es_idempotente(db, tmp_path):
    _company(db, "Real", "B12345678")
    _company(db, "Semilla", SEED_VALUE)
    before = _fiscal_ids(db)

    first = run(db, apply=True, backup_dir=tmp_path)
    after_first = _fiscal_ids(db)
    contents = json.loads(first.backup_files[0].read_text(encoding="utf-8"))
    # Cada ejecucion usa una marca de tiempo a segundos: se borra el fichero para repetir sin colision.
    first.backup_files[0].unlink()
    second = run(db, apply=True, backup_dir=tmp_path)

    assert before == after_first == _fiscal_ids(db)
    assert json.loads(second.backup_files[0].read_text(encoding="utf-8")) == contents


def test_apply_sin_backup_dir_falla_sin_escribir(db):
    _company(db, "Real", "B12345678")

    with pytest.raises(SystemExit) as exc:
        run(db, apply=True, backup_dir=None)

    assert "--backup-dir" in str(exc.value.code)


def test_sin_columna_informa_y_no_falla(db, tmp_path):
    db.execute(sa.text("ALTER TABLE companies DROP COLUMN fiscal_id"))
    db.commit()

    report = run(db, apply=False, backup_dir=None)

    assert report.changes == []
    assert any("no existe" in str(item.get("aviso", "")) for item in report.informational)
    assert report.exit_code() == 0


@only_sqlite
def test_main_por_defecto_es_dry_run(db, tmp_path, capsys):
    _company(db, "Real", "B12345678")
    backup = tmp_path / "backups"

    code = main(["--backup-dir", str(backup)])

    assert code == 0
    assert not backup.exists()
    assert "--dry-run" in capsys.readouterr().out


@only_sqlite
def test_main_apply_sin_backup_dir_devuelve_1(db, capsys, monkeypatch):
    monkeypatch.delenv("REPAIR_BACKUP_DIR", raising=False)

    code = main(["--apply"])

    assert code == 1
    assert "--backup-dir" in capsys.readouterr().err


@only_sqlite
def test_main_apply_escribe_el_export_y_devuelve_0(db, tmp_path, capsys):
    _company(db, "Real", "B12345678")

    code = main(["--apply", "--backup-dir", str(tmp_path)])

    assert code == 0
    assert len(_exports(tmp_path)) == 1
    assert "Backup escrito" in capsys.readouterr().out
