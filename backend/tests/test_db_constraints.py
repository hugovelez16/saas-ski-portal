"""Pruebas de restricciones de BD: CHECK de fechas, gross_amount NOT NULL y unicidad de suscripciones (#134)."""

import uuid
from datetime import date

import models
import pytest
from sqlalchemy.exc import IntegrityError

from tests.factories import make_company, make_user


def test_work_log_rejects_end_date_before_start_date(db):
    user = make_user(db)
    company = make_company(db)
    bad_log = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type="particular",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 9),
        gross_amount=100,
    )
    db.add(bad_log)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_work_log_accepts_equal_or_later_end_date(db):
    user = make_user(db)
    company = make_company(db)
    ok_log = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type="particular",
        start_date=date(2026, 12, 10),
        end_date=date(2026, 12, 10),
    )
    db.add(ok_log)
    db.flush()
    assert ok_log.gross_amount == 0


def test_module_subscription_partial_unique_rejects_duplicate_active_company(db):
    company = make_company(db)
    module = models.AppModule(code_name=f"mod_{uuid.uuid4().hex[:6]}", name="Mod Test", is_active=True)
    db.add(module)
    db.flush()

    first = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=models.SubscriptionStatus.active,
    )
    db.add(first)
    db.flush()

    duplicate = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=models.SubscriptionStatus.active,
    )
    db.add(duplicate)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


def test_module_subscription_partial_unique_allows_cancelled_plus_active(db):
    company = make_company(db)
    module = models.AppModule(code_name=f"mod_{uuid.uuid4().hex[:6]}", name="Mod Test", is_active=True)
    db.add(module)
    db.flush()

    cancelled = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=models.SubscriptionStatus.cancelled,
    )
    active = models.ModuleSubscription(
        module_id=module.id,
        company_id=company.id,
        status=models.SubscriptionStatus.active,
    )
    db.add_all([cancelled, active])
    db.flush()
    assert active.id is not None


def test_module_subscription_rejects_null_company_id(db):
    module = models.AppModule(code_name=f"mod_{uuid.uuid4().hex[:6]}", name="Mod Test", is_active=True)
    db.add(module)
    db.flush()

    bad = models.ModuleSubscription(
        module_id=module.id,
        company_id=None,
        status=models.SubscriptionStatus.active,
    )
    db.add(bad)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()
