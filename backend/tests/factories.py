"""Fabricas de datos para los tests. Cada funcion persiste el objeto y lo devuelve refrescado."""

import uuid
from datetime import date, time, timedelta

import auth
import models


def make_user(
    db,
    *,
    email: str | None = None,
    role: str = "user",
    is_active: bool = True,
    password: str = "pw12345678",
) -> models.User:
    user = models.User(
        email=email or f"u_{uuid.uuid4().hex[:6]}@test.com",
        hashed_password=auth.get_password_hash(password),
        first_name="Test",
        last_name="User",
        role=models.UserRole(role),
        is_active=is_active,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def make_company(
    db,
    *,
    name: str | None = None,
    is_active: bool = True,
    is_managed: bool = False,
    tax_config: dict | None = None,
    worklog_definitions: dict | None = None,
    settings: dict | None = None,
) -> models.Company:
    company = models.Company(
        name=name or f"Empresa {uuid.uuid4().hex[:6]}",
        is_active=is_active,
        is_managed=is_managed,
        tax_config=tax_config if tax_config is not None else {"social_security": 0.0648},
        worklog_definitions=(
            worklog_definitions
            if worklog_definitions is not None
            else {"particular": {"unit": "hours", "label": "Particular", "fields": []}}
        ),
        settings=settings if settings is not None else {},
    )
    db.add(company)
    db.commit()
    db.refresh(company)
    return company


def make_member(
    db,
    user: models.User,
    company: models.Company,
    *,
    role: str = "worker",
    is_active: bool = True,
    rates_config: dict | None = None,
) -> models.CompanyMember:
    member = models.CompanyMember(
        user_id=user.id,
        company_id=company.id,
        role=models.CompanyRole(role),
        is_active=is_active,
        rates_config=(
            rates_config
            if rates_config is not None
            else {"particular": {"base_rate": 20.0, "is_gross": True, "tax_overrides": {}}}
        ),
    )
    db.add(member)
    db.commit()
    db.refresh(member)
    return member


def make_work_log(
    db,
    user: models.User,
    company: models.Company,
    *,
    type: str = "particular",
    start_date: date | None = None,
    end_date: date | None = None,
    start_time: time | None = time(9, 0),
    end_time: time | None = time(11, 0),
    net_amount: float = 40.0,
    extra_data: dict | None = None,
) -> models.WorkLog:
    start = start_date or date(2026, 1, 10)
    work_log = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type=type,
        start_date=start,
        end_date=end_date or start,
        start_time=start_time,
        end_time=end_time,
        net_amount=net_amount,
        extra_data=extra_data if extra_data is not None else {},
    )
    db.add(work_log)
    db.commit()
    db.refresh(work_log)
    return work_log


def make_token(
    user: models.User,
    company: models.Company | None = None,
    *,
    scope: str = "full",
    claims: dict | None = None,
    expires_minutes: int = 30,
) -> str:
    data = {
        "sub": str(user.id),
        "cid": str(company.id) if company else None,
        "scope": scope,
        **(claims or {}),
    }
    return auth.create_access_token(data=data, expires_delta=timedelta(minutes=expires_minutes))


def as_user(
    client,
    user: models.User,
    company: models.Company | None = None,
    *,
    scope: str = "full",
    claims: dict | None = None,
):
    """Deja en el cliente la cookie `access_token` del usuario y devuelve el mismo cliente."""
    client.cookies.clear()
    client.cookies.set("access_token", make_token(user, company, scope=scope, claims=claims))
    return client
