"""
Pruebas HTTP de GET /modules/me (R-MOD-16, R-MOD-17):
- Sin empresa activa (usuario normal o PA sin contexto), devuelve [].
- Con empresa activa (token o parametro explicito), devuelve solo los modulos vigentes de esa empresa.
"""

import uuid

import models

from tests.factories import as_user, make_company, make_member, make_user

MSG_NO_ACCESS = "No tienes acceso a esta empresa"


def _module(db, prefix: str, name: str, is_active: bool = True) -> models.AppModule:
    module = models.AppModule(code_name=f"{prefix}_{uuid.uuid4().hex[:6]}", name=name, is_active=is_active)
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _subscribe_company(db, module, company):
    sub = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=models.SubscriptionStatus.active,
        expires_at=None,
    )
    db.add(sub)
    db.commit()
    return sub


def _codes(resp):
    return {item["codeName"] for item in resp.json()}


def _setup(db):
    module_active_1 = _module(db, "module_active_1", "Active Module 1")
    module_active_2 = _module(db, "module_active_2", "Active Module 2")
    module_inactive = _module(db, "module_inactive", "Inactive Module", is_active=False)

    company_a = make_company(db)
    company_b = make_company(db)

    admin = make_user(db, role="admin")
    user = make_user(db)

    membership_a = make_member(db, user, company_a, role="worker")

    _subscribe_company(db, module_active_1, company_a)
    _subscribe_company(db, module_active_2, company_b)
    _subscribe_company(db, module_inactive, company_a)

    return {
        "module_active_1": module_active_1,
        "module_active_2": module_active_2,
        "module_inactive": module_inactive,
        "company_a": company_a,
        "company_b": company_b,
        "admin": admin,
        "user": user,
        "membership_a": membership_a,
    }


def test_regular_user_no_company_context(client, db):
    """Un usuario normal sin empresa activa ni parametro company_id recibe lista vacia (R-MOD-16, R-MOD-17)."""
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_regular_user_active_company_id_context(client, db):
    """Con empresa activa en el token recibe solo los modulos activos suscritos por esa empresa."""
    s = _setup(db)
    as_user(client, s["user"], s["company_a"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    assert _codes(resp) == {s["module_active_1"].code_name}


def test_regular_user_explicit_company_id_context(client, db):
    """Con parametro company_id explicito de una empresa donde es miembro recibe los modulos de esa empresa."""
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_a"].id)})

    assert resp.status_code == 200, resp.text
    assert _codes(resp) == {s["module_active_1"].code_name}


def test_regular_user_explicit_company_id_not_member(client, db):
    """Pedir company_id de una empresa sin membresia responde 403."""
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_b"].id)})

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_regular_user_explicit_company_id_inactive_member(client, db):
    """Pedir company_id de una empresa con membresia inactiva responde 403."""
    s = _setup(db)
    s["membership_a"].is_active = False
    db.commit()
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_a"].id)})

    assert resp.status_code == 403, resp.text


def test_platform_admin_no_company_context(client, db):
    """Un PA sin empresa en contexto recibe lista vacia (R-MOD-16)."""
    s = _setup(db)
    as_user(client, s["admin"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    assert resp.json() == []


def test_platform_admin_with_active_company_id_context(client, db):
    """Un PA con active_company_id recibe solo los modulos activos suscritos por esa empresa."""
    s = _setup(db)
    as_user(client, s["admin"], s["company_a"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    assert _codes(resp) == {s["module_active_1"].code_name}


def test_platform_admin_with_explicit_company_id_context(client, db):
    """Un PA con parametro company_id explicito recibe solo los modulos activos suscritos por esa empresa."""
    s = _setup(db)
    as_user(client, s["admin"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_b"].id)})

    assert resp.status_code == 200, resp.text
    assert _codes(resp) == {s["module_active_2"].code_name}
