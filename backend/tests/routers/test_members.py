"""
Pruebas HTTP de los endpoints de miembros tras PR-05 (membresias solo de plataforma).

Describen el comportamiento objetivo de PR-05.0: `members/add`, `status`, `role` y `DELETE`
son solo de platform admin (PA); `rates` y `settings` siguen la politica de `access_policy`;
el PA en modo "ver como" es de solo lectura; se elimina la ruta antigua `PUT .../members/{uid}`;
se retira `users.default_company_id` (M3); `PUT /users/me` no borra nombres (M4); el PA no
puede dejarse la plataforma sin administradores (M9); y los eventos `member.*` registran
actor, empresa y usuario afectado.

Los casos que pasan con el codigo actual son regresiones que la implementacion debe mantener;
el resto falla por comportamiento ausente.

No hay test de la migracion `b7e1a0d10007` marcado `postgres`: el repositorio no tiene ningun
test que ejecute Alembic, asi que no existe el patron a reutilizar.
"""

import crud
import email_utils
import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

PA_CLAIMS = {"is_admin": True}

MSG_MANAGED_READONLY = "En empresas gestionadas solo el equipo gestor puede modificar turnos y tarifas"
MSG_SELF_DEACTIVATE = "No puedes desactivar tu propia cuenta"
MSG_SELF_DEMOTE = "No puedes cambiar tu propio rol de plataforma"
MSG_LAST_ADMIN = "La plataforma no puede quedarse sin administradores"
MSG_COMPANY_NOT_FOUND = "Empresa no encontrada"
VIEW_AS_READONLY_FRAGMENT = "solo lectura"

OLD_RATES = {"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}}
NEW_RATES = {"particular": {"base_rate": 25.0, "is_gross": True, "tax_overrides": {}}}

PA_ONLY_ENDPOINTS = ["add", "status", "role", "delete", "reset_email"]
ALL_MEMBER_ENDPOINTS = PA_ONLY_ENDPOINTS + ["rates", "settings"]


# --- Helpers ---


def _setup_company_with_worker(db):
    """Empresa con un worker activo, un usuario ajeno a la empresa y un PA de plataforma."""
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    outsider = make_user(db)
    pa = make_user(db, role="admin")
    return company, worker, outsider, pa


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


async def _async_noop_email(*args, **kwargs):
    return None


def _fake_email(monkeypatch):
    monkeypatch.setattr(email_utils, "send_password_reset_email", _async_noop_email)


def _call_member_endpoint(client, name, company, member, outsider):
    """Ejecuta la operacion `name` sobre `member` (worker activo de `company`)."""
    cid = company.id
    if name == "add":
        return client.post(f"/companies/{cid}/members/add", json={"email": outsider.email})
    if name == "status":
        return client.put(f"/companies/{cid}/members/{member.id}/status", params={"status": "inactive"})
    if name == "role":
        return client.put(f"/companies/{cid}/members/{member.id}/role", json={"role": "manager"})
    if name == "delete":
        return client.delete(f"/companies/{cid}/members/{member.id}")
    if name == "reset_email":
        return client.post(f"/users/{member.id}/reset-password-email")
    if name == "rates":
        return client.put(f"/companies/{cid}/members/{member.id}/rates", json={"ratesConfig": NEW_RATES})
    if name == "settings":
        return client.put(
            f"/companies/{cid}/members/{member.id}/settings", json={"settings": {"ui_preferences": {"theme": "dark"}}}
        )
    raise ValueError(f"endpoint desconocido: {name}")


# --- Matriz de permisos (Q1): solo PA en add, status, role, DELETE y reset de contrasena ---


@pytest.mark.parametrize("name", PA_ONLY_ENDPOINTS)
@pytest.mark.parametrize("role", ["manager", "worker"])
def test_manager_and_worker_get_403_on_pa_only_member_endpoints(client, db, monkeypatch, role, name):
    _fake_email(monkeypatch)
    company, worker, outsider, _pa = _setup_company_with_worker(db)
    actor = make_user(db)
    make_member(db, actor, company, role=role)
    as_user(client, actor, company, claims={"role": role})

    resp = _call_member_endpoint(client, name, company, worker, outsider)

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("name", PA_ONLY_ENDPOINTS)
def test_pa_gets_200_on_pa_only_member_endpoints(client, db, monkeypatch, name):
    _fake_email(monkeypatch)
    company, worker, outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = _call_member_endpoint(client, name, company, worker, outsider)

    assert resp.status_code == 200, resp.text


# --- members/add ---


def test_add_new_user_creates_active_worker_and_emits_member_added(client, db):
    company, _worker, outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/companies/{company.id}/members/add", json={"email": outsider.email})

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "worker"
    assert resp.json()["isActive"] is True
    membership = _membership(db, outsider, company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker
    rows = _audit_rows(db, "member.added")
    assert len(rows) == 1
    _assert_trace(rows[0], pa, company, outsider)


def test_add_reactivates_inactive_manager_as_worker_and_emits_reactivated(client, db):
    company, _worker, _outsider, pa = _setup_company_with_worker(db)
    former = make_user(db)
    make_member(db, former, company, role="manager", is_active=False)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/companies/{company.id}/members/add", json={"email": former.email})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, former, company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker  # M6: la reactivacion fuerza worker
    rows = _audit_rows(db, "member.reactivated")
    assert len(rows) == 1
    assert rows[0].old_value == {"is_active": False, "role": "manager"}
    assert rows[0].new_value == {"is_active": True, "role": "worker"}
    _assert_trace(rows[0], pa, company, former)


def test_add_already_active_member_is_noop(client, db):
    company, _worker, _outsider, pa = _setup_company_with_worker(db)
    active_manager = make_user(db)
    make_member(db, active_manager, company, role="manager", is_active=True)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/companies/{company.id}/members/add", json={"email": active_manager.email})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, active_manager, company)
    assert membership.role == models.CompanyRole.manager
    assert membership.is_active is True
    assert _audit_rows(db, "member.added") == []
    assert _audit_rows(db, "member.reactivated") == []


def test_add_unknown_email_returns_404(client, db):
    company, _worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/companies/{company.id}/members/add", json={"email": "nadie@test.com"})

    assert resp.status_code == 404, resp.text


def test_add_malformed_email_returns_422(client, db):
    company, _worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post(f"/companies/{company.id}/members/add", json={"email": "no-es-un-email"})

    assert resp.status_code == 422, resp.text


def test_add_to_nonexistent_company_returns_404(client, db):
    _company, _worker, outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, None, claims=PA_CLAIMS)

    resp = client.post("/companies/00000000-0000-0000-0000-000000000001/members/add", json={"email": outsider.email})

    assert resp.status_code == 404, resp.text
    assert resp.json()["detail"] == MSG_COMPANY_NOT_FOUND


# --- status ---


@pytest.mark.parametrize(
    "value, expected_active",
    [
        ("active", True),
        ("approved", True),
        ("true", True),
        ("1", True),
        ("inactive", False),
        ("rejected", False),
        ("false", False),
        ("0", False),
    ],
)
def test_status_accepts_current_and_legacy_values(client, db, value, expected_active):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/status", params={"status": value})

    assert resp.status_code == 200, resp.text
    assert _membership(db, worker, company).is_active is expected_active


def test_status_rejects_unknown_value_with_422(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/status", params={"status": "maybe"})

    assert resp.status_code == 422, resp.text
    assert _membership(db, worker, company).is_active is True


def test_deactivating_membership_does_not_reassign_other_memberships(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    user = make_user(db)
    make_member(db, user, company_a, role="worker")
    make_member(db, user, company_b, role="manager")
    pa = make_user(db, role="admin")
    as_user(client, pa, company_a, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company_a.id}/members/{user.id}/status", params={"status": "inactive"})

    assert resp.status_code == 200, resp.text
    assert _membership(db, user, company_a).is_active is False
    other = _membership(db, user, company_b)
    assert other.is_active is True
    assert other.role == models.CompanyRole.manager


def test_reactivating_member_forces_worker_role(client, db):
    company, _worker, _outsider, pa = _setup_company_with_worker(db)
    former = make_user(db)
    make_member(db, former, company, role="manager", is_active=False)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{former.id}/status", params={"status": "active"})

    assert resp.status_code == 200, resp.text
    membership = _membership(db, former, company)
    assert membership.is_active is True
    assert membership.role == models.CompanyRole.worker  # M6


# --- role ---


def test_pa_changes_worker_to_manager_and_emits_role_changed(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/role", json={"role": "manager"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "manager"
    assert _membership(db, worker, company).role == models.CompanyRole.manager
    rows = _audit_rows(db, "member.role_changed")
    assert len(rows) == 1
    _assert_trace(rows[0], pa, company, worker)


def test_role_admin_value_is_rejected_with_422(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/role", json={"role": "admin"})

    assert resp.status_code == 422, resp.text
    assert _membership(db, worker, company).role == models.CompanyRole.worker


def test_role_change_on_non_member_returns_404(client, db):
    company, _worker, outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{outsider.id}/role", json={"role": "manager"})

    assert resp.status_code == 404, resp.text


def test_role_change_takes_effect_on_next_request_of_affected_user(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    # El worker no puede listar miembros (requiere manager); la peticion deja la politica cacheada.
    as_user(client, worker, company, claims={"role": "worker"})
    assert client.get(f"/companies/{company.id}/members").status_code == 403

    as_user(client, pa, company, claims=PA_CLAIMS)
    resp = client.put(f"/companies/{company.id}/members/{worker.id}/role", json={"role": "manager"})
    assert resp.status_code == 200, resp.text

    as_user(client, worker, company, claims={"role": "manager"})
    assert client.get(f"/companies/{company.id}/members").status_code == 200


# --- DELETE members/{uid} ---


def test_delete_member_without_work_logs_removes_membership(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.delete(f"/companies/{company.id}/members/{worker.id}")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": True, "deactivated": False, "reason": None}
    db.expire_all()
    assert db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).count() == 0
    rows = _audit_rows(db, "member.removed")
    assert len(rows) == 1
    _assert_trace(rows[0], pa, company, worker)


def test_delete_member_with_work_logs_deactivates_and_keeps_logs(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    make_work_log(db, worker, company)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.delete(f"/companies/{company.id}/members/{worker.id}")

    assert resp.status_code == 200, resp.text
    assert resp.json() == {"deleted": False, "deactivated": True, "reason": "has_work_logs"}
    assert _membership(db, worker, company).is_active is False
    db.expire_all()
    assert db.query(models.WorkLog).filter_by(user_id=worker.id, company_id=company.id).count() == 1
    rows = _audit_rows(db, "member.deactivated")
    assert len(rows) == 1
    _assert_trace(rows[0], pa, company, worker)


# --- Ruta antigua PUT /companies/{cid}/members/{uid} ---


def test_old_put_member_route_no_longer_exists(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}", json={"role": "manager"})

    assert resp.status_code in (404, 405), resp.text
    assert _membership(db, worker, company).role == models.CompanyRole.worker


# --- rates ---


@pytest.mark.parametrize("is_managed", [False, True])
@pytest.mark.parametrize("target", ["other", "self"])
def test_manager_can_edit_rates_of_any_member(client, db, is_managed, target):
    company = make_company(db, is_managed=is_managed)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    other = make_user(db)
    make_member(db, other, company, role="worker")
    subject = other if target == "other" else manager
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.put(f"/companies/{company.id}/members/{subject.id}/rates", json={"ratesConfig": NEW_RATES})

    assert resp.status_code == 200, resp.text


@pytest.mark.parametrize("is_managed", [False, True])
def test_worker_edits_own_rates_only_when_company_is_autonomous(client, db, is_managed):
    company = make_company(db, is_managed=is_managed)
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config=OLD_RATES)
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json={"ratesConfig": NEW_RATES})

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
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{other.id}/rates", json={"ratesConfig": NEW_RATES})

    assert resp.status_code == 403, resp.text
    assert _membership(db, other, company).rates_config == OLD_RATES


def test_rates_change_emits_event_with_old_and_new_config(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker", rates_config=OLD_RATES)
    as_user(client, manager, company, claims={"role": "manager"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json={"ratesConfig": NEW_RATES})

    assert resp.status_code == 200, resp.text
    rows = _audit_rows(db, "member.rates_changed")
    assert len(rows) == 1
    assert rows[0].old_value == OLD_RATES
    assert rows[0].new_value == NEW_RATES
    _assert_trace(rows[0], manager, company, worker)


def test_rates_negative_base_rate_returns_422(client, db):
    company, worker, _outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims=PA_CLAIMS)
    negative = {"particular": {"base_rate": -5.0, "is_gross": True, "tax_overrides": {}}}

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/rates", json={"ratesConfig": negative})

    assert resp.status_code == 422, resp.text


# --- settings ---


@pytest.mark.parametrize("is_managed", [False, True])
def test_worker_edits_own_settings_in_managed_and_autonomous_company(client, db, is_managed):
    company = make_company(db, is_managed=is_managed)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/settings", json={"settings": {"ui_preferences": {"theme": "dark"}}})

    assert resp.status_code == 200, resp.text


def test_worker_cannot_edit_settings_of_another_member(client, db):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    other = make_user(db)
    make_member(db, other, company, role="worker")
    as_user(client, worker, company, claims={"role": "worker"})

    resp = client.put(f"/companies/{company.id}/members/{other.id}/settings", json={"settings": {"ui_preferences": {"theme": "dark"}}})

    assert resp.status_code == 403, resp.text


@pytest.mark.parametrize("actor_kind", ["manager", "pa"])
def test_manager_and_pa_can_edit_settings_of_another_member(client, db, actor_kind):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    if actor_kind == "manager":
        actor = make_user(db)
        make_member(db, actor, company, role="manager")
        as_user(client, actor, company, claims={"role": "manager"})
    else:
        actor = make_user(db, role="admin")
        as_user(client, actor, company, claims=PA_CLAIMS)

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/settings", json={"settings": {"ui_preferences": {"theme": "dark"}}})

    assert resp.status_code == 200, resp.text


# --- Modo "ver como" del PA: solo lectura en todos los endpoints de miembros ---


@pytest.mark.parametrize("view_as", ["worker", "manager"])
@pytest.mark.parametrize("name", ALL_MEMBER_ENDPOINTS)
def test_view_as_pa_is_read_only_on_member_endpoints(client, db, monkeypatch, view_as, name):
    _fake_email(monkeypatch)
    company, worker, outsider, pa = _setup_company_with_worker(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": view_as})

    resp = _call_member_endpoint(client, name, company, worker, outsider)

    assert resp.status_code == 403, resp.text
    assert VIEW_AS_READONLY_FRAGMENT in resp.json()["detail"]


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


# --- Filtro por estado en el listado de miembros ---


def test_members_list_filters_by_status(client, db):
    company = make_company(db)
    active = make_user(db)
    make_member(db, active, company, role="worker", is_active=True)
    inactive = make_user(db)
    make_member(db, inactive, company, role="worker", is_active=False)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp_active = client.get(f"/companies/{company.id}/members", params={"status": "active"})
    resp_inactive = client.get(f"/companies/{company.id}/members", params={"status": "inactive"})

    assert resp_active.status_code == 200, resp_active.text
    assert {m["userId"] for m in resp_active.json()} == {str(active.id)}
    assert resp_inactive.status_code == 200, resp_inactive.text
    assert {m["userId"] for m in resp_inactive.json()} == {str(inactive.id)}


def test_members_list_rejects_unknown_status_with_422(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get(f"/companies/{company.id}/members", params={"status": "maybe"})

    assert resp.status_code == 422, resp.text


# --- Trazas de auditoria de los eventos member.* ---


def test_member_events_carry_actor_company_and_target(client, db):
    company, worker, outsider, pa = _setup_company_with_worker(db)
    removable = make_user(db)
    make_member(db, removable, company, role="worker")
    as_user(client, pa, company, claims=PA_CLAIMS)

    assert client.post(f"/companies/{company.id}/members/add", json={"email": outsider.email}).status_code == 200
    assert (
        client.put(f"/companies/{company.id}/members/{worker.id}/role", json={"role": "manager"}).status_code == 200
    )
    assert client.delete(f"/companies/{company.id}/members/{removable.id}").status_code == 200

    added = _audit_rows(db, "member.added")
    role_changed = _audit_rows(db, "member.role_changed")
    removed = _audit_rows(db, "member.removed")
    assert len(added) == 1 and len(role_changed) == 1 and len(removed) == 1
    _assert_trace(added[0], pa, company, outsider)
    _assert_trace(role_changed[0], pa, company, worker)
    _assert_trace(removed[0], pa, company, removable)
