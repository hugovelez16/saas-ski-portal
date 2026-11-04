"""
Repositorios de empresa y de membresias sobre SQLAlchemy (PR-16.2).

Contratos de los puertos (todos async):
- CompanyRepositoryPort: get_by_id, get_by_name, list_companies(skip, limit), count_companies,
  save, delete, count_dependencies (claves: members, work_logs, subscriptions).
- CompanyMemberRepositoryPort: get_membership, list_members_by_company(company_id, is_active),
  list_companies_by_user, save, delete(user_id, company_id), count_work_logs(user_id, company_id).

El modulo del repositorio y el del puerto se importan con importlib en los helpers y en los tests
de contrato de puertos, para que la coleccion de pytest no dependa de ellos a nivel de modulo.

Dominio: los ids son str. En BD son UUID. Los tests comprueban la ida y vuelta sin perdida.
"""

import importlib
import uuid
from datetime import date, datetime

import models
import pytest
from domain.entities.company import Company
from domain.entities.company_member import CompanyMember, CompanyRole
from domain.exceptions.domain_exceptions import ConflictException
from sqlalchemy import text

from tests.factories import make_company, make_member, make_user, make_work_log

REPO_MODULE = "infrastructure.persistence.sqlalchemy.repositories.company_repository"
PORT_MODULE = "domain.ports.repositories.company_repository_port"

BASE_RATES = {"particular": {"base_rate": 25.0, "is_gross": False, "tax_overrides": {}}}


def _company_repo(db):
    return importlib.import_module(REPO_MODULE).SqlAlchemyCompanyRepository(db)


def _member_repo(db):
    return importlib.import_module(REPO_MODULE).SqlAlchemyCompanyMemberRepository(db)


def _reload(db):
    """Descarta el identity map para leer lo que realmente quedo persistido."""
    db.expire_all()


def _domain_company(**overrides) -> Company:
    """Empresa de dominio con los campos que existen hoy. Los campos nuevos se asignan despues."""
    data = {
        "id": str(uuid.uuid4()),
        "name": f"Empresa {uuid.uuid4().hex[:6]}",
        "tax_config": {"irpf": 0.15, "social_security": 0.0648},
        "worklog_definitions": {"particular": {"unit": "hours", "label": "Particular", "fields": []}},
        "settings": {"timezone": "Europe/Madrid", "feature_flags": {"reports": True}},
    }
    data.update(overrides)
    return Company(**data)


# --- Modulo y puertos ---


def test_company_repository_module_is_importable():
    module = importlib.import_module(REPO_MODULE)

    assert hasattr(module, "SqlAlchemyCompanyRepository")
    assert hasattr(module, "SqlAlchemyCompanyMemberRepository")


def test_company_ports_declare_new_methods():
    port = importlib.import_module(PORT_MODULE)

    for name in ("get_by_id", "get_by_name", "list_companies", "count_companies", "save", "delete"):
        assert hasattr(port.CompanyRepositoryPort, name), name
    assert hasattr(port.CompanyRepositoryPort, "count_dependencies")
    for name in (
        "get_membership",
        "list_members_by_company",
        "list_companies_by_user",
        "save",
        "delete",
        "count_work_logs",
    ):
        assert hasattr(port.CompanyMemberRepositoryPort, name), name


# --- CompanyRepositoryPort ---


async def test_get_by_id_returns_domain_company(db):
    company = make_company(db, name="Alfa")

    result = await _company_repo(db).get_by_id(str(company.id))

    assert isinstance(result, Company)
    assert result.id == str(company.id)
    assert result.name == "Alfa"


async def test_get_by_id_returns_none_for_unknown_id(db):
    assert await _company_repo(db).get_by_id(str(uuid.uuid4())) is None


async def test_get_by_name_returns_company(db):
    make_company(db, name="Beta")

    result = await _company_repo(db).get_by_name("Beta")

    assert result is not None
    assert result.name == "Beta"


async def test_get_by_name_returns_none_for_unknown_name(db):
    make_company(db, name="Beta")

    assert await _company_repo(db).get_by_name("Gamma") is None


async def test_list_companies_default_returns_all_rows_as_domain_objects(db):
    repo = _company_repo(db)
    for _ in range(3):
        make_company(db)

    result = await repo.list_companies()

    assert len(result) == 3
    assert all(isinstance(company, Company) for company in result)


async def test_list_companies_pages_do_not_overlap(db):
    repo = _company_repo(db)
    for _ in range(5):
        make_company(db)
    total = await repo.count_companies()

    seen_ids = []
    for skip in range(0, total, 2):
        page = await repo.list_companies(skip=skip, limit=2)
        assert len(page) <= 2
        seen_ids.extend(company.id for company in page)

    assert len(seen_ids) == total
    assert len(set(seen_ids)) == total


async def test_list_companies_skip_beyond_total_returns_empty(db):
    repo = _company_repo(db)
    make_company(db)

    assert await repo.list_companies(skip=10, limit=5) == []


async def test_count_companies_counts_all_rows(db):
    repo = _company_repo(db)
    before = await repo.count_companies()
    for _ in range(3):
        make_company(db)

    assert await repo.count_companies() == before + 3


async def test_save_creates_company_persisting_is_active_and_is_managed(db):
    repo = _company_repo(db)
    company = _domain_company()
    company.is_active = False
    company.is_managed = True

    await repo.save(company)
    _reload(db)
    loaded = await repo.get_by_id(company.id)

    assert loaded is not None
    assert loaded.is_active is False
    assert loaded.is_managed is True


async def test_save_round_trip_preserves_every_field(db):
    repo = _company_repo(db)
    original = _domain_company()
    original.is_active = False
    original.is_managed = True

    await repo.save(original)
    _reload(db)
    loaded = await repo.get_by_id(original.id)

    assert loaded.id == original.id
    assert loaded.name == original.name
    assert loaded.tax_config == original.tax_config
    assert loaded.worklog_definitions == original.worklog_definitions
    assert loaded.settings == original.settings
    assert loaded.is_active is False
    assert loaded.is_managed is True
    assert loaded.updated_at is not None


async def test_save_updates_existing_company_fields(db):
    company = make_company(
        db,
        name="Original",
        is_active=True,
        is_managed=False,
        settings={"a": 1},
    )
    repo = _company_repo(db)
    domain = await repo.get_by_id(str(company.id))
    domain.name = "Renombrada"
    domain.is_active = False
    domain.is_managed = True
    domain.settings = {"b": 2}
    domain.tax_config = {"irpf": 0.2}
    domain.worklog_definitions = {"otro": {"unit": "days", "label": "Otro", "fields": []}}

    await repo.save(domain)
    _reload(db)
    loaded = await repo.get_by_id(str(company.id))

    assert loaded.name == "Renombrada"
    assert loaded.is_active is False
    assert loaded.is_managed is True
    assert loaded.settings == {"b": 2}
    assert loaded.tax_config == {"irpf": 0.2}
    assert loaded.worklog_definitions == {"otro": {"unit": "days", "label": "Otro", "fields": []}}


async def test_delete_removes_company(db):
    company = make_company(db)
    repo = _company_repo(db)

    await repo.delete(str(company.id))
    _reload(db)

    assert await repo.get_by_id(str(company.id)) is None


async def test_delete_company_with_members_raises_conflict_and_session_stays_usable(db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company)
    repo = _company_repo(db)
    member_repo = _member_repo(db)
    # SQLite no aplica claves foraneas por defecto; PostgreSQL las aplica siempre.
    is_sqlite = db.get_bind().dialect.name == "sqlite"
    if is_sqlite:
        db.execute(text("PRAGMA foreign_keys=ON"))
    try:
        with pytest.raises(ConflictException) as exc_info:
            await repo.delete(str(company.id))

        assert exc_info.value.message == "No se puede eliminar: existen datos dependientes"
        # La sesion debe seguir utilizable tras el rollback: lecturas y escrituras posteriores funcionan.
        assert await repo.get_by_id(str(company.id)) is not None
        assert await member_repo.get_membership(str(user.id), str(company.id)) is not None
        other = _domain_company()
        await repo.save(other)
        assert await repo.get_by_id(other.id) is not None
    finally:
        if is_sqlite:
            db.execute(text("PRAGMA foreign_keys=OFF"))


async def test_count_dependencies_returns_zeros_for_empty_company(db):
    company = make_company(db)

    result = await _company_repo(db).count_dependencies(str(company.id))

    assert result == {"members": 0, "work_logs": 0, "subscriptions": 0}


async def test_count_dependencies_counts_members_work_logs_and_subscriptions(db):
    company = make_company(db)
    user_a = make_user(db)
    user_b = make_user(db)
    make_member(db, user_a, company)
    make_member(db, user_b, company)
    make_work_log(db, user_a, company)
    module = models.AppModule(code_name=f"mod_{uuid.uuid4().hex[:8]}", name="Modulo", is_active=True)
    db.add(module)
    db.commit()
    db.add(
        models.ModuleSubscription(
            module_id=module.id,
            company_id=company.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
        )
    )
    db.commit()

    result = await _company_repo(db).count_dependencies(str(company.id))

    assert result == {"members": 2, "work_logs": 1, "subscriptions": 1}


async def test_count_dependencies_ignores_other_companies(db):
    company = make_company(db)
    other_company = make_company(db)
    user = make_user(db)
    make_member(db, user, company)
    make_member(db, user, other_company)
    make_work_log(db, user, other_company)

    result = await _company_repo(db).count_dependencies(str(company.id))

    assert result == {"members": 1, "work_logs": 0, "subscriptions": 0}


# --- CompanyMemberRepositoryPort ---


async def test_get_membership_returns_domain_member(db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company, role="manager", is_active=True)

    result = await _member_repo(db).get_membership(str(user.id), str(company.id))

    assert isinstance(result, CompanyMember)
    assert result.user_id == str(user.id)
    assert result.company_id == str(company.id)
    assert result.role == CompanyRole.MANAGER
    assert result.is_active is True


async def test_get_membership_returns_none_when_user_is_not_member(db):
    company = make_company(db)
    user = make_user(db)

    assert await _member_repo(db).get_membership(str(user.id), str(company.id)) is None


async def test_list_members_by_company_returns_only_that_company(db):
    company = make_company(db)
    other_company = make_company(db)
    user_a = make_user(db)
    user_b = make_user(db)
    user_c = make_user(db)
    make_member(db, user_a, company)
    make_member(db, user_b, company)
    make_member(db, user_c, other_company)

    result = await _member_repo(db).list_members_by_company(str(company.id))

    assert {member.user_id for member in result} == {str(user_a.id), str(user_b.id)}


async def test_list_members_by_company_filters_by_is_active(db):
    company = make_company(db)
    user_active = make_user(db)
    user_inactive = make_user(db)
    user_active_2 = make_user(db)
    make_member(db, user_active, company, is_active=True)
    make_member(db, user_inactive, company, is_active=False)
    make_member(db, user_active_2, company, is_active=True)
    repo = _member_repo(db)

    active = await repo.list_members_by_company(str(company.id), is_active=True)
    inactive = await repo.list_members_by_company(str(company.id), is_active=False)
    unfiltered = await repo.list_members_by_company(str(company.id))
    explicit_none = await repo.list_members_by_company(str(company.id), is_active=None)

    assert {member.user_id for member in active} == {str(user_active.id), str(user_active_2.id)}
    assert {member.user_id for member in inactive} == {str(user_inactive.id)}
    assert len(unfiltered) == 3
    assert {m.user_id for m in explicit_none} == {m.user_id for m in unfiltered}


async def test_list_members_by_company_orders_by_sort_order_then_joined_at(db):
    company = make_company(db)
    user_first = make_user(db)
    user_tie_early = make_user(db)
    user_tie_late = make_user(db)
    early = datetime(2026, 1, 1, 9, 0)
    late = datetime(2026, 1, 2, 9, 0)

    m_late = make_member(db, user_tie_late, company)
    m_late.sort_order = 2
    m_late.joined_at = late
    m_first = make_member(db, user_first, company)
    m_first.sort_order = 1
    m_first.joined_at = late
    m_early = make_member(db, user_tie_early, company)
    m_early.sort_order = 2
    m_early.joined_at = early
    db.commit()

    result = await _member_repo(db).list_members_by_company(str(company.id))

    assert [member.user_id for member in result] == [
        str(user_first.id),
        str(user_tie_early.id),
        str(user_tie_late.id),
    ]


async def test_list_companies_by_user_returns_only_that_users_memberships(db):
    user = make_user(db)
    other_user = make_user(db)
    company_1 = make_company(db)
    company_2 = make_company(db)
    company_3 = make_company(db)
    make_member(db, user, company_1)
    make_member(db, user, company_2)
    make_member(db, other_user, company_3)

    result = await _member_repo(db).list_companies_by_user(str(user.id))

    assert all(isinstance(member, CompanyMember) for member in result)
    assert {member.company_id for member in result} == {str(company_1.id), str(company_2.id)}


async def test_save_creates_membership_persisting_settings_rates_role_active_and_order(db):
    company = make_company(db)
    user = make_user(db)
    member = CompanyMember(user_id=str(user.id), company_id=str(company.id))
    member.role = CompanyRole.MANAGER
    member.is_active = False
    member.sort_order = 7
    member.rates_config = BASE_RATES
    member.settings = {"notifications": {"email": True}}

    await _member_repo(db).save(member)
    _reload(db)
    loaded = await _member_repo(db).get_membership(str(user.id), str(company.id))

    assert loaded is not None
    assert loaded.role == CompanyRole.MANAGER
    assert loaded.is_active is False
    assert loaded.sort_order == 7
    assert loaded.rates_config == BASE_RATES
    assert loaded.settings == {"notifications": {"email": True}}


async def test_save_updates_existing_membership_fields(db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company, role="worker", is_active=True, rates_config=BASE_RATES)
    repo = _member_repo(db)
    member = await repo.get_membership(str(user.id), str(company.id))
    new_rates = {"particular": {"base_rate": 30.0, "is_gross": True, "tax_overrides": {}}}
    member.role = CompanyRole.ADMIN
    member.is_active = False
    member.sort_order = 3
    member.rates_config = new_rates
    member.settings = {"view": "compact"}

    await repo.save(member)
    _reload(db)
    loaded = await repo.get_membership(str(user.id), str(company.id))

    assert loaded.role == CompanyRole.ADMIN
    assert loaded.is_active is False
    assert loaded.sort_order == 3
    assert loaded.rates_config == new_rates
    assert loaded.settings == {"view": "compact"}


async def test_delete_removes_only_the_given_membership(db):
    company = make_company(db)
    other_company = make_company(db)
    user = make_user(db)
    other_user = make_user(db)
    make_member(db, user, company)
    make_member(db, user, other_company)
    make_member(db, other_user, company)
    repo = _member_repo(db)

    await repo.delete(str(user.id), str(company.id))
    _reload(db)

    assert await repo.get_membership(str(user.id), str(company.id)) is None
    assert await repo.get_membership(str(user.id), str(other_company.id)) is not None
    assert await repo.get_membership(str(other_user.id), str(company.id)) is not None


async def test_count_work_logs_is_zero_without_logs(db):
    company = make_company(db)
    user = make_user(db)
    make_member(db, user, company)

    assert await _member_repo(db).count_work_logs(str(user.id), str(company.id)) == 0


async def test_count_work_logs_counts_only_that_user_and_company(db):
    company = make_company(db)
    other_company = make_company(db)
    user = make_user(db)
    other_user = make_user(db)
    make_work_log(db, user, company, start_date=date(2026, 1, 10))
    make_work_log(db, user, company, start_date=date(2026, 1, 11))
    make_work_log(db, user, other_company, start_date=date(2026, 1, 12))
    make_work_log(db, other_user, company, start_date=date(2026, 1, 13))

    assert await _member_repo(db).count_work_logs(str(user.id), str(company.id)) == 2
