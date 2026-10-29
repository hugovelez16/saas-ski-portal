"""
Pruebas HTTP de la vista reducida de empresa en `/modules/subscriptions` (PR-13, P7).

Las vistas de empresa de v1 (`/users/me/companies`, `/companies/{id}`, `/companies/detailed` y
`/users/{id}/companies`) se retiran en PR-21.0; sus casos viven en tests/routers/v2/test_v2_companies.py.
"""

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}

FORBIDDEN_FRAGMENTS = ("costMarkup", "cost_markup", "allowedRates", "allowed_rates")
RATES = {"particular": {"base_rate": 31.5, "is_gross": False, "tax_overrides": {}}}
TAX_CONFIG = {"social_security": 0.0648}
DEFINITIONS = {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
COMPANY_SETTINGS = {
    "business_logic": {"price_type": "gross"},
    "worker_experience": {"input_mode": "timer", "allow_manual_amount": True},
    "modules": {"daily_report": True},
    "allowed_rates": ["particular"],
}


@pytest.fixture()
def world(db):
    company = make_company(db, tax_config=TAX_CONFIG, worklog_definitions=DEFINITIONS, settings=COMPANY_SETTINGS)
    pa = make_user(db, role="admin")
    manager = make_user(db)
    worker = make_user(db)
    make_member(db, manager, company, role="manager", rates_config=RATES)
    make_member(db, worker, company, role="worker", rates_config=RATES)
    return type("World", (), {"company": company, "pa": pa, "manager": manager, "worker": worker})()


def _assert_no_leak(text):
    for fragment in FORBIDDEN_FRAGMENTS:
        assert fragment not in text, fragment


# --- GET /modules/subscriptions ---


def test_subscriptions_manager_gets_brief_company(client, db, world):
    module = models.AppModule(code_name="mod_views", name="Modulo", is_active=True, target_scope="both")
    db.add(module)
    db.commit()
    db.add(
        models.ModuleSubscription(
            module_id=module.id,
            company_id=world.company.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus("active"),
        )
    )
    db.commit()

    as_user(client, world.manager, world.company, claims=MANAGER_CLAIMS)
    resp = client.get("/modules/subscriptions")
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    assert set(resp.json()[0]["company"]) == {"id", "name"}
    _assert_no_leak(resp.text)

    as_user(client, world.pa, claims=PA_CLAIMS)
    resp = client.get("/modules/subscriptions")
    assert resp.status_code == 200, resp.text
    assert resp.json()[0]["company"]["isActive"] is True
