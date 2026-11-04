"""
Calculo de impuestos con claves libres (PR-10).

`crud.calculate_dynamic_work_log` con impuestos de empresa y overrides de miembro de nombre libre;
semantica de `is_gross`; lineas del ticket y snapshot. La validacion de `taxConfig` y de
`tax_overrides` por HTTP y la no regresion de turnos guardados estan en tests/routers/v2/
(retirada de los endpoints de empresa de v1, PR-21).
"""

import crud
import pytest

HOURS_DEF = {"unit": "hours", "label": "Particular", "fields": []}
FIXED_DEF = {"unit": "fixed", "label": "Fijo", "fields": []}

COMPANY_TAXES = {"IRPF": 0.15, "Seguridad Social": 0.0648, "Mutua": 0.02}


def _log(hours=2.0, **extra):
    return {"duration_hours": hours, **extra}


def _calc(rate, taxes=None, *, hours=2.0, definition=HOURS_DEF, log=None):
    return crud.calculate_dynamic_work_log(log if log is not None else _log(hours), definition, rate, taxes)


def _tax_lines(result):
    return [line for line in result["snapshot"]["display_lines"] if line["type"] == "tax"]


# --- is_gross = True ---


def test_gross_rate_deducts_all_free_taxes():
    result = _calc({"base_rate": 100.0, "is_gross": True}, COMPANY_TAXES)

    total = sum(COMPANY_TAXES.values())
    assert result["gross_amount"] == pytest.approx(200.0)
    assert result["net_amount"] == pytest.approx(200.0 * (1 - total))


def test_gross_rate_with_fixed_unit():
    result = _calc({"base_rate": 50.0, "is_gross": True}, {"A": 0.1, "B": 0.2}, definition=FIXED_DEF, log={})

    assert result["gross_amount"] == pytest.approx(50.0)
    assert result["net_amount"] == pytest.approx(35.0)


def test_gross_rate_includes_extras_in_gross():
    rate = {"base_rate": 10.0, "is_gross": True, "extras": {"nocturno": {"value": 5.0}}}
    log = _log(2.0, extra_data={"opciones": {"nocturno": True}})

    result = _calc(rate, {"IRPF": 0.1}, log=log)

    assert result["gross_amount"] == pytest.approx(25.0)
    assert result["net_amount"] == pytest.approx(22.5)


def test_gross_rate_without_taxes_keeps_amount():
    result = _calc({"base_rate": 100.0, "is_gross": True}, {})

    assert result["net_amount"] == pytest.approx(200.0)
    assert result["gross_amount"] == pytest.approx(200.0)


# --- is_gross = False / ausente ---


def test_net_rate_does_not_deduct_even_with_company_taxes():
    result = _calc({"base_rate": 100.0, "is_gross": False}, COMPANY_TAXES)

    assert result["net_amount"] == pytest.approx(200.0)


def test_net_rate_gross_is_informative():
    result = _calc({"base_rate": 100.0, "is_gross": False}, COMPANY_TAXES)

    total = sum(COMPANY_TAXES.values())
    assert result["gross_amount"] == pytest.approx(200.0 / (1 - total))


def test_missing_is_gross_behaves_as_false():
    result = _calc({"base_rate": 100.0}, COMPANY_TAXES)

    assert result["net_amount"] == pytest.approx(200.0)
    assert result["gross_amount"] == pytest.approx(200.0 / (1 - sum(COMPANY_TAXES.values())))


def test_net_rate_with_taxes_of_100_percent_or_more_falls_back_to_net():
    result = _calc({"base_rate": 100.0, "is_gross": False}, {"A": 0.6, "B": 0.5})

    assert result["net_amount"] == pytest.approx(200.0)
    assert result["gross_amount"] == pytest.approx(200.0)


# --- overrides de miembro ---


def test_member_override_with_same_key_wins_over_company():
    rate = {"base_rate": 100.0, "is_gross": True, "tax_overrides": {"IRPF": 0.30}}

    result = _calc(rate, {"IRPF": 0.15})

    assert result["net_amount"] == pytest.approx(200.0 * 0.70)
    assert result["snapshot"]["tax_applied"] == {"IRPF": 0.30}


def test_member_override_with_zero_wins_over_company():
    rate = {"base_rate": 100.0, "is_gross": True, "tax_overrides": {"IRPF": 0}}

    result = _calc(rate, {"IRPF": 0.15})

    assert result["net_amount"] == pytest.approx(200.0)


def test_member_override_with_new_key_is_added_when_gross():
    rate = {"base_rate": 100.0, "is_gross": True, "tax_overrides": {"Retencion extra": 0.05}}

    result = _calc(rate, {"IRPF": 0.15})

    assert result["net_amount"] == pytest.approx(200.0 * (1 - 0.20))
    assert result["snapshot"]["tax_applied"] == {"IRPF": 0.15, "Retencion extra": 0.05}


def test_member_override_with_new_key_not_applied_when_net():
    rate = {"base_rate": 100.0, "is_gross": False, "tax_overrides": {"Retencion extra": 0.05}}

    result = _calc(rate, {"IRPF": 0.15})

    assert result["net_amount"] == pytest.approx(200.0)


def test_tax_overrides_none_does_not_break():
    rate = {"base_rate": 100.0, "is_gross": True, "tax_overrides": None}

    result = _calc(rate, {"IRPF": 0.15})

    assert result["net_amount"] == pytest.approx(200.0 * 0.85)


def test_override_with_none_value_equals_no_override():
    with_none = _calc({"base_rate": 100.0, "is_gross": True, "tax_overrides": {"IRPF": None}}, {"IRPF": 0.15})
    without = _calc({"base_rate": 100.0, "is_gross": True}, {"IRPF": 0.15})

    assert with_none["net_amount"] == pytest.approx(without["net_amount"])
    assert with_none["snapshot"]["tax_applied"] == {"IRPF": 0.15}


def test_company_tax_config_none_is_valid():
    result = _calc({"base_rate": 100.0, "is_gross": True}, None)

    assert result["net_amount"] == pytest.approx(200.0)
    assert result["snapshot"]["tax_applied"] == {}


@pytest.mark.parametrize("legacy_key", ["ss", "irpf", "extra"])
def test_legacy_magic_keys_are_not_special_anymore(legacy_key):
    # La clave antigua ya no mapea a social_security/irpf_base: es un impuesto libre mas.
    # Con is_gross=False no se aplica nunca y con una empresa que define social_security
    # el override {"ss": ...} no sustituye a esa clave.
    rate = {"base_rate": 100.0, "is_gross": True, "tax_overrides": {legacy_key: 0.10}}

    result = _calc(rate, {"social_security": 0.05, "irpf_base": 0.15})

    applied = result["snapshot"]["tax_applied"]
    assert applied["social_security"] == 0.05
    assert applied["irpf_base"] == 0.15


def test_legacy_override_ss_is_not_applied_when_net():
    rate = {"base_rate": 100.0, "is_gross": False, "tax_overrides": {"ss": 0.10}}

    result = _calc(rate, {"social_security": 0.05})

    assert result["net_amount"] == pytest.approx(200.0)
    assert result["snapshot"]["tax_applied"].get("social_security") == 0.05


# --- importe manual ---


@pytest.mark.parametrize("field", ["amount", "net_amount"])
def test_manual_amount_does_not_apply_taxes(field):
    rate = {"base_rate": 100.0, "is_gross": True}

    result = _calc(rate, COMPANY_TAXES, log={field: 77.0, "duration_hours": 2.0})

    assert result["net_amount"] == pytest.approx(77.0)
    assert result["gross_amount"] == pytest.approx(77.0)
    assert result["snapshot"]["type"] == "manual_override"
    assert "tax_applied" not in result["snapshot"]


# --- snapshot y lineas del ticket ---


def test_snapshot_has_tax_applied_and_new_version():
    result = _calc({"base_rate": 100.0, "is_gross": True}, COMPANY_TAXES)

    assert result["snapshot"]["tax_applied"] == COMPANY_TAXES
    assert result["snapshot"]["version"] == "2.3-free-taxes"


def test_snapshot_tax_applied_reflects_effective_taxes_when_net():
    result = _calc({"base_rate": 100.0, "is_gross": False}, COMPANY_TAXES)

    assert result["snapshot"]["tax_applied"] == COMPANY_TAXES
    assert result["snapshot"]["version"] == "2.3-free-taxes"


def test_display_lines_one_tax_line_per_tax():
    result = _calc({"base_rate": 100.0, "is_gross": True}, COMPANY_TAXES)

    lines = _tax_lines(result)
    assert [line["code"] for line in lines] == list(COMPANY_TAXES)
    gross = result["gross_amount"]
    for line in lines:
        rate = COMPANY_TAXES[line["code"]]
        assert line["label"] == f"{line['code']} ({round(rate * 100, 2)}%)"
        assert line["value"] == -round(gross * rate, 2)


def test_display_lines_label_format_example():
    result = _calc({"base_rate": 100.0, "is_gross": True}, {"Seguridad Social": 0.0648})

    (line,) = _tax_lines(result)
    assert line["label"] == "Seguridad Social (6.48%)"
    assert line["value"] == -round(200.0 * 0.0648, 2)


def test_display_lines_skip_zero_rate_tax():
    result = _calc({"base_rate": 100.0, "is_gross": True}, {"IRPF": 0.15, "Mutua": 0})

    assert [line["code"] for line in _tax_lines(result)] == ["IRPF"]


def test_display_lines_no_tax_lines_without_taxes():
    result = _calc({"base_rate": 100.0, "is_gross": True}, {"IRPF": 0})

    assert _tax_lines(result) == []


def test_display_lines_use_gross_total_for_net_rates():
    result = _calc({"base_rate": 100.0, "is_gross": False}, {"IRPF": 0.10})

    (line,) = _tax_lines(result)
    assert line["value"] == -round(result["gross_amount"] * 0.10, 2)


def test_display_lines_do_not_use_legacy_codes():
    result = _calc({"base_rate": 100.0, "is_gross": True}, {"social_security": 0.05, "irpf_base": 0.15})

    codes = [line["code"] for line in _tax_lines(result)]
    assert codes == ["social_security", "irpf_base"]
    assert not {"ss", "irpf", "other"} & set(codes)
