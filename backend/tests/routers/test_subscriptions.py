"""
Pruebas HTTP de catalogo de modulos y suscripciones solo de empresa (R-MOD-05, R-MOD-09, R-MOD-12, R-MOD-17, R-MOD-18).
"""

import uuid

import crud
import models

from tests.factories import as_user, make_company, make_user

PA_CLAIMS = {"is_admin": True}
MSG_DUPLICATE_COMPANY = "La empresa ya tiene este modulo activo"


def _module(db, *, is_active: bool = True) -> models.AppModule:
    module = models.AppModule(
        code_name=f"mod_{uuid.uuid4().hex[:6]}",
        name="Modulo",
        is_active=is_active,
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
    data = {"moduleId": str(module.id), "status": "active"}
    data.update(overrides)
    return data


def _existing(db, module, *, company, status="active"):
    sub = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
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
    body = resp.json()
    assert body["companyId"] == str(company.id)
    assert "scope" not in body
    assert "userId" not in body


def test_module_response_omits_target_scope_and_price_monthly(client, db):
    _pa(client, db)
    module = _module(db)

    resp = client.get(f"/modules/{module.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert "targetScope" not in body
    assert "priceMonthly" not in body


def test_create_subscription_for_inactive_module_returns_4xx(client, db):
    """R-MOD-05: no se puede suscribir un modulo con is_active = false."""
    _pa(client, db)
    module, company = _module(db, is_active=False), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, companyId=str(company.id)))

    assert 400 <= resp.status_code < 500, resp.text
    assert db.query(models.ModuleSubscription).filter_by(module_id=module.id, company_id=company.id).count() == 0


def test_reactivate_subscription_for_inactive_module_returns_4xx(client, db):
    """R-MOD-05: no se puede reactivar una suscripcion si su modulo esta inactivo."""
    _pa(client, db)
    module, company = _module(db, is_active=True), make_company(db)
    sub = _existing(db, module, company=company, status="cancelled")
    module.is_active = False
    db.commit()

    resp = client.put(f"/modules/subscriptions/{sub.id}", json={"status": "active"})

    assert 400 <= resp.status_code < 500, resp.text
    db.refresh(sub)
    assert sub.status == models.SubscriptionStatus.cancelled


def test_invalid_status_is_422(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)

    resp = client.post("/modules/subscriptions", json=_payload(module, status="otro", companyId=str(company.id)))

    assert resp.status_code == 422


def test_company_subscription_without_company_id_is_422(client, db):
    _pa(client, db)
    module = _module(db)

    resp = client.post("/modules/subscriptions", json=_payload(module))

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


def test_cancel_subscription_keeps_row_with_cancelled_status(client, db):
    """R-MOD-09: cancelar pasa la suscripcion a cancelled y conserva la fila en BD."""
    _pa(client, db)
    module, company = _module(db), make_company(db)
    sub = _existing(db, module, company=company)

    resp = client.put(f"/modules/subscriptions/{sub.id}", json={"status": "cancelled"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["status"] == "cancelled"
    row = db.query(models.ModuleSubscription).filter_by(id=sub.id).first()
    assert row is not None
    assert row.status == models.SubscriptionStatus.cancelled


def test_delete_subscription_endpoint_is_removed(client, db):
    """R-MOD-09: el borrado fisico DELETE de suscripciones ya no existe en v1 ni en /v2/admin."""
    _pa(client, db)
    module, company = _module(db), make_company(db)
    sub = _existing(db, module, company=company)

    resp_v1 = client.delete(f"/modules/subscriptions/{sub.id}")
    resp_v2 = client.delete(f"/v2/admin/modules/subscriptions/{sub.id}")

    assert resp_v1.status_code == 405
    assert resp_v2.status_code == 405
    assert db.query(models.ModuleSubscription).filter_by(id=sub.id).first() is not None


def test_reactivating_cancelled_duplicate_is_409(client, db):
    _pa(client, db)
    module, company = _module(db), make_company(db)
    _existing(db, module, company=company, status="active")
    cancelled = _existing(db, module, company=company, status="cancelled")

    resp = client.put(f"/modules/subscriptions/{cancelled.id}", json={"status": "active"})

    assert resp.status_code == 409


def test_crud_removed_functions_and_enum():
    assert not hasattr(crud, "get_subscriptions")
    assert not hasattr(crud, "delete_subscription")
    assert not hasattr(models, "SubscriptionScope")
