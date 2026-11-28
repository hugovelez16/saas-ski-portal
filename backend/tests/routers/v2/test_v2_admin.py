"""Pruebas HTTP de la API centralizada de administracion `/v2/admin/...` (R-ACC-25, R-ACC-26, R-ACC-61, R-ACC-69)."""

import uuid

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user


@pytest.fixture
def world(db):
    pa = make_user(db, role="admin")
    company = make_company(db, name="Escuela Admin")
    manager = make_user(db)
    worker = make_user(db)
    make_member(db, manager, company, role="manager")
    make_member(db, worker, company, role="worker")
    return type("World", (), {"pa": pa, "company": company, "manager": manager, "worker": worker})()


@pytest.mark.parametrize(
    "method, path_fn",
    [
        ("GET", lambda w: "/v2/admin/companies"),
        ("POST", lambda w: "/v2/admin/companies"),
        ("GET", lambda w: f"/v2/admin/companies/{w.company.id}"),
        ("PUT", lambda w: f"/v2/admin/companies/{w.company.id}"),
        ("DELETE", lambda w: f"/v2/admin/companies/{w.company.id}"),
        ("GET", lambda w: f"/v2/admin/companies/{w.company.id}/members"),
        ("POST", lambda w: f"/v2/admin/companies/{w.company.id}/members"),
        ("GET", lambda w: "/v2/admin/users"),
        ("POST", lambda w: "/v2/admin/users"),
        ("GET", lambda w: f"/v2/admin/users/{w.worker.id}/companies"),
        ("POST", lambda w: f"/v2/admin/impersonate/{w.worker.id}"),
        ("GET", lambda w: "/v2/admin/modules"),
        ("GET", lambda w: "/v2/admin/modules/subscriptions"),
        ("GET", lambda w: "/v2/admin/audit-logs"),
        ("GET", lambda w: "/v2/admin/audit-logs/actions"),
    ],
)
@pytest.mark.parametrize("actor", ["worker", "manager", "pa_view_as_manager"])
def test_v2_admin_router_rejects_non_acting_pa_with_403(client, world, method, path_fn, actor):
    if actor == "worker":
        as_user(client, world.worker, world.company)
    elif actor == "manager":
        as_user(client, world.manager, world.company)
    else:
        as_user(client, world.pa, world.company, claims={"view_as": "manager"})

    resp = client.request(method, path_fn(world))

    assert resp.status_code == 403, resp.text


def test_v2_admin_router_requires_auth(client, world):
    client.cookies.clear()
    assert client.get("/v2/admin/companies").status_code == 401


def test_v2_admin_companies_returns_full_view_and_404_on_missing(client, world):
    as_user(client, world.pa)

    detail = client.get(f"/v2/admin/companies/{world.company.id}")
    missing = client.get(f"/v2/admin/companies/{uuid.uuid4()}")

    assert detail.status_code == 200, detail.text
    assert "is_active" in detail.json()
    assert missing.status_code == 404, missing.text


def test_v2_admin_add_member_rejects_platform_admin_with_422(client, db, world):
    as_user(client, world.pa)

    resp = client.post(f"/v2/admin/companies/{world.company.id}/members", json={"email": world.pa.email})

    assert resp.status_code == 422, resp.text
    assert db.query(models.CompanyMember).filter_by(user_id=world.pa.id).count() == 0


@pytest.mark.parametrize("bad_domain", ["user@demo.invalid", "user@demo.test", "user@demo.local"])
def test_reserved_email_domains_rejected_with_422(client, world, bad_domain):
    as_user(client, world.pa)

    create_user_resp = client.post(
        "/v2/admin/users",
        json={"email": bad_domain, "firstName": "Demo", "lastName": "User", "sendEmail": False},
    )
    add_member_resp = client.post(
        f"/v2/admin/companies/{world.company.id}/members",
        json={"email": bad_domain},
    )

    assert create_user_resp.status_code == 422, create_user_resp.text
    assert add_member_resp.status_code == 422, add_member_resp.text


def test_v2_admin_impersonate_and_audit_logs_work_for_pa(client, world):
    as_user(client, world.pa)

    imp = client.post(f"/v2/admin/impersonate/{world.worker.id}")
    logs = client.get("/v2/admin/audit-logs")

    assert imp.status_code == 200, imp.text
    assert logs.status_code == 200, logs.text
