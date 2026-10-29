"""
Pruebas HTTP v1 de usuarios tras PR-05 (M3, M4, M9) y del reset de contrasena, que sigue en v1.

Los endpoints de membresia de empresa (`/companies/{id}/members...`) se retiran en PR-21.0: sus casos
viven en tests/routers/v2/test_v2_members.py. Los casos de `reset-password-email` se mantienen aqui
porque la ruta sigue en `/users/{id}`.
"""

import crud
import email_utils
import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user

PA_CLAIMS = {"is_admin": True}

MSG_SELF_DEACTIVATE = "No puedes desactivar tu propia cuenta"
MSG_SELF_DEMOTE = "No puedes cambiar tu propio rol de plataforma"
MSG_LAST_ADMIN = "La plataforma no puede quedarse sin administradores"


# --- Helpers ---


async def _async_noop_email(*args, **kwargs):
    return None


def _fake_email(monkeypatch):
    monkeypatch.setattr(email_utils, "send_password_reset_email", _async_noop_email)


# --- Reset de contrasena: solo PA (endpoint de usuarios, no de empresa) ---


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_manager_and_worker_get_403_on_reset_password_email(client, db, monkeypatch, role):
    _fake_email(monkeypatch)
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    actor = make_user(db)
    make_member(db, actor, company, role=role)
    as_user(client, actor, company, claims={"role": role})

    resp = client.post(f"/users/{worker.id}/reset-password-email")

    assert resp.status_code == 403, resp.text


def test_pa_gets_200_on_reset_password_email(client, db, monkeypatch):
    _fake_email(monkeypatch)
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/users/{worker.id}/reset-password-email")

    assert resp.status_code == 200, resp.text


# --- Ruta de rol antigua y M3: default_company_id retirado ---


def test_users_me_put_ignores_default_company_id(client, db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company, role="worker")
    as_user(client, user, company)

    resp = client.put("/users/me", json={"firstName": "Nuevo", "defaultCompanyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    assert "defaultCompanyId" not in resp.json()
    db.expire_all()
    assert getattr(db.get(models.User, user.id), "default_company_id", None) is None


def test_users_me_get_has_no_default_company_id(client, db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company, role="worker")
    as_user(client, user, company)

    resp = client.get("/users/me")

    assert resp.status_code == 200, resp.text
    assert "defaultCompanyId" not in resp.json()


def test_admin_put_user_ignores_default_company_id(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    target = make_user(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/users/{target.id}", json={"firstName": "Nuevo", "defaultCompanyId": str(company.id)})

    assert resp.status_code == 200, resp.text
    assert "defaultCompanyId" not in resp.json()
    db.expire_all()
    assert getattr(db.get(models.User, target.id), "default_company_id", None) is None


def test_user_model_has_no_default_company_id_column(db):
    assert "default_company_id" not in models.User.__table__.columns
    assert not hasattr(models.User, "default_company_id")


# --- M4: PUT /users/me no borra nombres ---


def test_users_me_put_without_name_fields_keeps_names(client, db):
    company = make_company(db)
    user = make_user(db)
    user.first_name, user.last_name = "Ana", "Lopez"
    db.commit()
    as_user(client, user, company)

    resp = client.put("/users/me", json={})

    assert resp.status_code == 200, resp.text
    db.expire_all()
    refreshed = db.get(models.User, user.id)
    assert refreshed.first_name == "Ana"
    assert refreshed.last_name == "Lopez"


def test_users_me_put_with_null_names_keeps_names(client, db):
    company = make_company(db)
    user = make_user(db)
    user.first_name, user.last_name = "Ana", "Lopez"
    db.commit()
    as_user(client, user, company)

    resp = client.put("/users/me", json={"firstName": None, "lastName": None})

    assert resp.status_code == 200, resp.text
    db.expire_all()
    refreshed = db.get(models.User, user.id)
    assert refreshed.first_name == "Ana"
    assert refreshed.last_name == "Lopez"


def test_users_me_put_with_only_first_name_keeps_last_name(client, db):
    company = make_company(db)
    user = make_user(db)
    user.first_name, user.last_name = "Ana", "Lopez"
    db.commit()
    as_user(client, user, company)

    resp = client.put("/users/me", json={"firstName": "Beatriz"})

    assert resp.status_code == 200, resp.text
    db.expire_all()
    refreshed = db.get(models.User, user.id)
    assert refreshed.first_name == "Beatriz"
    assert refreshed.last_name == "Lopez"


# --- M9: invariantes del platform admin ---


def test_pa_cannot_deactivate_own_account(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{pa.id}/status", params={"is_active": "false"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SELF_DEACTIVATE
    db.expire_all()
    assert db.get(models.User, pa.id).is_active is True


def test_pa_cannot_demote_own_role(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{pa.id}", json={"role": "user"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SELF_DEMOTE
    db.expire_all()
    assert db.get(models.User, pa.id).role == models.UserRole.admin


def test_last_active_pa_cannot_be_deactivated(client, db, monkeypatch):
    # Simula un unico PA activo en la plataforma: el objetivo es ese PA y el actor es otro.
    monkeypatch.setattr(crud, "count_active_platform_admins", lambda _db: 1, raising=False)
    actor = make_user(db, role="admin")
    target = make_user(db, role="admin")
    as_user(client, actor, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{target.id}/status", params={"is_active": "false"})

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_LAST_ADMIN
    db.expire_all()
    assert db.get(models.User, target.id).is_active is True


def test_last_active_pa_cannot_be_demoted(client, db, monkeypatch):
    monkeypatch.setattr(crud, "count_active_platform_admins", lambda _db: 1, raising=False)
    actor = make_user(db, role="admin")
    target = make_user(db, role="admin")
    as_user(client, actor, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{target.id}", json={"role": "user"})

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == MSG_LAST_ADMIN
    db.expire_all()
    assert db.get(models.User, target.id).role == models.UserRole.admin


def test_pa_can_deactivate_other_pa_when_two_remain(client, db):
    first = make_user(db, role="admin")
    second = make_user(db, role="admin")
    as_user(client, first, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{second.id}/status", params={"is_active": "false"})

    assert resp.status_code == 200, resp.text
    db.expire_all()
    assert db.get(models.User, second.id).is_active is False


def test_user_role_outside_admin_or_user_returns_422(client, db):
    pa = make_user(db, role="admin")
    target = make_user(db)
    as_user(client, pa, None, claims=PA_CLAIMS)

    resp = client.put(f"/users/{target.id}", json={"role": "superuser"})

    assert resp.status_code == 422, resp.text
