"""
Dashboard de empresa con miembros inactivos y con Redis caido (T11).

GET /companies/{cid}/dashboard-summary:
- Con Redis caido responde 200 con la misma forma (y contenido) que con cache.
- periodMetrics incluye los turnos de miembros inactivos.
- workersSummary incluye a los miembros inactivos con isActive == false (y los activos con true).
- Un miembro inactivo sin turnos hoy no aparece en todayMetrics.todayActiveMembers.

Tests escritos antes de la implementacion.
"""

from datetime import date, timedelta
from types import SimpleNamespace

import models

from tests.factories import as_user, make_company, make_member, make_user


def _log(db, user, company, day, hours, net):
    log = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type="particular",
        start_date=day,
        end_date=day,
        duration=hours,
        net_amount=net,
        gross_amount=net,
    )
    db.add(log)
    db.commit()
    return log


def _seed(db):
    """Una empresa con un gestor, un worker activo, un worker inactivo con turno de ayer y un inactivo sin turnos."""
    company = make_company(db)
    manager = make_user(db)
    make_member(db, manager, company, role="manager", is_active=True)
    active = make_user(db)
    make_member(db, active, company, role="worker", is_active=True)
    inactive = make_user(db)
    make_member(db, inactive, company, role="worker", is_active=False)
    idle_inactive = make_user(db)
    make_member(db, idle_inactive, company, role="worker", is_active=False)

    today = date.today()
    yesterday = today - timedelta(days=1)
    _log(db, active, company, today, hours=2.0, net=40.0)
    _log(db, inactive, company, yesterday, hours=3.0, net=60.0)

    return SimpleNamespace(
        company=company,
        manager=manager,
        active=active,
        inactive=inactive,
        idle_inactive=idle_inactive,
        start=(today - timedelta(days=7)).isoformat(),
        end=today.isoformat(),
    )


def _get_summary(client, seed):
    return client.get(
        f"/companies/{seed.company.id}/dashboard-summary",
        params={"start_date": seed.start, "end_date": seed.end},
    )


def test_dashboard_summary_returns_same_shape_when_redis_is_down(client, db, fake_redis):
    seed = _seed(db)
    as_user(client, seed.manager, seed.company)

    fresh = _get_summary(client, seed)  # cache vacia: calcula y guarda
    cached = _get_summary(client, seed)  # cache llena
    fake_redis.raise_errors = True
    degraded = _get_summary(client, seed)  # Redis caido: calcula sin cache

    assert fresh.status_code == 200, fresh.text
    assert cached.status_code == 200, cached.text
    assert degraded.status_code == 200, degraded.text
    assert set(degraded.json().keys()) == set(cached.json().keys())
    assert degraded.json() == cached.json()


def test_period_metrics_include_logs_of_inactive_members(client, db):
    seed = _seed(db)
    as_user(client, seed.manager, seed.company)

    resp = _get_summary(client, seed)

    assert resp.status_code == 200, resp.text
    period = resp.json()["periodMetrics"]
    # 2 h del activo (hoy) + 3 h del inactivo (ayer)
    assert period["totalHours"] == 5.0
    assert period["totalLogs"] == 2


def test_workers_summary_flags_active_and_inactive_members(client, db):
    seed = _seed(db)
    as_user(client, seed.manager, seed.company)

    resp = _get_summary(client, seed)

    assert resp.status_code == 200, resp.text
    workers = {w["userId"]: w for w in resp.json()["workersSummary"]}
    assert len(workers) == 4
    assert workers[str(seed.active.id)]["isActive"] is True
    assert workers[str(seed.manager.id)]["isActive"] is True
    assert workers[str(seed.inactive.id)]["isActive"] is False
    assert workers[str(seed.idle_inactive.id)]["isActive"] is False
    # Las estadisticas del inactivo tambien cuentan en su fila
    assert workers[str(seed.inactive.id)]["totalHours"] == 3.0


def test_inactive_member_without_logs_today_is_not_in_today_active_members(client, db):
    seed = _seed(db)
    as_user(client, seed.manager, seed.company)

    resp = _get_summary(client, seed)

    assert resp.status_code == 200, resp.text
    today_ids = {m["userId"] for m in resp.json()["todayMetrics"]["todayActiveMembers"]}
    assert str(seed.idle_inactive.id) not in today_ids
    assert str(seed.inactive.id) not in today_ids
    assert today_ids == {str(seed.active.id)}
