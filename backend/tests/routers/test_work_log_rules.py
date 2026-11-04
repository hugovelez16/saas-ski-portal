"""
Reglas de turnos (PR-08.0): contrato HTTP de POST/PUT/DELETE /work-logs, POST /work-logs/bulk,
GET /work-logs y funciones de crud asociadas.

Tests de contrato escritos antes de PR-08.1. Los casos que fallan hoy describen comportamiento
aun no implementado (membresia activa obligatoria, solo lectura en empresas gestionadas,
PUT sin cambio de titular, groupId controlado por el servidor, validaciones de fecha, importe
y limite, filtro por empresa en crud). Los casos que ya pasan son regresiones y se listan aparte.
"""

import uuid
from datetime import date, time

import access_policy
import crud
import models
import pytest
import schemas

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

MSG_NO_ACTIVE_MEMBER = "El usuario no tiene una membresia activa en esta empresa"
MSG_CHANGE_OWNER = "No se puede cambiar la empresa ni el usuario de un turno"
MSG_COMPANY_REQUIRED = "company_id es obligatorio"
MSG_NO_ACCESS = "No tienes acceso a esta empresa"
MSG_VIEW_AS_READONLY_FRAGMENT = "solo lectura"

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}


# --- Helpers ---


def _body(user, company, **extra):
    body = {
        "type": "particular",
        "startDate": "2026-01-10",
        "endDate": "2026-01-10",
        "startTime": "09:00:00",
        "endTime": "11:00:00",
        "netAmount": 40.0,
        "userId": str(user.id),
        "companyId": str(company.id),
    }
    body.update(extra)
    return body


def _without(body, *keys):
    return {k: v for k, v in body.items() if k not in keys}


def _bulk_body(company, users, **extra):
    body = _without(_body(users[0], company), "userId")
    body["userIds"] = [str(u.id) for u in users]
    body.update(extra)
    return body


def _count_logs(db):
    return db.query(models.WorkLog).count()


def _stored(db, log_id):
    """Relee el turno desde la BD (la sesion de test es la misma que usa la app)."""
    db.expire_all()
    return db.get(models.WorkLog, log_id)


def _member(db, company, *, role="worker", is_active=True):
    user = make_user(db)
    make_member(db, user, company, role=role, is_active=is_active)
    return user


# --- T1: membresia activa del usuario del turno ---


def test_t1_worker_creates_own_log_in_autonomous_company(client, db):
    company = make_company(db)
    worker = _member(db, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 200, resp.text


def test_t1_worker_without_active_membership_is_rejected_by_authorize(client, db):
    # Un worker con membresia inactiva no llega a la regla T1: authorize responde 403 antes.
    # Documentado para decidir si T1 debe responder 422 tambien en este caso.
    company = make_company(db)
    worker = _member(db, company, is_active=False)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS
    assert _count_logs(db) == 0


@pytest.mark.parametrize("membership", ["ausente", "inactiva"])
def test_t1_manager_cannot_create_log_for_user_without_active_membership(client, db, membership):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    target = make_user(db)
    if membership == "inactiva":
        make_member(db, target, company, role="worker", is_active=False)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(target, company))

    assert resp.status_code == 422, resp.text
    assert MSG_NO_ACTIVE_MEMBER in str(resp.json()["detail"])
    assert _count_logs(db) == 0


@pytest.mark.parametrize("membership", ["ausente", "inactiva"])
def test_t1_pa_cannot_create_log_for_user_without_active_membership(client, db, membership):
    company = make_company(db)
    pa = make_user(db, role="admin")
    target = make_user(db)
    if membership == "inactiva":
        make_member(db, target, company, role="worker", is_active=False)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post("/work-logs", json=_body(target, company))

    assert resp.status_code == 422, resp.text
    assert MSG_NO_ACTIVE_MEMBER in str(resp.json()["detail"])
    assert _count_logs(db) == 0


@pytest.mark.parametrize("membership", ["ausente", "inactiva"])
def test_t1_bulk_rejects_whole_batch_when_one_user_has_no_active_membership(client, db, membership):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    valid_a = _member(db, company)
    valid_b = _member(db, company)
    invalid = make_user(db)
    if membership == "inactiva":
        make_member(db, invalid, company, role="worker", is_active=False)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs/bulk", json=_bulk_body(company, [valid_a, invalid, valid_b]))

    assert resp.status_code == 422, resp.text
    assert MSG_NO_ACTIVE_MEMBER in str(resp.json()["detail"])
    assert _count_logs(db) == 0


# --- T2: empresas gestionadas (solo lectura para worker) ---


def test_t2_worker_cannot_create_own_log_in_managed_company(client, db):
    company = make_company(db, is_managed=True)
    worker = _member(db, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == access_policy.MSG_MANAGED_READONLY
    assert _count_logs(db) == 0


def test_t2_worker_can_create_own_log_in_autonomous_company(client, db):
    company = make_company(db, is_managed=False)
    worker = _member(db, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 200, resp.text


def test_t2_manager_can_create_log_in_managed_company(client, db):
    company = make_company(db, is_managed=True)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 200, resp.text


def test_t2_pa_can_create_log_in_managed_company(client, db):
    company = make_company(db, is_managed=True)
    pa = make_user(db, role="admin")
    worker = _member(db, company)
    as_user(client, pa, company, claims=PA_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 200, resp.text


def test_t2_worker_cannot_update_log_in_managed_company(client, db):
    company = make_company(db, is_managed=True)
    worker = _member(db, company)
    log = make_work_log(db, worker, company, net_amount=40.0)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json=_body(worker, company, netAmount=99.0))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == access_policy.MSG_MANAGED_READONLY
    assert _stored(db, log.id).net_amount == 40.0


def test_t2_worker_cannot_delete_log_in_managed_company(client, db):
    company = make_company(db, is_managed=True)
    worker = _member(db, company)
    log = make_work_log(db, worker, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.delete(f"/work-logs/{log.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == access_policy.MSG_MANAGED_READONLY
    assert _stored(db, log.id) is not None


@pytest.mark.parametrize("method", ["post", "put", "delete"])
def test_t2_pa_in_view_as_worker_is_read_only_in_managed_company(client, db, method):
    company = make_company(db, is_managed=True)
    worker = _member(db, company)
    log = make_work_log(db, worker, company, net_amount=40.0)
    pa = make_user(db, role="admin")
    as_user(client, pa, company, claims={**PA_CLAIMS, "view_as": "worker"})

    if method == "post":
        resp = client.post("/work-logs", json=_body(worker, company))
    elif method == "put":
        resp = client.put(f"/work-logs/{log.id}", json=_body(worker, company, netAmount=99.0))
    else:
        resp = client.delete(f"/work-logs/{log.id}")

    assert resp.status_code == 403, resp.text
    assert MSG_VIEW_AS_READONLY_FRAGMENT in resp.json()["detail"]
    stored = _stored(db, log.id)
    assert stored is not None
    assert stored.net_amount == 40.0


# --- T3: PUT no cambia el titular ni la empresa del turno ---


def test_t3_update_rejects_user_change(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker_a = _member(db, company)
    worker_b = _member(db, company)
    log = make_work_log(db, worker_a, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json=_body(worker_b, company))

    assert resp.status_code == 422, resp.text
    assert MSG_CHANGE_OWNER in str(resp.json()["detail"])
    assert _stored(db, log.id).user_id == worker_a.id


def test_t3_update_rejects_company_change(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager = _member(db, company_a, role="manager")
    worker_a = _member(db, company_a)
    log = make_work_log(db, worker_a, company_a)
    as_user(client, manager, company_a, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json=_body(worker_a, company_b))

    assert resp.status_code == 422, resp.text
    assert MSG_CHANGE_OWNER in str(resp.json()["detail"])
    assert _stored(db, log.id).company_id == company_a.id


def test_t3_update_accepts_same_user_and_company(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log = make_work_log(db, worker, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json=_body(worker, company, netAmount=55.0))

    assert resp.status_code == 200, resp.text
    stored = _stored(db, log.id)
    assert stored.user_id == worker.id
    assert stored.company_id == company.id


def test_t3_update_accepts_body_without_user_and_company_ids(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log = make_work_log(db, worker, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    body = _without(_body(worker, company, netAmount=55.0), "userId", "companyId")
    resp = client.put(f"/work-logs/{log.id}", json=body)

    assert resp.status_code == 200, resp.text
    stored = _stored(db, log.id)
    assert stored.user_id == worker.id
    assert stored.company_id == company.id
    assert stored.net_amount == 55.0


# --- T4: groupId controlado por el servidor ---


def test_t4_bulk_ignores_client_group_id(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker_a = _member(db, company)
    worker_b = _member(db, company)
    sent = str(uuid.uuid4())
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs/bulk", json=_bulk_body(company, [worker_a, worker_b], groupId=sent))

    assert resp.status_code == 200, resp.text
    logs = db.query(models.WorkLog).filter(models.WorkLog.company_id == company.id).all()
    assert len(logs) == 2
    group_ids = {(log.extra_data or {}).get("group_id") for log in logs}
    assert len(group_ids) == 1, group_ids
    assert None not in group_ids
    assert sent not in group_ids


def test_t4_create_ignores_client_group_id(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    sent = str(uuid.uuid4())
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, groupId=sent))

    assert resp.status_code == 200, resp.text
    log = db.query(models.WorkLog).filter(models.WorkLog.user_id == worker.id).one()
    assert (log.extra_data or {}).get("group_id") != sent


def test_t4_apply_to_group_updates_only_same_group_and_company(client, db):
    company = make_company(db)
    other_company = make_company(db)
    manager = _member(db, company, role="manager")
    worker_a = _member(db, company)
    worker_b = _member(db, company)
    outsider = make_user(db)
    group = str(uuid.uuid4())
    other_group = str(uuid.uuid4())

    log_a = make_work_log(db, worker_a, company, extra_data={"group_id": group})
    log_b = make_work_log(db, worker_b, company, extra_data={"group_id": group})
    log_other_group = make_work_log(
        db, worker_b, company, start_date=date(2026, 1, 11), extra_data={"group_id": other_group}
    )
    log_other_company = make_work_log(db, outsider, other_company, extra_data={"group_id": group})
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_a.id}?apply_to_group=true", json=_body(worker_a, company, netAmount=99.0))

    assert resp.status_code == 200, resp.text
    assert _stored(db, log_a.id).net_amount == 99.0
    stored_b = _stored(db, log_b.id)
    assert stored_b.net_amount == 99.0
    assert stored_b.user_id == worker_b.id
    assert _stored(db, log_other_group.id).net_amount == 40.0
    stored_other = _stored(db, log_other_company.id)
    assert stored_other.net_amount == 40.0
    assert stored_other.company_id == other_company.id


def test_t4_apply_to_group_forbidden_for_worker(client, db):
    company = make_company(db)
    worker_a = _member(db, company)
    worker_b = _member(db, company)
    group = str(uuid.uuid4())
    log_a = make_work_log(db, worker_a, company, extra_data={"group_id": group})
    log_b = make_work_log(db, worker_b, company, extra_data={"group_id": group})
    as_user(client, worker_a, company, claims=WORKER_CLAIMS)

    resp = client.put(f"/work-logs/{log_a.id}?apply_to_group=true", json=_body(worker_a, company, netAmount=99.0))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == access_policy.MSG_FORBIDDEN
    assert _stored(db, log_b.id).net_amount == 40.0


def test_t4_group_id_is_exposed_from_extra_data_in_list_and_update(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    group = str(uuid.uuid4())
    log = make_work_log(db, worker, company, extra_data={"group_id": group})
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    listed = client.get("/work-logs", params={"company_id": str(company.id)})

    assert listed.status_code == 200, listed.text
    item = next(i for i in listed.json() if i["id"] == str(log.id))
    assert item["groupId"] == group

    updated = client.put(f"/work-logs/{log.id}", json=_body(worker, company, netAmount=45.0))

    assert updated.status_code == 200, updated.text
    assert updated.json()["groupId"] == group


# --- T6: validaciones de fecha, importes e ids; limite de paginacion ---


def test_t6_start_date_after_end_date_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, startDate="2026-01-11", endDate="2026-01-10"))

    assert resp.status_code == 422, resp.text
    assert _count_logs(db) == 0


def test_t6_date_beyond_max_horizon_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, startDate="2062-01-01", endDate="2062-01-01"))

    assert resp.status_code == 422, resp.text
    assert _count_logs(db) == 0


def test_t6_date_before_min_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, startDate="1999-12-31", endDate="1999-12-31"))

    assert resp.status_code == 422, resp.text
    assert _count_logs(db) == 0


def test_t6_negative_duration_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, duration=-1.0))

    assert resp.status_code == 422, resp.text
    assert _count_logs(db) == 0


def test_t6_negative_net_amount_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, netAmount=-5.0))

    assert resp.status_code == 422, resp.text
    assert _count_logs(db) == 0


def test_t6_malformed_work_log_id_returns_422_on_delete_and_put(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    delete_resp = client.delete("/work-logs/no-es-un-uuid")
    put_resp = client.put("/work-logs/no-es-un-uuid", json=_body(worker, company))

    assert delete_resp.status_code == 422, delete_resp.text
    assert put_resp.status_code == 422, put_resp.text


def test_t6_read_limit_above_max_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company.id), "limit": 2001})

    assert resp.status_code == 422, resp.text


def test_t6_read_limit_zero_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company.id), "limit": 0})

    assert resp.status_code == 422, resp.text


def test_t6_read_limit_2000_returns_real_total_count_not_the_cap(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    total = 2001
    db.bulk_save_objects(
        [
            models.WorkLog(
                user_id=worker.id,
                company_id=company.id,
                type="particular",
                start_date=date(2026, 1, 10),
                end_date=date(2026, 1, 10),
                start_time=time(9, 0),
                end_time=time(11, 0),
                duration=2.0,
                net_amount=40.0,
                gross_amount=50.0,
                extra_data={},
            )
            for _ in range(total)
        ]
    )
    db.commit()
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs", params={"company_id": str(company.id), "limit": 2000})

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 2000
    assert resp.headers["x-total-count"] == str(total)


# --- M5: membresia inactiva en crud y en ediciones antiguas ---


def test_m5_crud_create_rejects_inactive_member_and_creates_nothing(db):
    company = make_company(db)
    worker = make_user(db)
    make_member(db, worker, company, role="worker", is_active=False)
    payload = schemas.WorkLogCreate.model_validate(_body(worker, company))

    with pytest.raises(ValueError):
        crud.create_work_log(db, payload)

    assert _count_logs(db) == 0


def test_m5_update_description_of_old_log_from_inactive_member_is_allowed(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker", is_active=False)
    log = make_work_log(db, worker, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json={"description": "Correccion de texto"})

    assert resp.status_code == 200, resp.text
    assert _stored(db, log.id).description == "Correccion de texto"


# --- P3: filtro por empresa en crud ---


def test_p3_crud_delete_with_other_company_is_noop(db):
    company = make_company(db)
    other_company = make_company(db)
    worker = _member(db, company)
    log = make_work_log(db, worker, company)

    result = crud.delete_work_log(db, str(log.id), company_id=other_company.id)

    assert result is None
    assert _stored(db, log.id) is not None


def test_p3_crud_update_with_other_company_is_noop(db):
    from schemas import WorkLogUpdate

    company = make_company(db)
    other_company = make_company(db)
    worker = _member(db, company)
    log = make_work_log(db, worker, company)
    payload = WorkLogUpdate(description="x")

    result = crud.update_work_log(db, str(log.id), payload, company_id=other_company.id)

    assert result is None
    assert _stored(db, log.id).description is None


# --- company_id obligatorio en el body ---


def test_company_id_is_required_on_create(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_without(_body(worker, company), "companyId"))

    assert resp.status_code == 422, resp.text
    assert MSG_COMPANY_REQUIRED in str(resp.json()["detail"])
    assert _count_logs(db) == 0


def test_company_id_is_required_on_bulk(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs/bulk", json=_without(_bulk_body(company, [worker]), "companyId"))

    assert resp.status_code == 422, resp.text
    assert MSG_COMPANY_REQUIRED in str(resp.json()["detail"])
    assert _count_logs(db) == 0


# --- Aislamiento entre empresas ---


def test_isolation_manager_of_a_cannot_create_log_in_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager_a = _member(db, company_a, role="manager")
    worker_b = _member(db, company_b)
    as_user(client, manager_a, company_a, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker_b, company_b))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS
    assert _count_logs(db) == 0


def test_isolation_manager_of_a_cannot_update_log_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager_a = _member(db, company_a, role="manager")
    worker_b = _member(db, company_b)
    log_b = make_work_log(db, worker_b, company_b, net_amount=40.0)
    as_user(client, manager_a, company_a, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_b.id}", json=_body(worker_b, company_b, netAmount=99.0))

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS
    assert _stored(db, log_b.id).net_amount == 40.0


@pytest.mark.parametrize("field", ["type", "startDate", "endDate"])
def test_put_explicit_null_in_required_field_returns_422(client, db, field):
    company = make_company(db)
    worker = _member(db, company)
    log = make_work_log(db, worker, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json={field: None})

    assert resp.status_code == 422, resp.text


def test_put_dates_unordered_against_stored_value_returns_422(client, db):
    company = make_company(db)
    worker = _member(db, company)
    log = make_work_log(db, worker, company, start_date=date(2026, 1, 10))
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json={"startDate": "2026-01-20"})

    assert resp.status_code == 422, resp.text
    assert _stored(db, log.id).start_date == date(2026, 1, 10)


def test_apply_to_group_is_all_or_nothing_on_invalid_dates(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker_a = _member(db, company)
    worker_b = _member(db, company)
    group = str(uuid.uuid4())
    log_a = make_work_log(db, worker_a, company, start_date=date(2026, 1, 10), extra_data={"group_id": group})
    log_b = make_work_log(
        db, worker_b, company, start_date=date(2026, 1, 10), end_date=date(2026, 1, 12), extra_data={"group_id": group}
    )
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    # 2026-01-11 es invalido para log_a (fin 01-10) y valido para log_b (fin 01-12): no debe aplicarse a ninguno
    resp = client.put(f"/work-logs/{log_a.id}", params={"apply_to_group": "true"}, json={"startDate": "2026-01-11"})

    assert resp.status_code == 422, resp.text
    assert _stored(db, log_a.id).start_date == date(2026, 1, 10)
    assert _stored(db, log_b.id).start_date == date(2026, 1, 10)


def test_bulk_duplicate_user_ids_create_one_log_per_user(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    body = _bulk_body(company, [worker])
    body["userIds"] = [str(worker.id), str(worker.id)]

    resp = client.post("/work-logs/bulk", json=body)

    assert resp.status_code == 200, resp.text
    assert _count_logs(db) == 1


def test_bulk_empty_user_ids_returns_422(client, db):
    company = make_company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    body = _bulk_body(company, [worker])
    body["userIds"] = []

    resp = client.post("/work-logs/bulk", json=body)

    assert resp.status_code == 422, resp.text


def test_missing_log_gives_same_403_as_foreign_log_for_non_pa_and_404_for_pa(client, db):
    company = make_company(db)
    worker = _member(db, company)
    pa = make_user(db, role="admin")
    missing = uuid.uuid4()

    as_user(client, worker, company, claims=WORKER_CLAIMS)
    assert client.delete(f"/work-logs/{missing}").status_code == 403
    assert client.put(f"/work-logs/{missing}", json={"description": "x"}).status_code == 403

    as_user(client, pa, claims=PA_CLAIMS)
    assert client.delete(f"/work-logs/{missing}").status_code == 404


def test_isolation_manager_of_a_cannot_delete_log_of_b(client, db):
    company_a = make_company(db)
    company_b = make_company(db)
    manager_a = _member(db, company_a, role="manager")
    worker_b = _member(db, company_b)
    log_b = make_work_log(db, worker_b, company_b)
    as_user(client, manager_a, company_a, claims=MANAGER_CLAIMS)

    resp = client.delete(f"/work-logs/{log_b.id}")

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS
    assert _stored(db, log_b.id) is not None
