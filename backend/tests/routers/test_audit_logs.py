"""
Pruebas HTTP de la consulta de logs de auditoria (PR-15): acceso solo PA, filtros, orden,
paginacion y catalogo de acciones.
"""

import uuid
from datetime import datetime, timedelta

import audit
import models

from tests.factories import as_user, make_company, make_member, make_user

BASE = datetime(2026, 3, 10, 12, 0, 0)


def _log(db, *, action="company.updated", actor=None, company=None, target=None, minutes=0, **kwargs):
    row = models.AuditLog(
        action=action,
        actor_user_id=actor.id if actor else None,
        admin_user_id=actor.id if actor else None,
        company_id=company.id if company else None,
        target_user_id=target.id if target else None,
        created_at=BASE + timedelta(minutes=minutes),
        **kwargs,
    )
    db.add(row)
    db.commit()
    return row


def _pa(client, db, **claims):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims={"is_admin": True, **claims})
    return pa


# --- Acceso ---


def test_audit_logs_without_token_is_401(client):
    client.cookies.clear()
    assert client.get("/audit-logs").status_code == 401
    assert client.get("/audit-logs/actions").status_code == 401


def test_audit_logs_manager_and_worker_are_403(client, db):
    company = make_company(db)
    manager = make_user(db)
    worker = make_user(db)
    make_member(db, manager, company, role="manager")
    make_member(db, worker, company, role="worker")

    for user, role in ((manager, "manager"), (worker, "worker")):
        as_user(client, user, company, claims={"role": role})
        assert client.get("/audit-logs").status_code == 403
        assert client.get("/audit-logs/actions").status_code == 403


def test_audit_logs_pa_in_view_as_is_403(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    for view_as in ("worker", "manager"):
        as_user(client, pa, company, claims={"is_admin": True, "view_as": view_as})
        assert client.get("/audit-logs").status_code == 403
        assert client.get("/audit-logs/actions").status_code == 403


def test_audit_logs_pa_gets_200(client, db):
    _pa(client, db)
    resp = client.get("/audit-logs")
    assert resp.status_code == 200, resp.text
    assert resp.json() == {"total": 0, "items": []}


# --- Contenido, orden y filtros ---


def test_audit_logs_item_shape_and_order_desc(client, db):
    pa = _pa(client, db)
    company = make_company(db)
    target = make_user(db)
    old = _log(db, actor=pa, company=company, target=target, minutes=0, old_value={"role": "worker"})
    new = _log(
        db,
        action="member.role_changed",
        actor=pa,
        company=company,
        target=target,
        minutes=5,
        old_value={"role": "worker"},
        new_value={"role": "manager"},
        reason="promocion",
        extra_data={"k": "v"},
    )

    body = client.get("/audit-logs").json()

    assert body["total"] == 2
    assert [i["id"] for i in body["items"]] == [str(new.id), str(old.id)]
    item = body["items"][0]
    assert set(item) == {
        "id",
        "action",
        "createdAt",
        "actorUserId",
        "actorEmail",
        "companyId",
        "targetUserId",
        "oldValue",
        "newValue",
        "reason",
        "extraData",
    }
    assert item["action"] == "member.role_changed"
    assert item["actorUserId"] == str(pa.id)
    assert item["actorEmail"] == pa.email
    assert item["companyId"] == str(company.id)
    assert item["targetUserId"] == str(target.id)
    assert item["newValue"] == {"role": "manager"}
    assert item["reason"] == "promocion"
    assert item["extraData"] == {"k": "v"}


def test_audit_logs_response_has_no_snake_case_keys(client, db):
    pa = _pa(client, db)
    _log(db, actor=pa)
    item = client.get("/audit-logs").json()["items"][0]
    assert not [k for k in item if "_" in k]


def test_audit_logs_filter_by_company(client, db):
    pa = _pa(client, db)
    a, b = make_company(db), make_company(db)
    row_a = _log(db, actor=pa, company=a)
    _log(db, actor=pa, company=b)

    body = client.get("/audit-logs", params={"company_id": str(a.id)}).json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == str(row_a.id)


def test_audit_logs_filter_by_actor_and_target(client, db):
    pa = _pa(client, db)
    other = make_user(db, role="admin")
    target = make_user(db)
    row = _log(db, actor=pa, target=target)
    _log(db, actor=other)

    by_actor = client.get("/audit-logs", params={"actor_user_id": str(pa.id)}).json()
    by_target = client.get("/audit-logs", params={"target_user_id": str(target.id)}).json()

    assert [i["id"] for i in by_actor["items"]] == [str(row.id)]
    assert [i["id"] for i in by_target["items"]] == [str(row.id)]


def test_audit_logs_filter_by_action_is_exact(client, db):
    pa = _pa(client, db)
    exact = _log(db, action="member.added", actor=pa)
    _log(db, action="member.added.extra", actor=pa)
    _log(db, action="member", actor=pa)

    body = client.get("/audit-logs", params={"action": "member.added"}).json()

    assert body["total"] == 1
    assert body["items"][0]["id"] == str(exact.id)


def test_audit_logs_filter_by_date_range(client, db):
    pa = _pa(client, db)
    _log(db, actor=pa, minutes=0)
    mid = _log(db, actor=pa, minutes=60)
    _log(db, actor=pa, minutes=120)

    params = {
        "from": (BASE + timedelta(minutes=30)).isoformat(),
        "to": (BASE + timedelta(minutes=90)).isoformat(),
    }
    body = client.get("/audit-logs", params=params).json()

    assert [i["id"] for i in body["items"]] == [str(mid.id)]


def test_audit_logs_from_after_to_is_422(client, db):
    _pa(client, db)
    params = {"from": "2026-03-11T00:00:00", "to": "2026-03-10T00:00:00"}
    assert client.get("/audit-logs", params=params).status_code == 422


def test_audit_logs_mixed_timezone_dates_do_not_fail(client, db):
    pa = _pa(client, db)
    row = _log(db, actor=pa, minutes=0)

    params = {"from": "2026-03-10T11:00:00Z", "to": "2026-03-10T13:00:00"}
    body = client.get("/audit-logs", params=params)

    assert body.status_code == 200, body.text
    assert [i["id"] for i in body.json()["items"]] == [str(row.id)]


def test_audit_logs_invalid_uuid_is_422(client, db):
    _pa(client, db)
    assert client.get("/audit-logs", params={"company_id": "no-es-uuid"}).status_code == 422


# --- Paginacion ---


def test_audit_logs_pagination_total_is_filtered_set(client, db):
    pa = _pa(client, db)
    company = make_company(db)
    for i in range(5):
        _log(db, actor=pa, company=company, minutes=i)
    _log(db, actor=pa, minutes=10)

    page = client.get("/audit-logs", params={"company_id": str(company.id), "limit": 2, "offset": 2}).json()

    assert page["total"] == 5
    assert len(page["items"]) == 2


def test_audit_logs_default_limit_is_50(client, db):
    pa = _pa(client, db)
    for i in range(55):
        db.add(models.AuditLog(action="company.updated", actor_user_id=pa.id, created_at=BASE + timedelta(minutes=i)))
    db.commit()

    body = client.get("/audit-logs").json()

    assert body["total"] == 55
    assert len(body["items"]) == 50


def test_audit_logs_limit_bounds(client, db):
    _pa(client, db)
    assert client.get("/audit-logs", params={"limit": 0}).status_code == 422
    assert client.get("/audit-logs", params={"limit": 201}).status_code == 422
    assert client.get("/audit-logs", params={"limit": 200}).status_code == 200
    assert client.get("/audit-logs", params={"limit": 1}).status_code == 200
    assert client.get("/audit-logs", params={"offset": -1}).status_code == 422
    assert client.get("/audit-logs", params={"offset": 2**40}).status_code == 422
    assert client.get("/audit-logs", params={"action": "x" * 101}).status_code == 422


# --- Eventos antiguos ---


def test_audit_logs_includes_legacy_2fa_reset_with_actor(client, db):
    pa = _pa(client, db)
    victim = make_user(db)
    row = models.AuditLog(
        action="2fa_reset",
        impersonated_user_id=victim.id,
        admin_user_id=pa.id,
        actor_user_id=pa.id,
        extra_data={"target_email": victim.email},
        created_at=BASE,
    )
    db.add(row)
    db.commit()

    body = client.get("/audit-logs", params={"action": "2fa_reset"}).json()

    assert body["total"] == 1
    assert body["items"][0]["actorUserId"] == str(pa.id)
    assert body["items"][0]["companyId"] is None


def test_audit_logs_legacy_row_without_actor_has_null_email(client, db):
    _pa(client, db)
    db.add(models.AuditLog(action="2fa_reset", created_at=BASE))
    db.commit()

    item = client.get("/audit-logs").json()["items"][0]

    assert item["actorUserId"] is None
    assert item["actorEmail"] is None


def test_audit_logs_survive_deleted_company(client, db):
    pa = _pa(client, db)
    gone = uuid.uuid4()
    db.add(models.AuditLog(action="company.deleted", actor_user_id=pa.id, company_id=gone, created_at=BASE))
    db.commit()

    body = client.get("/audit-logs", params={"company_id": str(gone)}).json()

    assert body["total"] == 1


# --- Catalogo ---


def test_audit_actions_catalog(client, db):
    _pa(client, db)

    resp = client.get("/audit-logs/actions")

    assert resp.status_code == 200
    actions = resp.json()
    assert {"company.updated", "member.added", "user.status_changed", "2fa_reset", "delete_work_log"} <= set(actions)
    assert {"create_work_log", "create_work_log_bulk", "update_work_log"} <= set(actions)
    assert all(v in actions for k, v in vars(audit.AuditAction).items() if k.isupper() and isinstance(v, str))
    assert len(actions) == len(set(actions))
