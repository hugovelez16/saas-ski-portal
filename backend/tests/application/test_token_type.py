"""
Issue #78: get_current_user y get_verified_user solo aceptan JWT con claim `type` = "access".
Un refresh token no debe servir como access token (401) en ninguna dependencia de autenticacion.

Los tokens de scope especial (impersonated, 2fa_pending) siguen su flujo normal.
Redis se sustituye por el doble de conftest (fixture autouse `fake_redis`).
"""

import auth
import pyotp

from tests.factories import as_user, make_token, make_user

SESSIONS_URL = "/sessions"
VERIFY_2FA_URL = "/verify-2fa"


def _refresh_for(user) -> str:
    return auth.create_refresh_token({"sub": str(user.id)})


# --- Refresh token contra get_verified_user (GET /sessions) ---


def test_refresh_token_in_bearer_header_returns_401(client, db):
    # Issue #78: un refresh token en Authorization Bearer no es un access token
    user = make_user(db)
    client.cookies.clear()

    resp = client.get(SESSIONS_URL, headers={"Authorization": f"Bearer {_refresh_for(user)}"})

    assert resp.status_code == 401, resp.text


def test_refresh_token_in_access_cookie_returns_401(client, db):
    # Issue #78: mismo rechazo cuando el refresh token viaja en la cookie access_token
    user = make_user(db)
    client.cookies.clear()
    client.cookies.set("access_token", _refresh_for(user))

    resp = client.get(SESSIONS_URL)

    assert resp.status_code == 401, resp.text


# --- Refresh token contra get_current_user (POST /verify-2fa) ---


def test_refresh_token_against_get_current_user_returns_401(client, db):
    # Issue #78: get_current_user tambien rechaza refresh tokens
    user = make_user(db)
    client.cookies.clear()
    client.cookies.set("access_token", _refresh_for(user))

    resp = client.post(VERIFY_2FA_URL, json={"code": "000000"})

    assert resp.status_code == 401, resp.text


# --- Access token normal y scopes especiales ---


def test_access_token_returns_200(client, db):
    # Issue #78: un access token valido sigue funcionando
    user = make_user(db)

    resp = as_user(client, user).get(SESSIONS_URL)

    assert resp.status_code == 200, resp.text


def test_impersonated_token_is_still_accepted(client, db):
    # Issue #78: el scope impersonated con claim admin_user_id no se rechaza por tipo
    admin = make_user(db, role="admin")
    user = make_user(db)

    resp = as_user(
        client,
        user,
        scope="impersonated",
        claims={"admin_user_id": str(admin.id)},
    ).get(SESSIONS_URL)

    assert resp.status_code != 401, resp.text
    assert resp.status_code == 200, resp.text


def test_2fa_pending_token_reaches_verify_2fa_and_fails_on_bad_code(client, db):
    # Issue #78: el token 2fa_pending debe llegar a /verify-2fa (no 401); codigo invalido -> 400
    user = make_user(db)
    secret = pyotp.random_base32()
    user.is_2fa_enabled = True
    user.otp_secret = auth.encrypt_secret(secret)
    db.commit()
    db.refresh(user)
    wrong_code = "000000" if pyotp.TOTP(secret).now() != "000000" else "111111"
    pending = make_token(user, scope="2fa_pending", expires_minutes=5)

    client.cookies.clear()
    client.cookies.set("access_token", pending)
    resp = client.post(VERIFY_2FA_URL, json={"code": wrong_code})

    assert resp.status_code != 401, resp.text
    assert resp.status_code == 400, resp.text


def test_2fa_pending_token_on_verified_endpoint_returns_403(client, db):
    # Issue #78 / flujo 2FA: get_verified_user rechaza 2fa_pending con 403 (no 401)
    user = make_user(db)

    resp = as_user(client, user, scope="2fa_pending").get(SESSIONS_URL)

    assert resp.status_code == 403, resp.text
