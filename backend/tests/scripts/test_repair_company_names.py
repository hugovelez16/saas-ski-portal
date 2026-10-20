"""Tests de scripts.repair_company_names (SQLite, fixtures de tests/conftest.py).

Los backups se escriben en tmp_path, siempre fuera del arbol del repositorio.
"""

import json
import os
import stat

import models
import pytest
from scripts.repair_common import (
    BACKEND_DIR,
    RepairReport,
    ensure_backup_dir,
    parse_args,
)
from scripts.repair_company_names import main, run

from tests.factories import make_company

# Con PostgreSQL la columna ya es VARCHAR(120) y no admite los nombres largos que reproducen datos
# antiguos; la migracion se prueba aparte en test_migration_company_name.py (marcador postgres).
pytestmark = pytest.mark.skipif(
    bool(os.getenv("TEST_DATABASE_URL")),
    reason="el script se prueba con SQLite: PostgreSQL rechaza nombres de mas de 120 caracteres",
)

LONG_NAME = "Escuela " + "x" * 120  # 128 caracteres, sin espacios sobrantes


def _company(db, name):
    # make_company sustituye "" por un nombre generado, por eso se asigna el valor despues.
    company = make_company(db, name="Nombre inicial")
    company.name = name
    db.commit()
    db.refresh(company)
    return company


def _name_of(db, company):
    db.expire_all()
    return db.get(models.Company, company.id).name


def _backup_files(directory):
    return sorted(directory.glob("company_names_*.json"))


def test_dry_run_no_escribe_en_bd_ni_en_disco(db, tmp_path):
    empty = _company(db, "")
    spaces = _company(db, "   ")
    long_name = _company(db, "A" * 121)
    backup = tmp_path / "backups"

    report = run(db, apply=False, backup_dir=backup)

    assert {change["company_id"] for change in report.changes} == {
        str(empty.id),
        str(spaces.id),
        str(long_name.id),
    }
    assert report.backup_files == []
    assert report.exit_code() == 0
    assert not backup.exists()
    assert _name_of(db, empty) == ""
    assert _name_of(db, spaces) == "   "
    assert _name_of(db, long_name) == "A" * 121


def test_dry_run_por_defecto_de_main_no_escribe(db, tmp_path, capsys):
    empty = _company(db, "")
    backup = tmp_path / "backups"

    code = main(["--backup-dir", str(backup)])

    assert code == 0
    assert not backup.exists()
    assert _name_of(db, empty) == ""
    assert "--dry-run" in capsys.readouterr().out


def test_apply_rellena_nombres_vacios_y_solo_espacios(db):
    empty = _company(db, "")
    spaces = _company(db, "   \t ")

    report = run(db, apply=True, backup_dir=None)

    assert report.backup_files == []
    assert _name_of(db, empty) == "Empresa " + str(empty.id)[:8]
    assert _name_of(db, spaces) == "Empresa " + str(spaces.id)[:8]


def test_apply_recorta_a_120_y_guarda_original_fuera_del_repo(db, tmp_path):
    original = "  " + ("ab" * 80) + "  "  # 164 caracteres con espacios
    company = _company(db, original)
    backup = tmp_path / "backups"

    report = run(db, apply=True, backup_dir=backup)

    assert _name_of(db, company) == ("ab" * 80)[:120]
    assert len(report.backup_files) == 1
    backup_file = report.backup_files[0]
    assert backup_file.parent == backup.resolve()
    assert BACKEND_DIR not in backup_file.parents
    assert json.loads(backup_file.read_text(encoding="utf-8")) == [
        {"company_id": str(company.id), "original_name": original}
    ]


def test_backup_tiene_permisos_0600_y_directorio_0700(db, tmp_path):
    _company(db, "B" * 130)
    backup = tmp_path / "backups_privados"

    report = run(db, apply=True, backup_dir=backup)

    backup_file = report.backup_files[0]
    assert stat.S_IMODE(backup_file.stat().st_mode) == 0o600
    assert stat.S_IMODE(backup.stat().st_mode) == 0o700


def test_apply_con_recortes_sin_backup_dir_falla_y_no_escribe(db, tmp_path):
    long_company = _company(db, LONG_NAME)
    empty = _company(db, "")

    with pytest.raises(SystemExit):
        run(db, apply=True, backup_dir=None)

    assert _name_of(db, long_company) == LONG_NAME
    assert _name_of(db, empty) == ""


def test_main_apply_con_recortes_sin_backup_dir_devuelve_1(db, monkeypatch):
    monkeypatch.delenv("REPAIR_BACKUP_DIR", raising=False)
    long_company = _company(db, LONG_NAME)

    assert main(["--apply"]) == 1
    assert _name_of(db, long_company) == LONG_NAME


def test_segunda_ejecucion_no_cambia_nada(db, tmp_path):
    _company(db, "")
    _company(db, "  Norte  ")
    _company(db, "C" * 150)
    backup = tmp_path / "backups"

    first = run(db, apply=True, backup_dir=backup)
    second = run(db, apply=True, backup_dir=None)

    assert len(first.changes) == 3
    assert second.changes == []
    assert second.backup_files == []
    assert len(_backup_files(backup)) == 1


def test_recorte_que_deja_espacio_final_es_idempotente(db, tmp_path):
    # Tras recortar a 120 el caracter 120 es un espacio; sin rstrip la segunda ejecucion cambiaria el nombre.
    company = _company(db, "a" * 119 + " " + "b" * 20)
    backup = tmp_path / "backups"

    run(db, apply=True, backup_dir=backup)
    assert _name_of(db, company) == "a" * 119
    second = run(db, apply=True, backup_dir=None)

    assert second.changes == []


def test_se_niega_backup_dir_dentro_del_repo(db):
    dentro = BACKEND_DIR / "tests" / "scripts" / "backup_no_permitido"
    _company(db, LONG_NAME)

    with pytest.raises(SystemExit):
        ensure_backup_dir(dentro, required=False)
    with pytest.raises(SystemExit):
        run(db, apply=True, backup_dir=dentro)
    assert not dentro.exists()


def test_main_se_niega_backup_dir_dentro_del_repo(db):
    dentro = BACKEND_DIR / "tests" / "scripts" / "backup_no_permitido"
    _company(db, LONG_NAME)

    assert main(["--apply", "--backup-dir", str(dentro)]) == 1
    assert not dentro.exists()


def test_nombres_validos_no_se_tocan(db, tmp_path):
    names = ["Escuela Norte", "Escuela  Norte Sur", "D" * 120, "Ñandú Ski 2026"]
    companies = [_company(db, name) for name in names]

    report = run(db, apply=True, backup_dir=tmp_path / "backups")

    assert report.changes == []
    assert report.backup_files == []
    for company, name in zip(companies, names):
        assert _name_of(db, company) == name


def test_codigo_de_salida_de_main_y_del_informe(db, tmp_path, capsys):
    _company(db, "")
    assert main(["--apply"]) == 0
    assert "Codigo de salida: 0" in capsys.readouterr().out

    assert RepairReport(topic="x").exit_code() == 0
    assert RepairReport(topic="x", manual=[{"id": 1}]).exit_code() == 2


def test_dry_run_y_apply_son_excluyentes(capsys):
    with pytest.raises(SystemExit):
        parse_args(["--dry-run", "--apply"])


def test_parse_args_usa_variable_de_entorno_para_backup_dir(monkeypatch, tmp_path):
    monkeypatch.setenv("REPAIR_BACKUP_DIR", str(tmp_path))

    args = parse_args([])

    assert args.apply is False
    assert args.backup_dir == tmp_path
