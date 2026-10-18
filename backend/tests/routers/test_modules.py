"""
Pruebas HTTP de GET /modules/me (PR-03): modulos personales, de la empresa activa y del
platform admin, y acceso a una empresa explicita.

Los casos marcados con `# PR-03:` describen un comportamiento que cambia respecto a la
expectativa anterior.
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
        scope=models.SubscriptionScope.company,
        status=models.SubscriptionStatus.active,
        expires_at=None,
    )
    db.add(sub)
    db.commit()
    return sub


def _subscribe_user(db, module, user):
    sub = models.ModuleSubscription(
        module_id=module.id,
        user_id=user.id,
        scope=models.SubscriptionScope.user,
        status=models.SubscriptionStatus.active,
        expires_at=None,
    )
    db.add(sub)
    db.commit()
    return sub


def _codes(resp):
    return {item["codeName"] for item in resp.json()}


def _setup(db):
    # Modulos: dos activos y uno inactivo
    module_active_1 = _module(db, "module_active_1", "Active Module 1")
    module_active_2 = _module(db, "module_active_2", "Active Module 2")
    module_inactive = _module(db, "module_inactive", "Inactive Module", is_active=False)

    # Dos empresas
    company_a = make_company(db)
    company_b = make_company(db)

    # Platform admin (users.role = admin en BD) y usuario normal
    admin = make_user(db, role="admin")
    user = make_user(db)

    # El usuario es worker en la empresa A
    membership_a = make_member(db, user, company_a, role="worker")

    # Empresa A -> modulo 1; empresa B -> modulo 2; usuario -> modulo 2 personal
    _subscribe_company(db, module_active_1, company_a)
    _subscribe_company(db, module_active_2, company_b)
    _subscribe_user(db, module_active_2, user)

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
    """
    Regular user without active_company_id or company_id query parameter
    should only get their personal active subscriptions.
    """
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    assert s["module_active_2"].code_name in module_codes
    assert s["module_active_1"].code_name not in module_codes


def test_regular_user_active_company_id_context(client, db):
    """
    Regular user with active_company_id should get personal + active company modules.
    """
    s = _setup(db)
    as_user(client, s["user"], s["company_a"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    assert s["module_active_1"].code_name in module_codes
    assert s["module_active_2"].code_name in module_codes


def test_regular_user_explicit_company_id_context(client, db):
    """
    Regular user with explicit company_id parameter should get personal + explicit company modules.
    """
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_a"].id)})

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    assert s["module_active_1"].code_name in module_codes
    assert s["module_active_2"].code_name in module_codes


def test_regular_user_explicit_company_id_not_member(client, db):
    """
    Regular user requesting a company they are not a member of should receive 403.
    """
    s = _setup(db)
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_b"].id)})

    assert resp.status_code == 403, resp.text
    # PR-03: empresa sin membresia -> 403 con el mensaje de access_policy (antes "No autorizado.").
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_regular_user_explicit_company_id_inactive_member(client, db):
    """
    Regular user requesting a company where their membership is inactive should receive 403.
    """
    s = _setup(db)
    s["membership_a"].is_active = False
    db.commit()
    as_user(client, s["user"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_a"].id)})

    assert resp.status_code == 403, resp.text


def test_platform_admin_no_company_context(client, db):
    """
    Platform admin with no company context should get all active modules in the catalog.
    """
    s = _setup(db)
    as_user(client, s["admin"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    # Inactive modules should not be returned
    assert s["module_inactive"].code_name not in module_codes
    # But both active modules should be returned
    assert s["module_active_1"].code_name in module_codes
    assert s["module_active_2"].code_name in module_codes


def test_platform_admin_with_active_company_id_context(client, db):
    """
    Platform admin with active_company_id set should get only modules subscribed by that company.
    """
    s = _setup(db)
    as_user(client, s["admin"], s["company_a"])

    resp = client.get("/modules/me")

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    assert s["module_active_1"].code_name in module_codes
    assert s["module_active_2"].code_name not in module_codes


def test_platform_admin_with_explicit_company_id_context(client, db):
    """
    Platform admin with explicit company_id parameter should get only modules subscribed by that company.
    """
    s = _setup(db)
    as_user(client, s["admin"])

    resp = client.get("/modules/me", params={"company_id": str(s["company_b"].id)})

    assert resp.status_code == 200, resp.text
    module_codes = _codes(resp)
    assert s["module_active_2"].code_name in module_codes
    assert s["module_active_1"].code_name not in module_codes
