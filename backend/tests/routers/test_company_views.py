"""
Pruebas HTTP de las vistas reducida y completa de empresa en v1 (PR-13, P7, P8).

Vista reducida (worker, manager y PA en "ver como"): conjunto EXACTO de claves, sin `isActive`,
`createdAt`/`updatedAt`, `settings.business_logic.costMarkup`, `allowedRates` ni `fiscalId`.
Vista completa: solo el platform admin actuando.
"""

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}

REDUCED_KEYS = {
    "id",
    "name",
    "isManaged",
    "role",
    "isActiveMember",
    "ratesConfig",
    "worklogDefinitions",
    "taxConfig",
    "settings",
}
REDUCED_SETTINGS_KEYS = {"worker_experience", "ui_customization", "modules", "business_logic"}
FISCAL_ID = "B12345678"
RATES = {"particular": {"base_rate": 31.5, "is_gross": False, "tax_overrides": {}}}
TAX_CONFIG = {"social_security": 0.0648}
DEFINITIONS = {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
COMPANY_SETTINGS = {
    "business_logic": {"price_type": "gross"},
    "worker_experience": {"input_mode": "timer", "allow_manual_amount": True},
    "modules": {"daily_report": True},
    "allowed_rates": ["particular"],
}
FORBIDDEN_FRAGMENTS = ("costMarkup", "cost_markup", "allowedRates", "allowed_rates", "fiscal", FISCAL_ID)


@pytest.fixture()
def world(db):
    company = make_company(db, tax_config=TAX_CONFIG, worklog_definitions=DEFINITIONS, settings=COMPANY_SETTINGS)
    company.fiscal_id = FISCAL_ID
    db.commit()
    pa = make_user(db, role="admin")
    manager = make_user(db)
    worker = make_user(db)
    make_member(db, manager, company, role="manager", rates_config=RATES)
    make_member(db, worker, company, role="worker", rates_config=RATES)
    return type("World", (), {"company": company, "pa": pa, "manager": manager, "worker": worker})()


def _assert_reduced(entry, company, role):
    assert set(entry) == REDUCED_KEYS, sorted(entry)
    assert entry["id"] == str(company.id)
    assert entry["name"] == company.name
    assert entry["isManaged"] is False
    assert entry["role"] == role
    assert entry["isActiveMember"] is True
    assert entry["ratesConfig"] == RATES
    assert entry["worklogDefinitions"] == DEFINITIONS
    assert entry["taxConfig"] == TAX_CONFIG
    settings = entry["settings"]
    assert set(settings) == REDUCED_SETTINGS_KEYS, sorted(settings)
    assert settings["business_logic"] == {"price_type": "gross"}
    assert settings["worker_experience"] == {"input_mode": "timer", "allow_manual_amount": True}
    assert settings["modules"] == {"daily_report": True}


def _assert_no_leak(text):
    for fragment in FORBIDDEN_FRAGMENTS:
        assert fragment not in text, fragment


# --- GET /users/me/companies ---


@pytest.mark.parametrize("who, claims, role", [("worker", WORKER_CLAIMS, "worker"), ("manager", MANAGER_CLAIMS, "manager")])
def test_me_companies_reduced_for_member(client, world, who, claims, role):
    as_user(client, getattr(world, who), world.company, claims=claims)

    resp = client.get("/users/me/companies")

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    _assert_reduced(resp.json()[0], world.company, role)
    _assert_no_leak(resp.text)


def test_member_settings_only_pass_whitelist(client, db, world):
    member = db.query(models.CompanyMember).filter_by(user_id=world.worker.id).one()
    member.settings = {
        "ui_preferences": {"theme": "dark"},
        "business_logic": {"price_type": "net"},
        "allowed_rates": ["hack"],
    }
    db.commit()
    as_user(client, world.worker, world.company, claims=WORKER_CLAIMS)

    for url in ("/users/me/companies", f"/companies/{world.company.id}"):
        body = client.get(url).json()
        settings = (body[0] if isinstance(body, list) else body)["settings"]
        assert settings["ui_preferences"] == {"theme": "dark"}
        assert settings["business_logic"] == {"price_type": "gross"}, url
        assert "allowed_rates" not in settings, url


def test_me_companies_pa_acting_gets_full_view(client, world):
    as_user(client, world.pa, claims=PA_CLAIMS)

    resp = client.get("/users/me/companies")

    assert resp.status_code == 200, resp.text
    entry = {item["id"]: item for item in resp.json()}[str(world.company.id)]
    assert entry["isActive"] is True
    assert entry["isManaged"] is False
    assert entry["settings"]["allowed_rates"] == ["particular"]
    assert "fiscalId" not in entry


def test_me_companies_pa_view_as_gets_reduced_view(client, db, world):
    make_member(db, world.pa, world.company, role="manager", rates_config=RATES)
    as_user(client, world.pa, world.company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get("/users/me/companies")

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    _assert_reduced(resp.json()[0], world.company, "manager")
    _assert_no_leak(resp.text)


# --- GET /companies/{id} ---


def test_company_detail_pa_gets_full_view(client, world):
    as_user(client, world.pa, world.company, claims=PA_CLAIMS)

    resp = client.get(f"/companies/{world.company.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["isActive"] is True
    assert body["settings"]["allowed_rates"] == ["particular"]
    assert "fiscalId" not in body


@pytest.mark.parametrize("who, claims, role", [("worker", WORKER_CLAIMS, "worker"), ("manager", MANAGER_CLAIMS, "manager")])
def test_company_detail_reduced_for_member(client, world, who, claims, role):
    as_user(client, getattr(world, who), world.company, claims=claims)

    resp = client.get(f"/companies/{world.company.id}")

    assert resp.status_code == 200, resp.text
    _assert_reduced(resp.json(), world.company, role)
    _assert_no_leak(resp.text)


def test_company_detail_pa_view_as_gets_reduced_view(client, world):
    as_user(client, world.pa, world.company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(f"/companies/{world.company.id}")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert set(body) == REDUCED_KEYS, sorted(body)
    assert body["role"] == "manager"
    _assert_no_leak(resp.text)


@pytest.mark.parametrize("who, claims", [("worker", WORKER_CLAIMS), ("manager", MANAGER_CLAIMS)])
def test_company_detail_suspended_is_403_for_non_pa(client, db, world, who, claims):
    world.company.is_active = False
    db.commit()
    as_user(client, getattr(world, who), world.company, claims=claims)

    resp = client.get(f"/companies/{world.company.id}")

    assert resp.status_code == 403, resp.text


# --- GET /users/{user_id}/companies (P8) ---


@pytest.fixture()
def shared(db, world):
    """El manager comparte `world.company` con el objetivo; el objetivo tambien esta en otras empresas."""
    target = make_user(db)
    make_member(db, target, world.company, role="worker", rates_config=RATES)
    other_manager_only = make_company(db)  # el solicitante no es miembro
    make_member(db, target, other_manager_only, role="worker")
    as_worker = make_company(db)  # el solicitante es solo worker
    make_member(db, world.manager, as_worker, role="worker")
    make_member(db, target, as_worker, role="worker")
    suspended = make_company(db, is_active=False)  # compartida pero suspendida
    make_member(db, world.manager, suspended, role="manager")
    make_member(db, target, suspended, role="worker")
    inactive_member = make_company(db)  # compartida, pero la membresia del objetivo esta desactivada
    make_member(db, world.manager, inactive_member, role="manager")
    make_member(db, target, inactive_member, role="worker", is_active=False)
    return type(
        "Shared",
        (),
        {
            "target": target,
            "all_ids": {
                str(c.id) for c in (world.company, other_manager_only, as_worker, suspended, inactive_member)
            },
        },
    )()


def test_user_companies_manager_sees_only_shared_active_managed(client, world, shared):
    as_user(client, world.manager, world.company, claims=MANAGER_CLAIMS)

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 200, resp.text
    assert [item["id"] for item in resp.json()] == [str(world.company.id)]
    entry = resp.json()[0]
    assert set(entry) == REDUCED_KEYS, sorted(entry)
    assert entry["role"] == "worker"
    _assert_no_leak(resp.text)


def test_user_companies_manager_limited_to_token_company(client, db, world, shared):
    other = make_company(db)
    make_member(db, world.manager, other, role="manager")
    make_member(db, shared.target, other, role="worker")

    as_user(client, world.manager, world.company, claims=MANAGER_CLAIMS)
    assert [i["id"] for i in client.get(f"/users/{shared.target.id}/companies").json()] == [str(world.company.id)]

    as_user(client, world.manager, other, claims=MANAGER_CLAIMS)
    assert [i["id"] for i in client.get(f"/users/{shared.target.id}/companies").json()] == [str(other.id)]


def test_user_companies_manager_with_worker_token_is_403(client, db, world, shared):
    # Manager de world.company, pero con el token apuntando a una empresa donde solo es worker.
    worker_side = make_company(db)
    make_member(db, world.manager, worker_side, role="worker")
    make_member(db, shared.target, worker_side, role="worker")
    as_user(client, world.manager, worker_side, claims=WORKER_CLAIMS)

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 403, resp.text


def test_user_companies_worker_is_403(client, world, shared):
    as_user(client, world.worker, world.company, claims=WORKER_CLAIMS)

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 403, resp.text


def test_user_companies_pa_sees_all_including_inactive(client, world, shared):
    as_user(client, world.pa, claims=PA_CLAIMS)

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 200, resp.text
    entries = resp.json()
    assert {item["id"] for item in entries} == shared.all_ids
    assert all("isActive" in item for item in entries)
    assert any(item["isActive"] is False for item in entries)
    assert any(item["isActiveMember"] is False for item in entries)


def test_user_companies_pa_view_as_worker_is_403(client, world, shared):
    as_user(client, world.pa, world.company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 403, resp.text


def test_user_companies_pa_view_as_manager_limited_to_token_company(client, db, world, shared):
    make_member(db, world.pa, world.company, role="manager")
    other = make_company(db)
    make_member(db, world.pa, other, role="manager")
    make_member(db, shared.target, other, role="worker")
    as_user(client, world.pa, world.company, claims={**PA_CLAIMS, "view_as": "manager"})

    resp = client.get(f"/users/{shared.target.id}/companies")

    assert resp.status_code == 200, resp.text
    assert [item["id"] for item in resp.json()] == [str(world.company.id)]
    assert set(resp.json()[0]) == REDUCED_KEYS


# --- Otros endpoints que embeben la empresa ---


def test_companies_detailed_manager_gets_reduced_view_with_members(client, world):
    as_user(client, world.manager, world.company, claims=MANAGER_CLAIMS)

    resp = client.get("/companies/detailed")

    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    entry = resp.json()[0]
    assert set(entry) == REDUCED_KEYS | {"members"}, sorted(entry)
    assert {m["userId"] for m in entry["members"]} == {str(world.manager.id), str(world.worker.id)}
    entry_without_members = {k: v for k, v in entry.items() if k != "members"}
    _assert_reduced(entry_without_members, world.company, "manager")
    assert "isActive" not in entry_without_members
    assert "allowed_rates" not in str(entry_without_members)
    assert "allowed_rates" not in str(entry["members"]), entry["members"]


def test_companies_detailed_pa_gets_full_view(client, world):
    as_user(client, world.pa, claims=PA_CLAIMS)

    resp = client.get("/companies/detailed")

    assert resp.status_code == 200, resp.text
    entry = {item["id"]: item for item in resp.json()}[str(world.company.id)]
    assert entry["isActive"] is True
    assert "members" in entry


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
