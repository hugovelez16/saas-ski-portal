"""
Paridad entre la API v1 y la API v2 de membresias y tarifas (PR-18.0).

Cada fila de la tabla de endpoints de PR-18 tiene al menos una prueba. Se ejecuta la misma operacion
contra v1 y contra v2 y se comparan codigos de estado, payloads tras `to_snake` y, en las escrituras,
las filas de auditoria. Las escrituras usan dos empresas gemelas con el mismo equipo: una se escribe
por v1 y otra por v2. Las unicas diferencias admitidas son las declaradas en KNOWN_DIFFERENCES; cualquier
otra es un fallo.
"""

from dataclasses import dataclass

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user, make_work_log
from tests.parity.helpers import assert_parity, call_both, to_snake

V1 = "/companies"
V2 = "/v2/companies"

PAIR_LIST = "GET /companies/{id}/members vs GET /v2/companies/{id}/members"
PAIR_ADD = "POST /companies/{id}/members/add vs POST /v2/companies/{id}/members"
PAIR_STATUS = "PUT /companies/{id}/members/{uid}/status vs PUT /v2/companies/{id}/members/{uid}/status"
PAIR_ROLE = "PUT /companies/{id}/members/{uid}/role vs PUT /v2/companies/{id}/members/{uid}/role"
PAIR_RATES = "PUT /companies/{id}/members/{uid}/rates vs PUT /v2/companies/{id}/members/{uid}/rates"
PAIR_SETTINGS = "PUT /companies/{id}/members/{uid}/settings vs PUT /v2/companies/{id}/members/{uid}/settings"
PAIR_ORDER = "PUT /companies/{id}/members/order vs PUT /v2/companies/{id}/members/order"
PAIR_RATES_LIST = "GET /companies/{id}/rates-v2 vs GET /v2/companies/{id}/rates"

# Pares cuya respuesta es un miembro (MemberOut): se comparan con _assert_member_parity.
MEMBER_PAIRS = [PAIR_LIST, PAIR_ADD, PAIR_STATUS, PAIR_ROLE, PAIR_RATES, PAIR_SETTINGS, PAIR_RATES_LIST]

# MemberOut de v2 anade sort_order y updated_at; v1 no los devuelve.
MEMBER_V2_EXTRA = frozenset({"sort_order", "updated_at"})
# Solo para comparar dos empresas gemelas: company_id y joined_at son distintos por construccion.
TWIN_IGNORE = frozenset({"company_id", "joined_at"})
# Campos comunes de UserResponse (v1) y UserBriefV2 (v2).
USER_BRIEF_KEYS = frozenset({"id", "email", "first_name", "last_name", "is_active"})

TAX_CONFIG = {"social_security": 0.0648}
DEFINITIONS = {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
OLD_RATES = {"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}}
NEW_RATES = {"particular": {"base_rate": 25.0, "is_gross": True, "tax_overrides": {}}}
UI_SETTINGS = {"ui_preferences": {"theme": "dark"}}
ORDER_MESSAGE = {"message": "Order updated successfully"}


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
        clave="filtro",
        motivo="v1 filtra con ?status=active|inactive; v2 filtra con ?is_active=bool (true|false).",
    ),
    KnownDifference(
        par=PAIR_ADD,
        clave="status",
        motivo="Alta de membresia nueva: v2 responde 201 Created; v1 responde 200. Reactivacion y ya activa: 200 en ambas.",
    ),
    KnownDifference(
        par=PAIR_ADD,
        clave="ruta",
        motivo="POST /companies/{id}/members/add (v1) pasa a POST /v2/companies/{id}/members (v2).",
    ),
    KnownDifference(
        par=PAIR_STATUS,
        clave="cuerpo",
        motivo="v1 recibe el estado en la query ?status= (valores heredados); v2 recibe el cuerpo {is_active: bool}.",
    ),
    KnownDifference(
        par=PAIR_RATES,
        clave="camelCase en el cuerpo",
        motivo="v1 espera ratesConfig; v2 espera rates_config.",
    ),
    KnownDifference(
        par=PAIR_ORDER,
        clave="camelCase en el cuerpo",
        motivo="v1 espera userIds; v2 espera user_ids.",
    ),
    KnownDifference(
        par=PAIR_RATES_LIST,
        clave="ruta",
        motivo="GET /companies/{id}/rates-v2 (v1) pasa a GET /v2/companies/{id}/rates (v2).",
    ),
    *[
        KnownDifference(
            par=par,
            clave="user resumido",
            motivo="v1 devuelve UserResponse completo; v2 devuelve UserBriefV2. Se compara el subconjunto comun.",
        )
        for par in MEMBER_PAIRS
    ],
    *[
        KnownDifference(
            par=par,
            clave="campos extra de v2",
            motivo="MemberOut de v2 anade sort_order y updated_at; v1 no los devuelve.",
            ignore=MEMBER_V2_EXTRA,
        )
        for par in MEMBER_PAIRS
    ],
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


# --- Helpers ---


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


def _member_view(payload):
    """Miembros en snake_case, ordenados por user_id, con el usuario reducido a USER_BRIEF_KEYS."""
    members = payload if isinstance(payload, list) else [payload]
    view = []
    for member in to_snake(members):
        copy = dict(member)
        if isinstance(copy.get("user"), dict):
            copy["user"] = {key: copy["user"].get(key) for key in USER_BRIEF_KEYS}
        view.append(copy)
    return sorted(view, key=lambda item: item["user_id"])


def _assert_member_parity(par: str, v1_payload, v2_payload, *, twins: bool = False) -> None:
    """Compara miembros (uno o una lista) tras normalizar; las diferencias declaradas para `par` se ignoran."""
    _known(par, "user resumido")
    _known(par, "campos extra de v2")
    ignore = _ignore_for(par) | (TWIN_IGNORE if twins else frozenset())
    assert_parity(_member_view(v1_payload), _member_view(v2_payload), ignore=ignore)


def _pair(db, world, *, is_managed: bool = False):
    """Dos empresas gemelas con el mismo equipo (manager y worker activos). Una se escribe por v1 y otra por v2."""
    twins = []
    for _ in range(2):
        company = make_company(
            db,
            name="Gemela paridad",
            is_managed=is_managed,
            tax_config=TAX_CONFIG,
            worklog_definitions=DEFINITIONS,
        )
        make_member(db, world.manager, company, role="manager")
        make_member(db, world.worker, company, role="worker")
        twins.append(company)
    return twins[0], twins[1]


def _signature(db, company_id):
    """Filas de auditoria de una empresa, sin ids propios, para comparar v1 y v2."""
    db.expire_all()
    rows = db.query(models.AuditLog).filter(models.AuditLog.company_id == company_id).all()
    return sorted(
        ((row.action, row.old_value, row.new_value, row.reason, str(row.actor_user_id)) for row in rows),
        key=lambda item: item[0],
    )


def _membership(db, user, company):
    db.expire_all()
    return db.query(models.CompanyMember).filter_by(user_id=user.id, company_id=company.id).one()


def _order_map(db, company_id):
    """Orden de los miembros de una empresa: user_id -> sort_order."""
    db.expire_all()
    rows = db.query(models.CompanyMember).filter(models.CompanyMember.company_id == company_id).all()
    return {str(row.user_id): row.sort_order for row in rows}


def _send(client, request):
    method, path, body = request
    return client.request(method, path, json=body)


def _requests(name, world, company):
    """Peticion (metodo, ruta, cuerpo) de v1 y de v2 para la operacion `name` sobre el manager de `company`."""
    cid = company.id
    uid = world.manager.id
    if name == "add":
        return (
            ("POST", f"{V1}/{cid}/members/add", {"email": world.manager.email}),
            ("POST", f"{V2}/{cid}/members", {"email": world.manager.email}),
        )
    if name == "status":
        return (
            ("PUT", f"{V1}/{cid}/members/{uid}/status?status=inactive", None),
            ("PUT", f"{V2}/{cid}/members/{uid}/status", {"is_active": False}),
        )
    if name == "role":
        return (
            ("PUT", f"{V1}/{cid}/members/{uid}/role", {"role": "worker"}),
            ("PUT", f"{V2}/{cid}/members/{uid}/role", {"role": "worker"}),
        )
    if name == "delete":
        return (
            ("DELETE", f"{V1}/{cid}/members/{uid}", None),
            ("DELETE", f"{V2}/{cid}/members/{uid}", None),
        )
    if name == "rates":
        return (
            ("PUT", f"{V1}/{cid}/members/{uid}/rates", {"ratesConfig": NEW_RATES}),
            ("PUT", f"{V2}/{cid}/members/{uid}/rates", {"rates_config": NEW_RATES}),
        )
    if name == "settings":
        return (
            ("PUT", f"{V1}/{cid}/members/{uid}/settings", {"settings": UI_SETTINGS}),
            ("PUT", f"{V2}/{cid}/members/{uid}/settings", {"settings": UI_SETTINGS}),
        )
    if name == "order":
        return (
            ("PUT", f"{V1}/{cid}/members/order", {"userIds": [str(uid)]}),
            ("PUT", f"{V2}/{cid}/members/order", {"user_ids": [str(uid)]}),
        )
    raise ValueError(f"operacion desconocida: {name}")


# --- Listado de miembros (GET) ---


@pytest.mark.parametrize("company_name", ["autonoma", "gestionada", "suspendida"])
@pytest.mark.parametrize("actor", ["pa", "manager", "worker"])
def test_list_members_matches_v1(client, parity_world, actor, company_name):
    company = getattr(parity_world, company_name)
    _act(client, parity_world, actor, company)

    v1, v2 = call_both(client, "GET", f"{V1}/{company.id}/members", f"{V2}/{company.id}/members")

    assert v1.status_code == v2.status_code, f"v1 {v1.status_code} / v2 {v2.status_code}: {v2.text}"
    if v1.status_code == 200:
        _assert_member_parity(PAIR_LIST, v1.json(), v2.json())
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


@pytest.mark.parametrize(
    "v1_params, v2_params",
    [({"status": "active"}, {"is_active": "true"}), ({"status": "inactive"}, {"is_active": "false"})],
    ids=["active", "inactive"],
)
def test_list_members_filter_matches_v1_status(client, db, parity_world, v1_params, v2_params):
    company = parity_world.autonoma
    inactive = make_user(db)
    make_member(db, inactive, company, role="worker", is_active=False)
    _act(client, parity_world, "pa", company)

    v1 = client.get(f"{V1}/{company.id}/members", params=v1_params)
    v2 = client.get(f"{V2}/{company.id}/members", params=v2_params)

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    _known(PAIR_LIST, "filtro")
    assert v1.json(), "el filtro v1 no devolvio miembros"
    _assert_member_parity(PAIR_LIST, v1.json(), v2.json())


# --- Alta de miembro (POST members/add en v1, POST members en v2) ---


@pytest.mark.parametrize("scenario", ["nueva", "reactivada", "activa"])
def test_add_member_matches_v1_response_and_audit(client, db, parity_world, scenario):
    v1_company, v2_company = _pair(db, parity_world)
    user = make_user(db)
    if scenario == "reactivada":
        make_member(db, user, v1_company, role="manager", is_active=False)
        make_member(db, user, v2_company, role="manager", is_active=False)
    elif scenario == "activa":
        make_member(db, user, v1_company, role="manager", is_active=True)
        make_member(db, user, v2_company, role="manager", is_active=True)
    expected_v2 = 201 if scenario == "nueva" else 200

    _act(client, parity_world, "pa", v1_company)
    v1 = client.post(f"{V1}/{v1_company.id}/members/add", json={"email": user.email})
    _act(client, parity_world, "pa", v2_company)
    v2 = client.post(f"{V2}/{v2_company.id}/members", json={"email": user.email})

    assert v1.status_code == 200, v1.text
    assert v2.status_code == expected_v2, v2.text
    _known(PAIR_ADD, "ruta")
    if scenario == "nueva":
        _known(PAIR_ADD, "status")
    _assert_member_parity(PAIR_ADD, v1.json(), v2.json(), twins=True)
    assert _signature(db, v1_company.id) == _signature(db, v2_company.id)


@pytest.mark.parametrize(
    "email, status_code",
    [("nadie@test.com", 404), ("no-es-un-email", 422)],
    ids=["email_inexistente", "email_malformado"],
)
def test_add_member_errors_match_v1(client, parity_world, email, status_code):
    company = parity_world.autonoma
    _act(client, parity_world, "pa", company)
    # Control: la ruta v2 de alta responde 200 para un miembro ya activo (sin cambios).
    control = client.post(f"{V2}/{company.id}/members", json={"email": parity_world.worker.email})
    assert control.status_code == 200, control.text

    v1 = client.post(f"{V1}/{company.id}/members/add", json={"email": email})
    v2 = client.post(f"{V2}/{company.id}/members", json={"email": email})

    assert v1.status_code == status_code, v1.text
    assert v2.status_code == status_code, v2.text


# --- Cambio de estado (query ?status= en v1, cuerpo {is_active} en v2) ---


@pytest.mark.parametrize(
    "v1_value, v2_body, expected_active",
    [("inactive", False, False), ("active", True, True)],
    ids=["desactivar", "activar"],
)
def test_status_matches_v1(client, db, parity_world, v1_value, v2_body, expected_active):
    v1_company, v2_company = _pair(db, parity_world)
    worker = parity_world.worker
    _act(client, parity_world, "pa", v1_company)
    v1 = client.put(f"{V1}/{v1_company.id}/members/{worker.id}/status", params={"status": v1_value})
    _act(client, parity_world, "pa", v2_company)
    v2 = client.put(f"{V2}/{v2_company.id}/members/{worker.id}/status", json={"is_active": v2_body})

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    _known(PAIR_STATUS, "cuerpo")
    _assert_member_parity(PAIR_STATUS, v1.json(), v2.json(), twins=True)
    assert _membership(db, worker, v1_company).is_active is expected_active
    assert _membership(db, worker, v2_company).is_active is expected_active


def test_status_invalid_value_is_422_in_both(client, parity_world):
    company = parity_world.autonoma
    worker = parity_world.worker
    _act(client, parity_world, "pa", company)

    v1 = client.put(f"{V1}/{company.id}/members/{worker.id}/status", params={"status": "maybe"})
    v2 = client.put(f"{V2}/{company.id}/members/{worker.id}/status", json={"is_active": "maybe"})

    assert v1.status_code == 422, v1.text
    assert v2.status_code == 422, v2.text


# --- Cambio de rol ---


@pytest.mark.parametrize("role, status_code", [("manager", 200), ("admin", 422)], ids=["manager", "admin"])
def test_role_matches_v1(client, db, parity_world, role, status_code):
    v1_company, v2_company = _pair(db, parity_world)
    worker = parity_world.worker
    _act(client, parity_world, "pa", v1_company)
    v1 = client.put(f"{V1}/{v1_company.id}/members/{worker.id}/role", json={"role": role})
    _act(client, parity_world, "pa", v2_company)
    v2 = client.put(f"{V2}/{v2_company.id}/members/{worker.id}/role", json={"role": role})

    assert v1.status_code == status_code, v1.text
    assert v2.status_code == status_code, v2.text
    if status_code == 200:
        _assert_member_parity(PAIR_ROLE, v1.json(), v2.json(), twins=True)
        assert _signature(db, v1_company.id) == _signature(db, v2_company.id)


def test_role_on_non_member_is_404_in_both(client, db, parity_world):
    company = parity_world.autonoma
    outsider = make_user(db)
    _act(client, parity_world, "pa", company)
    # Control: la ruta v2 responde 200 sobre un miembro real (rol sin cambios).
    control = client.put(f"{V2}/{company.id}/members/{parity_world.worker.id}/role", json={"role": "worker"})
    assert control.status_code == 200, control.text

    v1 = client.put(f"{V1}/{company.id}/members/{outsider.id}/role", json={"role": "manager"})
    v2 = client.put(f"{V2}/{company.id}/members/{outsider.id}/role", json={"role": "manager"})

    assert v1.status_code == 404, v1.text
    assert v2.status_code == 404, v2.text


# --- Baja de miembro (DELETE) ---


@pytest.mark.parametrize("with_logs", [False, True], ids=["sin_turnos", "con_turnos"])
def test_delete_member_matches_v1_response_and_audit(client, db, parity_world, with_logs):
    v1_company, v2_company = _pair(db, parity_world)
    worker = parity_world.worker
    if with_logs:
        make_work_log(db, worker, v1_company)
        make_work_log(db, worker, v2_company)
    expected = (
        {"deleted": False, "deactivated": True, "reason": "has_work_logs"}
        if with_logs
        else {"deleted": True, "deactivated": False, "reason": None}
    )
    _act(client, parity_world, "pa", v1_company)
    v1 = client.delete(f"{V1}/{v1_company.id}/members/{worker.id}")
    _act(client, parity_world, "pa", v2_company)
    v2 = client.delete(f"{V2}/{v2_company.id}/members/{worker.id}")

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    assert to_snake(v1.json()) == to_snake(v2.json()) == expected
    assert _signature(db, v1_company.id) == _signature(db, v2_company.id)
    assert _signature(db, v1_company.id), "v1 no dejo auditoria"


# --- Tarifas (PUT rates) ---

RATES_CASES = [
    pytest.param("pa", "worker", True, 200, id="pa-sobre-miembro-gestionada"),
    pytest.param("manager", "worker", True, 200, id="manager-sobre-miembro-gestionada"),
    pytest.param("worker", "worker", False, 200, id="worker-propia-autonoma"),
    pytest.param("worker", "worker", True, 403, id="worker-propia-gestionada"),
    pytest.param("worker", "manager", False, 403, id="worker-ajena"),
]


@pytest.mark.parametrize("actor, target, is_managed, status_code", RATES_CASES)
def test_rates_matches_v1(client, db, parity_world, actor, target, is_managed, status_code):
    v1_company, v2_company = _pair(db, parity_world, is_managed=is_managed)
    subject = getattr(parity_world, target)

    _act(client, parity_world, actor, v1_company)
    v1 = client.put(f"{V1}/{v1_company.id}/members/{subject.id}/rates", json={"ratesConfig": NEW_RATES})
    _act(client, parity_world, actor, v2_company)
    v2 = client.put(f"{V2}/{v2_company.id}/members/{subject.id}/rates", json={"rates_config": NEW_RATES})

    _known(PAIR_RATES, "camelCase en el cuerpo")
    assert v1.status_code == status_code, v1.text
    assert v2.status_code == status_code, v2.text
    if status_code == 200:
        _assert_member_parity(PAIR_RATES, v1.json(), v2.json(), twins=True)
        assert _signature(db, v1_company.id) == _signature(db, v2_company.id)
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


# --- Ajustes (PUT settings) ---

SETTINGS_CASES = [
    pytest.param("pa", "worker", 200, id="pa-sobre-miembro"),
    pytest.param("manager", "worker", 200, id="manager-sobre-miembro"),
    pytest.param("worker", "worker", 200, id="worker-propio"),
    pytest.param("worker", "manager", 403, id="worker-ajeno"),
]


@pytest.mark.parametrize("is_managed", [False, True], ids=["autonoma", "gestionada"])
@pytest.mark.parametrize("actor, target, status_code", SETTINGS_CASES)
def test_settings_matches_v1(client, db, parity_world, actor, target, status_code, is_managed):
    v1_company, v2_company = _pair(db, parity_world, is_managed=is_managed)
    subject = getattr(parity_world, target)

    _act(client, parity_world, actor, v1_company)
    v1 = client.put(f"{V1}/{v1_company.id}/members/{subject.id}/settings", json={"settings": UI_SETTINGS})
    _act(client, parity_world, actor, v2_company)
    v2 = client.put(f"{V2}/{v2_company.id}/members/{subject.id}/settings", json={"settings": UI_SETTINGS})

    assert v1.status_code == status_code, v1.text
    assert v2.status_code == status_code, v2.text
    if status_code == 200:
        _assert_member_parity(PAIR_SETTINGS, v1.json(), v2.json(), twins=True)
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


# --- Orden de miembros (PUT order) ---


@pytest.mark.parametrize(
    "actor, status_code",
    [("manager", 200), ("worker", 403), ("pa_view_as_worker", 403)],
)
def test_order_matches_v1(client, db, parity_world, actor, status_code):
    v1_company, v2_company = _pair(db, parity_world)
    ids = [str(parity_world.worker.id), str(parity_world.manager.id)]
    _act(client, parity_world, actor, v1_company)
    v1 = client.put(f"{V1}/{v1_company.id}/members/order", json={"userIds": ids})
    _act(client, parity_world, actor, v2_company)
    v2 = client.put(f"{V2}/{v2_company.id}/members/order", json={"user_ids": ids})

    _known(PAIR_ORDER, "camelCase en el cuerpo")
    assert v1.status_code == status_code, v1.text
    assert v2.status_code == status_code, v2.text
    if status_code == 200:
        assert to_snake(v1.json()) == to_snake(v2.json()) == ORDER_MESSAGE
        assert _order_map(db, v1_company.id) == _order_map(db, v2_company.id)
        assert _order_map(db, v1_company.id), "el orden no se aplico en v1"
    else:
        assert v1.json()["detail"] == v2.json()["detail"]


# --- Tarifas de todos los miembros (GET rates-v2 en v1, GET rates en v2) ---


@pytest.mark.parametrize("actor", ["pa", "manager"])
def test_rates_list_matches_v1_including_inactive_members(client, db, parity_world, actor):
    company = parity_world.gestionada
    inactive = make_user(db)
    make_member(db, inactive, company, role="worker", is_active=False)
    _act(client, parity_world, actor, company)

    v1, v2 = call_both(client, "GET", f"{V1}/{company.id}/rates-v2", f"{V2}/{company.id}/rates")

    assert v1.status_code == 200, v1.text
    assert v2.status_code == 200, v2.text
    _known(PAIR_RATES_LIST, "ruta")
    assert any(item["is_active"] is False for item in to_snake(v1.json())), "v1 no incluye miembros inactivos"
    _assert_member_parity(PAIR_RATES_LIST, v1.json(), v2.json())


def test_rates_list_forbidden_for_worker_matches_v1(client, parity_world):
    company = parity_world.autonoma
    _act(client, parity_world, "worker", company)

    v1, v2 = call_both(client, "GET", f"{V1}/{company.id}/rates-v2", f"{V2}/{company.id}/rates")

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]


# --- Escrituras prohibidas: mismo codigo y mismo detalle que v1 ---


@pytest.mark.parametrize(
    "actor, name",
    [("manager", name) for name in ["add", "status", "role", "delete"]]
    + [("worker", name) for name in ["add", "status", "role", "delete", "rates", "settings", "order"]]
    + [("pa_view_as_worker", name) for name in ["add", "status", "role", "delete", "rates", "settings", "order"]],
)
def test_writes_forbidden_match_v1_detail_and_leave_no_trace(client, db, parity_world, actor, name):
    company = parity_world.autonoma
    before = _signature(db, company.id)
    _act(client, parity_world, actor, company)
    v1_request, v2_request = _requests(name, parity_world, company)

    v1 = _send(client, v1_request)
    v2 = _send(client, v2_request)

    assert v1.status_code == 403, v1.text
    assert v2.status_code == 403, v2.text
    assert v1.json()["detail"] == v2.json()["detail"]
    assert _signature(db, company.id) == before
