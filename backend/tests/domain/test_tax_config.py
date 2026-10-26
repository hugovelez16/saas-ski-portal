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
    ],
    ids=["gt1", "neg", "str", "numeric_str", "bool", "nan", "empty_name", "blank_name", "long_name"],
)
def test_overrides_rejects_invalid(value):
    with pytest.raises(ValueError):
        validate_tax_overrides(value)
