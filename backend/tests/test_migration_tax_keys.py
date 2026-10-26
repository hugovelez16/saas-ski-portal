"""Migracion b7e1a0d10004 (unificar claves de tax_overrides) sobre PostgreSQL real (PR-10).

Requiere TEST_DATABASE_URL. El fixture `db` revierte la transaccion al final, asi que los datos
y los cambios de la migracion no persisten.
"""

import importlib.util
from pathlib import Path

import models
import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations

from tests.factories import make_company, make_member, make_user

pytestmark = pytest.mark.postgres

MIGRATION_PATH = (
    Path(__file__).resolve().parents[1] / "migrations" / "versions" / "b7e1a0d10004_unify_tax_override_keys.py"
)
ERROR_FRAGMENT = "valores de impuestos no validos"


def _load_migration():
    spec = importlib.util.spec_from_file_location("migration_b7e1a0d10004", MIGRATION_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _run(db, step: str):
    module = _load_migration()
    context = MigrationContext.configure(connection=db.connection())
    with Operations.context(context):
        getattr(module, step)()


def _member(db, tax_config, overrides, *, tipo="particular", rates_config=None):
    company = make_company(db, tax_config=tax_config)
    rates = (
        rates_config
        if rates_config is not None
        else {tipo: {"base_rate": 20.0, "is_gross": True, "tax_overrides": overrides}}
    )
    member = make_member(db, make_user(db), company, rates_config=rates)
    db.flush()
    return company, member


def _rates_of(db, member):
    db.expire_all()
    return db.get(models.CompanyMember, (member.user_id, member.company_id)).rates_config


def _overrides_of(db, member, tipo="particular"):
    return _rates_of(db, member)[tipo]["tax_overrides"]


def _tax_config_of(db, company):
    db.expire_all()
    return db.get(models.Company, company.id).tax_config


def _assert_aborts_without_changes(db, member, company, expected_in_message=()):
    rates_before = _rates_of(db, member)
    tax_before = _tax_config_of(db, company)

    with pytest.raises(RuntimeError) as exc:
        _run(db, "upgrade")

    message = str(exc.value)
    assert ERROR_FRAGMENT in message
    assert "repair_tax_values.py" in message
    for fragment in expected_in_message:
        assert fragment in message
    assert _rates_of(db, member) == rates_before
    assert _tax_config_of(db, company) == tax_before


def test_migration_file_declares_expected_revisions():
    module = _load_migration()

    assert module.revision == "b7e1a0d10004"
    assert module.down_revision == "b7e1a0d10002"


def test_upgrade_renames_keys_and_removes_zero_extra_not_defined_by_company(db):
    _, member = _member(db, {"IRPF": 0.15}, {"ss": 0.06, "irpf": 0.15, "extra": 0})

    _run(db, "upgrade")

    assert _overrides_of(db, member) == {"social_security": 0.06, "irpf_base": 0.15}


def test_downgrade_reverts_renaming_without_recreating_extra(db):
    company, member = _member(db, {"IRPF": 0.15}, {"ss": 0.06, "irpf": 0.15, "extra": 0})
    _run(db, "upgrade")

    _run(db, "downgrade")

    assert _overrides_of(db, member) == {"ss": 0.06, "irpf": 0.15}
    assert _tax_config_of(db, company) == {"IRPF": 0.15}


def test_downgrade_does_not_overwrite_existing_destination_key(db):
    _, member = _member(db, {}, {"social_security": 0.06, "ss": 0.01})

    _run(db, "downgrade")

    assert _overrides_of(db, member)["ss"] == 0.01


def test_zero_extra_defined_by_company_is_kept(db):
    _, member = _member(db, {"extra": 0.02}, {"ss": 0.06, "extra": 0})

    _run(db, "upgrade")

    assert _overrides_of(db, member) == {"social_security": 0.06, "extra": 0}


def test_null_extra_is_kept(db):
    _, member = _member(db, {}, {"extra": None})

    _run(db, "upgrade")

    assert _overrides_of(db, member) == {"extra": None}


@pytest.mark.parametrize("value", [0.05, 1, "abc", 15, True], ids=["0.05", "uno", "abc", "15", "true"])
def test_upgrade_aborts_without_changes_when_extra_is_not_zero(db, value):
    company, member = _member(db, {}, {"ss": 0.06, "extra": value})

    _assert_aborts_without_changes(db, member, company, ["tax_overrides.extra", str(company.id)])


@pytest.mark.parametrize("value", [-0.1, 1.5, 15, "abc", "0.15", "15", True, False, None])
def test_upgrade_aborts_without_changes_on_invalid_value_in_tax_config(db, value):
    company, member = _member(db, {"IRPF": value}, {"ss": 0.06})

    _assert_aborts_without_changes(db, member, company, ["tax_config.IRPF", str(company.id)])
    assert _overrides_of(db, member) == {"ss": 0.06}


@pytest.mark.parametrize("value", [-0.1, 1.5, 15, "abc", "0.15", "15", True, False])
def test_upgrade_aborts_without_changes_on_invalid_value_in_tax_overrides(db, value):
    company, member = _member(db, {"IRPF": 0.15}, {"ss": 0.06, "IRPF": value})

    _assert_aborts_without_changes(db, member, company, ["tax_overrides.IRPF", str(company.id)])
    assert _overrides_of(db, member)["ss"] == 0.06


@pytest.mark.parametrize(
    "tax_config",
    [
        {"": 0.1},
        {"   ": 0.1},
        {"A" * 51: 0.1},
        {f"T{i}": 0.01 for i in range(21)},
        {"IRPF": 0.15, "IRPF ": 0.1},
    ],
    ids=["vacio", "espacios", "51-caracteres", "21-entradas", "duplicado-tras-strip"],
)
def test_upgrade_aborts_without_changes_on_invalid_tax_config_names(db, tax_config):
    company, member = _member(db, tax_config, {"ss": 0.06})

    _assert_aborts_without_changes(db, member, company, [str(company.id)])
    assert _overrides_of(db, member) == {"ss": 0.06}


def test_tax_config_with_20_entries_and_50_char_name_is_valid(db):
    tax_config = {f"T{i}": 0.01 for i in range(19)}
    tax_config["A" * 50] = 0.1
    _, member = _member(db, tax_config, {"ss": 0.06})

    _run(db, "upgrade")

    assert _overrides_of(db, member) == {"social_security": 0.06}


@pytest.mark.parametrize(
    "overrides",
    [{"ss": 0.06, "social_security": 0.07}, {"irpf": 0.15, "irpf_base": 0.2}],
    ids=["ss", "irpf"],
)
def test_upgrade_aborts_on_key_collision(db, overrides):
    company, member = _member(db, {}, overrides)

    _assert_aborts_without_changes(db, member, company, [str(company.id)])
    assert _overrides_of(db, member) == overrides


def test_abort_does_not_change_other_valid_members(db):
    company, bad = _member(db, {}, {"extra": 0.05})
    good = make_member(db, make_user(db), company, rates_config={"particular": {"tax_overrides": {"ss": 0.06}}})
    db.flush()

    with pytest.raises(RuntimeError):
        _run(db, "upgrade")

    assert _overrides_of(db, good) == {"ss": 0.06}
    assert _overrides_of(db, bad) == {"extra": 0.05}


def test_upgrade_passes_after_repair_script_converts_numeric_strings(db, tmp_path):
    # Import local: asi un script ausente no impide recoger (ni ejecutar) el resto de pruebas.
    from scripts import repair_tax_values

    company, member = _member(db, {"IRPF": "0.15"}, {"ss": "0.06", "irpf": "0.15", "extra": "0"})
    _assert_aborts_without_changes(db, member, company)

    repair_tax_values.run(db, apply=True, backup_dir=tmp_path)
    _run(db, "upgrade")

    assert _tax_config_of(db, company) == {"IRPF": 0.15}
    assert _overrides_of(db, member) == {"social_security": 0.06, "irpf_base": 0.15}


def test_manual_decision_value_keeps_aborting_until_fixed_by_hand(db, tmp_path):
    from scripts import repair_tax_values

    company, member = _member(db, {"IRPF": 15}, {"ss": "0.06"})

    report = repair_tax_values.run(db, apply=True, backup_dir=tmp_path)
    assert report.exit_code() == 2
    _assert_aborts_without_changes(db, member, company, ["tax_config.IRPF"])

    company.tax_config = {"IRPF": 0.15}
    db.flush()
    _run(db, "upgrade")

    assert _overrides_of(db, member) == {"social_security": 0.06}


def test_upgrade_twice_is_idempotent(db):
    _, member = _member(db, {}, {"ss": 0.06, "irpf": 0.15, "extra": 0})

    _run(db, "upgrade")
    first = _rates_of(db, member)
    _run(db, "upgrade")

    assert _rates_of(db, member) == first
    assert _overrides_of(db, member) == {"social_security": 0.06, "irpf_base": 0.15}


def test_downgrade_twice_is_idempotent(db):
    _, member = _member(db, {}, {"social_security": 0.06, "irpf_base": 0.15})

    _run(db, "downgrade")
    first = _rates_of(db, member)
    _run(db, "downgrade")

    assert _rates_of(db, member) == first
    assert _overrides_of(db, member) == {"ss": 0.06, "irpf": 0.15}


def test_non_dict_entries_in_rates_config_are_ignored(db):
    rates = {
        "particular": 30.0,
        "texto": "abc",
        "lista": [1, 2],
        "sin_overrides": {"base_rate": 10.0},
        "overrides_no_dict": {"tax_overrides": "foo"},
        "valida": {"base_rate": 5.0, "tax_overrides": {"ss": 0.06}},
    }
    _, member = _member(db, {}, None, rates_config=rates)

    _run(db, "upgrade")

    after = _rates_of(db, member)
    assert after["particular"] == 30.0
    assert after["texto"] == "abc"
    assert after["lista"] == [1, 2]
    assert after["sin_overrides"] == {"base_rate": 10.0}
    assert after["overrides_no_dict"] == {"tax_overrides": "foo"}
    assert after["valida"]["tax_overrides"] == {"social_security": 0.06}

    _run(db, "downgrade")

    assert _rates_of(db, member)["valida"]["tax_overrides"] == {"ss": 0.06}


def test_null_tax_overrides_is_respected(db):
    _, member = _member(db, {}, None)

    _run(db, "upgrade")

    assert _overrides_of(db, member) is None


def test_renames_in_every_job_type(db):
    _, member = _member(
        db,
        {},
        None,
        rates_config={
            "particular": {"tax_overrides": {"ss": 0.06}},
            "grupo": {"tax_overrides": {"irpf": 0.15, "extra": 0}},
        },
    )

    _run(db, "upgrade")

    assert _overrides_of(db, member, "particular") == {"social_security": 0.06}
    assert _overrides_of(db, member, "grupo") == {"irpf_base": 0.15}


def test_rows_without_changes_are_left_untouched(db):
    _, member = _member(db, {"IRPF": 0.15}, {"IRPF": 0.2, "Mutua": 0.01})
    before = _rates_of(db, member)

    _run(db, "upgrade")

    assert _rates_of(db, member) == before
