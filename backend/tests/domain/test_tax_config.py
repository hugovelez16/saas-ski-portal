"""
Contrato de impuestos con claves libres (PR-10).

`TaxConfig` valida la configuracion de impuestos de empresa, `resolve_taxes` combina empresa y
overrides de miembro y `validate_tax_overrides` valida los overrides de miembro.
"""

import pytest
from contracts import TaxConfig, resolve_taxes, validate_tax_overrides
from pydantic import ValidationError


def _cfg(value):
    return TaxConfig.model_validate(value)


# --- TaxConfig: casos validos ---


def test_accepts_empty_dict():
    assert _cfg({}).as_dict() == {}


def test_accepts_free_named_taxes():
    data = {"IRPF": 0.15, "Seguridad Social": 0.0648}
    assert _cfg(data).as_dict() == data


@pytest.mark.parametrize("value", [0, 1, 0.0, 1.0])
def test_accepts_boundary_values(value):
    assert _cfg({"IRPF": value}).as_dict() == {"IRPF": value}


def test_accepts_name_of_50_chars():
    name = "x" * 50
    assert _cfg({name: 0.1}).as_dict() == {name: 0.1}


def test_accepts_20_entries():
    data = {f"imp{i}": 0.01 for i in range(20)}
    assert len(_cfg(data).as_dict()) == 20


def test_keys_are_normalized_with_strip():
    assert _cfg({"  IRPF  ": 0.15}).as_dict() == {"IRPF": 0.15}


# --- TaxConfig: nombres invalidos ---


@pytest.mark.parametrize("name", ["", " ", "   ", "\t"])
def test_rejects_empty_or_blank_name(name):
    with pytest.raises(ValidationError):
        _cfg({name: 0.1})


def test_rejects_name_of_51_chars():
    with pytest.raises(ValidationError):
        _cfg({"x" * 51: 0.1})


def test_rejects_21_entries():
    data = {f"imp{i}": 0.01 for i in range(21)}
    with pytest.raises(ValidationError):
        _cfg(data)


def test_rejects_duplicates_after_strip():
    with pytest.raises(ValidationError):
        _cfg({"IRPF": 0.1, "IRPF ": 0.2})


# --- TaxConfig: valores invalidos ---


@pytest.mark.parametrize(
    "value",
    [-0.1, 1.1, "0.1", True, False, None, float("nan"), float("inf"), float("-inf"), [0.1], {"a": 1}],
    ids=["neg", "gt1", "str", "true", "false", "none", "nan", "inf", "-inf", "list", "dict"],
)
def test_rejects_invalid_values(value):
    with pytest.raises(ValidationError):
        _cfg({"IRPF": value})


def test_rejects_non_dict_root():
    with pytest.raises(ValidationError):
        _cfg([("IRPF", 0.1)])


# --- resolve_taxes ---


def test_resolve_merges_company_and_overrides():
    assert resolve_taxes({"IRPF": 0.15}, {"Seguridad Social": 0.06}) == {"IRPF": 0.15, "Seguridad Social": 0.06}


def test_resolve_override_wins_over_company():
    assert resolve_taxes({"IRPF": 0.15, "SS": 0.06}, {"IRPF": 0.2}) == {"IRPF": 0.2, "SS": 0.06}


def test_resolve_none_in_override_means_no_override():
    assert resolve_taxes({"IRPF": 0.15}, {"IRPF": None}) == {"IRPF": 0.15}


def test_resolve_none_in_override_does_not_add_key():
    assert resolve_taxes({}, {"IRPF": None}) == {}


def test_resolve_override_zero_wins():
    assert resolve_taxes({"IRPF": 0.15}, {"IRPF": 0}) == {"IRPF": 0}


def test_resolve_new_key_in_override_is_added():
    assert resolve_taxes({"IRPF": 0.15}, {"Mutua": 0.02}) == {"IRPF": 0.15, "Mutua": 0.02}


@pytest.mark.parametrize("company", [None, {}])
@pytest.mark.parametrize("overrides", [None, {}])
def test_resolve_accepts_none_and_empty(company, overrides):
    assert resolve_taxes(company, overrides) == {}


def test_resolve_does_not_mutate_inputs():
    company = {"IRPF": 0.15}
    overrides = {"IRPF": 0.2, "Mutua": None}
    resolve_taxes(company, overrides)
    assert company == {"IRPF": 0.15}
    assert overrides == {"IRPF": 0.2, "Mutua": None}


# --- validate_tax_overrides ---


@pytest.mark.parametrize("value", [None, {}, {"IRPF": None}, {"IRPF": 0}, {"IRPF": 1}, {"IRPF": 0.15, "SS": None}])
def test_overrides_accepts_valid(value):
    assert validate_tax_overrides(value) == value


@pytest.mark.parametrize(
    "value",
    [
        {"IRPF": 1.5},
        {"IRPF": -0.1},
        {"IRPF": "x"},
        {"IRPF": "0.1"},
        {"IRPF": True},
        {"IRPF": float("nan")},
        {"": 0.1},
        {" ": 0.1},
        {"x" * 51: 0.1},
        {"A": 0.6, "B": 0.5},
    ],
    ids=["gt1", "neg", "str", "numeric_str", "bool", "nan", "empty_name", "blank_name", "long_name", "sum_gt1"],
)
def test_overrides_rejects_invalid(value):
    with pytest.raises(ValueError):
        validate_tax_overrides(value)


def test_tax_config_accepts_sum_equal_to_one():
    assert _cfg({"IRPF": 0.7, "SS": 0.3}).as_dict() == {"IRPF": 0.7, "SS": 0.3}


@pytest.mark.parametrize(
    "data",
    [
        {"IRPF": 0.6, "SS": 0.5},
        {"IRPF": 0.7, "SS": 0.3001},
        {"A": 0.34, "B": 0.34, "C": 0.33},
    ],
)
def test_tax_config_rejects_sum_greater_than_one(data):
    with pytest.raises(ValidationError):
        _cfg(data)


def test_overrides_rejects_effective_sum_greater_than_one():
    with pytest.raises(ValueError):
        validate_tax_overrides({"Mutua": 0.5}, company_tax_config={"IRPF": 0.6}, is_managed=False)


def test_overrides_accepts_when_override_reduces_effective_sum_to_one():
    result = validate_tax_overrides(
        {"IRPF": 0.5},
        company_tax_config={"IRPF": 0.7, "SS": 0.5},
        is_managed=True,
    )
    assert result == {"IRPF": 0.5}


def test_overrides_managed_rejects_unknown_name_and_allows_company_key():
    assert validate_tax_overrides(
        {"IRPF": 0.2},
        company_tax_config={"IRPF": 0.15},
        is_managed=True,
    ) == {"IRPF": 0.2}

    with pytest.raises(ValueError):
        validate_tax_overrides(
            {"Mutua": 0.05},
            company_tax_config={"IRPF": 0.15},
            is_managed=True,
        )


def test_overrides_autonomous_allows_custom_name():
    assert validate_tax_overrides(
        {"Mutua": 0.05},
        company_tax_config={"IRPF": 0.15},
        is_managed=False,
    ) == {"Mutua": 0.05}


def test_overrides_managed_conserves_existing_custom_tax_without_editing():
    # Conservar sin cambiar: valido
    assert validate_tax_overrides(
        {"Mutua": 0.05},
        company_tax_config={"IRPF": 0.15},
        is_managed=True,
        existing_overrides={"Mutua": 0.05},
    ) == {"Mutua": 0.05}

    # Intentar cambiar su porcentaje en modo gestionado: rechazado
    with pytest.raises(ValueError):
        validate_tax_overrides(
            {"Mutua": 0.08},
            company_tax_config={"IRPF": 0.15},
            is_managed=True,
            existing_overrides={"Mutua": 0.05},
        )
