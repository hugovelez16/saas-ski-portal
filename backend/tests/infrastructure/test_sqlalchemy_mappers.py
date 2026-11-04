"""
Pruebas para mapeadores de persistencia SQLAlchemy.
"""

from datetime import datetime
from decimal import Decimal

import models
from domain.entities.company import Company
from domain.entities.company_member import CompanyRole
from domain.entities.user import User, UserRole
from domain.entities.work_log import WorkLog
from domain.value_objects.money import Money
from infrastructure.persistence.sqlalchemy.mappers.company_mapper import SqlAlchemyCompanyMapper
from infrastructure.persistence.sqlalchemy.mappers.user_mapper import (
    SqlAlchemyCompanyMemberMapper,
    SqlAlchemyUserMapper,
)
from infrastructure.persistence.sqlalchemy.mappers.work_log_mapper import SqlAlchemyWorkLogMapper


def test_user_mapper_bidirectional():
    user = User(
        id="usr-123",
        email="test@vesotel.com",
        first_name="Carlos",
        last_name="Gomez",
        is_active=True,
        role=UserRole.ADMIN,
        must_change_password=False,
    )

    orm_model = SqlAlchemyUserMapper.to_orm(user, hashed_password="hashed_pwd")
    assert orm_model.id == "usr-123"
    assert orm_model.email == "test@vesotel.com"
    assert orm_model.hashed_password == "hashed_pwd"

    domain_entity = SqlAlchemyUserMapper.to_domain(orm_model)
    assert domain_entity.id == user.id
    assert domain_entity.email == user.email
    assert domain_entity.role == UserRole.ADMIN
    assert domain_entity.full_name == "Carlos Gomez"


def test_company_mapper_bidirectional():
    comp = Company(
        id="comp-123",
        name="Escuela Sierra Nevada",
        tax_config={"irpf_base": 0.15},
        settings={"timezone": "Europe/Madrid"},
        is_active=False,
        is_managed=True,
        updated_at=datetime(2026, 3, 1, 10, 30),
    )

    orm_comp = SqlAlchemyCompanyMapper.to_orm(comp)
    assert orm_comp.name == "Escuela Sierra Nevada"
    assert orm_comp.tax_config == {"irpf_base": 0.15}
    assert orm_comp.settings == {"timezone": "Europe/Madrid"}
    assert orm_comp.is_active is False
    assert orm_comp.is_managed is True
    assert orm_comp.updated_at == datetime(2026, 3, 1, 10, 30)

    domain_comp = SqlAlchemyCompanyMapper.to_domain(orm_comp)
    assert domain_comp.id == comp.id
    assert domain_comp.name == comp.name
    assert domain_comp.settings == {"timezone": "Europe/Madrid"}
    assert domain_comp.is_active is False
    assert domain_comp.is_managed is True
    assert domain_comp.updated_at == datetime(2026, 3, 1, 10, 30)


def test_company_member_mapper_maps_settings_and_updated_at():
    orm_member = models.CompanyMember(
        user_id="usr-1",
        company_id="comp-1",
        role=models.CompanyRole.manager,
        is_active=True,
        sort_order=1,
        rates_config={},
        settings={"view": "compact"},
        joined_at=datetime(2026, 2, 1, 8, 0),
        updated_at=datetime(2026, 3, 2, 9, 15),
    )

    domain_member = SqlAlchemyCompanyMemberMapper.to_domain(orm_member)

    assert domain_member.role == CompanyRole.MANAGER
    assert domain_member.settings == {"view": "compact"}
    assert domain_member.updated_at == datetime(2026, 3, 2, 9, 15)


def test_work_log_mapper_bidirectional():
    from datetime import date, time

    log = WorkLog(
        id="log-1",
        user_id="u1",
        company_id="c1",
        type="clase",
        start_date=date(2026, 2, 1),
        start_time=time(9, 0),
        end_time=time(11, 0),
        duration_hours=2.0,
        gross_amount=Money(60.0),
        net_amount=Money(51.0),
        extra_data={"group_id": "grp-99"},
    )

    orm_log = SqlAlchemyWorkLogMapper.to_orm(log)
    assert orm_log.gross_amount == 60.0
    assert orm_log.net_amount == 51.0
    assert orm_log.extra_data == {"group_id": "grp-99"}

    domain_log = SqlAlchemyWorkLogMapper.to_domain(orm_log)
    assert domain_log.id == "log-1"
    assert domain_log.gross_amount.amount == Decimal("60.00")
    assert domain_log.net_amount.amount == Decimal("51.00")
    assert domain_log.group_id == "grp-99"
