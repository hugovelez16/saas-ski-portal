"""
Pruebas HTTP de la API v2 de membresias y tarifas (PR-18.0).

Contrato: los mismos casos que tests/routers/test_members.py (PR-05, API v1) pero contra
`/v2/companies/{company_id}/members` y `/rates`, en snake_case. La politica de acceso es identica a
v1 final: add, DELETE, status y role solo PA; rates y settings segun access_policy; order y listado
para manager; sin guardia de ultimo manager (E7).

Hoy los endpoints v2 de membresias no existen (PR-18.1), asi que estas pruebas deben FALLAR con 404
(ruta inexistente). Cada prueba comprueba primero el codigo de estado para que el fallo sea siempre
por la razon correcta y no por un assert posterior.

No se mockea la logica: se usan el TestClient (`client`), la sesion `db` y las fabricas de tests/factories.py.
"""

import json
import re
import uuid
from types import SimpleNamespace

import models
import pytest
from contracts import RATES_CONFIG_MAX_KEYS

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

BASE = "/v2/companies"

MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_FORBIDDEN = "No tienes permisos para esta accion"
MSG_NOT_FOUND = "Empresa no encontrada"
MSG_MANAGED_READONLY = "En empresas gestionadas solo el equipo gestor puede modificar turnos y tarifas"
VIEW_AS_READONLY_FRAGMENT = "solo lectura"
ORDER_MESSAGE = "Order updated successfully"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_SWITCH_COMPANY = "Cambia a esta empresa para gestionarla"

OLD_RATES = {"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}}
NEW_RATES = {"particular": {"base_rate": 25.0, "is_gross": True, "tax_overrides": {}}}
NEGATIVE_RATES = {"particular": {"base_rate": -5.0, "is_gross": True, "tax_overrides": {}}}
UNDEFINED_TYPE_RATES = {"guardia": {"base_rate": 10.0, "is_gross": True, "tax_overrides": {}}}
UI_SETTINGS = {"ui_preferences": {"theme": "dark"}}

# Contrato MemberOut de v2 (PR-18 tabla de endpoints) y del usuario anidado.
MEMBER_KEYS = {
    "user_id",
    "company_id",
    "role",
    "is_active",
    "sort_order",
    "rates_config",
    "settings",
    "joined_at",
    "updated_at",
    "user",
}
MEMBER_USER_KEYS = {"id", "email", "first_name", "last_name", "is_active"}

PA_ONLY_ENDPOINTS = ["add", "status", "role", "delete"]
ALL_MEMBER_ENDPOINTS = PA_ONLY_ENDPOINTS + ["rates", "settings", "order"]
# Respuesta 201 solo cuando el alta crea una membresia nueva (el resto de casos responde 200).
PA_EXPECTED_STATUS = {"add": 201}


# --- Fixtures y helpers ---


def _scenario(db):
    """Empresa con un manager y un worker activos, un usuario ajeno a la empresa y un PA de plataforma."""
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    outsider = make_user(db)
    pa = make_user(db, role="admin")
    return SimpleNamespace(company=company, manager=manager, worker=worker, outsider=outsider, pa=pa)


def _members_url(company):
    return f"{BASE}/{company.id}/members"


def _membership(db, user, company):
    db.expire_all()
    return db.query(models.CompanyMember).filter_by(user_id=user.id, company_id=company.id).one()


def _audit_rows(db, action):
    db.expire_all()
    return db.query(models.AuditLog).filter(models.AuditLog.action == action).all()


def _assert_trace(row, actor, company, target):
    assert row.actor_user_id == actor.id
    assert row.company_id == company.id
    assert row.target_user_id == target.id


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
    """Ninguna clave de la respuesta contiene mayusculas (contrato snake_case sin alias camelCase)."""
    camel = [key for key in _all_keys(body) if isinstance(key, str) and re.search(r"[A-Z]", key)]
    assert camel == [], f"claves no snake_case: {camel}"


def _call(client, name, company, member, outsider):
    """Ejecuta la operacion `name` de la API v2 sobre `member` (miembro de `company`)."""
    cid = company.id
    mid = member.id
    if name == "add":
        return client.post(f"{BASE}/{cid}/members", json={"email": outsider.email})
    if name == "status":
        return client.put(f"{BASE}/{cid}/members/{mid}/status", json={"is_active": False})
    if name == "role":
        return client.put(f"{BASE}/{cid}/members/{mid}/role", json={"role": "manager"})
    if name == "delete":
        return client.delete(f"{BASE}/{cid}/members/{mid}")
    if name == "rates":
        return client.put(f"{BASE}/{cid}/members/{mid}/rates", json={"rates_config": NEW_RATES})
    if name == "settings":
        return client.put(f"{BASE}/{cid}/members/{mid}/settings", json={"settings": UI_SETTINGS})
    if name == "order":
        return client.put(f"{BASE}/{cid}/members/order", json={"user_ids": [str(mid)]})
    raise ValueError(f"endpoint desconocido: {name}")


# --- Listado de membresias (manager) ---


def test_list_members_returns_member_out_contract(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company)

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert isinstance(body, list)
    assert {member["user_id"] for member in body} == {str(s.manager.id), str(s.worker.id)}
    for member in body:
        assert set(member) == MEMBER_KEYS, sorted(set(member) ^ MEMBER_KEYS)
        assert set(member["user"]) == MEMBER_USER_KEYS, sorted(member["user"])
    _assert_snake_case(body)


def test_list_members_filters_by_is_active(client, db):
    s = _scenario(db)
    inactive = make_user(db)
    make_member(db, inactive, s.company, role="worker", is_active=False)
    as_user(client, s.pa, s.company)

    resp_all = client.get(_members_url(s.company))
    resp_active = client.get(_members_url(s.company), params={"is_active": "true"})
    resp_inactive = client.get(_members_url(s.company), params={"is_active": "false"})

    assert resp_all.status_code == 200, resp_all.text
    assert resp_active.status_code == 200, resp_active.text
    assert resp_inactive.status_code == 200, resp_inactive.text
    assert {m["user_id"] for m in resp_all.json()} == {str(s.manager.id), str(s.worker.id), str(inactive.id)}
    assert {m["user_id"] for m in resp_active.json()} == {str(s.manager.id), str(s.worker.id)}
    assert {m["user_id"] for m in resp_inactive.json()} == {str(inactive.id)}


def test_list_members_rejects_non_boolean_is_active_with_422(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.get(_members_url(s.company), params={"is_active": "maybe"})

    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize("claims", [None, {"view_as": "worker"}], ids=["worker", "pa_view_as_worker"])
def test_list_members_forbidden_for_worker_and_pa_view_as_worker(client, db, claims):
    s = _scenario(db)
    if claims is None:
        as_user(client, s.worker, s.company)
    else:
        as_user(client, s.pa, s.company, claims=claims)

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN


def test_list_members_unknown_or_foreign_company_return_same_codes(client, db):
    s = _scenario(db)
    other = make_company(db)
    other_manager = make_user(db)
    make_member(db, other_manager, other, role="manager")
    as_user(client, s.manager, s.company)

    foreign = client.get(_members_url(other))
    unknown = client.get(f"{BASE}/{uuid.uuid4()}/members")

    assert foreign.status_code == 403, foreign.text
    assert unknown.status_code == 403, unknown.text
    assert foreign.json()["detail"] == MSG_NO_ACCESS
    assert unknown.json()["detail"] == MSG_NO_ACCESS


def test_list_members_unknown_company_for_pa_returns_404_with_detail(client, db):
    s = _scenario(db)
    as_user(client, s.pa, None)

    resp = client.get(f"{BASE}/{uuid.uuid4()}/members")

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


# --- Matriz de permisos ---


@pytest.mark.parametrize("name", PA_ONLY_ENDPOINTS)
def test_manager_gets_403_on_pa_only_member_endpoints(client, db, name):
    s = _scenario(db)
    as_user(client, s.manager, s.company)

    resp = _call(client, name, s.company, s.worker, s.outsider)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN


@pytest.mark.parametrize("name", ALL_MEMBER_ENDPOINTS)
def test_worker_gets_403_on_every_member_endpoint_for_other_member(client, db, name):
    s = _scenario(db)
    actor = make_user(db)
    make_member(db, actor, s.company, role="worker")
    as_user(client, actor, s.company)

    resp = _call(client, name, s.company, s.worker, s.outsider)

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("name", ALL_MEMBER_ENDPOINTS)
def test_pa_gets_success_on_every_member_endpoint(client, db, name):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = _call(client, name, s.company, s.worker, s.outsider)

    assert resp.status_code == PA_EXPECTED_STATUS.get(name, 200), resp.text


@pytest.mark.parametrize("name", ["rates", "settings", "order"])
def test_manager_is_allowed_on_rates_settings_and_order(client, db, name):
    s = _scenario(db)
    as_user(client, s.manager, s.company)

    resp = _call(client, name, s.company, s.worker, s.outsider)

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("name", ALL_MEMBER_ENDPOINTS)
@pytest.mark.parametrize("view_as", ["worker", "manager"])
def test_view_as_pa_is_read_only_on_member_endpoints(client, db, view_as, name):
    s = _scenario(db)
    as_user(client, s.pa, s.company, claims={"view_as": view_as})

    resp = _call(client, name, s.company, s.worker, s.outsider)

    assert resp.status_code == 403, resp.text
    assert VIEW_AS_READONLY_FRAGMENT in resp.json()["detail"]


# --- add: POST /v2/companies/{company_id}/members ---


def test_add_new_user_returns_201_creates_active_worker_and_emits_member_added(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.post(_members_url(s.company), json={"email": s.outsider.email})

    assert resp.status_code == 201, resp.text
    assert set(resp.json()) == MEMBER_KEYS
    assert resp.json()["role"] == "worker"
    assert resp.json()["is_active"] is True
    membership = _membership(db, s.outsider, s.company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker
    rows = _audit_rows(db, "member.added")
    assert len(rows) == 1
    _assert_trace(rows[0], s.pa, s.company, s.outsider)


def test_add_reactivates_inactive_manager_as_worker_and_emits_reactivated(client, db):
    s = _scenario(db)
    former = make_user(db)
    make_member(db, former, s.company, role="manager", is_active=False)
    as_user(client, s.pa, s.company)

    resp = client.post(_members_url(s.company), json={"email": former.email})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, former, s.company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker  # M6: la reactivacion fuerza worker
    rows = _audit_rows(db, "member.reactivated")
    assert len(rows) == 1
    assert rows[0].old_value == {"is_active": False, "role": "manager"}
    assert rows[0].new_value == {"is_active": True, "role": "worker"}
    _assert_trace(rows[0], s.pa, s.company, former)


def test_add_already_active_member_returns_200_without_events(client, db):
    s = _scenario(db)
    active_manager = make_user(db)
    make_member(db, active_manager, s.company, role="manager", is_active=True)
    as_user(client, s.pa, s.company)

    resp = client.post(_members_url(s.company), json={"email": active_manager.email})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, active_manager, s.company)
    assert membership.role == models.CompanyRole.manager
    assert membership.is_active is True
    assert _audit_rows(db, "member.added") == []
    assert _audit_rows(db, "member.reactivated") == []


def test_add_unknown_email_returns_404(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    # Control: la misma ruta da de alta a un usuario real; asi el 404 siguiente no puede venir de una ruta inexistente.
    control = client.post(_members_url(s.company), json={"email": s.outsider.email})
    assert control.status_code == 201, control.text

    resp = client.post(_members_url(s.company), json={"email": "nadie@test.com"})

    assert resp.status_code == 404, resp.text


def test_add_malformed_email_returns_422(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.post(_members_url(s.company), json={"email": "no-es-un-email"})

    assert resp.status_code == 422, resp.text


def test_add_to_nonexistent_company_returns_404_with_detail(client, db):
    s = _scenario(db)
    as_user(client, s.pa, None)

    resp = client.post(f"{BASE}/{uuid.uuid4()}/members", json={"email": s.outsider.email})

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


def test_pa_only_endpoints_do_not_reveal_company_existence_to_manager(client, db):
    s = _scenario(db)
    other = make_company(db)
    as_user(client, s.manager, s.company)

    foreign = client.post(_members_url(other), json={"email": s.outsider.email})
    unknown = client.post(f"{BASE}/{uuid.uuid4()}/members", json={"email": s.outsider.email})

    assert foreign.status_code == 403, foreign.text
    assert unknown.status_code == 403, unknown.text
    assert foreign.json()["detail"] == unknown.json()["detail"] == MSG_FORBIDDEN


# --- status: PUT .../members/{user_id}/status con cuerpo {is_active} ---


def test_status_false_deactivates_and_true_reactivates(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    off = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/status", json={"is_active": False})

    assert off.status_code == 200, off.text
    assert off.json()["is_active"] is False
    assert _membership(db, s.worker, s.company).is_active is False

    on = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/status", json={"is_active": True})

    assert on.status_code == 200, on.text
    assert on.json()["is_active"] is True
    assert _membership(db, s.worker, s.company).is_active is True


@pytest.mark.parametrize("body", [{"is_active": "maybe"}, {}, {"status": "inactive"}])
def test_status_rejects_invalid_body_with_422(client, db, body):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/status", json=body)

    assert resp.status_code == 422, resp.text
    assert _membership(db, s.worker, s.company).is_active is True


def test_status_legacy_query_parameter_is_not_accepted(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/status", params={"status": "inactive"})

    assert resp.status_code == 422, resp.text
    assert _membership(db, s.worker, s.company).is_active is True


def test_status_on_non_member_returns_404(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    # Control: la ruta responde 200 sobre un miembro real.
    control = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/status", json={"is_active": True})
    assert control.status_code == 200, control.text

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.outsider.id}/status", json={"is_active": False})

    assert resp.status_code == 404, resp.text


def test_deactivating_membership_does_not_reassign_other_memberships(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    user = make_user(db)
    make_member(db, user, company_a, role="worker")
    make_member(db, user, company_b, role="manager")
    pa = make_user(db, role="admin")
    as_user(client, pa, company_a)

    resp = client.put(f"{BASE}/{company_a.id}/members/{user.id}/status", json={"is_active": False})

    assert resp.status_code == 200, resp.text
    assert _membership(db, user, company_a).is_active is False
    other = _membership(db, user, company_b)
    assert other.is_active is True
    assert other.role == models.CompanyRole.manager


def test_reactivating_member_forces_worker_role(client, db):
    s = _scenario(db)
    former = make_user(db)
    make_member(db, former, s.company, role="manager", is_active=False)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{former.id}/status", json={"is_active": True})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, former, s.company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker  # M6


# --- role: PUT .../members/{user_id}/role ---


def test_pa_changes_worker_to_manager_and_emits_role_changed(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/role", json={"role": "manager"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "manager"
    assert _membership(db, s.worker, s.company).role == models.CompanyRole.manager
    rows = _audit_rows(db, "member.role_changed")
    assert len(rows) == 1
    _assert_trace(rows[0], s.pa, s.company, s.worker)


def test_role_admin_value_is_rejected_with_422(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/role", json={"role": "admin"})

    assert resp.status_code == 422, resp.text
    assert _membership(db, s.worker, s.company).role == models.CompanyRole.worker


def test_role_change_on_non_member_returns_404(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    # Control: la ruta responde 200 sobre un miembro real.
    control = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/role", json={"role": "worker"})
    assert control.status_code == 200, control.text

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.outsider.id}/role", json={"role": "manager"})

    assert resp.status_code == 404, resp.text


def test_role_change_takes_effect_on_next_request_of_affected_user(client, db):
    s = _scenario(db)
    # El worker no puede listar miembros (requiere manager); la peticion deja la politica cacheada.
    as_user(client, s.worker, s.company)
    assert client.get(_members_url(s.company)).status_code == 403

    as_user(client, s.pa, s.company)
    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/role", json={"role": "manager"})
    assert resp.status_code == 200, resp.text

    as_user(client, s.worker, s.company)
    assert client.get(_members_url(s.company)).status_code == 200


def test_last_manager_can_be_demoted_and_deactivated(client, db):
    # Sin guardia de ultimo manager en la empresa (E7): el PA puede degradarlo y desactivarlo.
    company = make_company(db)
    only_manager = make_user(db)
    make_member(db, only_manager, company, role="manager")
    pa = make_user(db, role="admin")
    as_user(client, pa, company)

    demote = client.put(f"{BASE}/{company.id}/members/{only_manager.id}/role", json={"role": "worker"})
    deactivate = client.put(f"{BASE}/{company.id}/members/{only_manager.id}/status", json={"is_active": False})

    assert demote.status_code == 200, demote.text
    assert deactivate.status_code == 200, deactivate.text
    assert _membership(db, only_manager, company).is_active is False


# --- delete: DELETE .../members/{user_id} ---


def test_delete_member_without_work_logs_removes_membership(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.delete(f"{BASE}/{s.company.id}/members/{s.worker.id}")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": True, "deactivated": False, "reason": None}
    db.expire_all()
    assert db.query(models.CompanyMember).filter_by(user_id=s.worker.id, company_id=s.company.id).count() == 0
    rows = _audit_rows(db, "member.removed")
    assert len(rows) == 1
    _assert_trace(rows[0], s.pa, s.company, s.worker)


def test_delete_member_with_work_logs_deactivates_and_keeps_logs(client, db):
    s = _scenario(db)
    make_work_log(db, s.worker, s.company)
    as_user(client, s.pa, s.company)

    resp = client.delete(f"{BASE}/{s.company.id}/members/{s.worker.id}")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": False, "deactivated": True, "reason": "has_work_logs"}
    assert _membership(db, s.worker, s.company).is_active is False
    db.expire_all()
    assert db.query(models.WorkLog).filter_by(user_id=s.worker.id, company_id=s.company.id).count() == 1
    rows = _audit_rows(db, "member.deactivated")
    assert len(rows) == 1
    _assert_trace(rows[0], s.pa, s.company, s.worker)


def test_delete_non_member_returns_404(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    # Control: la ruta borra a un miembro real (sin turnos).
    control = client.delete(f"{BASE}/{s.company.id}/members/{s.worker.id}")
    assert control.status_code == 200, control.text

    resp = client.delete(f"{BASE}/{s.company.id}/members/{s.outsider.id}")

    assert resp.status_code == 404, resp.text


# --- rates: PUT .../members/{user_id}/rates con cuerpo {rates_config} ---


@pytest.mark.parametrize("is_managed", [False, True])
@pytest.mark.parametrize("target", ["other", "self"])
def test_manager_can_edit_rates_of_any_member(client, db, is_managed, target):
    company = make_company(db, is_managed=is_managed)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    other = make_user(db)
    make_member(db, other, company, role="worker")
    subject = other if target == "other" else manager
    as_user(client, manager, company)

    resp = client.put(f"{BASE}/{company.id}/members/{subject.id}/rates", json={"rates_config": NEW_RATES})

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("is_managed", [False, True])
def test_worker_edits_own_rates_only_when_company_is_autonomous(client, db, is_managed):
    company = make_company(db, is_managed=is_managed)
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config=OLD_RATES)
    as_user(client, worker, company)

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": NEW_RATES})

    if is_managed:
        assert resp.status_code == 403, resp.text
        assert resp.json()["detail"] == MSG_MANAGED_READONLY
        assert _membership(db, worker, company).rates_config == OLD_RATES
    else:
        assert resp.status_code == 200, resp.text
        assert _membership(db, worker, company).rates_config == NEW_RATES


@pytest.mark.parametrize("is_managed", [False, True])
def test_worker_cannot_edit_rates_of_another_member(client, db, is_managed):
    company = make_company(db, is_managed=is_managed)
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config=OLD_RATES)
    other = make_user(db)
    make_member(db, other, company, role="worker", rates_config=OLD_RATES)
    as_user(client, worker, company)

    resp = client.put(f"{BASE}/{company.id}/members/{other.id}/rates", json={"rates_config": NEW_RATES})

    assert resp.status_code == 403, resp.text
    assert _membership(db, other, company).rates_config == OLD_RATES


def test_rates_change_emits_event_with_old_and_new_config(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config=OLD_RATES)
    as_user(client, manager, company)

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": NEW_RATES})

    assert resp.status_code == 200, resp.text
    rows = _audit_rows(db, "member.rates_changed")
    assert len(rows) == 1
    assert rows[0].old_value == OLD_RATES
    assert rows[0].new_value == NEW_RATES
    _assert_trace(rows[0], manager, company, worker)


def test_rates_negative_base_rate_returns_422(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/rates", json={"rates_config": NEGATIVE_RATES})

    assert resp.status_code == 422, resp.text


def test_rates_unknown_shift_type_returns_422(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/rates", json={"rates_config": UNDEFINED_TYPE_RATES})

    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "Tipo de turno desconocido"


# --- settings: PUT .../members/{user_id}/settings con cuerpo {settings} ---


@pytest.mark.parametrize("is_managed", [False, True])
def test_worker_edits_own_settings_in_managed_and_autonomous_company(client, db, is_managed):
    company = make_company(db, is_managed=is_managed)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, worker, company)

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/settings", json={"settings": UI_SETTINGS})

    assert resp.status_code == 200, resp.text


def test_worker_cannot_edit_settings_of_another_member(client, db):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    other = make_user(db)
    make_member(db, other, company, role="worker")
    as_user(client, worker, company)

    resp = client.put(f"{BASE}/{company.id}/members/{other.id}/settings", json={"settings": UI_SETTINGS})

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("actor_kind", ["manager", "pa"])
def test_manager_and_pa_can_edit_settings_of_another_member(client, db, actor_kind):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    if actor_kind == "manager":
        actor = make_user(db)
        make_member(db, actor, company, role="manager")
        as_user(client, actor, company)
    else:
        actor = make_user(db, role="admin")
        as_user(client, actor, company)

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/settings", json={"settings": UI_SETTINGS})

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("actor_kind", ["manager", "pa", "worker_self"])
@pytest.mark.parametrize(
    "bad_settings",
    [{"hacked": True}, {"ui_preferences": {"theme": "dark"}, "role": "admin"}],
    ids=["clave_desconocida", "clave_mezclada"],
)
def test_settings_rejects_keys_outside_whitelist_with_422(client, db, actor_kind, bad_settings):
    # M2: lista blanca de claves en todos los caminos que escriben settings.
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    if actor_kind == "manager":
        actor = make_user(db)
        make_member(db, actor, company, role="manager")
        as_user(client, actor, company)
    elif actor_kind == "pa":
        actor = make_user(db, role="admin")
        as_user(client, actor, company)
    else:
        actor = worker
        as_user(client, actor, company)

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/settings", json={"settings": bad_settings})

    assert resp.status_code == 422, resp.text
    assert _membership(db, worker, company).settings in (None, {})


# --- order: PUT /v2/companies/{company_id}/members/order ---


def test_manager_reorders_members_and_gets_message(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company)

    resp = client.put(
        f"{BASE}/{s.company.id}/members/order",
        json={"user_ids": [str(s.worker.id), str(s.manager.id)]},
    )

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"message": ORDER_MESSAGE}
    assert _membership(db, s.worker, s.company).sort_order == 0
    assert _membership(db, s.manager, s.company).sort_order == 1


# --- Listado de tarifas: GET /v2/companies/{company_id}/rates ---


def test_rates_list_includes_inactive_members_in_snake_case(client, db):
    s = _scenario(db)
    inactive = make_user(db)
    make_member(db, inactive, s.company, role="worker", is_active=False)
    as_user(client, s.manager, s.company)

    resp = client.get(f"{BASE}/{s.company.id}/rates")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {member["user_id"] for member in body} == {str(s.manager.id), str(s.worker.id), str(inactive.id)}
    for member in body:
        assert set(member) == MEMBER_KEYS, sorted(set(member) ^ MEMBER_KEYS)
    _assert_snake_case(body)


def test_rates_list_forbidden_for_worker(client, db):
    s = _scenario(db)
    as_user(client, s.worker, s.company)

    resp = client.get(f"{BASE}/{s.company.id}/rates")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN


# --- Contrato transversal ---


def test_member_responses_never_use_camel_case(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    requests = [
        ("GET", _members_url(s.company), None),
        ("POST", _members_url(s.company), {"email": s.outsider.email}),
        ("PUT", f"{BASE}/{s.company.id}/members/{s.worker.id}/status", {"is_active": True}),
        ("PUT", f"{BASE}/{s.company.id}/members/{s.worker.id}/role", {"role": "manager"}),
        ("PUT", f"{BASE}/{s.company.id}/members/{s.worker.id}/rates", {"rates_config": NEW_RATES}),
        ("PUT", f"{BASE}/{s.company.id}/members/{s.worker.id}/settings", {"settings": UI_SETTINGS}),
    ]

    for method, url, body in requests:
        resp = client.request(method, url, json=body)
        assert resp.status_code in (200, 201), f"{method} {url}: {resp.status_code} {resp.text}"
        _assert_snake_case(resp.json())


# --- Ruta antigua PUT sobre el recurso miembro (PR-21.0: sustituida por status, role, rates y settings) ---


def test_put_on_member_resource_is_not_a_v2_route(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}", json={"role": "manager"})

    assert resp.status_code in (404, 405), resp.text
    assert _membership(db, s.worker, s.company).role == models.CompanyRole.worker


# --- Portados de tests/routers/test_company_contracts.py, test_company_access.py, test_governance.py,
#     test_auth_security.py y test_tax_calculation.py (retirada de v1 en PR-21) ---


def _put_json(client, url, body):
    """Envia el cuerpo con json.dumps para reproducir NaN (no es JSON estandar, pero Starlette lo acepta)."""
    return client.put(url, content=json.dumps(body), headers={"content-type": "application/json"})


def _member_of_a_and_b(db, role):
    """Usuario no PA con membresia activa del mismo rol en las empresas A y B."""
    company_a = make_company(db)
    company_b = make_company(db)
    user = make_user(db)
    make_member(db, user, company_a, role=role)
    make_member(db, user, company_b, role=role)
    return user, company_a, company_b


def _other_member(db, company, role="worker"):
    other = make_user(db)
    make_member(db, other, company, role=role)
    return other


RATE_BASE = {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}

RATE_VALUE_OUTSIDE_CONTRACT = [
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

COMPANY_LEVEL_SETTINGS = [
    pytest.param({"business_logic": {"price_type": "gross"}}, id="business_logic"),
    pytest.param({"worker_experience": {"input_mode": "bulk"}}, id="worker_experience"),
    pytest.param({"ui_customization": {"labels": {"worklog": "Turno"}}}, id="ui_customization"),
    pytest.param({"modules": {"tutorials": True}}, id="modules"),
    pytest.param({"allowed_rates": ["particular"]}, id="allowed_rates"),
    pytest.param({"is_managed": True}, id="is_managed"),
]


def test_rates_keep_retired_type_already_in_member_rates(client, db):
    # "retirado" ya estaba en la tarifa del miembro y ya no existe en la empresa: no se vuelve a validar.
    company = make_company(db, worklog_definitions={"particular": {"unit": "hours", "label": "Particular"}})
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config={"retirado": {**RATE_BASE}})
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company)
    rates = {"retirado": {**RATE_BASE}, "particular": {**RATE_BASE}}

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": rates})

    assert resp.status_code == 200, resp.text


def test_rates_reject_new_undefined_type_even_when_retired_type_is_kept(client, db):
    company = make_company(db, worklog_definitions={"particular": {"unit": "hours", "label": "Particular"}})
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config={"retirado": {**RATE_BASE}})
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company)
    rates = {"retirado": {**RATE_BASE}, "guardia": {**RATE_BASE}}

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": rates})

    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == "Tipo de turno desconocido"


def test_rates_of_unknown_company_return_404_for_pa(client, db):
    # Equivalente v2 de la rama "empresa no resuelta" de v1: la autorizacion rechaza una empresa inexistente.
    pa = make_user(db, role="admin")
    as_user(client, pa)

    resp = client.put(f"{BASE}/{uuid.uuid4()}/members/{uuid.uuid4()}/rates", json={"rates_config": NEW_RATES})

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_NOT_FOUND


def test_rates_above_key_limit_return_422(client, db):
    # Limite de claves de contracts.RATES_CONFIG_MAX_KEYS; todos los tipos estan definidos en la empresa.
    many_types = {f"tipo{i}": {"unit": "hours", "label": f"Tipo {i}"} for i in range(RATES_CONFIG_MAX_KEYS + 1)}
    company = make_company(db, worklog_definitions=many_types)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company)
    rates = {f"tipo{i}": {**RATE_BASE} for i in range(RATES_CONFIG_MAX_KEYS + 1)}

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": rates})

    assert resp.status_code == 422, resp.text


def test_rates_with_few_keys_on_same_company_return_200(client, db):
    # Control: mismo tipo de empresa y de actor, con pocas claves, debe aceptarse.
    many_types = {f"tipo{i}": {"unit": "hours", "label": f"Tipo {i}"} for i in range(3)}
    company = make_company(db, worklog_definitions=many_types)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company)
    rates = {f"tipo{i}": {**RATE_BASE} for i in range(3)}

    resp = client.put(f"{BASE}/{company.id}/members/{worker.id}/rates", json={"rates_config": rates})

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("field, value", RATE_VALUE_OUTSIDE_CONTRACT)
def test_rates_with_invalid_numeric_value_return_422(client, db, field, value):
    s = _scenario(db)
    as_user(client, s.manager, s.company)
    entry = {**RATE_BASE, field: value}

    resp = _put_json(
        client,
        f"{BASE}/{s.company.id}/members/{s.worker.id}/rates",
        {"rates_config": {"particular": entry}},
    )

    assert resp.status_code == 422, resp.text


@pytest.mark.parametrize(
    "overrides",
    [{"IRPF": 1.5}, {"IRPF": -0.1}, {"IRPF": "x"}, {"IRPF": True}, {"": 0.1}],
    ids=["gt1", "neg", "str", "bool", "empty_name"],
)
def test_rates_with_invalid_tax_overrides_are_rejected_and_keep_previous(client, db, overrides):
    s = _scenario(db)
    as_user(client, s.pa, s.company)
    before = _membership(db, s.worker, s.company).rates_config

    resp = client.put(
        f"{BASE}/{s.company.id}/members/{s.worker.id}/rates",
        json={"rates_config": {"particular": {"base_rate": 20, "tax_overrides": overrides}}},
    )

    assert resp.status_code == 422, resp.text
    assert _membership(db, s.worker, s.company).rates_config == before


@pytest.mark.parametrize(
    "overrides",
    [None, {}, {"IRPF": 0.2}, {"IRPF": None}, {"IRPF": 0, "Mutua": 1}],
    ids=["null", "empty", "value", "none_value", "bounds"],
)
def test_rates_with_valid_tax_overrides_are_accepted_and_stored(client, db, overrides):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(
        f"{BASE}/{s.company.id}/members/{s.worker.id}/rates",
        json={"rates_config": {"particular": {"base_rate": 20, "tax_overrides": overrides}}},
    )

    assert resp.status_code == 200, resp.text
    assert _membership(db, s.worker, s.company).rates_config["particular"]["tax_overrides"] == overrides


def test_rates_without_tax_overrides_key_are_accepted(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company)

    resp = client.put(
        f"{BASE}/{s.company.id}/members/{s.worker.id}/rates",
        json={"rates_config": {"particular": {"base_rate": 20}}},
    )

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("settings", COMPANY_LEVEL_SETTINGS)
def test_worker_cannot_store_company_level_keys_in_member_settings(client, db, settings):
    s = _scenario(db)
    as_user(client, s.worker, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/settings", json={"settings": settings})

    assert resp.status_code == 422, resp.text
    assert _membership(db, s.worker, s.company).settings in (None, {})


def test_member_settings_keep_legacy_dialog_keys_until_o10(client, db):
    # TEMPORAL (O10): member-settings-dialog.tsx aun guarda estas claves; borrar con el dialogo.
    s = _scenario(db)
    as_user(client, s.worker, s.company)

    resp = client.put(
        f"{BASE}/{s.company.id}/members/{s.worker.id}/settings",
        json={"settings": {"allow_tutorial": True, "allow_coordination": False}},
    )

    assert resp.status_code == 200, resp.text


def test_worker_can_store_allowed_user_keys_in_member_settings(client, db):
    s = _scenario(db)
    as_user(client, s.worker, s.company)
    allowed = {"notifications": {"email": True}, "ui_preferences": {"compact": True}}

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/settings", json={"settings": allowed})

    assert resp.status_code == 200, resp.text
    assert _membership(db, s.worker, s.company).settings == allowed


def test_worker_member_settings_over_size_limit_returns_422(client, db):
    s = _scenario(db)
    as_user(client, s.worker, s.company)
    huge = {"ui_preferences": {"nota": "x" * 200_000}}

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/settings", json={"settings": huge})

    assert resp.status_code == 422, resp.text


def test_manager_cannot_change_member_role_and_role_is_kept(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company)

    resp = client.put(f"{BASE}/{s.company.id}/members/{s.worker.id}/role", json={"role": "manager"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN
    assert _membership(db, s.worker, s.company).role == models.CompanyRole.worker


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_change_role_in_a(client, db, role):
    # Para un no PA el cambio de rol responde 403 generico (anti-enumeracion), no el mensaje de cambio de empresa.
    user, company_a, company_b = _member_of_a_and_b(db, role)
    other = _other_member(db, company_a)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.put(f"{BASE}/{company_a.id}/members/{other.id}/role", json={"role": "manager"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN
    assert _membership(db, other, company_a).role == models.CompanyRole.worker


def test_list_members_is_allowed_for_pa_view_as_manager(client, db):
    s = _scenario(db)
    as_user(client, s.pa, s.company, claims={"view_as": "manager"})

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 200, resp.text
    assert {member["user_id"] for member in resp.json()} == {str(s.manager.id), str(s.worker.id)}


def test_view_as_claim_is_ignored_for_non_pa_manager(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company, claims={"role": "manager", "view_as": "worker"})

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 200, resp.text


def test_role_claim_manager_is_ignored_when_membership_is_worker(client, db):
    s = _scenario(db)
    as_user(client, s.worker, s.company, claims={"role": "manager"})

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 403, resp.text


def test_role_claim_worker_is_ignored_when_membership_is_manager(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company, claims={"role": "worker"})

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 200, resp.text


def test_manager_token_for_other_company_cannot_list_members_of_company_a(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    make_member(db, manager, company_b, role="manager")
    as_user(client, manager, company_b, claims={"role": "manager"})

    resp = client.get(_members_url(company_a))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


def test_manager_of_a_cannot_list_rates_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims={"role": "manager"})

    resp = client.get(f"{BASE}/{company_b.id}/rates")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_role_downgrade_takes_effect_on_next_request_of_manager(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company, claims={"role": "manager"})
    assert client.get(_members_url(s.company)).status_code == 200

    as_user(client, s.pa, s.company)
    resp_change = client.put(f"{BASE}/{s.company.id}/members/{s.manager.id}/role", json={"role": "worker"})
    assert resp_change.status_code == 200, resp_change.text

    as_user(client, s.manager, s.company, claims={"role": "manager"})
    assert client.get(_members_url(s.company)).status_code == 403


def test_membership_deactivation_takes_effect_on_next_request_of_manager(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company, claims={"role": "manager"})
    assert client.get(_members_url(s.company)).status_code == 200

    as_user(client, s.pa, s.company)
    resp_change = client.put(f"{BASE}/{s.company.id}/members/{s.manager.id}/status", json={"is_active": False})
    assert resp_change.status_code == 200, resp_change.text

    as_user(client, s.manager, s.company, claims={"role": "manager"})
    resp = client.get(_members_url(s.company))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_company_suspension_takes_effect_on_next_request_of_manager(client, db):
    s = _scenario(db)
    as_user(client, s.manager, s.company, claims={"role": "manager"})
    assert client.get(_members_url(s.company)).status_code == 200

    as_user(client, s.pa, s.company)
    resp_change = client.put(f"{BASE}/{s.company.id}", json={"is_active": False})
    assert resp_change.status_code == 200, resp_change.text

    as_user(client, s.manager, s.company, claims={"role": "manager"})
    resp = client.get(_members_url(s.company))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


def test_redis_down_does_not_block_legit_manager(client, db, fake_redis):
    s = _scenario(db)
    fake_redis.raise_errors = True
    as_user(client, s.manager, s.company)

    resp = client.get(_members_url(s.company))

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize(
    "method, path_template, kwargs",
    [
        ("PUT", f"{BASE}/{{cid}}/members/{{uid}}/status", {"json": {"is_active": False}}),
        ("GET", f"{BASE}/{{cid}}", {}),
        ("GET", f"{BASE}/{{cid}}/rates", {}),
        ("PUT", f"{BASE}/{{cid}}/members/{{uid}}/rates", {"json": {"rates_config": {}}}),
    ],
)
def test_2fa_pending_token_rejected_on_company_endpoints(client, db, method, path_template, kwargs):
    user = make_user(db)
    company = make_company(db)
    make_member(db, user, company, role="manager")
    as_user(client, user, company, scope="2fa_pending")

    resp = client.request(method, path_template.format(cid=company.id, uid=user.id), **kwargs)

    assert resp.status_code == 403, resp.text
    assert resp.json().get("detail") == "2FA Verification Required"
