"""Migracion b7e1a0d10005 (normalizar settings y tipos de turno) sobre PostgreSQL real (PR-11).

Los tests que tocan la BD llevan el marcador `postgres` y requieren TEST_DATABASE_URL. El fixture
`db` revierte la transaccion al final, asi que los datos y los cambios de la migracion no persisten.
Los tests de fichero (revision y ausencia de DDL) no necesitan base de datos y se ejecutan siempre.
"""

import importlib.util
from pathlib import Path

import models
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.factories import make_company

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1]
    / "migrations"
    / "versions"
    / "b7e1a0d10005_normalize_settings_and_definitions.py"
)
REPAIR_HINT = "repair_settings_definitions.py"
FORBIDDEN_DDL = ("op.alter_column", "op.drop_column", "op.add_column")

needs_postgres = pytest.mark.postgres


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_b7e1a0d10005", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(db, step: str):
    module = _load_migration()
    context = MigrationContext.configure(connection=db.connection())
    with Operations.context(context):
        getattr(module, step)()


def _company(db, settings, worklog_definitions=None):
    return make_company(db, settings=settings, worklog_definitions=worklog_definitions)


def _stored(db, company):
    db.expire_all()
    row = db.get(models.Company, company.id)
    return row.settings, row.worklog_definitions


def _settings_of(db, company):
    return _stored(db, company)[0]


def _definitions_of(db, company):
    return _stored(db, company)[1]


def _without_empty_sections(settings):
    """Quita secciones vacias (`billing: {}`) que puede dejar la retirada de una clave."""
    return {key: value for key, value in settings.items() if value != {}}


def _assert_aborts_without_changes(db, company):
    before = _stored(db, company)

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    message = str(exc.value)
    assert str(company.id) in message
    assert REPAIR_HINT in message
    assert _stored(db, company) == before


# --- Ficheros (sin base de datos) ---


def test_migration_file_declares_expected_revisions():
    module = _load_migration()

    assert module.revision == "b7e1a0d10005"
    assert module.down_revision == "b7e1a0d10004"


def test_migration_only_updates_data_without_ddl():
    text = MIGRATION_PATH.read_text(encoding="utf-8")

    for fragment in FORBIDDEN_DDL:
        assert fragment not in text, f"la migracion no debe usar {fragment}: solo UPDATE de datos"


@pytest.mark.parametrize(
    "settings",
    [
        pytest.param({"billing": {"price_type": "gross"}}, id="billing_price_type_valido"),
        pytest.param({"input_mode": "bulk"}, id="input_mode_valido"),
        pytest.param({"input_mode": None}, id="input_mode_null_se_ignora"),
        pytest.param({"modules": {"tutorials": True}, "features": {"night_shifts": False}}, id="modulos_booleanos"),
        pytest.param({"modules": None}, id="modules_null"),
    ],
)
def test_valores_validos_no_son_problemas(settings):
    assert _load_migration()._settings_problems(settings) == []


@pytest.mark.parametrize(
    "settings, fragment",
    [
        pytest.param({"billing": {"price_type": "bruto"}}, "billing.price_type", id="billing_price_type_fuera"),
        pytest.param({"billing": {"price_type": None}}, "billing.price_type", id="billing_price_type_null"),
        pytest.param({"input_mode": "rapido"}, "input_mode", id="input_mode_fuera"),
        pytest.param({"input_mode": ["timer"]}, "input_mode", id="input_mode_no_texto"),
        pytest.param({"modules": {"tutorials": "si"}}, "modules.tutorials", id="modules_no_booleano"),
        pytest.param({"modules": {"tutorials": 1}}, "modules.tutorials", id="modules_entero_no_booleano"),
        pytest.param({"features": {"night_shifts": None}}, "features.night_shifts", id="features_no_booleano"),
    ],
)
def test_valores_fuera_de_contrato_son_problemas(settings, fragment):
    problems = _load_migration()._settings_problems(settings)

    assert any(fragment in problem for problem in problems), problems


def test_constantes_de_la_migracion_coinciden_con_contratos_y_script():
    import typing

    import contracts

    from scripts import repair_settings_definitions as script

    migration = _load_migration()

    assert migration.VALID_SETTINGS_KEYS == set(contracts.CompanySettings.model_fields)
    assert migration.MAPPED_KEYS == set(script.MAPPED_TOP)
    assert migration.RETIRED_KEYS == set(script.RETIRED_TOP)
    assert migration.BILLING_KNOWN_KEYS == set(script.BILLING_KNOWN)
    assert migration.OBJECT_BLOCKS == script.OBJECT_BLOCKS
    assert migration.UNITS == script.UNITS
    assert migration.LABEL_MAX == script.LABEL_MAX
    assert migration.PRICE_TYPES == script.PRICE_TYPES
    assert migration.INPUT_MODES == script.INPUT_MODES
    assert migration.PRICE_TYPES == typing.get_args(contracts.BusinessLogic.model_fields["price_type"].annotation)
    assert migration.INPUT_MODES == typing.get_args(
        contracts.WorkerExperience.model_fields["input_mode"].annotation
    )
    assert migration.UNITS == typing.get_args(contracts.WorklogDefinition.model_fields["unit"].annotation)
    label_schema = contracts.WorklogDefinition.model_json_schema()["properties"]["label"]
    assert migration.LABEL_MAX == label_schema["maxLength"]


# --- Mapeo de claves de settings ---


@needs_postgres
def test_features_se_mapea_a_modules(db):
    company = _company(db, {"features": {"tutorials": True, "night_shifts": False}})

    _run(db, "upgrade")

    settings = _settings_of(db, company)
    assert settings["modules"] == {"tutorials": True, "night_shifts": False}
    assert "features" not in settings


@needs_postgres
def test_billing_price_type_se_mapea_a_business_logic(db):
    company = _company(db, {"billing": {"price_type": "gross"}})

    _run(db, "upgrade")

    settings = _settings_of(db, company)
    assert settings["business_logic"]["price_type"] == "gross"
    assert "price_type" not in settings.get("billing", {})


@needs_postgres
def test_input_mode_de_la_raiz_se_mapea_a_worker_experience(db):
    company = _company(db, {"input_mode": "timer"})

    _run(db, "upgrade")

    settings = _settings_of(db, company)
    assert settings["worker_experience"]["input_mode"] == "timer"
    assert "input_mode" not in settings


@needs_postgres
def test_allowed_rates_se_conserva(db):
    company = _company(db, {"allowed_rates": ["particular"], "modules": {"tutorials": True}})

    _run(db, "upgrade")

    assert _settings_of(db, company)["allowed_rates"] == ["particular"]


# --- Retirada de claves ---


@needs_postgres
@pytest.mark.parametrize(
    "before, expected",
    [
        pytest.param({"allow_tutorial": True}, {}, id="allow_tutorial"),
        pytest.param({"allow_coordination": False}, {}, id="allow_coordination"),
        pytest.param({"is_managed": True}, {}, id="is_managed"),
        pytest.param(
            {"business_logic": {"cost_markup": 0, "price_type": "gross"}},
            {"business_logic": {"price_type": "gross"}},
            id="business_logic_cost_markup",
        ),
        pytest.param({"billing": {"cost_markup_percent": 32.0}}, {}, id="billing_cost_markup_percent"),
    ],
)
def test_claves_retiradas_se_eliminan(db, before, expected):
    company = _company(db, before)

    _run(db, "upgrade")

    assert _without_empty_sections(_settings_of(db, company)) == expected


# --- Mapeo de tipos de turno: is_range ---


@needs_postgres
@pytest.mark.parametrize(
    "definition, expected_unit",
    [
        pytest.param({"label": "A", "is_range": True}, "days", id="is_range_true_sin_unit"),
        pytest.param({"label": "A", "is_range": False}, "hours", id="is_range_false_sin_unit"),
        pytest.param({"label": "A"}, "hours", id="sin_unit_ni_is_range"),
        pytest.param({"label": "A", "unit": "fixed", "is_range": True}, "fixed", id="fixed_se_conserva"),
        pytest.param({"label": "A", "unit": "days"}, "days", id="days_se_conserva"),
        pytest.param({"label": "A", "unit": "hours"}, "hours", id="hours_se_conserva"),
    ],
)
def test_is_range_se_convierte_a_unit_y_se_borra(db, definition, expected_unit):
    company = _company(db, {}, {"tipo": definition})

    _run(db, "upgrade")

    migrated = _definitions_of(db, company)["tipo"]
    assert migrated["unit"] == expected_unit
    assert "is_range" not in migrated
    assert migrated["label"] == "A"


@needs_postgres
def test_downgrade_restaura_is_range_solo_para_days(db):
    company = _company(
        db,
        {},
        {"dias": {"unit": "days", "label": "Dias"}, "horas": {"unit": "hours", "label": "Horas"}},
    )
    _run(db, "upgrade")

    _run(db, "downgrade")

    definitions = _definitions_of(db, company)
    assert definitions["dias"].get("is_range") is True
    assert definitions["horas"].get("is_range") is not True


# --- Abortos: datos que la migracion no puede normalizar ---


@needs_postgres
@pytest.mark.parametrize(
    "settings, worklog_definitions",
    [
        pytest.param(
            {"features": {"tutorials": True}, "clave_inventada": 1},
            None,
            id="clave_de_settings_desconocida",
        ),
        pytest.param({}, {"tipo": {"unit": "weekly", "label": "T"}}, id="unit_no_soportado"),
        pytest.param({}, {"tipo": {"unit": "hours", "is_range": True, "label": "T"}}, id="hours_con_is_range_true"),
        pytest.param({}, {"tipo": {"unit": "hours", "label": ""}}, id="label_vacio"),
        pytest.param({}, {"tipo": {"unit": "hours", "label": "x" * 61}}, id="label_de_61_caracteres"),
        pytest.param({"billing": {"price_type": "bruto"}}, None, id="billing_price_type_fuera_de_contrato"),
        pytest.param({"input_mode": "rapido"}, None, id="input_mode_fuera_de_contrato"),
        pytest.param({"modules": {"tutorials": "si"}}, None, id="modules_no_booleano"),
        pytest.param({"features": {"night_shifts": 1}}, None, id="features_no_booleano"),
    ],
)
def test_upgrade_aborts_without_changes_on_data_it_cannot_normalize(db, settings, worklog_definitions):
    company = _company(db, settings, worklog_definitions)

    _assert_aborts_without_changes(db, company)


@needs_postgres
def test_abort_on_one_company_keeps_valid_companies_unchanged(db):
    valid = _company(db, {"features": {"tutorials": True}}, {"tipo": {"unit": "days", "label": "Dias"}})
    broken = _company(db, {"clave_inventada": 1})
    before_valid = _stored(db, valid)

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    assert str(broken.id) in str(exc.value)
    assert _stored(db, valid) == before_valid


# --- Reparacion previa: tras eliminar la clave desconocida la migracion pasa ---


@needs_postgres
def test_upgrade_passes_after_drop_unknown_of_the_offending_key(db, tmp_path):
    # Import local: un script ausente no impide recoger (ni ejecutar) el resto de pruebas.
    from scripts import repair_settings_definitions

    company = _company(db, {"clave_inventada": 1, "features": {"tutorials": True}})
    _assert_aborts_without_changes(db, company)

    repair_settings_definitions.run(db, apply=True, backup_dir=tmp_path, drop_unknown=["clave_inventada"])
    _run(db, "upgrade")

    settings = _settings_of(db, company)
    assert "clave_inventada" not in settings
    assert settings["modules"] == {"tutorials": True}
