"""
Contrato de las entidades de empresa tras PR-16.2 (alineacion del dominio con la BD).

- Company: is_active (default True), is_managed (default False), updated_at (default None)
  y sin fiscal_id (retirado en PR-06).
- CompanyMember: settings (dict por defecto, no compartido entre instancias) y updated_at.

Hasta implementar PR-16.2 estos tests fallan con AttributeError/TypeError sobre los campos nuevos.
"""

import dataclasses

from domain.entities.company import Company
from domain.entities.company_member import CompanyMember


def _field_names(cls) -> set[str]:
    return {f.name for f in dataclasses.fields(cls)}


def test_company_is_active_defaults_to_true():
    company = Company(id="c1", name="Escuela")

    assert company.is_active is True


def test_company_is_managed_defaults_to_false():
    company = Company(id="c1", name="Escuela")

    assert company.is_managed is False


def test_company_accepts_is_active_and_is_managed_keywords():
    company = Company(id="c1", name="Escuela", is_active=False, is_managed=True)

    assert company.is_active is False
    assert company.is_managed is True


def test_company_declares_updated_at_defaulting_to_none():
    company = Company(id="c1", name="Escuela")

    assert "updated_at" in _field_names(Company)
    assert company.updated_at is None


def test_company_has_no_fiscal_id():
    assert "fiscal_id" not in _field_names(Company)
    assert not hasattr(Company(id="c1", name="Escuela"), "fiscal_id")


def test_company_member_settings_defaults_to_empty_dict():
    member = CompanyMember(user_id="u1", company_id="c1")

    assert member.settings == {}


def test_company_member_settings_is_not_shared_between_instances():
    first = CompanyMember(user_id="u1", company_id="c1")
    second = CompanyMember(user_id="u2", company_id="c1")

    first.settings["notifications"] = True

    assert second.settings == {}


def test_company_member_declares_updated_at_defaulting_to_none():
    member = CompanyMember(user_id="u1", company_id="c1")

    assert "updated_at" in _field_names(CompanyMember)
    assert member.updated_at is None
