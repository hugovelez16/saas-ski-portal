"""
Paridad entre la API v1 y la API v2 de empresa (PR-17.0).

Cada par se ejecuta sobre el escenario `parity_world` (PA, manager, worker; empresas autonoma,
gestionada y suspendida). Se comparan codigos de estado y payloads tras `to_snake`. Las unicas
diferencias admitidas son las declaradas en KNOWN_DIFFERENCES; cualquier otra es un fallo.

Las escrituras usan dos empresas gemelas (mismos datos): una se escribe por v1 y otra por v2. Se
comparan la respuesta y las filas de auditoria resultantes (accion, old_value, new_value, reason, actor).
"""

import uuid
from dataclasses import dataclass

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user
from tests.parity.helpers import assert_parity, call_both, to_snake

PAIR_LIST = "GET /companies vs GET /v2/companies"
PAIR_DETAILED = "GET /companies/detailed vs GET /v2/companies?include=members"
PAIR_CREATE = "POST /companies vs POST /v2/companies"
PAIR_GET_ONE = "GET /companies/{id} vs GET /v2/companies/{id}"
PAIR_UPDATE = "PUT /companies/{id} vs PUT /v2/companies/{id}"
PAIR_DELETE = "DELETE /companies/{id} vs DELETE /v2/companies/{id}"
PAIR_ME = "GET /users/me/companies vs GET /v2/me/companies"
PAIR_USER = "GET /users/{id}/companies vs GET /v2/users/{id}/companies"

# Claves que v1 incluye en las vistas completas y v2 no (CompanyFull de v2 no las lleva).
FULL_VIEW_IGNORE = frozenset({"role", "is_active_member", "rates_config"})
# Identificadores y fechas que se generan en un alta.
CREATED_IGNORE = frozenset({"id", "created_at", "updated_at"})
# Solo para comparar dos empresas gemelas: sus ids y fechas son distintos por construccion, no es una diferencia de API.
TWIN_IGNORE = frozenset({"id", "created_at", "updated_at"})

TAX_CONFIG = {"social_security": 0.0648}
DEFINITIONS = {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
SETTINGS = {"modules": {"daily_report": True}}


@dataclass(frozen=True)
class KnownDifference:
    """Diferencia intencionada entre v1 y v2. `clave` identifica la excepcion dentro del par."""

    par: str
    clave: str
    motivo: str
    ignore: frozenset[str] = frozenset()


KNOWN_DIFFERENCES = [
    KnownDifference(
        par=PAIR_LIST,
        clave="forma",
        motivo="v2 devuelve {items, total} paginado en lugar de una lista plana. La comparacion usa items.",
    ),
    KnownDifference(
        par=PAIR_LIST,
        clave="vista completa",
        motivo="CompanyFull de v2 no lleva role, is_active_member ni rates_config (v1 si en las vistas completas).",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_DETAILED,
        clave="include=members",
        motivo=(
            "v2 incluye los miembros con include=members sobre el listado de empresas; v1 usa /companies/detailed. "
            "El miembro v2 anade sort_order y su user es un resumen de 5 claves (v1 devuelve UserResponse completo)."
        ),
        ignore=frozenset({"sort_order", "user"}),
    ),
    KnownDifference(
        par=PAIR_DETAILED,
        clave="manager",
        motivo=(
            "v1 devuelve al manager una vista reducida con miembros (200). v2 responde 403: "
            "los managers consultan sus empresas en /v2/me/companies."
        ),
    ),
    KnownDifference(
        par=PAIR_DETAILED,
        clave="vista completa",
        motivo="CompanyWithMembers de v1 lleva role, is_active_member y rates_config; CompanyFull de v2 no.",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_CREATE,
        clave="status",
        motivo="El alta v2 responde 201 Created; v1 responde 200.",
    ),
    KnownDifference(
        par=PAIR_CREATE,
        clave="ids y fechas",
        motivo="Un alta genera id, created_at y updated_at distintos en cada empresa.",
        ignore=CREATED_IGNORE,
    ),
    KnownDifference(
        par=PAIR_CREATE,
        clave="vista completa",
        motivo="CompanyFull de v2 no lleva role, is_active_member ni rates_config.",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_GET_ONE,
        clave="vista completa",
        motivo="CompanyFull de v2 no lleva role, is_active_member ni rates_config (solo PA actuando).",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_UPDATE,
        clave="vista completa",
        motivo="CompanyFull de v2 no lleva role, is_active_member ni rates_config.",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_ME,
        clave="vista completa",
        motivo="CompanyFull de v2 no lleva role, is_active_member ni rates_config (solo PA actuando).",
        ignore=FULL_VIEW_IGNORE,
    ),
    KnownDifference(
        par=PAIR_USER,
        clave="nombres",
        motivo=(
            "Los datos de la membresia (role, is_active_member, rates_config) llegan en ambas versiones; "
            "v1 los nombra en camelCase (isActiveMember, ratesConfig) y v2 en snake_case. "
            "La comparacion normaliza los nombres con to_snake y no ignora ninguna clave."
        ),
    ),
]


def _ignore_for(par: str) -> frozenset[str]:
    """Union de las claves ignorables declaradas para un par."""
    return frozenset().union(*(known.ignore for known in KNOWN_DIFFERENCES if known.par == par))


def _known(par: str, clave: str) -> KnownDifference:
    """Devuelve la excepcion declarada o falla: una diferencia no declarada no puede usarse en un test."""
    for known in KNOWN_DIFFERENCES:
        if known.par == par and known.clave == clave:
            return known
    raise AssertionError(f"Diferencia no declarada en KNOWN_DIFFERENCES: {par} / {clave}")


def _act(client, world, actor: str, company):
    """Deja en el cliente el token del actor sobre la empresa indicada."""
    if actor == "pa":
        return as_user(client, world.pa, company)
    if actor == "pa_view_as_worker":
        return as_user(client, world.pa, company, claims={"view_as": "worker"})
    if actor == "manager":
        return as_user(client, world.manager, company)
    if actor == "worker":
        return as_user(client, world.worker, company)
    raise ValueError(f"actor desconocido: {actor}")


def _normalize(companies: list[dict]) -> list[dict]:
    """Ordena empresas por id y miembros por user_id. v1 no garantiza orden."""
    result = []
    for company in sorted(companies, key=lambda item: item["id"]):
        copy = dict(company)
        if "members" in copy:
            copy["members"] = sorted(copy["members"], key=lambda member: member["user_id"])
        result.append(copy)
    return result


def _twin(db):
    """Empresa gemela: mismos datos que cualquier otra gemela, sin miembros."""
    return make_company(db, name="Gemela", tax_config=TAX_CONFIG, worklog_definitions=DEFINITIONS, settings=SETTINGS)


def _signature(db, company_id):
    """Filas de auditoria de una empresa, sin ids propios, para comparar v1 y v2."""
    db.expire_all()
    rows = db.query(models.AuditLog).filter(models.AuditLog.company_id == company_id).all()
    return sorted(
        ((row.action, row.old_value, row.new_value, row.reason, str(row.actor_user_id)) for row in rows),
        key=lambda item: item[0],
    )


def _company_total(db):
    db.expire_all()
    return db.query(models.Company).count()


# --- Listado ---


def test_list_pa_payload_matches_v1(client, parity_world):
    _act(client, parity_world, "pa", parity_world.autonoma)

    v1, v2 = call_both(client, "GET", "/companies", "/v2/companies")

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    _known(PAIR_LIST, "forma")
    v2_body = to_snake(v2.json())
    assert set(v2_body) == {"items", "total"}, sorted(v2_body)
    assert v2_body["total"] == len(v1.json())
    assert_parity(_normalize(to_snake(v1.json())), _normalize(v2_body["items"]), ignore=_ignore_for(PAIR_LIST))


@pytest.mark.parametrize("actor", ["manager", "worker", "pa_view_as_worker"])
def test_list_forbidden_status_and_detail_match_v1(client, parity_world, actor):
    _act(client, parity_world, actor, parity_world.autonoma)

    v1, v2 = call_both(client, "GET", "/companies", "/v2/companies")

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]


# --- Listado detallado con miembros ---


def test_detailed_pa_matches_v2_include_members(client, parity_world):
    _act(client, parity_world, "pa", parity_world.autonoma)

    v1 = client.get("/companies/detailed")
    v2 = client.get("/v2/companies?include=members")

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    _known(PAIR_DETAILED, "include=members")
    assert_parity(
        _normalize(to_snake(v1.json())),
        _normalize(to_snake(v2.json())["items"]),
        ignore=_ignore_for(PAIR_DETAILED),
    )


def test_detailed_manager_is_200_in_v1_and_403_in_v2(client, parity_world):
    _act(client, parity_world, "manager", parity_world.autonoma)

    v1 = client.get("/companies/detailed")
    v2 = client.get("/v2/companies?include=members")

    _known(PAIR_DETAILED, "manager")
    assert v1.status_code == 200, v1.text
    assert v2.status_code == 403, v2.text


def test_detailed_worker_is_forbidden_in_both(client, parity_world):
    _act(client, parity_world, "worker", parity_world.autonoma)

    v1 = client.get("/companies/detailed")
    v2 = client.get("/v2/companies?include=members")

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]


# --- Alta ---


def test_create_pa_matches_v1_response_and_audit(client, db, parity_world):
    _act(client, parity_world, "pa", parity_world.autonoma)

    v1 = client.post("/companies", json={"name": "Parity alta", "taxConfig": TAX_CONFIG, "isManaged": True})
    v2 = client.post("/v2/companies", json={"name": "Parity alta", "tax_config": TAX_CONFIG, "is_managed": True})

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 201, v2.text
    _known(PAIR_CREATE, "status")
    _known(PAIR_CREATE, "ids y fechas")
    assert_parity(to_snake(v1.json()), to_snake(v2.json()), ignore=_ignore_for(PAIR_CREATE))
    v1_signature = _signature(db, uuid.UUID(v1.json()["id"]))
    v2_signature = _signature(db, uuid.UUID(v2.json()["id"]))
    assert [row[0] for row in v2_signature] == ["company.created"]
    assert v1_signature == v2_signature


@pytest.mark.parametrize("actor", ["manager", "worker"])
@pytest.mark.parametrize("kind", ["create", "update", "delete"])
def test_writes_forbidden_for_non_pa_match_v1(client, db, parity_world, actor, kind):
    cid = parity_world.autonoma.id
    _act(client, parity_world, actor, parity_world.autonoma)
    before = _company_total(db)
    if kind == "create":
        method, v1_path, v2_path = "POST", "/companies", "/v2/companies"
        v1_body, v2_body = {"name": "Intruso", "taxConfig": {}}, {"name": "Intruso", "tax_config": {}}
    elif kind == "update":
        method, v1_path, v2_path = "PUT", f"/companies/{cid}", f"/v2/companies/{cid}"
        v1_body, v2_body = {"name": "Intruso"}, {"name": "Intruso"}
    else:
        method, v1_path, v2_path = "DELETE", f"/companies/{cid}", f"/v2/companies/{cid}"
        v1_body, v2_body = None, None

    v1, v2 = call_both(client, method, v1_path, v2_path, v1_body=v1_body, v2_body=v2_body)

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]
    assert _company_total(db) == before


# --- Lectura de una empresa ---


@pytest.mark.parametrize("company_name", ["autonoma", "gestionada", "suspendida"])
@pytest.mark.parametrize("actor", ["pa", "pa_view_as_worker", "manager", "worker"])
def test_get_one_matches_v1(client, parity_world, actor, company_name):
    company = getattr(parity_world, company_name)
    _act(client, parity_world, actor, company)

    v1, v2 = call_both(client, "GET", f"/companies/{company.id}", f"/v2/companies/{company.id}")

    assert v1.status_code == v2.status_code, f"v1 {v1.status_code} / v2 {v2.status_code}: {v2.text}"
    if v1.status_code == 200:
        ignore = _ignore_for(PAIR_GET_ONE) if actor == "pa" else frozenset()
        assert_parity(to_snake(v1.json()), to_snake(v2.json()), ignore=ignore)
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


# --- Edicion: respuesta y auditoria con dos empresas gemelas ---

PUT_CASES = [
    pytest.param({"name": "Renombrada"}, {"name": "Renombrada"}, id="name"),
    pytest.param({"isActive": False, "reason": "Impago"}, {"is_active": False, "reason": "Impago"}, id="suspend"),
    pytest.param({"taxConfig": {"social_security": 0.1}}, {"tax_config": {"social_security": 0.1}}, id="tax_config"),
    pytest.param({"isManaged": True}, {"is_managed": True}, id="is_managed"),
    pytest.param(
        {"worklogDefinitions": {"guardia": {"unit": "hours", "label": "Guardia", "fields": []}}},
        {"worklog_definitions": {"guardia": {"unit": "hours", "label": "Guardia", "fields": []}}},
        id="worklog_definitions",
    ),
    pytest.param(
        {"settings": {"modules": {"coordination": True}}},
        {"settings": {"modules": {"coordination": True}}},
        id="settings",
    ),
]


@pytest.mark.parametrize("v1_body, v2_body", PUT_CASES)
def test_put_pa_matches_v1_response_and_audit(client, db, parity_world, v1_body, v2_body):
    _act(client, parity_world, "pa", parity_world.autonoma)
    v1_twin = _twin(db)
    v2_twin = _twin(db)
    v1_id, v2_id = v1_twin.id, v2_twin.id

    v1 = client.put(f"/companies/{v1_id}", json=v1_body)
    v2 = client.put(f"/v2/companies/{v2_id}", json=v2_body)

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    assert_parity(to_snake(v1.json()), to_snake(v2.json()), ignore=_ignore_for(PAIR_UPDATE) | TWIN_IGNORE)
    v1_signature = _signature(db, v1_id)
    assert v1_signature, "v1 no dejo auditoria"
    assert v1_signature == _signature(db, v2_id)


@pytest.mark.parametrize("actor", ["manager", "worker"])
def test_put_forbidden_for_non_pa_is_not_applied_in_either_api(client, db, parity_world, actor):
    """Complementa test_writes_forbidden_for_non_pa_match_v1 con el cambio de nombre real en la empresa."""
    _act(client, parity_world, actor, parity_world.autonoma)
    v1_twin = _twin(db)
    v2_twin = _twin(db)

    v1 = client.put(f"/companies/{v1_twin.id}", json={"name": "Intruso"})
    v2 = client.put(f"/v2/companies/{v2_twin.id}", json={"name": "Intruso"})

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]
    db.expire_all()
    assert db.get(models.Company, v1_twin.id).name == "Gemela"
    assert db.get(models.Company, v2_twin.id).name == "Gemela"


# --- Borrado ---


def test_delete_empty_company_matches_v1_and_audit(client, db, parity_world):
    _act(client, parity_world, "pa", parity_world.autonoma)
    v1_twin = _twin(db)
    v2_twin = _twin(db)
    v1_id, v2_id = v1_twin.id, v2_twin.id

    v1 = client.delete(f"/companies/{v1_id}")
    v2 = client.delete(f"/v2/companies/{v2_id}")

    assert v1.status_code == 204, v1.text
    assert v2.status_code == 204, v2.text
    assert v1.content == v2.content == b""
    v1_signature = _signature(db, v1_id)
    assert v1_signature, "v1 no dejo auditoria"
    assert v1_signature == _signature(db, v2_id)


def test_delete_blocked_company_matches_v1_detail(client, db, parity_world):
    _act(client, parity_world, "pa", parity_world.autonoma)
    v1_twin = _twin(db)
    v2_twin = _twin(db)
    make_member(db, parity_world.worker, v1_twin, role="worker")
    make_member(db, parity_world.worker, v2_twin, role="worker")
    v1_id, v2_id = v1_twin.id, v2_twin.id

    v1 = client.delete(f"/companies/{v1_id}")
    v2 = client.delete(f"/v2/companies/{v2_id}")

    assert v1.status_code == 409, v1.text
    assert v2.status_code == 409, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]
    db.expire_all()
    assert db.get(models.Company, v1_id) is not None
    assert db.get(models.Company, v2_id) is not None


# --- Mis empresas ---


@pytest.mark.parametrize("actor", ["pa", "pa_view_as_worker", "manager", "worker"])
def test_me_companies_matches_v1(client, parity_world, actor):
    _act(client, parity_world, actor, parity_world.autonoma)

    v1, v2 = call_both(client, "GET", "/users/me/companies", "/v2/me/companies")

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    ignore = _ignore_for(PAIR_ME) if actor == "pa" else frozenset()
    assert_parity(_normalize(to_snake(v1.json())), _normalize(to_snake(v2.json())), ignore=ignore)


# --- Empresas de un usuario ---


@pytest.mark.parametrize("actor", ["pa", "pa_view_as_worker", "manager", "worker"])
def test_user_companies_matches_v1(client, parity_world, actor):
    _act(client, parity_world, actor, parity_world.autonoma)
    target = parity_world.worker.id

    v1, v2 = call_both(client, "GET", f"/users/{target}/companies", f"/v2/users/{target}/companies")

    assert v1.status_code == v2.status_code, f"v1 {v1.status_code} / v2 {v2.status_code}: {v2.text}"
    if v1.status_code == 200:
        ignore = _ignore_for(PAIR_USER) if actor == "pa" else frozenset()
        assert_parity(_normalize(to_snake(v1.json())), _normalize(to_snake(v2.json())), ignore=ignore)
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


@pytest.mark.parametrize("actor", ["pa", "manager"])
def test_user_companies_membership_fields_match_v1(client, db, parity_world, actor):
    """role, is_active_member y rates_config del usuario objetivo coinciden con v1, incluida una membresia inactiva."""
    rates = {"particular": {"base_rate": 27.5, "is_gross": False, "tax_overrides": {}}}
    target = make_user(db)
    member = make_member(db, target, parity_world.autonoma, role="manager", rates_config=rates)
    member.settings = {"notifications": {"email": False}, "not_allowed_key": 1}
    db.commit()
    make_member(db, target, parity_world.gestionada, role="worker", is_active=False)
    _act(client, parity_world, actor, parity_world.autonoma)

    v1, v2 = call_both(client, "GET", f"/users/{target.id}/companies", f"/v2/users/{target.id}/companies")

    assert v1.status_code == v2.status_code == 200, f"v1 {v1.status_code} / v2 {v2.status_code}: {v2.text}"
    keys = ("role", "is_active_member", "rates_config")
    v1_items = {item["id"]: {key: item[key] for key in keys} for item in to_snake(v1.json())}
    v2_items = {item["id"]: {key: item[key] for key in keys} for item in to_snake(v2.json())}
    assert v1_items == v2_items
    assert str(parity_world.autonoma.id) in v2_items
    assert v2_items[str(parity_world.autonoma.id)]["rates_config"] == rates
    if actor == "pa":
        assert v2_items[str(parity_world.gestionada.id)]["is_active_member"] is False
        autonoma = next(i for i in v2.json() if i["id"] == str(parity_world.autonoma.id))
        assert autonoma["settings"]["notifications"] == {"email": False}
        assert "not_allowed_key" not in autonoma["settings"]
    assert_parity(_normalize(to_snake(v1.json())), _normalize(to_snake(v2.json())), ignore=_ignore_for(PAIR_USER))
