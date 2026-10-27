"""Tests de scripts.repair_settings_definitions (PR-11.R, SQLite, fixtures de tests/conftest.py).

Describen el contrato del script (docs/empresa/plan-implementacion-empresa.md, seccion 9):
- `run(db, *, apply, backup_dir, drop_unknown=())` -> RepairReport y `main(argv) -> int`.
- Con `--apply` solo se escribe el backup JSON (`settings_definitions_before_<ts>.json`, 0600) con el
  valor original de `settings` y `worklog_definitions` de todas las empresas. Solo `--drop-unknown`
  modifica la BD, y solo para claves desconocidas.
- Codigos de salida: 0 sin pendientes de decision manual, 2 con ellos.

Los backups se escriben en tmp_path, siempre fuera del arbol del repositorio. El modulo se importa
dentro de los helpers para que su ausencia haga fallar cada test por separado.
"""

import importlib
import json
import stat

import database
import models
import pytest
from scripts.repair_common import BACKEND_DIR

from tests.factories import make_company

BACKUP_GLOB = "settings_definitions_before_*.json"

CLASSIFY_SETTINGS = {
    "features": {"tutorials": True},
    "billing": {"price_type": "gross", "cost_markup_percent": 32.0},
    "input_mode": "timer",
    "allow_tutorial": True,
    "business_logic": {"cost_markup": 0, "price_type": "net"},
    "allowed_rates": ["particular"],
    "clave_inventada": 1,
}


def _script():
    return importlib.import_module("scripts.repair_settings_definitions")


def _run(db, **kwargs):
    return _script().run(db, **kwargs)


def _main(argv):
    return _script().main(argv)


def _company(db, settings, worklog_definitions=None):
    return make_company(db, settings=settings, worklog_definitions=worklog_definitions)


def _stored(db, company):
    db.expire_all()
    row = db.get(models.Company, company.id)
    return row.settings, row.worklog_definitions


def _settings_of(db, company):
    return _stored(db, company)[0]


def _mentions(items, fragment):
    return any(fragment in str(item) for item in items)


def _all_items(report):
    return [*report.changes, *report.manual, *report.informational]


def _values_of_key(node, key):
    """Todos los valores asociados a `key` en una estructura JSON anidada."""
    found = []
    if isinstance(node, dict):
        for name, value in node.items():
            if name == key:
                found.append(value)
            found.extend(_values_of_key(value, key))
    elif isinstance(node, list):
        for item in node:
            found.extend(_values_of_key(item, key))
    return found


def _backup_files(directory):
    return sorted(directory.glob(BACKUP_GLOB)) if directory.exists() else []


def _load(path):
    return json.loads(path.read_text(encoding="utf-8"))


# (1) clasificacion de claves de settings


def test_clasifica_mapeadas_retiradas_validas_y_desconocidas(db, tmp_path):
    _company(db, CLASSIFY_SETTINGS, {"particular": {"unit": "hours", "label": "Particular"}})

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert _mentions(report.manual, "clave_inventada")
    assert report.exit_code() == 2
    for fragment in ["features", "input_mode", "allow_tutorial", "cost_markup"]:
        assert _mentions(_all_items(report), fragment), f"{fragment} debe aparecer en el informe"
        assert not _mentions(report.manual, fragment), f"{fragment} no es decision manual"
    assert not _mentions(report.manual, "allowed_rates")


# (2) clasificacion de tipos de turno


@pytest.mark.parametrize(
    "definitions, key",
    [
        pytest.param(
            {"tipo_semanal": {"unit": "weekly", "label": "Semanal"}}, "tipo_semanal", id="unit_fuera_de_contrato"
        ),
        pytest.param(
            {"tipo_contradictorio": {"unit": "hours", "is_range": True, "label": "Contradictorio"}},
            "tipo_contradictorio",
            id="hours_con_is_range_true",
        ),
        pytest.param({"tipo_etiqueta_vacia": {"unit": "hours", "label": ""}}, "tipo_etiqueta_vacia", id="label_vacio"),
        pytest.param(
            {"tipo_etiqueta_larga": {"unit": "hours", "label": "x" * 61}},
            "tipo_etiqueta_larga",
            id="label_de_61_caracteres",
        ),
    ],
)
def test_tipos_fuera_de_contrato_son_decision_manual(db, tmp_path, definitions, key):
    _company(db, {}, definitions)

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert _mentions(report.manual, key)
    assert report.exit_code() == 2


def test_unit_fixed_se_acepta_sin_decision_manual(db, tmp_path):
    _company(db, {}, {"fijo": {"unit": "fixed", "label": "Fijo"}, "dias": {"unit": "days", "label": "Dias"}})

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert report.manual == []
    assert report.exit_code() == 0


# (2b) retiradas con valor: cost_markup va al backup antes de borrarse


def _values_in_backup(path):
    payload = _load(path)
    return {
        "cost_markup_percent": _values_of_key(payload, "cost_markup_percent"),
        "cost_markup": _values_of_key(payload, "cost_markup"),
    }


def test_cost_markup_retirado_queda_en_backup_con_permisos_0600(db, tmp_path):
    masski = _company(db, {"billing": {"cost_markup_percent": 32.0}})
    querkus = _company(db, {"business_logic": {"cost_markup": 0}})
    backup = tmp_path / "backups"

    report = _run(db, apply=True, backup_dir=backup)

    files = _backup_files(backup)
    assert len(files) == 1
    assert stat.S_IMODE(files[0].stat().st_mode) == 0o600
    assert report.backup_files == files
    values = _values_in_backup(files[0])
    assert values["cost_markup_percent"] == [32.0]
    assert values["cost_markup"] == [0]
    assert str(masski.id) in files[0].read_text(encoding="utf-8")
    assert str(querkus.id) in files[0].read_text(encoding="utf-8")


# (3) is_range sin unit: informativo


def test_is_range_sin_unit_es_informativo_y_no_bloquea(db, tmp_path):
    _company(db, {}, {"legado": {"is_range": True, "label": "Legado"}})

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert _mentions(report.informational, "legado")
    assert report.manual == []
    assert report.exit_code() == 0


# (3b) valores fuera de contrato: decision manual, igual que en la migracion


@pytest.mark.parametrize(
    "settings, key",
    [
        pytest.param({"billing": {"price_type": "bruto"}}, "price_type", id="billing_price_type_fuera"),
        pytest.param({"billing": {"price_type": None}}, "price_type", id="billing_price_type_null"),
        pytest.param({"input_mode": "rapido"}, "input_mode", id="input_mode_fuera"),
        pytest.param({"modules": {"tutorials": "si"}}, "tutorials", id="modules_no_booleano"),
        pytest.param({"features": {"night_shifts": 1}}, "night_shifts", id="features_no_booleano"),
    ],
)
def test_valores_fuera_de_contrato_son_decision_manual(db, tmp_path, settings, key):
    _company(db, settings)

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert _mentions(report.manual, key)
    assert report.exit_code() == 2


def test_billing_price_type_valido_no_es_decision_manual(db, tmp_path):
    _company(db, {"billing": {"price_type": "gross"}, "input_mode": "bulk", "features": {"tutorials": False}})

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert report.manual == []
    assert _mentions(report.informational, "business_logic.price_type")


# (3c) is_range con unit explicito: la migracion lo borra, se informa

def test_is_range_con_unit_explicito_se_informa_como_borrado(db, tmp_path):
    _company(db, {}, {"dias": {"unit": "days", "is_range": True, "label": "Dias"}})

    report = _run(db, apply=False, backup_dir=tmp_path / "backups")

    assert _mentions(report.informational, "is_range_borrado")
    assert report.manual == []
    assert report.exit_code() == 0


# (4) dry-run no escribe


def test_dry_run_no_escribe_en_bd_ni_en_disco(db, tmp_path):
    company = _company(db, CLASSIFY_SETTINGS, {"particular": {"unit": "hours", "label": "Particular"}})
    before = _stored(db, company)
    backup = tmp_path / "backups"

    report = _run(db, apply=False, backup_dir=backup)

    assert report.backup_files == []
    assert _backup_files(backup) == []
    assert _stored(db, company) == before


# (5) apply sin drop-unknown: BD intacta, backup completo fuera del repo


def test_apply_sin_drop_unknown_no_cambia_bd_y_escribe_backup_completo_fuera_del_repo(db, tmp_path):
    first = _company(db, CLASSIFY_SETTINGS, {"particular": {"unit": "hours", "label": "Particular"}})
    second = _company(db, {"input_mode": "bulk"}, {"fijo": {"unit": "fixed", "label": "Fijo"}})
    before_first = _stored(db, first)
    before_second = _stored(db, second)
    backup = tmp_path / "backups"

    report = _run(db, apply=True, backup_dir=backup)

    assert _stored(db, first) == before_first
    assert _stored(db, second) == before_second
    files = _backup_files(backup)
    assert len(files) == 1
    assert report.backup_files == files
    text = files[0].read_text(encoding="utf-8")
    assert str(first.id) in text
    assert str(second.id) in text
    assert _values_of_key(_load(files[0]), "clave_inventada") == [1]
    repo_root = BACKEND_DIR.parent.resolve()
    assert repo_root not in files[0].resolve().parents


# (6) --drop-unknown elimina solo la clave indicada y la guarda en el backup


def test_drop_unknown_elimina_solo_la_clave_indicada_y_la_guarda(db, tmp_path):
    company = _company(db, {"foo": 1, "bar": 2, "allow_tutorial": True})
    backup = tmp_path / "backups"

    _run(db, apply=True, backup_dir=backup, drop_unknown=["foo"])

    settings = _settings_of(db, company)
    assert "foo" not in settings
    assert settings["bar"] == 2
    assert settings["allow_tutorial"] is True
    files = _backup_files(backup)
    assert len(files) == 1
    assert _values_of_key(_load(files[0]), "foo") == [1]


# (7) --drop-unknown de claves mapeadas o validas: rechazado


@pytest.mark.parametrize("key", ["features", "input_mode", "business_logic", "allowed_rates"])
def test_drop_unknown_rechaza_claves_mapeadas_o_validas(db, tmp_path, key):
    company = _company(
        db,
        {
            "features": {"tutorials": True},
            "input_mode": "timer",
            "business_logic": {"price_type": "net"},
            "allowed_rates": ["particular"],
        },
    )
    before = _stored(db, company)

    with pytest.raises((SystemExit, ValueError)):
        _run(db, apply=True, backup_dir=tmp_path / "backups", drop_unknown=[key])

    assert _stored(db, company) == before


# (8) idempotencia


def test_apply_con_drop_unknown_es_idempotente(db, tmp_path):
    company = _company(db, {"foo": 1, "features": {"tutorials": True}})
    _run(db, apply=True, backup_dir=tmp_path / "b1", drop_unknown=["foo"])
    first = _stored(db, company)

    second_report = _run(db, apply=True, backup_dir=tmp_path / "b2", drop_unknown=["foo"])

    assert _stored(db, company) == first
    assert second_report.exit_code() == 0


# (9) codigos de salida 0 y 2 desde main


def test_main_devuelve_0_sin_pendientes_y_2_con_desconocidas(db, tmp_path, monkeypatch):
    # main() abre su propia sesion. Con PostgreSQL el fixture `db` vive en una transaccion externa que
    # no es visible desde otra conexion, asi que main debe usar la sesion del fixture.
    monkeypatch.setattr(database, "SessionLocal", lambda: db)
    _company(db, {"features": {"tutorials": True}}, {"fijo": {"unit": "fixed", "label": "Fijo"}})
    backup = tmp_path / "backups"

    assert _main(["--dry-run"]) == 0

    _company(db, {"clave_inventada": 1})

    assert _main(["--dry-run"]) == 2
    assert _main(["--apply", "--backup-dir", str(backup)]) == 2
    assert len(_backup_files(backup)) == 1


# Seguridad: negativa a escribir dentro del repositorio


def test_se_niega_backup_dir_dentro_del_repo(db):
    company = _company(db, {"clave_inventada": 1})
    dentro = BACKEND_DIR / "tmp_backup_settings_definitions"

    with pytest.raises(SystemExit):
        _run(db, apply=True, backup_dir=dentro)

    assert not dentro.exists()
    assert _settings_of(db, company) == {"clave_inventada": 1}


def test_main_se_niega_backup_dir_dentro_del_repo(db):
    _company(db, {"clave_inventada": 1})
    dentro = BACKEND_DIR / "tmp_backup_settings_definitions_main"

    assert _main(["--apply", "--backup-dir", str(dentro)]) == 1
    assert not dentro.exists()


def test_main_muestra_el_detalle_de_un_error_de_disco(db, tmp_path, monkeypatch, capsys):
    _company(db, {"clave_inventada": 1})

    def sin_espacio(*args, **kwargs):
        raise OSError(28, "No queda espacio en el dispositivo")

    monkeypatch.setattr(_script(), "write_backup", sin_espacio)

    assert _main(["--apply", "--backup-dir", str(tmp_path / "backups")]) == 1
    err = capsys.readouterr().err
    assert "OSError" in err
    assert "No queda espacio en el dispositivo" in err
