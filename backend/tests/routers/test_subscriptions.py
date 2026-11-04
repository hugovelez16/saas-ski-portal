"""
Pruebas HTTP de validacion de suscripciones y modulos (PR-14, items B3 y B4 del catalogo):
esquemas cerrados, coherencia scope/company_id/user_id, compatibilidad con el target_scope
del modulo y 409 en altas duplicadas activas/trial [P-15].
"""

import uuid

import crud
import models

from tests.factories import as_user, make_company, make_user

PA_CLAIMS = {"is_admin": True}
MSG_DUPLICATE_COMPANY = "La empresa ya tiene este modulo activo"


def _module(db, target_scope: str = "both") -> models.AppModule:
    module = models.AppModule(
        code_name=f"mod_{uuid.uuid4().hex[:6]}", name="Modulo", is_active=True, target_scope=target_scope
    )
    db.add(module)
    db.commit()
    db.refresh(module)
    return module


def _pa(client, db):
    pa = make_user(db, role="admin")
    as_user(client, pa, claims=PA_CLAIMS)
    return pa


def _payload(module, **overrides) -> dict:
    data = {"moduleId": str(module.id), "scope": "company", "status": "active"}
    data.update(overrides)
    return data


def _existing(db, module, *, company=None, user=None, status="active"):
    sub = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id if company else None,
        user_id=user.id if user else None,
        scope=models.SubscriptionScope.company if company else models.SubscriptionScope.user,
        status=models.SubscriptionStatus(status),
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


def test_create_company_subscription_ok(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id)))

    assert resp.status_code == 200, resp.text
    assert resp.json()["scope"] == "company"


def test_create_user_subscription_ok(client, db):
    _pa(client, db)
    module, user = _module(db), make_user(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, scope="user", userId=str(user.id)))

    assert resp.status_code == 200, resp.text


def test_invalid_scope_is_422(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, scope="otra", companyId=str(company.id)))

    assert resp.status_code == 422


def test_invalid_status_is_422(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, status="otro", companyId=str(company.id)))

    assert resp.status_code == 422


def test_company_scope_without_company_id_is_422(client, db):
    _pa(client, db)
    module = _module(db)

    resp = client.post("/modules/subscriptions", json=_payload(module))

    assert resp.status_code == 422


def test_user_scope_without_user_id_is_422(client, db):
    _pa(client, db)
    module = _module(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, scope="user"))

    assert resp.status_code == 422


def test_company_scope_with_user_id_is_422(client, db):
    _pa(client, db)
    module, company, user = _module(db), make_company(db), make_user(db)

    resp = client.post(
        "/modules/subscriptions", json=_payload(module, companyId=str(company.id), userId=str(user.id))
    )

    assert resp.status_code == 422


def test_user_scope_with_company_id_is_422(client, db):
    _pa(client, db)
    module, company, user = _module(db), make_company(db), make_user(db)

    resp = client.post(
        "/modules/subscriptions", json=_payload(module, scope="user", companyId=str(company.id), userId=str(user.id))
    )

    assert resp.status_code == 422


def test_company_only_module_rejects_user_subscription(client, db):
    _pa(client, db)
    module, user = _module(db, target_scope="company"), make_user(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, scope="user", userId=str(user.id)))

    assert resp.status_code == 422


def test_user_only_module_rejects_company_subscription(client, db):
    _pa(client, db)
    module, company = _module(db, target_scope="user"), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id)))

    assert resp.status_code == 422


def test_duplicate_active_company_subscription_is_409(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    _existing(db, module, company=company, status="active")

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id)))

    assert resp.status_code == 409
    assert resp.json()["detail"] == MSG_DUPLICATE_COMPANY


def test_duplicate_trial_company_subscription_is_409(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    _existing(db, module, company=company, status="trial")

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id), status="trial"))

    assert resp.status_code == 409


def test_duplicate_active_user_subscription_is_409(client, db):
    _pa(client, db)
    module, user = _module(db), make_user(db)
    _existing(db, module, user=user, status="active")

    resp = client.post("/modules/subscriptions", json=_payload(module, scope="user", userId=str(user.id)))

    assert resp.status_code == 409


def test_cancelled_subscription_does_not_block_new_one(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    _existing(db, module, company=company, status="cancelled")

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id)))

    assert resp.status_code == 200, resp.text


def test_same_module_other_company_is_not_duplicate(client, db):
    _pa(client, db)
    module, company, other = _module(db), make_company(db), make_company(db)
    _existing(db, module, company=company, status="active")

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(other.id)))

    assert resp.status_code == 200, resp.text


def test_update_with_invalid_status_is_422(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    sub = _existing(db, module, company=company)

    resp = client.put(f"/modules/subscriptions/{sub.id}", json={"status": "otro"})

    assert resp.status_code == 422


def test_update_with_valid_status_ok(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    sub = _existing(db, module, company=company)

    resp = client.put(f"/modules/subscriptions/{sub.id}", json={"status": "cancelled"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"


def test_reactivating_cancelled_duplicate_is_409(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    _existing(db, module, company=company, status="active")
    cancelled = _existing(db, module, company=company, status="cancelled")

    resp = client.put(f"/modules/subscriptions/{cancelled.id}", json={"status": "active"})

    assert resp.status_code == 409


def test_module_create_with_invalid_target_scope_is_422(client, db):
    _pa(client, db)

    resp = client.post("/modules", json={"codeName": "x_mod", "name": "X", "targetScope": "otro"})

    assert resp.status_code == 422


def test_module_update_with_invalid_target_scope_is_422(client, db):
    _pa(client, db)
    module = _module(db)

    resp = client.put(f"/modules/{module.id}", json={"targetScope": "otro"})

    assert resp.status_code == 422


def test_crud_get_subscriptions_is_removed():
    assert not hasattr(crud, "get_subscriptions")
