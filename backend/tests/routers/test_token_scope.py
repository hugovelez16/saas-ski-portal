"""
Pruebas del contrato de token minimo, seleccion de empresa y modo "ver como" (PR-04.0).

Describen el contrato nuevo: el JWT solo lleva sub, cid, scope, exp, iat, type y jti; el rol
se consulta en BD; switch-scope, login, verify-2fa y refresh aplican las mismas reglas de
resolucion de empresa activa. Hasta implementar PR-04.1 estas pruebas deben fallar.
"""

import uuid
from datetime import datetime

import auth
import pyotp
import pytest

from tests.factories import as_user, make_company, make_member, make_user

PASSWORD = "pw12345678"
BASE_CLAIMS = {"sub", "cid", "scope", "exp", "iat", "type", "jti"}
MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_VIEW_AS = "Solo el administrador de la plataforma puede usar 'ver como'"


# --- Helpers ---


def _cookie(resp, name):
    """Valor de una cookie emitida por la respuesta. El cliente de pruebas no reenvia cookies `secure` por HTTP."""
    for raw in resp.headers.get_list("set-cookie"):
        key, _, value = raw.split(";", 1)[0].partition("=")
        if key.strip() == name:
            return value
    return None


def _decode(token):
    return auth.jwt.decode(token, auth.PUBLIC_KEY, algorithms=["RS256"])


def _use_token(client, token):
    client.cookies.clear()
    client.cookies.set("access_token", token)


def _current_access(client):
    """Access token que el cliente envia en la siguiente peticion."""
    return client.cookies.get("access_token")


def _use_refresh(client, token):
    client.cookies.clear()
    client.cookies.set("refresh_token", token)


def _login(client, user, company_id=None):
    """POST /token (form). Deja el access token en el cliente. Devuelve (access, refresh)."""
    client.cookies.clear()
    data = {"username": user.email, "password": PASSWORD}
    if company_id is not None:
        data["company_id"] = str(company_id)
    resp = client.post("/token", data=data)
    assert resp.status_code == 200, resp.text
    access = _cookie(resp, "access_token")
    refresh = _cookie(resp, "refresh_token")
    _use_token(client, access)
    return access, refresh


def _me(client):
    resp = client.get("/users/me")
    assert resp.status_code == 200, resp.text
    return resp.json()


def _join(db, user, sort_order=1000, *, active=True, company_active=True, role="worker", joined_at=None):
    """Crea una empresa y una membresia del usuario. Devuelve (empresa, membresia)."""
    company = make_company(db, is_active=company_active)
    member = make_member(db, user, company, role=role, is_active=active)
    member.sort_order = sort_order
    if joined_at is not None:
        member.joined_at = joined_at
    db.commit()
    db.refresh(member)
    return company, member


def _user_2fa(db, **kwargs):
    secret = pyotp.random_base32()
    user = make_user(db, **kwargs)
    user.is_2fa_enabled = True
    user.otp_secret = auth.encrypt_secret(secret)
    db.commit()
    db.refresh(user)
    return user, secret


def _verify_2fa(client, provisional, body):
    _use_token(client, provisional)
    return client.post("/verify-2fa", json=body)


def _assert_cid(payload, expected_company_id):
    if expected_company_id is None:
        assert "cid" not in payload, payload
    else:
        assert payload.get("cid") == str(expected_company_id), payload


def _work_log_body(user, company):
    return {
        "type": "particular",
        "startDate": "2026-01-10",
        "endDate": "2026-01-10",
        "startTime": "09:00:00",
        "endTime": "11:00:00",
        "netAmount": 40.0,
        "userId": str(user.id),
        "companyId": str(company.id),
    }


# --- Casos de seleccion de empresa (login y verify-2fa comparten las mismas reglas) ---
# Cada builder recibe (db, user) y devuelve (company_id pedido por el cliente, company_id esperado).


def _case_requested_active_membership(db, user):
    a, _ = _join(db, user, 2)
    _join(db, user, 1)
    return a.id, a.id


def _case_requested_without_membership(db, user):
    b, _ = _join(db, user, 1)
    other = make_company(db)
    return other.id, b.id


def _case_requested_inactive_membership(db, user):
    a, _ = _join(db, user, 1, active=False)
    b, _ = _join(db, user, 2)
    return a.id, b.id


def _case_requested_nonexistent(db, user):
    a, _ = _join(db, user, 1)
    _join(db, user, 2)
    return uuid.uuid4(), a.id


def _case_requested_suspended_company(db, user):
    a, _ = _join(db, user, 1, company_active=False)
    b, _ = _join(db, user, 2)
    return a.id, b.id


def _case_no_request_uses_sort_order(db, user):
    _join(db, user, 2)
    b, _ = _join(db, user, 1)
    return None, b.id


def _case_no_request_skips_suspended(db, user):
    _join(db, user, 1, company_active=False)
    b, _ = _join(db, user, 2)
    return None, b.id


SELECTION_CASES = [
    pytest.param(_case_requested_active_membership, id="company_id_membresia_activa"),
    pytest.param(_case_requested_without_membership, id="company_id_sin_membresia"),
    pytest.param(_case_requested_inactive_membership, id="company_id_membresia_inactiva"),
    pytest.param(_case_requested_nonexistent, id="company_id_inexistente"),
    pytest.param(_case_requested_suspended_company, id="company_id_empresa_suspendida"),
    pytest.param(_case_no_request_uses_sort_order, id="sin_company_id_sort_order"),
    pytest.param(_case_no_request_skips_suspended, id="sin_company_id_salta_suspendida"),
]


# --- 1. Claims minimos ---


def test_access_token_claims_are_minimal(client, db):
    manager = make_user(db)
    company = make_company(db)
    make_member(db, manager, company, role="manager")

    access, _ = _login(client, manager)

    payload = _decode(access)
    assert set(payload) == BASE_CLAIMS
    assert payload["cid"] == str(company.id)


def test_platform_admin_token_without_company_has_no_cid(client, db):
    pa = make_user(db, role="admin")

    access, _ = _login(client, pa)

    payload = _decode(access)
    assert "cid" not in payload
    assert set(payload) == BASE_CLAIMS - {"cid"}


# --- 2. switch-scope ignora el rol enviado por el cliente ---


@pytest.mark.parametrize(
    "member_role, client_role, expected_role",
    [
        ("worker", "manager", "worker"),
        ("manager", "worker", "manager"),
    ],
)
def test_switch_scope_ignores_client_role(client, db, member_role, client_role, expected_role):
    user = make_user(db)
    company = make_company(db)
    make_member(db, user, company, role=member_role)
    _login(client, user)

    resp = client.post(
        "/auth/switch-scope",
        json={"companyId": str(company.id), "companyRole": client_role},
    )

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    assert _me(client)["activeRole"] == expected_role


# --- 3. switch-scope exige membresia activa y empresa activa ---


@pytest.mark.parametrize("role", ["worker", "manager"])
@pytest.mark.parametrize(
    "scenario, expected_detail",
    [
        ("sin_membresia", MSG_NO_ACCESS),
        ("membresia_inactiva", MSG_NO_ACCESS),
        ("empresa_suspendida", MSG_SUSPENDED),
        ("empresa_inexistente", MSG_NO_ACCESS),
    ],
)
def test_switch_scope_requires_active_membership(client, db, role, scenario, expected_detail):
    user = make_user(db)
    home, _ = _join(db, user, 1, role=role)
    _login(client, user)
    assert _decode(_current_access(client))["cid"] == str(home.id)

    if scenario == "sin_membresia":
        target = make_company(db)
    elif scenario == "membresia_inactiva":
        target = make_company(db)
        make_member(db, user, target, role=role, is_active=False)
    elif scenario == "empresa_suspendida":
        target, _ = _join(db, user, 2, company_active=False, role=role)
    else:
        target = None
    target_id = target.id if target is not None else uuid.uuid4()

    resp = client.post("/auth/switch-scope", json={"companyId": str(target_id)})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == expected_detail


# --- 4. switch-scope para platform admin ---


def test_switch_scope_platform_admin_without_company_resets_context(client, db):
    pa = make_user(db, role="admin")
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json={})

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    assert "cid" not in _decode(_current_access(client))
    assert _me(client)["activeCompanyId"] is None


def test_switch_scope_platform_admin_active_company(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    payload = _decode(_current_access(client))
    assert payload["cid"] == str(company.id)
    assert "view_as" not in payload
    assert _me(client)["activeRole"] is None


def test_switch_scope_platform_admin_suspended_company_is_allowed(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, is_active=False)
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    assert _decode(_current_access(client))["cid"] == str(company.id)


def test_switch_scope_platform_admin_nonexistent_company_returns_404(client, db):
    pa = make_user(db, role="admin")
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json={"companyId": str(uuid.uuid4())})

    assert resp.status_code == 404, resp.text


# --- 5. Modo "ver como" ---


def test_view_as_sets_read_only_context(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id), "viewAs": "worker"})

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    payload = _decode(_current_access(client))
    assert payload["cid"] == str(company.id)
    assert payload["view_as"] == "worker"
    me = _me(client)
    assert me["activeRole"] == "worker"
    assert me["viewAs"] == "worker"
    assert me["isReadOnlyView"] is True


@pytest.mark.parametrize(
    "payload_builder",
    [
        pytest.param(lambda company_id: {"companyId": company_id, "viewAs": "admin"}, id="view_as_invalido"),
        pytest.param(lambda company_id: {"viewAs": "worker"}, id="view_as_sin_company_id"),
    ],
)
def test_view_as_rejects_invalid_payloads(client, db, payload_builder):
    pa = make_user(db, role="admin")
    company = make_company(db)
    _login(client, pa)

    resp = client.post("/auth/switch-scope", json=payload_builder(str(company.id)))

    assert resp.status_code == 422, resp.text


def test_view_as_denied_for_non_platform_admin(client, db):
    user = make_user(db)
    company, _ = _join(db, user, 1, role="manager")
    _login(client, user)

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id), "viewAs": "worker"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_VIEW_AS


def test_switch_back_without_view_as_clears_read_only_mode(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    _login(client, pa)
    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id), "viewAs": "worker"})
    _use_token(client, _cookie(resp, "access_token"))

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))
    assert "view_as" not in _decode(_current_access(client))
    assert _me(client)["isReadOnlyView"] is False


def test_view_as_token_blocks_writes(client, db):
    pa = make_user(db, role="admin")
    worker = make_user(db)
    company, _ = _join(db, worker, 1)
    _login(client, pa)
    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id), "viewAs": "worker"})
    _use_token(client, _cookie(resp, "access_token"))

    resp = client.post("/work-logs", json=_work_log_body(worker, company))

    assert resp.status_code == 403, resp.text


def test_refresh_drops_view_as(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    _, refresh = _login(client, pa)
    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id), "viewAs": "worker"})
    assert resp.status_code == 200, resp.text

    _use_refresh(client, refresh)
    resp = client.post("/refresh-token")

    assert resp.status_code == 200, resp.text
    payload = _decode(_cookie(resp, "access_token"))
    assert "view_as" not in payload
    assert "cid" not in payload


# --- 6. Seleccion de empresa en login ---


@pytest.mark.parametrize("build", SELECTION_CASES)
def test_login_company_selection(client, db, build):
    user = make_user(db)
    requested, expected = build(db, user)

    access, _ = _login(client, user, company_id=requested)

    _assert_cid(_decode(access), expected)


def test_login_fallback_breaks_ties_by_joined_at(client, db):
    user = make_user(db)
    _join(db, user, 1000, joined_at=datetime(2026, 3, 1))
    early, _ = _join(db, user, 1000, joined_at=datetime(2025, 1, 1))

    access, _ = _login(client, user)

    _assert_cid(_decode(access), early.id)


def test_login_user_with_only_suspended_companies_has_no_cid(client, db):
    user = make_user(db)
    _join(db, user, 1, company_active=False)

    access, _ = _login(client, user)

    _assert_cid(_decode(access), None)


def test_login_user_without_memberships_has_no_cid_and_me_is_ok(client, db):
    user = make_user(db)

    access, _ = _login(client, user)

    _assert_cid(_decode(access), None)
    assert _me(client)["activeCompanyId"] is None


@pytest.mark.parametrize("with_company_id", [False, True], ids=["sin_company_id", "con_company_id"])
def test_platform_admin_login_has_no_cid(client, db, with_company_id):
    pa = make_user(db, role="admin")
    company, _ = _join(db, pa, 1)

    access, _ = _login(client, pa, company_id=company.id if with_company_id else None)

    _assert_cid(_decode(access), None)


# --- 6b. Seleccion de empresa en verify-2fa ---


@pytest.mark.parametrize("build", SELECTION_CASES)
def test_verify_2fa_company_selection(client, db, build):
    user, secret = _user_2fa(db)
    requested, expected = build(db, user)
    provisional, _ = _login(client, user)
    _assert_cid(_decode(provisional), None)
    assert _decode(provisional)["scope"] == "2fa_pending"

    body = {"code": pyotp.TOTP(secret).now()}
    if requested is not None:
        body["companyId"] = str(requested)
    resp = _verify_2fa(client, provisional, body)

    assert resp.status_code == 200, resp.text
    _assert_cid(_decode(_cookie(resp, "access_token")), expected)


def test_verify_2fa_user_without_memberships_has_no_cid(client, db):
    user, secret = _user_2fa(db)
    provisional, _ = _login(client, user)

    resp = _verify_2fa(client, provisional, {"code": pyotp.TOTP(secret).now()})

    assert resp.status_code == 200, resp.text
    _assert_cid(_decode(_cookie(resp, "access_token")), None)


def test_verify_2fa_platform_admin_with_company_id_has_no_cid(client, db):
    pa, secret = _user_2fa(db, role="admin")
    company, _ = _join(db, pa, 1)
    provisional, _ = _login(client, pa, company_id=company.id)

    resp = _verify_2fa(client, provisional, {"code": pyotp.TOTP(secret).now(), "companyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    _assert_cid(_decode(_cookie(resp, "access_token")), None)


def test_verify_2fa_malformed_company_id_returns_422(client, db):
    user, secret = _user_2fa(db)
    provisional, _ = _login(client, user)

    resp = _verify_2fa(client, provisional, {"code": pyotp.TOTP(secret).now(), "companyId": "no-es-uuid"})

    assert resp.status_code == 422, resp.text


def test_verify_2fa_wrong_code_returns_400(client, db):
    user, _ = _user_2fa(db)
    provisional, _ = _login(client, user)

    resp = _verify_2fa(client, provisional, {"code": "000000"})

    assert resp.status_code == 400, resp.text


def test_verify_2fa_rejects_token_that_is_not_pending(client, db):
    user, secret = _user_2fa(db)
    company, _ = _join(db, user, 1)
    as_user(client, user, company)

    resp = client.post("/verify-2fa", json={"code": pyotp.TOTP(secret).now()})

    assert resp.status_code == 403, resp.text


def test_2fa_login_never_sends_cid_even_with_company_id(client, db):
    user, _ = _user_2fa(db)
    company, _ = _join(db, user, 1)

    provisional, _ = _login(client, user, company_id=company.id)

    payload = _decode(provisional)
    assert "cid" not in payload
    assert payload["scope"] == "2fa_pending"


# --- 7. refresh aplica las mismas reglas ---


@pytest.mark.parametrize(
    "scenario, expects_b",
    [
        ("membresia_a_revocada", True),
        ("empresa_a_suspendida", True),
        ("empresa_a_y_b_suspendidas", False),
    ],
)
def test_refresh_applies_same_rules(client, db, scenario, expects_b):
    user = make_user(db)
    a, a_member = _join(db, user, 1)
    b, _ = _join(db, user, 2)
    access, refresh = _login(client, user)
    _assert_cid(_decode(access), a.id)

    if scenario == "membresia_a_revocada":
        a_member.is_active = False
    elif scenario == "empresa_a_suspendida":
        a.is_active = False
    else:
        a.is_active = False
        b.is_active = False
    db.commit()

    _use_refresh(client, refresh)
    resp = client.post("/refresh-token")

    assert resp.status_code == 200, resp.text
    _assert_cid(_decode(_cookie(resp, "access_token")), b.id if expects_b else None)


# --- 8. cid nunca sin rol de empresa ---


def _scenario_worker(db):
    user = make_user(db)
    _join(db, user, 1, role="worker")
    return user


def _scenario_manager(db):
    user = make_user(db)
    _join(db, user, 1, role="manager")
    return user


def _scenario_only_suspended(db):
    user = make_user(db)
    _join(db, user, 1, company_active=False)
    return user


def _scenario_only_inactive_membership(db):
    user = make_user(db)
    _join(db, user, 1, active=False)
    return user


def _scenario_no_memberships(db):
    return make_user(db)


def _scenario_platform_admin(db):
    return make_user(db, role="admin")


@pytest.mark.parametrize(
    "scenario",
    [
        _scenario_worker,
        _scenario_manager,
        _scenario_only_suspended,
        _scenario_only_inactive_membership,
        _scenario_no_memberships,
        _scenario_platform_admin,
    ],
    ids=lambda f: f.__name__,
)
def test_cid_never_without_role(client, db, scenario):
    user = scenario(db)
    access, _ = _login(client, user)

    payload = _decode(access)
    me = _me(client)

    assert (payload.get("cid") is None) == (me["activeCompanyId"] is None)
    if me["activeRole"] is not None:
        assert me["activeCompanyId"] is not None
    if not me["isPlatformAdmin"]:
        assert me["activeCompanyId"] is None or me["activeRole"] in ("worker", "manager")


# --- 9. Token de impersonacion ---


def test_impersonation_token(client, db):
    pa = make_user(db, role="admin")
    target = make_user(db)
    _join(db, target, 1)
    as_user(client, pa)

    resp = client.post(f"/admin/impersonate/{target.id}")

    assert resp.status_code == 200, resp.text
    payload = _decode(_cookie(resp, "access_token"))
    assert payload["scope"] == "impersonated"
    assert payload["admin_user_id"] == str(pa.id)
    assert 9 * 60 <= payload["exp"] - payload["iat"] <= 11 * 60
    assert set(payload) <= BASE_CLAIMS | {"admin_user_id"}
    _use_token(client, _cookie(resp, "access_token"))
    me = _me(client)
    assert me["isImpersonated"] is True
    assert me["isPlatformAdmin"] is False


def test_switch_scope_rejected_while_impersonating(client, db):
    pa = make_user(db, role="admin")
    target = make_user(db)
    company, _member = _join(db, target, 1)
    as_user(client, pa)
    resp = client.post(f"/admin/impersonate/{target.id}")
    assert resp.status_code == 200, resp.text
    _use_token(client, _cookie(resp, "access_token"))

    resp = client.post("/auth/switch-scope", json={"companyId": str(company.id)})

    assert resp.status_code == 403
