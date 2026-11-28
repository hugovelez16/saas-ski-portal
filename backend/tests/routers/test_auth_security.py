"""
Pruebas de seguridad de autenticacion (PR-01): tokens 2FA pendientes, usuarios inactivos,
registro publico, bypass de desarrollo y sembrado inicial.

Cubren el comportamiento de PR-01.1 a PR-01.5.
"""

import inspect

import auth
import dev_seed
import main
import models
import pytest
import seed

from tests.factories import as_user, make_company, make_member, make_user

ADMIN_EMAIL = "nuevo-admin@test.com"
ADMIN_PASSWORD = "pw12345678"
ADMIN_COMPANY = "Empresa Seed Test"


def _seed_env(monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.setenv("INITIAL_COMPANY_NAME", ADMIN_COMPANY)


def _dev_env(monkeypatch, environment=None, bypass=None, node_env=None):
    for name, value in (("ENVIRONMENT", environment), ("DEV_LOGIN_BYPASS", bypass), ("NODE_ENV", node_env)):
        if value is None:
            monkeypatch.delenv(name, raising=False)
        else:
            monkeypatch.setenv(name, value)


# --- S7: token 2fa_pending y verify-2fa ---


def test_2fa_pending_token_reaches_verify_2fa(client, db):
    user = make_user(db)
    as_user(client, user, scope="2fa_pending")

    resp = client.post("/verify-2fa", json={"code": "000000"})

    assert resp.status_code == 400, resp.text
    assert resp.json().get("detail") == "2FA not enabled for this user"


# --- S3: usuarios inactivos ---


def test_login_rejects_inactive_user(client, db):
    user = make_user(db, is_active=False)

    resp = client.post("/token", data={"username": user.email, "password": ADMIN_PASSWORD})

    assert resp.status_code == 403, resp.text
    assert resp.json().get("detail") == "Cuenta desactivada. Contacta con el administrador"


def test_login_active_user_ok(client, db):
    user = make_user(db, is_active=True)

    resp = client.post("/token", data={"username": user.email, "password": ADMIN_PASSWORD})

    assert resp.status_code == 200, resp.text


def test_valid_token_of_inactive_user_rejected(client, db):
    user = make_user(db, is_active=False)
    as_user(client, user)

    resp = client.get("/users/me")

    assert resp.status_code == 401, resp.text


def test_refresh_rejects_inactive_user(client, db):
    user = make_user(db, is_active=False)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    auth.create_session(db, str(user.id), refresh_token)
    client.cookies.set("refresh_token", refresh_token)

    resp = client.post("/refresh-token")

    assert resp.status_code == 401, resp.text


# --- S8: registro publico eliminado ---


@pytest.mark.parametrize("path", ["/users/", "/users"])
def test_public_registration_removed(client, db, path):
    body = {"email": "new@test.com", "password": "x"}

    resp = client.post(path, json=body)

    assert resp.status_code not in (200, 201), resp.text
    assert db.query(models.User).filter_by(email="new@test.com").count() == 0


def test_create_user_requires_platform_admin(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.post("/users", json={"email": "new2@test.com", "password": "x"})

    assert resp.status_code == 403, resp.text


# --- I1: bypass de desarrollo y sembrado ---


def test_dev_mode_requires_environment_and_flag(monkeypatch):
    _dev_env(monkeypatch, environment="development", bypass="true")
    assert dev_seed.is_dev_mode() is True

    _dev_env(monkeypatch, environment="development")
    assert dev_seed.is_dev_mode() is False

    _dev_env(monkeypatch, bypass="true")
    assert dev_seed.is_dev_mode() is False

    _dev_env(monkeypatch, node_env="development")
    assert dev_seed.is_dev_mode() is False


def test_assert_dev_bypass_safe(monkeypatch):
    assert hasattr(dev_seed, "assert_dev_bypass_safe"), "dev_seed.assert_dev_bypass_safe no esta implementada"

    _dev_env(monkeypatch, environment="production", bypass="true")
    with pytest.raises(RuntimeError):
        dev_seed.assert_dev_bypass_safe()

    _dev_env(monkeypatch, environment="development", bypass="true")
    dev_seed.assert_dev_bypass_safe()

    _dev_env(monkeypatch, environment="production")
    dev_seed.assert_dev_bypass_safe()


def test_lifespan_does_not_seed():
    assert "seed_initial_data" not in inspect.getsource(main.lifespan)


def test_seed_skips_when_platform_admin_exists(db, monkeypatch):
    _seed_env(monkeypatch)
    make_user(db, email="pa-existente@test.com", role="admin")

    result = seed.seed_initial_data(db)

    assert result is False
    assert db.query(models.User).filter_by(email=ADMIN_EMAIL).count() == 0
    assert db.query(models.Company).filter_by(name=ADMIN_COMPANY).count() == 0


def test_seed_creates_when_no_platform_admin(db, monkeypatch):
    _seed_env(monkeypatch)
    # Tests legacy con SessionLocal dejan administradores confirmados en PostgreSQL;
    # se degradan dentro de la transaccion del test (se revierte al final).
    db.query(models.User).filter(models.User.role == models.UserRole.admin).update(
        {"role": models.UserRole.user}
    )
    db.flush()

    result = seed.seed_initial_data(db)

    assert result is True
    admin = db.query(models.User).filter_by(email=ADMIN_EMAIL).one()
    assert admin.role == models.UserRole.admin
    # R-ACC-26: el PA no tiene membresia en la empresa inicial.
    assert db.query(models.CompanyMember).filter_by(user_id=admin.id).count() == 0

    company = db.query(models.Company).filter_by(name=ADMIN_COMPANY).one()
    # R-EMP-37: el seed no define impuestos por defecto.
    assert company.tax_config == {}
    manager = db.query(models.User).filter_by(email="manager.demo@vesotel.com").one()
    worker = db.query(models.User).filter_by(email="worker.demo@vesotel.com").one()
    assert manager.role == models.UserRole.user
    assert worker.role == models.UserRole.user
    assert db.query(models.CompanyMember).filter_by(user_id=manager.id, company_id=company.id).one().role == models.CompanyRole.manager
    assert db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one().role == models.CompanyRole.worker


def test_seed_defaults_company_name_to_demo_without_env(db, monkeypatch):
    monkeypatch.setenv("INITIAL_ADMIN_EMAIL", ADMIN_EMAIL)
    monkeypatch.setenv("INITIAL_ADMIN_PASSWORD", ADMIN_PASSWORD)
    monkeypatch.delenv("INITIAL_COMPANY_NAME", raising=False)
    db.query(models.User).filter(models.User.role == models.UserRole.admin).update(
        {"role": models.UserRole.user}
    )
    db.flush()

    assert seed.seed_initial_data(db) is True
    assert db.query(models.Company).filter_by(name="Demo").one().is_active is True


def test_dev_seed_creates_demo_members_and_no_pa_membership(db, monkeypatch):
    monkeypatch.delenv("DEV_ADMIN_COMPANY", raising=False)
    user = dev_seed.ensure_dev_admin_user(db)

    assert db.query(models.CompanyMember).filter_by(user_id=user.id).count() == 0
    demo_company = db.query(models.Company).filter_by(name="Demo").first() or db.query(models.Company).first()
    assert demo_company is not None
    manager = db.query(models.User).filter_by(email="manager.demo@vesotel.com").one()
    worker = db.query(models.User).filter_by(email="worker.demo@vesotel.com").one()
    assert (
        db.query(models.CompanyMember)
        .filter_by(user_id=manager.id, company_id=demo_company.id)
        .one()
        .role
        == models.CompanyRole.manager
    )
    assert (
        db.query(models.CompanyMember)
        .filter_by(user_id=worker.id, company_id=demo_company.id)
        .one()
        .role
        == models.CompanyRole.worker
    )


def test_dev_seed_creates_company_without_default_tax_config(db, monkeypatch):
    # R-EMP-37: dev_seed crea la empresa inicial sin tax_config por defecto.
    monkeypatch.setenv("DEV_ADMIN_COMPANY", "Empresa Dev Vacia")
    db.query(models.WorkLog).delete()
    db.query(models.ModuleSubscription).delete()
    db.query(models.CompanyInvitation).delete()
    db.query(models.CompanyMember).delete()
    db.query(models.Company).delete()
    db.flush()

    dev_seed.ensure_dev_admin_user(db)

    created = db.query(models.Company).filter_by(name="Empresa Dev Vacia").one()
    assert created.tax_config == {}
