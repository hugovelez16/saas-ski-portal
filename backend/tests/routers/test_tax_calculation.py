"""
Calculo de impuestos con claves libres (PR-10).

(a) `crud.calculate_dynamic_work_log` con impuestos de empresa y overrides de miembro de nombre
libre; semantica de `is_gross`; lineas del ticket y snapshot. (b) Validacion de `taxConfig` y de
`tax_overrides` en la API. (c) No regresion: los turnos guardados no cambian al editar impuestos.
"""

import copy
from datetime import date, time

import crud
import models
import pytest
import schemas

from tests.factories import as_user, make_company, make_member, make_user

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


# --- API: taxConfig en alta y edicion de empresa ---


@pytest.fixture
def pa(db):
    return make_user(db, role="admin")


def _company_count(db):
    return db.query(models.Company).count()


def test_create_company_without_tax_config_is_rejected(client, db, pa):
    as_user(client, pa)
    before = _company_count(db)

    resp = client.post("/companies", json={"name": "Sin impuestos"})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_with_null_tax_config_is_rejected(client, db, pa):
    as_user(client, pa)

    resp = client.post("/companies", json={"name": "Nula", "taxConfig": None})

    assert resp.status_code == 422, resp.text


def test_create_company_with_empty_tax_config_is_accepted(client, db, pa):
    as_user(client, pa)

    resp = client.post("/companies", json={"name": "Vacia", "taxConfig": {}})

    assert resp.status_code == 200, resp.text
    assert resp.json()["taxConfig"] == {}


@pytest.mark.parametrize(
    "tax_config",
    [{"IRPF": 1.5}, {"IRPF": "x"}, {"IRPF": -0.1}, {"IRPF": True}, {"IRPF": "0.1"}, {"": 0.1}, {"x" * 51: 0.1}],
    ids=["gt1", "str", "neg", "bool", "numeric_str", "empty_name", "long_name"],
)
def test_create_company_with_invalid_tax_config_is_rejected(client, db, pa, tax_config):
    as_user(client, pa)
    before = _company_count(db)

    resp = client.post("/companies", json={"name": "Invalida", "taxConfig": tax_config})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_with_free_taxes_returns_tax_config(client, db, pa):
    as_user(client, pa)
    tax_config = {"IRPF": 0.15, "Seguridad Social": 0}

    resp = client.post("/companies", json={"name": "Libres", "taxConfig": tax_config})

    assert resp.status_code == 200, resp.text
    assert resp.json()["taxConfig"] == tax_config
    stored = db.query(models.Company).filter_by(name="Libres").one()
    assert stored.tax_config == tax_config


@pytest.mark.parametrize("tax_config", [{"IRPF": "x"}, {"IRPF": 1.5}, {"IRPF": None}])
def test_update_company_with_invalid_tax_config_is_rejected(client, db, pa, tax_config):
    company = make_company(db, tax_config={"IRPF": 0.1})
    as_user(client, pa)

    resp = client.put(f"/companies/{company.id}", json={"taxConfig": tax_config})

    assert resp.status_code == 422, resp.text
    db.refresh(company)
    assert company.tax_config == {"IRPF": 0.1}


def test_update_company_with_free_taxes_is_accepted(client, db, pa):
    company = make_company(db, tax_config={"IRPF": 0.1})
    as_user(client, pa)

    resp = client.put(f"/companies/{company.id}", json={"taxConfig": {"Mutua": 0.02}})

    assert resp.status_code == 200, resp.text
    assert resp.json()["taxConfig"] == {"Mutua": 0.02}


# --- API: tax_overrides en tarifas de miembro ---


def _rates_url(company, user):
    return f"/companies/{company.id}/members/{user.id}/rates"


@pytest.fixture
def member_world(db, pa):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    return company, worker


@pytest.mark.parametrize(
    "overrides",
    [{"IRPF": 1.5}, {"IRPF": -0.1}, {"IRPF": "x"}, {"IRPF": True}, {"": 0.1}],
    ids=["gt1", "neg", "str", "bool", "empty_name"],
)
def test_member_rates_with_invalid_tax_overrides_are_rejected(client, db, pa, member_world, overrides):
    company, worker = member_world
    as_user(client, pa)
    before = copy.deepcopy(
        db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one().rates_config
    )

    resp = client.put(
        _rates_url(company, worker),
        json={"ratesConfig": {"particular": {"base_rate": 20, "tax_overrides": overrides}}},
    )

    assert resp.status_code == 422, resp.text
    member = db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one()
    db.refresh(member)
    assert member.rates_config == before


@pytest.mark.parametrize(
    "overrides",
    [None, {}, {"IRPF": 0.2}, {"IRPF": None}, {"IRPF": 0, "Mutua": 1}],
    ids=["null", "empty", "value", "none_value", "bounds"],
)
def test_member_rates_with_valid_tax_overrides_are_accepted(client, db, pa, member_world, overrides):
    company, worker = member_world
    as_user(client, pa)
    rates = {"particular": {"base_rate": 20, "tax_overrides": overrides}}

    resp = client.put(_rates_url(company, worker), json={"ratesConfig": rates})

    assert resp.status_code == 200, resp.text
    member = db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one()
    db.refresh(member)
    assert member.rates_config["particular"]["tax_overrides"] == overrides


def test_member_rates_without_tax_overrides_key_are_accepted(client, db, pa, member_world):
    company, worker = member_world
    as_user(client, pa)

    resp = client.put(_rates_url(company, worker), json={"ratesConfig": {"particular": {"base_rate": 20}}})

    assert resp.status_code == 200, resp.text


# --- No regresion: los turnos guardados no cambian ---


def test_saved_work_log_does_not_change_when_company_taxes_are_edited(client, db, pa):
    company = make_company(db, tax_config={"IRPF": 0.15})
    worker = make_user(db)
    make_member(
        db,
        worker,
        company,
        role="worker",
        rates_config={"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}},
    )
    work_log = crud.create_work_log(
        db,
        schemas.WorkLogCreate(
            type="particular",
            start_date=date(2026, 1, 10),
            end_date=date(2026, 1, 10),
            start_time=time(9, 0),
            end_time=time(11, 0),
            user_id=worker.id,
            company_id=company.id,
        ),
    )
    work_log_id = work_log.id
    net_before = float(work_log.net_amount)
    snapshot_before = copy.deepcopy(work_log.calculation_snapshot)

    as_user(client, pa)
    resp = client.put(f"/companies/{company.id}", json={"taxConfig": {"IRPF": 0.5, "Mutua": 0.1}})
    assert resp.status_code == 200, resp.text

    db.expire_all()
    reloaded = db.query(models.WorkLog).filter_by(id=work_log_id).one()
    assert float(reloaded.net_amount) == net_before
    assert reloaded.calculation_snapshot == snapshot_before
