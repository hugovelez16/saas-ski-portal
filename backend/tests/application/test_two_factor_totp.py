"""
Pruebas del 2FA TOTP: verificacion protegida (limite de intentos y anti-replay),
cifrado del secreto y endpoints /verify-2fa, /2fa/setup, /2fa/activate y /2fa/disable.

Redis se sustituye por un doble en memoria; no se necesita base de datos.
"""

import uuid
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import auth
import pyotp
import pytest
import schemas
from fastapi import HTTPException, Response
from routers import auth as auth_router
from routers import users as users_router


class FakeRedis:
    """Doble en memoria con la parte de la API de redis-py que usa auth.py."""

    def __init__(self):
        self.store = {}
        self.ttl = {}

    def get(self, key):
        return self.store.get(key)

    def incr(self, key):
        self.store[key] = int(self.store.get(key, 0)) + 1
        return self.store[key]

    def expire(self, key, seconds):
        self.ttl[key] = seconds

    def set(self, key, value, ex=None, nx=False):
        if nx and key in self.store:
            return None
        self.store[key] = value
        if ex is not None:
            self.ttl[key] = ex
        return True

    def delete(self, key):
        return 1 if self.store.pop(key, None) is not None else 0


class FakeRedisManager:
    def __init__(self, client):
        self.client = client

    def get(self, key):
        return self.client.get(key)

    def set(self, key, value, ex=3600):
        return bool(self.client.set(key, value, ex=ex))

    def delete(self, key):
        return self.client.delete(key) > 0


@pytest.fixture
def fake_redis(monkeypatch):
    client = FakeRedis()
    monkeypatch.setattr(auth, "redis_manager", FakeRedisManager(client))
    return client


def make_user(secret=None, enabled=True):
    secret = secret or pyotp.random_base32()
    return SimpleNamespace(
        id=uuid.uuid4(),
        email="usuario@vesotel.com",
        is_2fa_enabled=enabled,
        otp_secret=auth.encrypt_secret(secret),
        token_scope="2fa_pending",
    ), secret


def make_request(token=None):
    request = MagicMock()
    request.cookies = {"access_token": token} if token else {}
    request.headers = {}
    request.client.host = "127.0.0.1"
    return request


# --- Cifrado del secreto ---


def test_secret_is_stored_encrypted_and_round_trips():
    secret = pyotp.random_base32()
    encrypted = auth.encrypt_secret(secret)
    assert encrypted != secret
    assert secret not in encrypted
    assert auth.decrypt_secret(encrypted) == secret


def test_provisioning_uri_uses_issuer_from_environment(monkeypatch):
    monkeypatch.setenv("TOTP_ISSUER_NAME", "Escuela Test")
    uri = auth.get_totp_uri(pyotp.random_base32(), "usuario@vesotel.com")
    assert uri.startswith("otpauth://totp/")
    assert "Escuela%20Test" in uri


# --- Verificacion protegida ---


def test_valid_code_is_accepted(fake_redis):
    user, secret = make_user()
    assert auth.verify_totp_with_protection(user, pyotp.TOTP(secret).now()) is True


def test_invalid_code_is_rejected_and_counted(fake_redis):
    user, _ = make_user()
    assert auth.verify_totp_with_protection(user, "000000") is False
    assert fake_redis.store[f"2fa_fail_{user.id}"] == 1
    assert fake_redis.ttl[f"2fa_fail_{user.id}"] == auth.TOTP_FAILURE_WINDOW_SECONDS


def test_replayed_code_is_rejected(fake_redis):
    user, secret = make_user()
    code = pyotp.TOTP(secret).now()
    assert auth.verify_totp_with_protection(user, code) is True
    assert auth.verify_totp_with_protection(user, code) is False


def test_lockout_after_max_failures_returns_429(fake_redis):
    user, secret = make_user()
    for _ in range(auth.TOTP_MAX_FAILURES):
        assert auth.verify_totp_with_protection(user, "000000") is False

    # Incluso un codigo correcto queda bloqueado dentro de la ventana
    with pytest.raises(HTTPException) as exc:
        auth.verify_totp_with_protection(user, pyotp.TOTP(secret).now())
    assert exc.value.status_code == 429


def test_successful_verification_resets_failure_counter(fake_redis):
    user, secret = make_user()
    auth.verify_totp_with_protection(user, "000000")
    auth.verify_totp_with_protection(user, "000000")
    assert auth.verify_totp_with_protection(user, pyotp.TOTP(secret).now()) is True
    assert f"2fa_fail_{user.id}" not in fake_redis.store


def test_redis_unavailable_fails_closed(monkeypatch):
    monkeypatch.setattr(auth, "redis_manager", FakeRedisManager(None))
    user, secret = make_user()
    with pytest.raises(HTTPException) as exc:
        auth.verify_totp_with_protection(user, pyotp.TOTP(secret).now())
    assert exc.value.status_code == 503


def test_redis_error_fails_closed(monkeypatch):
    broken = MagicMock()
    broken.get.side_effect = ConnectionError("redis caido")
    monkeypatch.setattr(auth, "redis_manager", FakeRedisManager(broken))
    user, secret = make_user()
    with pytest.raises(HTTPException) as exc:
        auth.verify_totp_with_protection(user, pyotp.TOTP(secret).now())
    assert exc.value.status_code == 503


# --- /verify-2fa ---


@pytest.fixture
def stub_token_issuing(monkeypatch):
    monkeypatch.setattr(auth, "generate_user_tokens", lambda db, user: ("access-final", "refresh-final"))
    monkeypatch.setattr(auth, "create_session", lambda *args, **kwargs: None)


async def call_verify_2fa(user, code, token):
    return await auth_router.verify_2fa(
        schemas.Verify2FA(code=code),
        Response(),
        make_request(token),
        db=MagicMock(),
        current_user=user,
    )


async def test_verify_2fa_issues_tokens_and_blacklists_pending_token(fake_redis, stub_token_issuing):
    user, secret = make_user()
    pending = auth.create_access_token({"sub": str(user.id), "scope": "2fa_pending"}, timedelta(minutes=5))
    jti = auth.jwt.decode(pending, auth.PUBLIC_KEY, algorithms=[auth.ALGORITHM])["jti"]

    result = await call_verify_2fa(user, pyotp.TOTP(secret).now(), pending)

    assert result["requires_2fa"] is False
    assert fake_redis.store[f"bl_{jti}"] == "1"


async def test_verify_2fa_rejects_full_scope_token(fake_redis, stub_token_issuing):
    user, secret = make_user()
    user.token_scope = "full"
    with pytest.raises(HTTPException) as exc:
        await call_verify_2fa(user, pyotp.TOTP(secret).now(), None)
    assert exc.value.status_code == 403


async def test_verify_2fa_rejects_wrong_code(fake_redis, stub_token_issuing):
    user, _ = make_user()
    with pytest.raises(HTTPException) as exc:
        await call_verify_2fa(user, "000000", None)
    assert exc.value.status_code == 400


async def test_verify_2fa_locks_out_after_repeated_failures(fake_redis, stub_token_issuing):
    user, secret = make_user()
    for _ in range(auth.TOTP_MAX_FAILURES):
        with pytest.raises(HTTPException):
            await call_verify_2fa(user, "000000", None)

    with pytest.raises(HTTPException) as exc:
        await call_verify_2fa(user, pyotp.TOTP(secret).now(), None)
    assert exc.value.status_code == 429


# --- /2fa/setup, /2fa/activate, /2fa/disable ---


async def test_setup_stores_encrypted_secret_and_returns_uri(fake_redis):
    user, _ = make_user(enabled=False)
    user.otp_secret = None
    db = MagicMock()

    result = await auth_router.setup_2fa(db=db, current_user=user)

    assert user.is_2fa_enabled is False
    assert user.otp_secret != result["secret"]
    assert auth.decrypt_secret(user.otp_secret) == result["secret"]
    assert result["qr_code_uri"].startswith("otpauth://totp/")
    db.commit.assert_called_once()


async def test_setup_with_2fa_already_active_returns_409(fake_redis):
    user, _ = make_user(enabled=True)
    previous_secret = user.otp_secret

    with pytest.raises(HTTPException) as exc:
        await auth_router.setup_2fa(db=MagicMock(), current_user=user)

    assert exc.value.status_code == 409
    assert user.otp_secret == previous_secret
    assert user.is_2fa_enabled is True


async def test_activate_enables_2fa_with_valid_code(fake_redis):
    user, secret = make_user(enabled=False)
    db = MagicMock()

    result = await auth_router.activate_2fa(
        schemas.TOTPActivate(code=pyotp.TOTP(secret).now()), db=db, current_user=user
    )

    assert user.is_2fa_enabled is True
    assert "activated" in result["message"]


async def test_activate_rejects_invalid_code(fake_redis):
    user, _ = make_user(enabled=False)

    with pytest.raises(HTTPException) as exc:
        await auth_router.activate_2fa(schemas.TOTPActivate(code="000000"), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 400
    assert user.is_2fa_enabled is False


async def test_activate_without_setup_returns_400(fake_redis):
    user, _ = make_user(enabled=False)
    user.otp_secret = None

    with pytest.raises(HTTPException) as exc:
        await auth_router.activate_2fa(schemas.TOTPActivate(code="123456"), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 400


async def test_disable_requires_valid_code(fake_redis):
    user, secret = make_user(enabled=True)
    db = MagicMock()

    with pytest.raises(HTTPException) as exc:
        await auth_router.disable_2fa(schemas.TOTPDisable(code="000000"), db=db, current_user=user)
    assert exc.value.status_code == 400
    assert user.is_2fa_enabled is True
    assert user.otp_secret is not None

    await auth_router.disable_2fa(schemas.TOTPDisable(code=pyotp.TOTP(secret).now()), db=db, current_user=user)
    assert user.is_2fa_enabled is False
    assert user.otp_secret is None


async def test_disable_when_not_enabled_returns_400(fake_redis):
    user, _ = make_user(enabled=False)
    user.otp_secret = None

    with pytest.raises(HTTPException) as exc:
        await auth_router.disable_2fa(schemas.TOTPDisable(code="123456"), db=MagicMock(), current_user=user)

    assert exc.value.status_code == 400


# --- Reset de 2FA por el administrador de la plataforma ---


def make_admin(is_platform_admin=True):
    return SimpleNamespace(id=uuid.uuid4(), email="admin@vesotel.com", is_platform_admin=is_platform_admin)


def test_admin_reset_clears_2fa_revokes_sessions_and_audits(fake_redis, monkeypatch):
    user, _ = make_user(enabled=True)
    admin = make_admin()
    db = MagicMock()
    monkeypatch.setattr(users_router.crud, "get_user", lambda session, uid: user)
    fake_redis.store[f"2fa_fail_{user.id}"] = 5

    result = users_router.reset_user_2fa(str(user.id), db=db, current_user=admin)

    assert result == {"message": "2FA reset"}
    assert user.is_2fa_enabled is False
    assert user.otp_secret is None
    db.query.return_value.filter.return_value.update.assert_called_once_with(
        {"is_active": False}, synchronize_session=False
    )
    audit = db.add.call_args.args[0]
    assert audit.action == "2fa_reset"
    assert audit.impersonated_user_id == user.id
    assert audit.admin_user_id == admin.id
    assert audit.extra_data == {"target_email": user.email}
    db.commit.assert_called_once()
    assert f"2fa_fail_{user.id}" not in fake_redis.store


def test_reset_is_forbidden_for_non_platform_admin(fake_redis, monkeypatch):
    user, _ = make_user(enabled=True)
    monkeypatch.setattr(users_router.crud, "get_user", lambda session, uid: user)

    with pytest.raises(HTTPException) as exc:
        users_router.reset_user_2fa(str(user.id), db=MagicMock(), current_user=make_admin(is_platform_admin=False))

    assert exc.value.status_code == 403
    assert user.is_2fa_enabled is True
    assert user.otp_secret is not None


def test_reset_unknown_user_returns_404(fake_redis, monkeypatch):
    monkeypatch.setattr(users_router.crud, "get_user", lambda session, uid: None)

    with pytest.raises(HTTPException) as exc:
        users_router.reset_user_2fa(str(uuid.uuid4()), db=MagicMock(), current_user=make_admin())

    assert exc.value.status_code == 404


def test_reset_user_without_2fa_returns_400_and_writes_nothing(fake_redis, monkeypatch):
    user, _ = make_user(enabled=False)
    user.otp_secret = None
    db = MagicMock()
    monkeypatch.setattr(users_router.crud, "get_user", lambda session, uid: user)

    with pytest.raises(HTTPException) as exc:
        users_router.reset_user_2fa(str(user.id), db=db, current_user=make_admin())

    assert exc.value.status_code == 400
    db.add.assert_not_called()
    db.commit.assert_not_called()
