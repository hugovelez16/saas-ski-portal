"""
Pruebas HTTP de la API v2 de empresa (PR-17.0): /v2/companies, /v2/me/companies y /v2/users/{id}/companies.

Contrato: JSON en snake_case sin alias camelCase; la politica de acceso es identica a v1
(access_policy.py y routers/deps.py). Hoy los endpoints v2 de empresa no existen, asi que estas
pruebas deben FALLAR (404/405 o ausencia de funcionalidad). Cada prueba comprueba primero el codigo
de estado para que el fallo sea siempre por la razon correcta y no por un assert posterior.

No se mockea la logica: se usan el TestClient (`client`), la sesion `db` y las fabricas de tests/factories.py.
"""

import re
import uuid
from types import SimpleNamespace

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

BASE = "/v2/companies"
ME_COMPANIES = "/v2/me/companies"

MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_SWITCH_COMPANY = "Cambia a esta empresa para gestionarla"
MSG_NOT_FOUND = "Empresa no encontrada"
MSG_NO_CHANGES = "No hay cambios que guardar"
MSG_DELETE_BLOCKED = "No se puede borrar la empresa: tiene "

VIEW_AS_WORKER = {"view_as": "worker"}
VIEW_AS_MANAGER = {"view_as": "manager"}

ESCUELA_NORTE = "Escuela Norte"
TAX_CONFIG = {"social_security": 0.0648}
DEFINITIONS = {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
SETTINGS = {"modules": {"daily_report": True}, "allowed_rates": ["particular"]}

# Claves de estructura del contrato (CompanyFull, CompanyReduced, miembro y usuario del miembro).
FULL_KEYS = {
    "id",
    "name",
    "is_active",
    "is_managed",
    "tax_config",
    "worklog_definitions",
    "settings",
    "created_at",
    "updated_at",
}
# Datos de la membresia del usuario objetivo que anade la vista completa de /v2/users/{id}/companies.
MEMBERSHIP_KEYS = {"role", "is_active_member", "rates_config"}
REDUCED_KEYS = {
    "id",
    "name",
    "is_managed",
    "role",
    "is_active_member",
    "rates_config",
    "worklog_definitions",
    "tax_config",
    "settings",
}
REDUCED_SETTINGS_KEYS = {"worker_experience", "ui_customization", "modules", "business_logic"}
MEMBER_KEYS = {
    "user_id",
    "company_id",
    "role",
    "is_active",
    "sort_order",
    "rates_config",
    "settings",
    "joined_at",
    "user",
}
MEMBER_USER_KEYS = {"id", "email", "first_name", "last_name", "is_active"}
FORBIDDEN_ANYWHERE = ("cost_markup",)

# Actores de la matriz. PA en "ver como" se modela con el claim view_as sobre el token del PA.
NON_PA_ACTORS = ["manager", "worker", "pa_view_as_worker", "pa_view_as_manager"]


# --- Fixtures y helpers ---


@pytest.fixture
def world(db):
    """Empresa con manager y worker, empresa suspendida con los mismos miembros y una empresa ajena
    con su propio manager. El PA no es miembro de ninguna."""
    company = make_company(
        db, name=ESCUELA_NORTE, tax_config=TAX_CONFIG, worklog_definitions=DEFINITIONS, settings=SETTINGS
    )
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    pa = make_user(db, role="admin")

    suspended = make_company(db, name="Escuela Suspendida", is_active=False)
    make_member(db, manager, suspended, role="manager")
    make_member(db, worker, suspended, role="worker")

    other = make_company(db, name="Escuela Sur")
    other_manager = make_user(db)
    make_member(db, other_manager, other, role="manager")

    return SimpleNamespace(
        company=company,
        manager=manager,
        worker=worker,
        pa=pa,
        suspended=suspended,
        other=other,
        other_manager=other_manager,
    )


def _act(client, world, actor: str):
    """Deja en el cliente el token del actor sobre la empresa del escenario."""
    if actor == "manager":
        return as_user(client, world.manager, world.company)
    if actor == "worker":
        return as_user(client, world.worker, world.company)
    if actor == "pa":
        return as_user(client, world.pa, world.company)
    if actor == "pa_view_as_worker":
        return as_user(client, world.pa, world.company, claims=VIEW_AS_WORKER)
    if actor == "pa_view_as_manager":
        return as_user(client, world.pa, world.company, claims=VIEW_AS_MANAGER)
    raise ValueError(f"actor desconocido: {actor}")


def _fresh(db, company_id):
    db.expire_all()
    return db.get(models.Company, company_id)


def _company_count(db):
    db.expire_all()
    return db.query(models.Company).count()


def _audit_rows(db, action=None, company_id=None):
    db.expire_all()
    query = db.query(models.AuditLog)
    if action is not None:
        query = query.filter(models.AuditLog.action == action)
    if company_id is not None:
        query = query.filter(models.AuditLog.company_id == company_id)
    return query.all()


def _audit_count(db):
    db.expire_all()
    return db.query(models.AuditLog).count()


def _all_keys(node):
    """Todas las claves de una estructura JSON anidada, a cualquier profundidad."""
    if isinstance(node, dict):
        for key, value in node.items():
            yield key
            yield from _all_keys(value)
    elif isinstance(node, list):
        for item in node:
            yield from _all_keys(item)


def _assert_snake_case(body):
    """Ninguna clave de estructura contiene mayusculas. Los datos del usuario (tax_config, worklog,
    settings) se crean con claves en minuscula en este fichero, asi que la comprobacion es completa."""
    camel = [key for key in _all_keys(body) if isinstance(key, str) and re.search(r"[A-Z]", key)]
    assert camel == [], f"claves no snake_case: {camel}"


def _assert_no_leak(body):
    keys = set(_all_keys(body))
    leaked = [name for name in FORBIDDEN_ANYWHERE if name in keys]
    assert leaked == [], f"campos que no deben salir: {leaked}"


def _assert_reduced(body, *, role):
    assert set(body) == REDUCED_KEYS, sorted(body)
    assert "is_active" not in body
    assert set(body["settings"]) == REDUCED_SETTINGS_KEYS, sorted(body["settings"])
    assert "allowed_rates" not in body["settings"]
    assert body["role"] == role
    _assert_no_leak(body)
    _assert_snake_case(body)


def _assert_full(body):
    assert set(body) == FULL_KEYS, sorted(body)
    _assert_no_leak(body)
    _assert_snake_case(body)


def _assert_full_with_membership(body, *, role, is_active_member=True):
    """Vista completa de `/v2/users/{id}/companies`: CompanyFull mas la membresia del usuario objetivo."""
    assert set(body) == FULL_KEYS | MEMBERSHIP_KEYS, sorted(body)
    assert body["role"] == role
    assert body["is_active_member"] is is_active_member
    assert isinstance(body["rates_config"], dict)
    _assert_no_leak(body)
    _assert_snake_case(body)


def _ids(items):
    return {item["id"] for item in items}


# --- 1. Matriz de permisos: solo el PA actuando gestiona empresas ---


@pytest.mark.parametrize("actor", NON_PA_ACTORS)
def test_list_companies_is_platform_admin_only(client, world, actor):
    _act(client, world, actor)

    resp = client.get(BASE)

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("actor", NON_PA_ACTORS)
def test_create_company_is_platform_admin_only(client, db, world, actor):
    _act(client, world, actor)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": "Nueva Escuela", "tax_config": {}})

    assert resp.status_code == 403, resp.text
    assert _company_count(db) == before


@pytest.mark.parametrize("actor", NON_PA_ACTORS)
def test_update_company_is_platform_admin_only(client, db, world, actor):
    _act(client, world, actor)

    resp = client.put(f"{BASE}/{world.company.id}", json={"name": "Cambiada"})

    assert resp.status_code == 403, resp.text
    assert _fresh(db, world.company.id).name == ESCUELA_NORTE
    assert _audit_rows(db, company_id=world.company.id) == []


@pytest.mark.parametrize("actor", NON_PA_ACTORS)
def test_delete_company_is_platform_admin_only(client, db, world, actor):
    _act(client, world, actor)

    resp = client.delete(f"{BASE}/{world.company.id}")

    assert resp.status_code == 403, resp.text
    assert _fresh(db, world.company.id) is not None


# --- 2. Alta: validacion y auditoria ---


def test_create_company_returns_201_full_view_and_audits_creation(client, db, world):
    as_user(client, world.pa, world.company)

    resp = client.post(BASE, json={"name": "Nueva Escuela", "tax_config": {}})

    assert resp.status_code == 201, resp.text
    body = resp.json()
    _assert_full(body)
    assert body["name"] == "Nueva Escuela"
    assert body["is_active"] is True
    assert body["is_managed"] is False
    assert body["tax_config"] == {}
    rows = _audit_rows(db, "company.created", uuid.UUID(body["id"]))
    assert len(rows) == 1
    assert rows[0].actor_user_id == world.pa.id
    assert rows[0].new_value == {"name": "Nueva Escuela", "is_active": True, "is_managed": False}


@pytest.mark.parametrize(
    "name",
    [
        pytest.param("", id="empty"),
        pytest.param("   ", id="only_spaces"),
        pytest.param("x" * 121, id="121_chars"),
    ],
)
def test_create_company_rejects_invalid_name_with_422(client, db, world, name):
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": name, "tax_config": {}})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_accepts_name_of_exactly_120_chars(client, world):
    as_user(client, world.pa, world.company)

    resp = client.post(BASE, json={"name": "x" * 120, "tax_config": {}})

    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "x" * 120


def test_create_company_strips_surrounding_spaces_from_name(client, world):
    as_user(client, world.pa, world.company)

    resp = client.post(BASE, json={"name": "  Escuela Recortada  ", "tax_config": {}})

    assert resp.status_code == 201, resp.text
    assert resp.json()["name"] == "Escuela Recortada"


def test_create_company_requires_tax_config(client, db, world):
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": "Sin impuestos"})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_accepts_empty_tax_config(client, world):
    as_user(client, world.pa, world.company)

    resp = client.post(BASE, json={"name": "Impuestos vacios", "tax_config": {}})

    assert resp.status_code == 201, resp.text
    assert resp.json()["tax_config"] == {}


@pytest.mark.parametrize(
    "tax_config",
    [
        pytest.param({"iva": -0.1}, id="negative_rate"),
        pytest.param({"iva": 1.5}, id="rate_above_one"),
        pytest.param({"iva": "0.1"}, id="rate_as_string"),
        pytest.param({"": 0.1}, id="empty_tax_name"),
        pytest.param({"x" * 51: 0.1}, id="tax_name_51_chars"),
        pytest.param({f"t{i}": 0.01 for i in range(21)}, id="more_than_20_taxes"),
    ],
)
def test_create_company_rejects_invalid_tax_config(client, db, world, tax_config):
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": "Impuestos malos", "tax_config": tax_config})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


@pytest.mark.parametrize("unit", ["days", "fixed"])
def test_create_company_accepts_days_and_fixed_worklog_units(client, world, unit):
    as_user(client, world.pa, world.company)
    definitions = {"guardia": {"unit": unit, "label": "Guardia", "fields": []}}

    resp = client.post(BASE, json={"name": "Turnos", "tax_config": {}, "worklog_definitions": definitions})

    assert resp.status_code == 201, resp.text
    assert resp.json()["worklog_definitions"] == definitions


@pytest.mark.parametrize(
    "definition",
    [
        pytest.param({"unit": "weeks", "label": "G", "fields": []}, id="unit_weeks"),
        pytest.param({"label": "G", "fields": []}, id="missing_unit"),
    ],
)
def test_create_company_rejects_invalid_worklog_unit(client, db, world, definition):
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": "Turnos", "tax_config": {}, "worklog_definitions": {"guardia": definition}})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_rejects_cost_markup_in_settings(client, db, world):
    """CompanySettings tiene extra="forbid": cost_markup no es una clave admitida en escritura."""
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(
        BASE,
        json={"name": "Con coste", "tax_config": {}, "settings": {"cost_markup": 1.2}},
    )

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_rejects_null_is_active(client, db, world):
    as_user(client, world.pa, world.company)
    before = _company_count(db)

    resp = client.post(BASE, json={"name": "Nula", "tax_config": {}, "is_active": None})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


# --- 3. Edicion: auditoria por campo y casos sin cambios ---

# (payload v2, accion de auditoria esperada, campo que cambia)
EVENT_CASES = [
    pytest.param({"tax_config": {"social_security": 0.1}}, "company.tax_config_changed", "tax_config", id="tax_config"),
    pytest.param(
        {"settings": {"modules": {"coordination": True}}}, "company.settings_changed", "settings", id="settings"
    ),
    pytest.param(
        {"worklog_definitions": {"guardia": {"unit": "hours", "label": "Guardia", "fields": []}}},
        "company.worklog_definitions_changed",
        "worklog_definitions",
        id="worklog_definitions",
    ),
    pytest.param({"name": "Renombrada"}, "company.updated", "name", id="name"),
    pytest.param({"is_managed": True}, "company.managed_changed", "is_managed", id="is_managed"),
    pytest.param({"is_active": False}, "company.suspended", "is_active", id="suspended"),
]

# Valor antiguo de cada campo en el escenario `world.company`
OLD_VALUES = {
    "tax_config": TAX_CONFIG,
    "settings": SETTINGS,
    "worklog_definitions": DEFINITIONS,
    "name": ESCUELA_NORTE,
    "is_managed": False,
    "is_active": True,
}


@pytest.mark.parametrize("payload, action, field", EVENT_CASES)
def test_put_emits_single_event_with_old_and_new_value(client, db, world, payload, action, field):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"{BASE}/{cid}", json=payload)

    assert resp.status_code == 200, resp.text
    rows = _audit_rows(db, action, cid)
    assert len(rows) == 1
    assert rows[0].actor_user_id == world.pa.id
    assert rows[0].old_value == {field: OLD_VALUES[field]}
    assert rows[0].new_value == {field: payload[field]}
    assert rows[0].reason is None


def test_put_with_several_fields_emits_one_event_per_field(client, db, world):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(
        f"{BASE}/{cid}",
        json={"name": "Renombrada", "is_managed": True, "tax_config": {"social_security": 0.1}},
    )

    assert resp.status_code == 200, resp.text
    rows = _audit_rows(db, company_id=cid)
    assert {row.action for row in rows} == {
        "company.updated",
        "company.managed_changed",
        "company.tax_config_changed",
    }
    assert len(rows) == 3
    assert all(row.actor_user_id == world.pa.id for row in rows)


def test_suspend_stores_reason_only_on_is_active_event(client, db, world):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"{BASE}/{cid}", json={"is_active": False, "reason": "Impago", "name": "Renombrada"})

    assert resp.status_code == 200, resp.text
    suspended = _audit_rows(db, "company.suspended", cid)
    updated = _audit_rows(db, "company.updated", cid)
    assert len(suspended) == 1 and suspended[0].reason == "Impago"
    assert len(updated) == 1 and updated[0].reason is None
    assert _fresh(db, cid).is_active is False


def test_reactivate_emits_reactivated_with_reason(client, db, world):
    cid = world.suspended.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"{BASE}/{cid}", json={"is_active": True, "reason": "Pago recibido"})

    assert resp.status_code == 200, resp.text
    rows = _audit_rows(db, "company.reactivated", cid)
    assert len(rows) == 1
    assert rows[0].reason == "Pago recibido"
    assert rows[0].old_value == {"is_active": False}
    assert rows[0].new_value == {"is_active": True}
    assert _fresh(db, cid).is_active is True


def test_put_rejects_reason_longer_than_500_chars(client, db, world):
    as_user(client, world.pa, world.company)
    before = _audit_count(db)

    resp = client.put(f"{BASE}/{world.company.id}", json={"is_active": False, "reason": "x" * 501})

    assert resp.status_code == 422, resp.text
    assert _fresh(db, world.company.id).is_active is True
    assert _audit_count(db) == before


@pytest.mark.parametrize("field", ["tax_config", "worklog_definitions", "settings"])
def test_put_rejects_explicit_null_json_field(client, db, world, field):
    as_user(client, world.pa, world.company)
    before = _audit_count(db)

    resp = client.put(f"{BASE}/{world.company.id}", json={field: None})

    assert resp.status_code == 422, resp.text
    assert _audit_count(db) == before


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty_body"),
        pytest.param({"name": ESCUELA_NORTE}, id="same_name"),
        pytest.param({"is_active": True}, id="same_is_active"),
        pytest.param({"is_managed": False}, id="same_is_managed"),
        pytest.param({"tax_config": TAX_CONFIG}, id="same_tax_config"),
    ],
)
def test_put_without_changes_returns_422_and_writes_no_audit(client, db, world, payload):
    as_user(client, world.pa, world.company)
    before = _audit_count(db)

    resp = client.put(f"{BASE}/{world.company.id}", json=payload)

    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == MSG_NO_CHANGES
    assert _audit_count(db) == before


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({"is_active": None}, id="is_active_null"),
        pytest.param({"is_managed": None}, id="is_managed_null"),
        pytest.param({"name": ""}, id="empty_name"),
        pytest.param({"name": None}, id="null_name"),
        pytest.param({"name": "x" * 121}, id="name_121_chars"),
        pytest.param({"settings": {"cost_markup": 1.2}}, id="cost_markup_in_settings"),
        pytest.param({"tax_config": {"iva": 2}}, id="tax_rate_above_one"),
        pytest.param({"worklog_definitions": {"g": {"unit": "weeks", "label": "G"}}}, id="invalid_unit"),
    ],
)
def test_put_rejects_invalid_payload_with_422(client, db, world, payload):
    as_user(client, world.pa, world.company)
    before = _audit_count(db)

    resp = client.put(f"{BASE}/{world.company.id}", json=payload)

    assert resp.status_code == 422, resp.text
    assert _audit_count(db) == before


def test_put_unknown_company_returns_404_with_detail(client, db, world):
    as_user(client, world.pa, world.company)

    resp = client.put(f"{BASE}/{uuid.uuid4()}", json={"name": "Fantasma"})

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


def test_put_returns_full_view(client, world):
    as_user(client, world.pa, world.company)

    resp = client.put(f"{BASE}/{world.company.id}", json={"name": "Otra"})

    assert resp.status_code == 200, resp.text
    _assert_full(resp.json())
    assert resp.json()["name"] == "Otra"


def test_suspension_invalidates_cached_access_for_worker(client, world):
    """Tras suspender, un worker con la cache de acceso caliente recibe 403 en la siguiente llamada."""
    cid = world.company.id
    as_user(client, world.worker, world.company)
    warm = client.get(f"{BASE}/{cid}")
    assert warm.status_code == 200, warm.text

    as_user(client, world.pa, world.company)
    suspend = client.put(f"{BASE}/{cid}", json={"is_active": False})
    assert suspend.status_code == 200, suspend.text

    as_user(client, world.worker, world.company)
    resp = client.get(f"{BASE}/{cid}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


# --- 4. Borrado: 204 o 409 con motivos ---


def test_delete_empty_company_returns_204_and_audits_snapshot(client, db, world):
    empty = make_company(db, name="Vacia", is_managed=True)
    cid = empty.id
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{cid}")

    assert resp.status_code == 204, resp.text
    assert resp.content == b""
    assert _fresh(db, cid) is None
    rows = _audit_rows(db, "company.deleted", cid)
    assert len(rows) == 1
    assert rows[0].actor_user_id == world.pa.id
    assert rows[0].old_value == {"name": "Vacia", "is_active": True, "is_managed": True}


def test_delete_company_with_members_returns_409_without_deleting(client, db, world):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{cid}")

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_DELETE_BLOCKED + "2 miembros"
    assert _fresh(db, cid) is not None
    assert _audit_rows(db, "company.deleted", cid) == []


def test_delete_company_with_shifts_only_lists_shifts(client, db, world):
    shifty = make_company(db, name="Con turnos")
    make_work_log(db, world.pa, shifty)
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{shifty.id}")

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_DELETE_BLOCKED + "1 turnos"
    assert _fresh(db, shifty.id) is not None


def test_delete_company_with_subscription_lists_subscriptions(client, db, world):
    subscribed = make_company(db, name="Suscrita")
    module = models.AppModule(code_name="export_pdf", name="Exportar PDF", is_active=True)
    db.add(module)
    db.commit()
    db.add(
        models.ModuleSubscription(
            module_id=module.id,
            company_id=subscribed.id,
            user_id=None,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
        )
    )
    db.commit()
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{subscribed.id}")

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_DELETE_BLOCKED + "1 suscripciones"
    assert _fresh(db, subscribed.id) is not None


def test_delete_company_lists_all_blockers_separated_by_comma(client, db, world):
    cid = world.company.id
    make_work_log(db, world.pa, world.company)
    module = models.AppModule(code_name="coordination", name="Coordinacion", is_active=True)
    db.add(module)
    db.commit()
    db.add(
        models.ModuleSubscription(
            module_id=module.id,
            company_id=cid,
            user_id=None,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
        )
    )
    db.commit()
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{cid}")

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_DELETE_BLOCKED + "2 miembros, 1 turnos, 1 suscripciones"
    assert _fresh(db, cid) is not None


def test_delete_unknown_company_returns_404_with_detail(client, world):
    as_user(client, world.pa, world.company)

    resp = client.delete(f"{BASE}/{uuid.uuid4()}")

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


# --- 5. Lectura de una empresa: vista completa, reducida y anti-enumeracion ---


def test_get_company_pa_acting_gets_full_view(client, world):
    as_user(client, world.pa, world.company)

    resp = client.get(f"{BASE}/{world.company.id}")

    assert resp.status_code == 200, resp.text
    _assert_full(resp.json())
    assert resp.json()["id"] == str(world.company.id)
    assert resp.json()["settings"]["allowed_rates"] == ["particular"]


@pytest.mark.parametrize(
    "actor, role",
    [
        pytest.param("manager", "manager", id="manager"),
        pytest.param("worker", "worker", id="worker"),
        pytest.param("pa_view_as_worker", "worker", id="pa_view_as_worker"),
        pytest.param("pa_view_as_manager", "manager", id="pa_view_as_manager"),
    ],
)
def test_get_company_gets_reduced_view_for_non_acting_pa(client, world, actor, role):
    _act(client, world, actor)

    resp = client.get(f"{BASE}/{world.company.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    _assert_reduced(body, role=role)
    assert body["id"] == str(world.company.id)
    assert body["is_managed"] is False
    assert body["is_active_member"] is True
    assert body["worklog_definitions"] == DEFINITIONS
    assert body["tax_config"] == TAX_CONFIG
    assert set(body["settings"]) == REDUCED_SETTINGS_KEYS
    assert body["settings"]["modules"] == {"daily_report": True}
    assert body["settings"]["business_logic"] == {"price_type": "net"}


@pytest.mark.parametrize("actor", ["manager", "worker"])
def test_get_suspended_company_returns_403_for_members(client, world, actor):
    as_user(client, getattr(world, actor), world.suspended)

    resp = client.get(f"{BASE}/{world.suspended.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


def test_no_access_to_foreign_company_is_identical_to_missing_company(client, world):
    """Anti-enumeracion: una empresa ajena y una inexistente responden exactamente igual."""
    as_user(client, world.worker, world.company)
    foreign = client.get(f"{BASE}/{world.other.id}")
    missing = client.get(f"{BASE}/{uuid.uuid4()}")

    assert foreign.status_code == 403, foreign.text
    assert missing.status_code == 403, missing.text
    assert foreign.json() == missing.json()
    assert foreign.json()["detail"] == MSG_NO_ACCESS


def test_manager_foreign_company_is_identical_to_missing_company(client, world):
    as_user(client, world.manager, world.company)
    foreign = client.get(f"{BASE}/{world.other.id}")
    missing = client.get(f"{BASE}/{uuid.uuid4()}")

    assert foreign.status_code == 403, foreign.text
    assert foreign.json() == missing.json()
    assert foreign.json()["detail"] == MSG_NO_ACCESS


def test_pa_acting_on_missing_company_returns_404(client, world):
    as_user(client, world.pa, world.company)

    resp = client.get(f"{BASE}/{uuid.uuid4()}")

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


def test_manager_with_token_of_other_company_gets_switch_company(client, db, world):
    """Un manager de A y B con token de B no puede leer A sin cambiar de scope."""
    both = make_user(db)
    make_member(db, both, world.company, role="manager")
    make_member(db, both, world.other, role="manager")
    as_user(client, both, world.other)

    resp = client.get(f"{BASE}/{world.company.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


def test_manager_of_company_a_cannot_read_company_b(client, world):
    as_user(client, world.manager, world.company)

    resp = client.get(f"{BASE}/{world.other.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


# --- 6. Listado: paginacion, orden y include=members ---


def test_list_returns_items_and_total_for_pa(client, db, world):
    as_user(client, world.pa, world.company)

    resp = client.get(BASE)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == {"items", "total"}
    assert body["total"] == _company_count(db)
    assert len(body["items"]) == body["total"]
    for item in body["items"]:
        _assert_full(item)
        assert "members" not in item


def test_list_total_is_independent_of_page_size(client, db, world):
    as_user(client, world.pa, world.company)
    total = _company_count(db)

    page = client.get(f"{BASE}?limit=1&skip=0")
    beyond = client.get(f"{BASE}?skip={total}")

    assert page.status_code == 200, page.text
    assert len(page.json()["items"]) == 1
    assert page.json()["total"] == total
    assert beyond.status_code == 200, beyond.text
    assert beyond.json()["items"] == []
    assert beyond.json()["total"] == total


@pytest.mark.parametrize(
    "query",
    [
        pytest.param("limit=0", id="limit_zero"),
        pytest.param("limit=2001", id="limit_above_2000"),
        pytest.param("skip=-1", id="negative_skip"),
    ],
)
def test_list_rejects_out_of_range_pagination(client, world, query):
    as_user(client, world.pa, world.company)

    resp = client.get(f"{BASE}?{query}")

    assert resp.status_code == 422, resp.text


def test_list_orders_by_name_then_id(client, db, world):
    make_company(db, name="Igual")
    make_company(db, name="Igual")
    make_company(db, name="Alfa")
    as_user(client, world.pa, world.company)

    resp = client.get(BASE)

    assert resp.status_code == 200, resp.text
    keys = [(item["name"], uuid.UUID(item["id"]).int) for item in resp.json()["items"]]
    assert keys == sorted(keys)


def test_list_include_members_adds_members_to_each_item(client, world):
    as_user(client, world.pa, world.company)

    resp = client.get(f"{BASE}?include=members")

    assert resp.status_code == 200, resp.text
    items = {item["id"]: item for item in resp.json()["items"]}
    for item in items.values():
        assert set(item) == FULL_KEYS | {"members"}, sorted(item)
    members = items[str(world.company.id)]["members"]
    assert {member["user_id"] for member in members} == {str(world.manager.id), str(world.worker.id)}
    for member in members:
        assert set(member) == MEMBER_KEYS, sorted(member)
        assert set(member["user"]) == MEMBER_USER_KEYS, sorted(member["user"])
    _assert_snake_case(resp.json())


def test_list_without_include_has_no_members_key(client, world):
    as_user(client, world.pa, world.company)

    resp = client.get(BASE)

    assert resp.status_code == 200, resp.text
    assert all("members" not in item for item in resp.json()["items"])


def test_list_include_members_is_forbidden_for_manager(client, world):
    as_user(client, world.manager, world.company)

    resp = client.get(f"{BASE}?include=members")

    assert resp.status_code == 403, resp.text


def test_company_without_manager_is_a_valid_state_for_pa(client, db, world):
    """E7: una empresa sin gestor se lee, se edita, aparece en el listado y se borra si esta vacia."""
    orphan = make_company(db, name="Sin gestor")
    as_user(client, world.pa, world.company)

    read = client.get(f"{BASE}/{orphan.id}")
    edit = client.put(f"{BASE}/{orphan.id}", json={"name": "Gestionada despues"})
    listed = client.get(BASE)
    deleted = client.delete(f"{BASE}/{orphan.id}")

    assert read.status_code == 200, read.text
    _assert_full(read.json())
    assert edit.status_code == 200, edit.text
    assert edit.json()["name"] == "Gestionada despues"
    assert listed.status_code == 200, listed.text
    assert str(orphan.id) in _ids(listed.json()["items"])
    assert deleted.status_code == 204, deleted.text
    assert _fresh(db, orphan.id) is None


# --- 7. Snake_case en todas las respuestas ---


def test_every_v2_company_response_is_snake_case(client, world):
    cid = str(world.company.id)
    as_user(client, world.pa, world.company)
    pa_responses = [
        client.get(BASE),
        client.get(f"{BASE}?include=members"),
        client.get(f"{BASE}/{cid}"),
        client.get(ME_COMPANIES),
        client.get(f"/v2/users/{world.worker.id}/companies"),
        client.post(BASE, json={"name": "Alta snake", "tax_config": TAX_CONFIG}),
        client.put(f"{BASE}/{cid}", json={"name": "Snake editada"}),
    ]
    _act(client, world, "manager")
    manager_read = client.get(f"{BASE}/{cid}")
    for resp in pa_responses + [manager_read]:
        assert resp.status_code in (200, 201), resp.text
        _assert_snake_case(resp.json())


# --- 8. Mi lista de empresas: /v2/me/companies ---


def test_me_companies_pa_acting_returns_all_companies_as_full_view(client, db, world):
    as_user(client, world.pa, world.company)

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert _ids(resp.json()) == {str(company.id) for company in db.query(models.Company).all()}
    for item in resp.json():
        _assert_full(item)


def test_me_companies_worker_lists_only_own_active_memberships(client, db, world):
    stranger = make_company(db, name="Ajena")
    inactive = make_company(db, name="Membresia inactiva")
    make_member(db, world.worker, inactive, is_active=False)
    as_user(client, world.worker, world.company)

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert _ids(resp.json()) == {str(world.company.id)}
    assert str(stranger.id) not in _ids(resp.json())
    assert str(world.suspended.id) not in _ids(resp.json())
    for item in resp.json():
        _assert_reduced(item, role="worker")
        assert item["is_active_member"] is True


def test_me_companies_manager_lists_own_company_with_manager_role(client, world):
    as_user(client, world.manager, world.company)

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 200, resp.text
    assert _ids(resp.json()) == {str(world.company.id)}
    _assert_reduced(resp.json()[0], role="manager")


def test_me_companies_pa_view_as_with_membership_returns_reduced_list(client, db, world):
    make_member(db, world.pa, world.company, role="manager")
    as_user(client, world.pa, world.company, claims=VIEW_AS_WORKER)

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    _assert_reduced(resp.json()[0], role="manager")


def test_me_companies_pa_view_as_without_membership_returns_empty_list(client, world):
    as_user(client, world.pa, world.company, claims=VIEW_AS_WORKER)

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_me_companies_requires_authentication(client, world):
    client.cookies.clear()

    resp = client.get(ME_COMPANIES)

    assert resp.status_code == 401, resp.text


# --- 9. Empresas de un usuario: /v2/users/{id}/companies ---


def test_user_companies_pa_acting_returns_all_including_inactive(client, db, world):
    inactive = make_company(db, name="Membresia desactivada")
    make_member(db, world.worker, inactive, is_active=False)
    as_user(client, world.pa, world.company)

    resp = client.get(f"/v2/users/{world.worker.id}/companies")

    assert resp.status_code == 200, resp.text
    assert isinstance(resp.json(), list)
    assert _ids(resp.json()) == {str(world.company.id), str(world.suspended.id), str(inactive.id)}
    by_id = {item["id"]: item for item in resp.json()}
    _assert_full_with_membership(by_id[str(world.company.id)], role="worker")
    _assert_full_with_membership(by_id[str(inactive.id)], role="worker", is_active_member=False)
    for item in resp.json():
        assert set(item) == FULL_KEYS | MEMBERSHIP_KEYS, sorted(item)


def test_user_companies_pa_full_view_carries_target_membership_not_actor_membership(client, db, world):
    """role y rates_config son los del usuario objetivo en cada empresa, no los del PA ni de otra empresa."""
    rates = {"particular": {"base_rate": 33.5, "is_gross": False, "tax_overrides": {}}}
    target = make_user(db)
    make_member(db, target, world.company, role="manager", rates_config=rates)
    make_member(db, target, world.other, role="worker", rates_config={})
    as_user(client, world.pa, world.company)

    resp = client.get(f"/v2/users/{target.id}/companies")

    assert resp.status_code == 200, resp.text
    by_id = {item["id"]: item for item in resp.json()}
    assert set(by_id) == {str(world.company.id), str(world.other.id)}
    assert by_id[str(world.company.id)]["role"] == "manager"
    assert by_id[str(world.company.id)]["rates_config"] == rates
    assert by_id[str(world.other.id)]["role"] == "worker"
    assert by_id[str(world.other.id)]["rates_config"] == {}


def test_user_companies_pa_inactive_member_is_reflected(client, db, world):
    target = make_user(db)
    make_member(db, target, world.company, role="worker", is_active=False)
    as_user(client, world.pa, world.company)

    resp = client.get(f"/v2/users/{target.id}/companies")

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    _assert_full_with_membership(resp.json()[0], role="worker", is_active_member=False)


def test_user_companies_manager_reduced_view_keeps_membership_and_hides_management_fields(client, db, world):
    """Vista reducida: misma forma que v1 (role, is_active_member y rates_config del objetivo; nada mas de gestion)."""
    rates = {"particular": {"base_rate": 18.0, "is_gross": True, "tax_overrides": {}}}
    target = make_user(db)
    make_member(db, target, world.company, role="worker", rates_config=rates)
    as_user(client, world.manager, world.company)

    resp = client.get(f"/v2/users/{target.id}/companies")

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    body = resp.json()[0]
    _assert_reduced(body, role="worker")
    assert body["is_active_member"] is True
    assert body["rates_config"] == rates


def test_user_companies_manager_only_reveals_token_company(client, db, world):
    """El manager de A y B con token de A solo ve la empresa del token, aunque el usuario pertenezca a B."""
    make_member(db, world.manager, world.other, role="manager")
    make_member(db, world.worker, world.other, role="worker")
    as_user(client, world.manager, world.company)

    resp = client.get(f"/v2/users/{world.worker.id}/companies")

    assert resp.status_code == 200, resp.text
    assert _ids(resp.json()) == {str(world.company.id)}
    _assert_reduced(resp.json()[0], role="worker")


def test_user_companies_manager_gets_empty_list_when_target_is_inactive_member(client, db, world):
    target = make_user(db)
    make_member(db, target, world.company, role="worker", is_active=False)
    as_user(client, world.manager, world.company)

    resp = client.get(f"/v2/users/{target.id}/companies")

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_user_companies_manager_without_token_company_is_forbidden(client, world):
    as_user(client, world.manager)

    resp = client.get(f"/v2/users/{world.worker.id}/companies")

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize(
    "actor",
    [
        pytest.param("worker", id="worker"),
        pytest.param("pa_view_as_worker", id="pa_view_as_worker"),
    ],
)
def test_user_companies_forbidden_for_worker_and_pa_view_as(client, world, actor):
    _act(client, world, actor)

    resp = client.get(f"/v2/users/{world.worker.id}/companies")

    assert resp.status_code == 403, resp.text
