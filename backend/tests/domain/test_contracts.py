"""
Contratos de settings, tipos de turno y tarifas (PR-11, F2/F3/F4/F5).

Describen el comportamiento objetivo de PR-11.1 en `contracts.py`:
- `CompanySettings`: defaults, `extra="forbid"` con las claves retiradas, y lectura tolerante
  `from_db` que descarta claves desconocidas con `logging.warning`.
- `WorklogDefinition` / `WorklogDefinitions`: `unit` obligatorio en `hours|days|fixed`, `label` 1..60.
- `RateEntry` / `RatesConfig`: `base_rate >= 0`, `is_gross` por defecto False, `tax_overrides` 0..1,
  `extras` con `value >= 0`, y limites de numero de claves y de tamano.
- F5: los `default={...}` mutables de los modelos se sustituyen por callables (`default=dict`).

El modulo `contracts` existe, pero los simbolos de PR-11 aun no: las pruebas fallan con
AttributeError hasta implementar PR-11.1. Los tests de la capa de API estan en
`tests/routers/test_company_contracts.py`.
"""

import logging
from datetime import date

import contracts
import models
import pytest
from pydantic import ValidationError

from tests.factories import make_company, make_user

LABEL_MAX = 60
KEY_MAX = 50
RATES_MANY_KEYS = 1000
RATES_HUGE_TEXT = 1_000_000


def _settings(payload):
    return contracts.CompanySettings.model_validate(payload)


def _definition(payload):
    return contracts.WorklogDefinition.model_validate(payload)


def _rate(payload):
    return contracts.RateEntry.model_validate(payload)


# --- CompanySettings: defaults ---


def test_company_settings_defaults_match_contract():
    dumped = contracts.CompanySettings().model_dump()

    assert dumped == {"default_is_gross": False}


def test_company_settings_accepts_valid_full_document():
    settings = _settings({"default_is_gross": True})

    assert settings.default_is_gross is True


# --- CompanySettings: extra="forbid" y tipos ---


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"allow_tutorial": True}, id="allow_tutorial"),
        pytest.param({"allow_coordination": True}, id="allow_coordination"),
        pytest.param({"is_managed": True}, id="is_managed"),
        pytest.param({"business_logic": {"price_type": "gross"}}, id="business_logic_retirada"),
        pytest.param({"worker_experience": {"input_mode": "timer"}}, id="worker_experience_retirada"),
        pytest.param({"ui_customization": {"labels": {"worklog": "Turno"}}}, id="ui_customization_retirada"),
        pytest.param({"modules": {"tutorials": True}}, id="modules_fuera_de_settings"),
        pytest.param({"allowed_rates": ["particular"]}, id="allowed_rates_retirada"),
        pytest.param({"price_type": "net"}, id="price_type_retirada"),
        pytest.param({"clave_inventada": 1}, id="clave_desconocida"),
        pytest.param({"default_is_gross": "si"}, id="default_is_gross_no_booleano"),
    ],
)
def test_company_settings_forbids_retired_unknown_and_wrong_typed_keys(payload):
    with pytest.raises(ValidationError):
        _settings(payload)


# --- CompanySettings.from_db: lectura tolerante ---


def test_from_db_none_returns_defaults():
    settings = contracts.CompanySettings.from_db(None)

    assert settings.model_dump() == contracts.CompanySettings().model_dump()


def test_from_db_empty_dict_returns_defaults():
    settings = contracts.CompanySettings.from_db({})

    assert settings.model_dump() == contracts.CompanySettings().model_dump()


def test_from_db_ignores_unknown_and_retired_keys_and_logs_warning(caplog):
    raw = {
        "allow_tutorial": True,
        "business_logic": {"price_type": "gross"},
        "modules": {"tutorials": True},
        "default_is_gross": True,
        "_platform": {"plan": "pro"},
    }

    with caplog.at_level(logging.WARNING):
        settings = contracts.CompanySettings.from_db(raw)

    dumped = settings.model_dump()
    assert dumped == {"default_is_gross": True}
    assert any(record.levelno == logging.WARNING for record in caplog.records)


def test_from_db_without_unknown_keys_does_not_warn(caplog):
    with caplog.at_level(logging.WARNING):
        contracts.CompanySettings.from_db({"default_is_gross": True, "_platform": {"plan": "free"}})

    assert not [record for record in caplog.records if record.levelno == logging.WARNING]


# --- PlatformSettings ---


def test_platform_settings_defaults_and_full_document():
    assert contracts.PlatformSettings().model_dump() == {
        "plan": None,
        "limits": {"max_monitors": None, "max_managers": None},
        "modules": {},
    }

    full = contracts.PlatformSettings.model_validate(
        {
            "plan": "pro",
            "limits": {"max_monitors": 15, "max_managers": 3},
            "modules": {"daily_report": True},
        }
    )
    assert full.plan == "pro"
    assert full.limits.max_monitors == 15
    assert full.limits.max_managers == 3
    assert full.modules == {"daily_report": True}


def test_platform_settings_forbids_unknown_and_invalid_values():
    with pytest.raises(ValidationError):
        contracts.PlatformSettings.model_validate({"default_is_gross": True})
    with pytest.raises(ValidationError):
        contracts.PlatformSettings.model_validate({"limits": {"max_monitors": -1}})


def test_platform_settings_from_db_filters_invalid_modules_with_warning(caplog):
    raw = {"plan": "basic", "modules": {"tutorials": True, "bad": "si"}, "legacy": 1}

    with caplog.at_level(logging.WARNING):
        ps = contracts.PlatformSettings.from_db(raw)

    assert ps.model_dump() == {
        "plan": "basic",
        "limits": {"max_monitors": None, "max_managers": None},
        "modules": {"tutorials": True},
    }
    assert any(record.levelno == logging.WARNING for record in caplog.records)


@pytest.mark.parametrize(
    "plan, expected_monitors, expected_managers",
    [
        ("pista_verde", 10, 1),
        ("pista_azul", 25, 2),
        ("pista_roja", 50, None),
    ],
)
def test_platform_settings_applies_commercial_plan_presets(plan, expected_monitors, expected_managers):
    ps = contracts.PlatformSettings.model_validate({"plan": plan})
    assert ps.limits.max_monitors == expected_monitors
    assert ps.limits.max_managers == expected_managers

    from_db = contracts.PlatformSettings.from_db({"plan": plan})
    assert from_db.limits.max_monitors == expected_monitors
    assert from_db.limits.max_managers == expected_managers


def test_platform_settings_personalizado_keeps_custom_limits():
    ps = contracts.PlatformSettings.model_validate(
        {"plan": "personalizado", "limits": {"max_monitors": 35, "max_managers": 4}}
    )
    assert ps.limits.max_monitors == 35
    assert ps.limits.max_managers == 4


# --- WorklogDefinition ---


@pytest.mark.parametrize("unit", ["hours", "days", "fixed"])
def test_worklog_definition_accepts_contract_units(unit):
    definition = _definition({"unit": unit, "label": "Turno"})

    assert definition.unit == unit
    assert definition.options == []
    assert definition.is_active is True


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"unit": "weekly", "label": "Semanal"}, id="unit_fuera_de_contrato"),
        pytest.param({"unit": None, "label": "Turno"}, id="unit_null"),
        pytest.param({"label": "Turno"}, id="unit_ausente"),
        pytest.param({"is_range": True, "label": "Turno"}, id="solo_is_range_sin_unit"),
        pytest.param({"unit": "hours", "label": ""}, id="label_vacio"),
        pytest.param({"unit": "hours", "label": "x" * (LABEL_MAX + 1)}, id="label_de_61_caracteres"),
        pytest.param({"unit": "hours"}, id="label_ausente"),
        pytest.param({"unit": "hours", "label": "Turno", "fields": []}, id="fields_retirado"),
        pytest.param({"unit": "hours", "label": "Turno", "options": "no-lista"}, id="options_no_lista"),
        pytest.param({"unit": "hours", "label": "Turno", "is_active": "si"}, id="is_active_no_booleano"),
    ],
)
def test_worklog_definition_rejects_invalid_definitions(payload):
    with pytest.raises(ValidationError):
        _definition(payload)


def test_worklog_definition_accepts_options_and_is_active_false():
    definition = _definition(
        {"unit": "hours", "label": "x" * LABEL_MAX, "options": ["coordinacion", "extra"], "is_active": False}
    )

    assert len(definition.label) == LABEL_MAX
    assert definition.options == ["coordinacion", "extra"]
    assert definition.is_active is False


# --- WorklogDefinitions (mapa de tipos) ---


def test_worklog_definitions_accepts_valid_map():
    definitions = contracts.WorklogDefinitions.model_validate(
        {"particular": {"unit": "hours", "label": "Particular"}, "fijo": {"unit": "fixed", "label": "Fijo"}}
    )

    assert set(definitions.root) == {"particular", "fijo"}


def test_worklog_definitions_accepts_key_of_50_characters():
    key = "k" * KEY_MAX

    definitions = contracts.WorklogDefinitions.model_validate({key: {"unit": "days", "label": "Dias"}})

    assert key in definitions.root


@pytest.mark.parametrize("key", ["", "k" * (KEY_MAX + 1)], ids=["vacia", "51-caracteres"])
def test_worklog_definitions_rejects_key_outside_1_to_50(key):
    with pytest.raises(ValidationError):
        contracts.WorklogDefinitions.model_validate({key: {"unit": "days", "label": "Dias"}})


def test_worklog_definitions_rejects_invalid_value_inside_map():
    with pytest.raises(ValidationError):
        contracts.WorklogDefinitions.model_validate({"particular": {"unit": "weekly", "label": "Particular"}})


# --- RateEntry ---


def test_rate_entry_defaults_are_net_and_not_gross():
    entry = _rate({"base_rate": 20.0})

    assert entry.is_gross is False
    assert entry.tax_overrides == {}
    assert entry.extras == {}


@pytest.mark.parametrize("value", [0, 0.0, 20.5], ids=["cero", "cero-float", "decimal"])
def test_rate_entry_accepts_non_negative_base_rate(value):
    assert _rate({"base_rate": value}).base_rate == value


@pytest.mark.parametrize(
    "value",
    [-1, -0.01, float("nan"), float("inf"), float("-inf"), "abc", "20", None, True],
    ids=["negativo", "negativo-decimal", "nan", "inf", "-inf", "texto", "cadena-numerica", "null", "bool"],
)
def test_rate_entry_rejects_invalid_base_rate(value):
    with pytest.raises(ValidationError):
        _rate({"base_rate": value})


def test_rate_entry_is_gross_defaults_to_false_and_rejects_non_bool():
    assert _rate({"base_rate": 1.0, "is_gross": True}).is_gross is True
    with pytest.raises(ValidationError):
        _rate({"base_rate": 1.0, "is_gross": "si"})


@pytest.mark.parametrize(
    "overrides",
    [{"irpf": 0.15}, {"irpf": 0}, {"irpf": 1}, {"irpf": None}, {"irpf": 0.15, "social_security": None}],
)
def test_rate_entry_accepts_valid_tax_overrides(overrides):
    assert _rate({"base_rate": 1.0, "tax_overrides": overrides}).tax_overrides == overrides


@pytest.mark.parametrize(
    "value",
    [1.5, -0.1, float("nan"), "abc", "0.15", True],
    ids=["gt1", "neg", "nan", "texto", "cadena-numerica", "bool"],
)
def test_rate_entry_rejects_invalid_tax_override_values(value):
    with pytest.raises(ValidationError):
        _rate({"base_rate": 1.0, "tax_overrides": {"irpf": value}})


def test_rate_entry_accepts_extras_with_value_and_per_unit():
    entry = _rate({"base_rate": 1.0, "extras": {"noche": {"value": 5, "per_unit": True}}})

    assert entry.extras["noche"].value == 5
    assert entry.extras["noche"].per_unit is True


def test_rate_entry_extra_per_unit_defaults_to_false():
    entry = _rate({"base_rate": 1.0, "extras": {"noche": {"value": 5}}})

    assert entry.extras["noche"].per_unit is False


@pytest.mark.parametrize(
    "extra",
    [
        pytest.param({"value": -1}, id="value_negativo"),
        pytest.param({"value": float("nan")}, id="value_nan"),
        pytest.param({"value": "x"}, id="value_texto"),
        pytest.param({"per_unit": True}, id="value_ausente"),
        pytest.param({"value": 5, "per_unit": "si"}, id="per_unit_no_bool"),
    ],
)
def test_rate_entry_rejects_invalid_extras(extra):
    with pytest.raises(ValidationError):
        _rate({"base_rate": 1.0, "extras": {"noche": extra}})


# --- RatesConfig: limites ---


def test_rates_config_accepts_few_valid_types():
    rates = contracts.RatesConfig.model_validate(
        {f"t{i}": {"base_rate": 1.0, "is_gross": False, "tax_overrides": {}} for i in range(3)}
    )

    assert len(rates.root) == 3


def test_rates_config_rejects_too_many_keys():
    many = {f"t{i}": {"base_rate": 1.0} for i in range(RATES_MANY_KEYS)}

    with pytest.raises(ValidationError):
        contracts.RatesConfig.model_validate(many)


def test_rates_config_rejects_oversized_total_content():
    huge = {"particular": {"base_rate": 1.0, "notas": "x" * RATES_HUGE_TEXT}}

    with pytest.raises(ValidationError):
        contracts.RatesConfig.model_validate(huge)


def test_rates_config_rejects_invalid_entry_inside_map():
    with pytest.raises(ValidationError):
        contracts.RatesConfig.model_validate({"particular": {"base_rate": -5.0}})


# --- F5: defaults mutables de los modelos ---


@pytest.mark.parametrize("attr", ["settings", "worklog_definitions"])
def test_company_json_defaults_are_not_shared_between_instances(db, attr):
    first = models.Company(name="Primera")
    second = models.Company(name="Segunda")
    db.add_all([first, second])
    db.flush()

    _assert_not_shared(first, second, attr)


@pytest.mark.parametrize("attr", ["rates_config", "settings"])
def test_company_member_json_defaults_are_not_shared_between_instances(db, attr):
    user_a = make_user(db)
    user_b = make_user(db)
    company = make_company(db)
    first = models.CompanyMember(user_id=user_a.id, company_id=company.id)
    second = models.CompanyMember(user_id=user_b.id, company_id=company.id)
    db.add_all([first, second])
    db.flush()

    _assert_not_shared(first, second, attr)


def test_work_log_extra_data_default_is_not_shared_between_instances(db):
    user = make_user(db)
    company = make_company(db)
    first = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type="particular",
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 10),
    )
    second = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type="particular",
        start_date=date(2026, 1, 11),
        end_date=date(2026, 1, 11),
    )
    db.add_all([first, second])
    db.flush()

    _assert_not_shared(first, second, "extra_data")


def test_audit_log_extra_data_default_is_not_shared_between_instances(db):
    first = models.AuditLog(action="test.defaults")
    second = models.AuditLog(action="test.defaults")
    db.add_all([first, second])
    db.flush()

    _assert_not_shared(first, second, "extra_data")


def _assert_not_shared(first, second, attr):
    first_value = getattr(first, attr)
    second_value = getattr(second, attr)
    assert isinstance(first_value, dict), f"{attr} debe ser un dict por defecto"
    assert isinstance(second_value, dict), f"{attr} debe ser un dict por defecto"
    assert first_value is not second_value, f"{attr} comparte el mismo objeto mutable entre instancias"

    first_value["probe"] = True
    assert "probe" not in getattr(second, attr)
