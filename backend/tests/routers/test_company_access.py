"""
Pruebas HTTP de la politica de acceso a empresas (PR-03): modo "ver como", aislamiento entre
empresas, empresa suspendida, efecto inmediato de cambios de membresia, Redis caido, rol y
platform admin leidos de BD, caducidad de token y limites de paginacion.

Los tokens llevan los mismos claims que emite `auth.generate_user_tokens` (`is_admin`, `role`, `cid`),
para que los fallos reflejen la politica y no tokens incompletos.

Los casos marcados con `# PR-03:` describen un comportamiento que cambia respecto al codigo actual.
Los tests que usan la funcion SQL `get_billing_summary` llevan el marcador `postgres`.
"""

import uuid

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_token, make_user, make_work_log

MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_SWITCH_COMPANY = "Cambia a esta empresa para gestionarla"
MSG_FORBIDDEN = "No tienes permisos para esta accion"
MSG_VIEW_AS_READONLY_FRAGMENT = "solo lectura"

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}


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


def _set_token(client, user, company=None, claims=None):
    """Como as_user, pero sin borrar cookies previas: util para alternar usuarios en el mismo test."""
    client.cookies.set("access_token", make_token(user, company, claims=claims))
    return client


# --- Modo "ver como" (view_as) del platform admin ---


def test_view_as_worker_pa_can_read_company(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get(f"/companies/{company.id}")

    assert resp.status_code == 200, resp.text


def test_view_as_worker_pa_cannot_list_company_members(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: en modo "ver como" worker el PA pierde permisos de manager sobre la empresa.
    assert resp.status_code == 403, resp.text


def test_view_as_worker_pa_cannot_create_work_log_with_read_only_message(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.post("/work-logs", json=_work_log_body(worker, company))

    # PR-03: los metodos no seguros se rechazan en modo "ver como" con MSG_VIEW_AS_READONLY.
    assert resp.status_code == 403, resp.text
    assert MSG_VIEW_AS_READONLY_FRAGMENT in resp.json()["detail"]


def test_view_as_worker_pa_cannot_update_company(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, name="Original")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.put(f"/companies/{company.id}", json={"name": "Modificada"})

    # PR-03: modo "ver como" de solo lectura bloquea PUT /companies/{cid}.
    assert resp.status_code == 403, resp.text
    db.refresh(company)
    assert company.name == "Original"


def test_view_as_worker_pa_cannot_list_users(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get("/users")

    # PR-03: GET /users es solo PA; con "ver como" activo se rechaza (require_platform_admin).
    assert resp.status_code == 403, resp.text


def test_view_as_pa_can_switch_scope(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.post("/auth/switch-scope", json={})

    assert resp.status_code == 200, resp.text


def test_view_as_pa_can_logout(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.post("/logout")

    assert resp.status_code == 200, resp.text


def test_view_as_manager_pa_can_list_company_members(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(f"/companies/{company.id}/members")

    assert resp.status_code == 200, resp.text


def test_view_as_manager_pa_can_read_dashboard_summary(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(f"/companies/{company.id}/dashboard-summary")

    assert resp.status_code == 200, resp.text


@pytest.mark.postgres
def test_view_as_manager_pa_can_read_billing_summary(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(company.id), "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert resp.status_code == 200, resp.text


def test_view_as_manager_pa_cannot_create_work_log(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.post("/work-logs", json=_work_log_body(worker, company))

    assert resp.status_code == 403, resp.text
    assert MSG_VIEW_AS_READONLY_FRAGMENT in resp.json()["detail"]


def test_view_as_manager_pa_cannot_update_company(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, name="Original")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.put(f"/companies/{company.id}", json={"name": "Modificada"})

    assert resp.status_code == 403, resp.text


def test_view_as_manager_pa_cannot_update_member_role(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.put(f"/companies/{company.id}/members/{worker.id}/role", json={"role": "manager"})

    assert resp.status_code == 403, resp.text


def test_view_as_manager_pa_cannot_delete_work_log(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    work_log = make_work_log(db, worker, company)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.delete(f"/work-logs/{work_log.id}")

    assert resp.status_code == 403, resp.text
    assert db.query(models.WorkLog).filter_by(id=work_log.id).count() == 1


def test_view_as_claim_ignored_for_non_platform_admin_manager_can_read(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={**MANAGER_CLAIMS, "view_as": "worker"})

    resp = client.get(f"/companies/{company.id}/members")

    assert resp.status_code == 200, resp.text


def test_view_as_claim_ignored_for_non_platform_admin_manager_can_write(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={**MANAGER_CLAIMS, "view_as": "worker"})

    resp = client.post("/work-logs", json=_work_log_body(manager, company))

    assert resp.status_code == 200, resp.text


def test_view_as_without_company_is_ignored(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, name="Original")
    as_user(client, pa, None, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.put(f"/companies/{company.id}", json={"name": "Modificada"})

    assert resp.status_code == 200, resp.text
    db.refresh(company)
    assert company.name == "Modificada"


def test_users_me_reports_view_as_worker_as_read_only(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get("/users/me")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # PR-03: /users/me expone el modo "ver como" (campos nuevos en UserResponse).
    assert body["viewAs"] == "worker"
    assert body["isReadOnlyView"] is True
    assert body["activeRole"] == "worker"
    assert body["isPlatformAdmin"] is True


def test_users_me_pa_without_view_as_has_null_active_role(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get("/users/me")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    # PR-03: PA con cid y sin view_as no tiene rol activo.
    assert body["activeRole"] is None
    assert body["isPlatformAdmin"] is True


# --- Aislamiento entre empresas (Q1) ---


def test_manager_of_a_cannot_list_members_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company_b.id}/members")

    # PR-03: 403 con mensaje uniforme para empresa ajena (P-5), en vez de otro detalle.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_manager_of_a_cannot_read_dashboard_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company_b.id}/dashboard-summary")

    # PR-03: 403 con MSG_NO_ACCESS para empresa ajena (P-5); hoy el mensaje es otro.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_manager_of_a_cannot_read_billing_summary_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(company_b.id), "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert resp.status_code == 403, resp.text


def test_manager_of_a_cannot_read_rates_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company_b.id}/rates-v2")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_manager_token_for_b_cannot_manage_a(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    make_member(db, manager, company_b, role="manager")
    # Token emitido para B (cid=B) intentando gestionar A.
    as_user(client, manager, company_b, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company_a.id}/members")

    # PR-03: la empresa de gestion debe coincidir con el cid del token (MSG_SWITCH_COMPANY).
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


def test_worker_of_a_cannot_list_work_logs_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    worker_a = make_user(db)
    make_member(db, worker_a, company_a, role="worker")
    worker_b = make_user(db)
    make_member(db, worker_b, company_b, role="worker")
    make_work_log(db, worker_b, company_b)
    as_user(client, worker_a, company_a, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company_b.id)})

    # PR-03: sin membresia activa en B, el worker recibe 403 y no ve turnos de B.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_manager_gets_403_for_nonexistent_company(client, db):
    company_a = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company_a, role="manager")
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{uuid.uuid4()}")

    # PR-03: empresa inexistente para no-PA responde 403 (P-5), no 404.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_pa_gets_404_for_nonexistent_company(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims=PA_CLAIMS)

    resp = client.get(f"/companies/{uuid.uuid4()}")

    assert resp.status_code == 404, resp.text


def test_malformed_company_id_returns_422(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims=PA_CLAIMS)

    resp = client.get("/companies/no-es-un-uuid")

    # PR-03: company_id de path pasa a tipo UUID (422 si es invalido).
    assert resp.status_code == 422, resp.text


# --- Empresa suspendida ---


def test_suspended_company_blocks_worker_work_logs_listing(client, db):
    company = make_company(db, is_active=False)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company.id)})

    # PR-03: empresa suspendida bloquea el listado de turnos para no-PA.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


@pytest.mark.postgres
def test_suspended_company_blocks_manager_billing_summary(client, db):
    company = make_company(db, is_active=False)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(company.id), "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    # PR-03: empresa suspendida bloquea billing para no-PA.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


def test_suspended_company_blocks_manager_dashboard_summary(client, db):
    company = make_company(db, is_active=False)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company.id}/dashboard-summary")

    # PR-03: empresa suspendida bloquea el dashboard para no-PA.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


def test_suspended_company_still_readable_by_pa_work_logs(client, db):
    company = make_company(db, is_active=False)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company.id)})

    assert resp.status_code == 200, resp.text


def test_suspended_company_still_readable_by_pa_dashboard_summary(client, db):
    company = make_company(db, is_active=False)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get(f"/companies/{company.id}/dashboard-summary")

    assert resp.status_code == 200, resp.text


@pytest.mark.postgres
def test_suspended_company_still_readable_by_pa_billing_summary(client, db):
    company = make_company(db, is_active=False)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.get(
        "/work-logs/billing-summary",
        params={"company_id": str(company.id), "start_date": "2026-01-01", "end_date": "2026-01-31"},
    )

    assert resp.status_code == 200, resp.text


def _create_company_module(db, company, code_name):
    module = models.AppModule(code_name=code_name, name="Modulo de prueba", is_active=True)
    db.add(module)
    db.flush()
    subscription = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        user_id=None,
        scope=models.SubscriptionScope.company,
        status=models.SubscriptionStatus.active,
    )
    db.add(subscription)
    db.commit()
    return module


def test_modules_me_returns_company_module_when_company_active(client, db):
    # Control: con la empresa activa el modulo de empresa aparece; valida el propio setup.
    company = make_company(db, is_active=True)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    module = _create_company_module(db, company, f"mod_activa_{uuid.uuid4().hex[:6]}")
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/modules/me", params={"company_id": str(company.id)})

    assert resp.status_code == 200, resp.text
    assert module.code_name in [m["codeName"] for m in resp.json()]


def test_suspended_company_hides_company_module_from_worker_modules_me(client, db):
    company = make_company(db, is_active=False)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    module = _create_company_module(db, company, f"mod_suspendida_{uuid.uuid4().hex[:6]}")
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.get("/modules/me", params={"company_id": str(company.id)})

    # PR-03: una empresa suspendida no aporta sus suscripciones de empresa a los no-PA.
    assert resp.status_code == 200, resp.text
    assert module.code_name not in [m["codeName"] for m in resp.json()]


# --- Efecto inmediato (S5): sin esperar al TTL de la cache ---


def test_role_downgrade_takes_effect_immediately(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    # Primera peticion: la membresia de manager queda cacheada si hay cache.
    assert client.get(f"/companies/{company.id}/members").status_code == 200

    as_user(client, pa, company, claims=PA_CLAIMS)
    resp_change = client.put(f"/companies/{company.id}/members/{manager.id}/role", json={"role": "worker"})
    assert resp_change.status_code == 200, resp_change.text

    # El token del manager sigue siendo el mismo (claim role=manager); solo cambia la BD.
    _set_token(client, manager, company, claims=MANAGER_CLAIMS)
    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: el rol sale de la membresia; el cambio es inmediato.
    assert resp.status_code == 403, resp.text


def test_membership_deactivation_takes_effect_immediately(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    assert client.get(f"/companies/{company.id}/members").status_code == 200

    as_user(client, pa, company, claims=PA_CLAIMS)
    resp_change = client.put(
        f"/companies/{company.id}/members/{manager.id}/status", params={"status": "inactive"}
    )
    assert resp_change.status_code == 200, resp_change.text

    _set_token(client, manager, company, claims=MANAGER_CLAIMS)
    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: membresia desactivada pierde acceso de inmediato.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_company_suspension_takes_effect_immediately(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    assert client.get(f"/companies/{company.id}/members").status_code == 200

    as_user(client, pa, company, claims=PA_CLAIMS)
    resp_change = client.put(f"/companies/{company.id}", json={"isActive": False})
    assert resp_change.status_code == 200, resp_change.text

    _set_token(client, manager, company, claims=MANAGER_CLAIMS)
    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: suspender la empresa bloquea de inmediato a sus managers.
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SUSPENDED


# --- Redis caido ---


def test_redis_down_does_not_block_legit_manager(client, db, fake_redis):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    fake_redis.raise_errors = True
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get(f"/companies/{company.id}/members")

    # Con Redis caido la politica lee de BD y el manager legitimo sigue accediendo.
    assert resp.status_code == 200, resp.text


# --- Platform admin y rol leidos de BD (P4, P-3) ---


def test_pa_from_database_ignores_is_admin_false_claim(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims={"is_admin": False})

    resp = client.get("/users")

    # PR-03: el PA se decide por users.role en BD; el claim is_admin se ignora.
    assert resp.status_code == 200, resp.text


def test_non_pa_with_is_admin_true_claim_is_not_pa(client, db):
    user = make_user(db, role="user")
    as_user(client, user, claims={"is_admin": True})

    resp = client.get("/users")

    # PR-03: un usuario sin role admin en BD no es PA aunque el token diga is_admin.
    assert resp.status_code == 403, resp.text


def test_role_claim_manager_ignored_when_membership_is_worker(client, db):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    as_user(client, worker, company, claims={"role": "manager"})

    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: el rol sale de la membresia (BD), no del claim role del token.
    assert resp.status_code == 403, resp.text


def test_role_claim_worker_ignored_when_membership_is_manager(client, db):
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    as_user(client, manager, company, claims={"role": "worker"})

    resp = client.get(f"/companies/{company.id}/members")

    # PR-03: el manager conserva su rol aunque el token diga worker.
    assert resp.status_code == 200, resp.text


# --- Caducidad de token ---


def test_expired_token_returns_401(client, db):
    user = make_user(db)
    token = make_token(user, expires_minutes=-1)
    client.cookies.clear()
    client.cookies.set("access_token", token)

    resp = client.get("/users/me")

    assert resp.status_code == 401, resp.text


# --- Limites de paginacion en GET /work-logs (tope de limit 2000 desde PR-08) ---


def test_work_logs_negative_skip_returns_422(client, db):
    user = make_user(db)
    as_user(client, user)

    resp = client.get("/work-logs", params={"skip": -1})

    assert resp.status_code == 422, resp.text


def test_work_logs_zero_limit_returns_422(client, db):
    user = make_user(db)
    as_user(client, user)

    resp = client.get("/work-logs", params={"limit": 0})

    assert resp.status_code == 422, resp.text


def test_work_logs_limit_above_cap_returns_422(client, db):
    """Tope de limit (2000) aplicado en PR-08 [P-12]."""
    user = make_user(db)
    as_user(client, user)

    resp = client.get("/work-logs", params={"limit": 5000})

    assert resp.status_code == 422, resp.text


# --- Cambio de empresa obligatorio: no PA miembro de A y B con token cid=B ---


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


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_list_work_logs_of_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    make_work_log(db, user, company_a)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.get("/work-logs", params={"company_id": str(company_a.id)})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_create_work_log_in_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.post("/work-logs", json=_work_log_body(user, company_a))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY
    assert db.query(models.WorkLog).filter_by(company_id=company_a.id).count() == 0


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_update_work_log_of_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    other = _other_member(db, company_a)
    work_log = make_work_log(db, other, company_a)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.put(f"/work-logs/{work_log.id}", json=_work_log_body(other, company_a))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY
    db.refresh(work_log)
    assert work_log.net_amount == 40.0


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_delete_work_log_of_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    other = _other_member(db, company_a)
    work_log = make_work_log(db, other, company_a)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.delete(f"/work-logs/{work_log.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY
    assert db.query(models.WorkLog).filter_by(id=work_log.id).count() == 1


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_update_member_of_a(client, db, role):
    # PR-05: el cambio de rol es solo de plataforma (PA). Para un no PA la respuesta es el 403 generico
    # (anti-enumeracion, P-5), no el mensaje de cambio de empresa.
    user, company_a, company_b = _member_of_a_and_b(db, role)
    other = _other_member(db, company_a, role="worker")
    as_user(client, user, company_b, claims={"role": role})

    resp = client.put(f"/companies/{company_a.id}/members/{other.id}/role", json={"role": "manager"})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_FORBIDDEN
    member = db.query(models.CompanyMember).filter_by(user_id=other.id, company_id=company_a.id).one()
    assert member.role == models.CompanyRole.worker


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_read_company_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.get(f"/companies/{company_a.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_b_cannot_read_modules_of_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    as_user(client, user, company_b, claims={"role": role})

    resp = client.get("/modules/me", params={"company_id": str(company_a.id)})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_SWITCH_COMPANY


@pytest.mark.parametrize("role", ["manager", "worker"])
def test_member_of_a_and_b_with_token_a_reads_company_a(client, db, role):
    user, company_a, company_b = _member_of_a_and_b(db, role)
    make_work_log(db, user, company_a)
    as_user(client, user, company_a, claims={"role": role})

    assert client.get("/work-logs", params={"company_id": str(company_a.id)}).status_code == 200
    assert client.get(f"/companies/{company_a.id}").status_code == 200


def test_manager_of_a_and_b_with_token_a_can_write_company_a(client, db):
    user, company_a, company_b = _member_of_a_and_b(db, "manager")
    other = _other_member(db, company_a)
    work_log = make_work_log(db, other, company_a)
    as_user(client, user, company_a, claims=MANAGER_CLAIMS)

    assert client.post("/work-logs", json=_work_log_body(user, company_a)).status_code == 200
    assert client.put(f"/work-logs/{work_log.id}", json=_work_log_body(other, company_a)).status_code == 200
    # PR-05: el estado de membresia es solo de plataforma (PA). Un manager recibe 403 y el estado no cambia.
    status_resp = client.put(f"/companies/{company_a.id}/members/{other.id}/status", params={"status": "inactive"})
    assert status_resp.status_code == 403, status_resp.text
    assert status_resp.json()["detail"] == MSG_FORBIDDEN
    member = db.query(models.CompanyMember).filter_by(user_id=other.id, company_id=company_a.id).one()
    assert member.is_active is True
    # Escritura de membresia que el manager si tiene: tarifas de un miembro de su empresa gestionada.
    rates_resp = client.put(
        f"/companies/{company_a.id}/members/{other.id}/rates",
        json={"ratesConfig": {"particular": {"base_rate": 20.0}}},
    )
    assert rates_resp.status_code == 200, rates_resp.text
    assert client.delete(f"/work-logs/{work_log.id}").status_code == 200


def test_worker_of_a_and_b_with_token_a_can_create_own_work_log_in_a(client, db):
    user, company_a, company_b = _member_of_a_and_b(db, "worker")
    as_user(client, user, company_a, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_work_log_body(user, company_a))

    assert resp.status_code == 200, resp.text


def test_manager_of_a_and_b_with_token_b_lists_only_b_work_logs_without_company_id(client, db):
    user, company_a, company_b = _member_of_a_and_b(db, "manager")
    other_a = _other_member(db, company_a)
    log_a = make_work_log(db, other_a, company_a)
    log_b = make_work_log(db, user, company_b)
    as_user(client, user, company_b, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs")

    assert resp.status_code == 200, resp.text
    ids = {item["id"] for item in resp.json()}
    assert str(log_b.id) in ids
    assert str(log_a.id) not in ids
    assert {item["companyId"] for item in resp.json()} == {str(company_b.id)}


def test_worker_of_a_and_b_with_daily_report_is_forbidden_in_detailed(client, db):
    # PR-14: el worker con modulo ya no ve la empresa en /companies/detailed (usa /companies/{id}/daily-report)
    user, company_a, company_b = _member_of_a_and_b(db, "worker")
    # Con PostgreSQL migrado el modulo ya existe (lo siembra una migracion); con SQLite se crea.
    module = db.query(models.AppModule).filter(models.AppModule.code_name == "worker_daily_report").first()
    if module is None:
        module = models.AppModule(code_name="worker_daily_report", name="Parte diario", is_active=True)
        db.add(module)
        db.flush()
    for company in (company_a, company_b):
        db.add(
            models.ModuleSubscription(
                module_id=module.id,
                company_id=company.id,
                user_id=None,
                scope=models.SubscriptionScope.company,
                status=models.SubscriptionStatus.active,
            )
        )
    db.commit()
    as_user(client, user, company_b, claims=WORKER_CLAIMS)

    resp = client.get("/companies/detailed")

    assert resp.status_code == 403, resp.text


def test_pa_with_token_b_accesses_company_a(client, db):
    pa = make_user(db, role="admin")
    company_a = make_company(db)
    company_b = make_company(db)
    other_a = _other_member(db, company_a)
    log_a = make_work_log(db, other_a, company_a)
    as_user(client, pa, company_b, claims=PA_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company_a.id)})

    assert resp.status_code == 200, resp.text
    assert str(log_a.id) in {item["id"] for item in resp.json()}
    assert client.get(f"/companies/{company_a.id}").status_code == 200
