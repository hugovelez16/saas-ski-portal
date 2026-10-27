"""
Contratos de settings, tipos de turno y tarifas en la API (PR-11.0 y seguimiento de PR-05: M1, M2).

Describen el comportamiento objetivo de PR-11.1:
- `PUT /companies/{id}` valida `settings` (CompanySettings) y `worklogDefinitions` (unit obligatorio).
- `GET /companies/{id}` (PA) devuelve `settings` con los defaults aplicados.
- `PUT .../members/{uid}/rates` rechaza tipos sin definicion en la empresa, por encima del limite de
  claves o con valores de tarifa negativos, no finitos o no numericos.
- `PUT .../members/{uid}/settings` solo admite la lista blanca de claves de usuario. Se fija aqui:
  `notifications` y `ui_preferences`. Cualquier clave de nivel empresa (la de `CompanySettings`) -> 422.

Hasta implementar PR-11.1 estas pruebas deben fallar porque la validacion no existe.
"""

import json

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user

# Lista blanca minima de claves de usuario en `MemberSettingsUpdate` (PR-11.1, seguimiento M1).
USER_SETTINGS_ALLOWED = {"notifications": {"email": True}, "ui_preferences": {"compact": True}}

RATE_BASE = {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}
RATES_MANY_KEYS = 1000
USER_SETTINGS_HUGE_TEXT = 200_000


@pytest.fixture
def world(db):
    """Empresa con manager y worker, PA de plataforma."""
    company = make_company(db, name="Escuela Norte")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    pa = make_user(db, role="admin")
    return {"company": company, "manager": manager, "worker": worker, "pa": pa}


def _put_json(client, url, body):
    """Envia el cuerpo con `json.dumps` para poder reproducir NaN (JSON no estandar pero aceptado por Starlette)."""
    return client.put(url, content=json.dumps(body), headers={"content-type": "application/json"})


def _company_row(db, company):
    db.expire_all()
    return db.get(models.Company, company.id)


def _membership(db, user, company):
    db.expire_all()
    return db.query(models.CompanyMember).filter_by(user_id=user.id, company_id=company.id).one()


def _rates_body(rates):
    return {"ratesConfig": rates}


# --- PUT /companies/{id}: settings ---


SETTINGS_INVALID = [
    pytest.param({"allow_tutorial": True}, id="allow_tutorial_retirada"),
    pytest.param({"allow_coordination": False}, id="allow_coordination_retirada"),
    pytest.param({"is_managed": True}, id="is_managed_retirada"),
    pytest.param({"business_logic": {"cost_markup": 0}}, id="cost_markup_retirada"),
    pytest.param({"billing": {"cost_markup_percent": 32.0}}, id="cost_markup_percent_retirada"),
    pytest.param({"clave_inventada": 1}, id="clave_desconocida"),
    pytest.param({"business_logic": {"price_type": "bruto"}}, id="price_type_fuera_de_enum"),
    pytest.param({"worker_experience": {"input_mode": "voz"}}, id="input_mode_fuera_de_enum"),
    pytest.param({"worker_experience": {"allow_manual_amount": "si"}}, id="allow_manual_amount_no_bool"),
    pytest.param({"ui_customization": {"labels": {"worklog": "x" * 61}}}, id="label_de_61_caracteres"),
]


@pytest.mark.parametrize("settings", SETTINGS_INVALID)
def test_pa_put_company_with_invalid_settings_returns_422_and_keeps_previous(client, db, world, settings):
    company = world["company"]
    before = dict(_company_row(db, company).settings or {})
    as_user(client, world["pa"], company)

    resp = client.put(f"/companies/{company.id}", json={"settings": settings})

    assert resp.status_code == 422, resp.text
    assert (_company_row(db, company).settings or {}) == before


def test_pa_put_company_with_valid_settings_returns_200(client, db, world):
    company = world["company"]
    as_user(client, world["pa"], company)

    resp = client.put(
        f"/companies/{company.id}",
        json={"settings": {"business_logic": {"price_type": "gross"}, "modules": {"tutorials": True}}},
    )

    assert resp.status_code == 200, resp.text


WORKLOG_DEFINITIONS_INVALID = [
    pytest.param({"guardia": {"unit": "weekly", "label": "Guardia"}}, id="unit_fuera_de_contrato"),
    pytest.param({"guardia": {"is_range": True, "label": "Guardia"}}, id="sin_unit_con_is_range"),
    pytest.param({"guardia": {"unit": "hours", "label": "x" * 61}}, id="label_de_61_caracteres"),
    pytest.param({"guardia": {"unit": "hours", "label": ""}}, id="label_vacio"),
    pytest.param({"": {"unit": "hours", "label": "Guardia"}}, id="clave_vacia"),
]


@pytest.mark.parametrize("definitions", WORKLOG_DEFINITIONS_INVALID)
def test_pa_put_company_with_invalid_worklog_definitions_returns_422(client, db, world, definitions):
    company = world["company"]
    as_user(client, world["pa"], company)

    resp = client.put(f"/companies/{company.id}", json={"worklogDefinitions": definitions})

    assert resp.status_code == 422, resp.text


# --- GET /companies/{id}: defaults de settings ---


def test_pa_get_company_returns_settings_with_defaults(client, db, world):
    company = world["company"]
    as_user(client, world["pa"], company)

    resp = client.get(f"/companies/{company.id}")

    assert resp.status_code == 200, resp.text
    settings = resp.json()["settings"]
    assert settings["business_logic"]["price_type"] == "net"
    assert "cost_markup" not in settings["business_logic"]
    assert settings["worker_experience"]["input_mode"] == "manual_single"
    assert settings["worker_experience"]["allow_manual_amount"] is False
    assert settings["modules"] == {}
    labels = settings["ui_customization"]["labels"]
    assert {key: value for key, value in labels.items() if value is not None} == {}


# --- PUT .../members/{uid}/rates: tipos de turno ---


def test_manager_put_rates_with_undefined_shift_type_returns_422(client, db, world):
    company, worker = world["company"], world["worker"]
    as_user(client, world["manager"], company, claims={"role": "manager"})
    rates = {"guardia": {**RATE_BASE}}  # make_company solo define "particular"

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body(rates))

    assert resp.status_code == 422, resp.text
    assert "Tipo de turno desconocido" in resp.text


def test_manager_put_rates_with_defined_shift_type_returns_200(client, db, world):
    company, worker = world["company"], world["worker"]
    as_user(client, world["manager"], company, claims={"role": "manager"})

    resp = client.put(
        f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body({"particular": {**RATE_BASE}})
    )

    assert resp.status_code == 200, resp.text


def test_manager_put_rates_conserva_tipo_retirado_ya_presente_en_la_tarifa(client, db):
    # "retirado" ya estaba en la tarifa del miembro y ya no existe en la empresa: no se re-valida.
    company = make_company(db, worklog_definitions={"particular": {"unit": "hours", "label": "Particular"}})
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config={"retirado": {**RATE_BASE}})
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "manager"})
    rates = {"retirado": {**RATE_BASE}, "particular": {**RATE_BASE}}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body(rates))

    assert resp.status_code == 200, resp.text


def test_manager_put_rates_con_tipo_nuevo_no_definido_sigue_en_422(client, db):
    company = make_company(db, worklog_definitions={"particular": {"unit": "hours", "label": "Particular"}})
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config={"retirado": {**RATE_BASE}})
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "manager"})
    rates = {"retirado": {**RATE_BASE}, "guardia": {**RATE_BASE}}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body(rates))

    assert resp.status_code == 422, resp.text
    assert "Tipo de turno desconocido" in resp.text


def test_put_rates_sin_empresa_en_el_contexto_devuelve_404(client, db, world, monkeypatch):
    # Fuerza el caso en que el contexto de acceso no resuelve la empresa (ctx.company is None).
    from routers import deps

    monkeypatch.setattr(deps.AccessContext, "company", property(lambda self: None))
    company, worker = world["company"], world["worker"]
    as_user(client, world["manager"], company, claims={"role": "manager"})

    resp = client.put(
        f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body({"particular": {**RATE_BASE}})
    )

    assert resp.status_code == 404, resp.text
    assert "Empresa no encontrada" in resp.text


# --- PUT .../members/{uid}/rates: limite de numero de claves ---


def test_manager_put_rates_above_key_limit_returns_422(client, db):
    many_types = {f"tipo{i}": {"unit": "hours", "label": f"Tipo {i}"} for i in range(RATES_MANY_KEYS)}
    company = make_company(db, worklog_definitions=many_types)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "manager"})
    rates = {f"tipo{i}": {**RATE_BASE} for i in range(RATES_MANY_KEYS)}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body(rates))

    assert resp.status_code == 422, resp.text


def test_manager_put_rates_with_few_keys_on_same_company_returns_200(client, db):
    # Control: mismo tipo de empresa y de actor, con pocas claves, debe aceptarse.
    many_types = {f"tipo{i}": {"unit": "hours", "label": f"Tipo {i}"} for i in range(3)}
    company = make_company(db, worklog_definitions=many_types)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "manager"})
    rates = {f"tipo{i}": {**RATE_BASE} for i in range(3)}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json=_rates_body(rates))

    assert resp.status_code == 200, resp.text


# --- PUT .../members/{uid}/rates: valores numericos de tarifa ---


RATE_VALUE_INVALID = [
    pytest.param("base_rate", -1, id="base_rate_negativo"),
    pytest.param("base_rate", float("nan"), id="base_rate_nan"),
    pytest.param("base_rate", "abc", id="base_rate_texto"),
    pytest.param("base_rate", True, id="base_rate_bool"),
    pytest.param("tax_overrides", {"irpf": -0.1}, id="tax_override_negativo"),
    pytest.param("tax_overrides", {"irpf": 1.5}, id="tax_override_mayor_que_1"),
    pytest.param("tax_overrides", {"irpf": float("nan")}, id="tax_override_nan"),
    pytest.param("tax_overrides", {"irpf": "abc"}, id="tax_override_texto"),
    pytest.param("extras", {"noche": {"value": -1}}, id="extra_value_negativo"),
    pytest.param("extras", {"noche": {"value": float("nan")}}, id="extra_value_nan"),
    pytest.param("extras", {"noche": {"value": "abc"}}, id="extra_value_texto"),
]


@pytest.mark.parametrize("field, value", RATE_VALUE_INVALID)
def test_manager_put_rates_with_invalid_numeric_value_returns_422(client, db, world, field, value):
    company, worker = world["company"], world["worker"]
    as_user(client, world["manager"], company, claims={"role": "manager"})
    entry = {**RATE_BASE, field: value}

    resp = _put_json(
        client,
        f"/companies/{company.id}/members/{worker.id}/rates",
        _rates_body({"particular": entry}),
    )

    assert resp.status_code == 422, resp.text


# --- PUT .../members/{uid}/settings: lista blanca de claves de usuario (M1) ---


COMPANY_LEVEL_SETTINGS = [
    pytest.param({"business_logic": {"price_type": "gross"}}, id="business_logic"),
    pytest.param({"worker_experience": {"input_mode": "bulk"}}, id="worker_experience"),
    pytest.param({"ui_customization": {"labels": {"worklog": "Turno"}}}, id="ui_customization"),
    pytest.param({"modules": {"tutorials": True}}, id="modules"),
    pytest.param({"allowed_rates": ["particular"]}, id="allowed_rates"),
    pytest.param({"is_managed": True}, id="is_managed"),
]


@pytest.mark.parametrize("settings", COMPANY_LEVEL_SETTINGS)
def test_worker_cannot_store_company_level_keys_in_member_settings(client, db, world, settings):
    company, worker = world["company"], world["worker"]
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/settings", json={"settings": settings})

    assert resp.status_code == 422, resp.text


def test_member_settings_keep_legacy_dialog_keys_until_o10(client, db, world):
    # TEMPORAL (O10): member-settings-dialog.tsx aun guarda estas claves; borrar con el dialogo.
    company, worker = world["company"], world["worker"]
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(
        f"/companies/{company.id}/members/{worker.id}/settings",
        json={"settings": {"allow_tutorial": True, "allow_coordination": False}},
    )

    assert resp.status_code == 200, resp.text


def test_worker_can_store_allowed_user_keys_in_member_settings(client, db, world):
    # Control: las claves de la lista blanca siguen aceptandose.
    company, worker = world["company"], world["worker"]
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/settings", json={"settings": USER_SETTINGS_ALLOWED})

    assert resp.status_code == 200, resp.text
    assert _membership(db, worker, company).settings == USER_SETTINGS_ALLOWED


def test_worker_member_settings_over_size_limit_returns_422(client, db, world):
    company, worker = world["company"], world["worker"]
    as_user(client, worker, company, claims={"role": "worker"})
    huge = {"ui_preferences": {"nota": "x" * USER_SETTINGS_HUGE_TEXT}}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/settings", json={"settings": huge})

    assert resp.status_code == 422, resp.text
