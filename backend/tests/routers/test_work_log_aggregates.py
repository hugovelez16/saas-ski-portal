"""
Agregados de turnos (PR-07): GET /work-logs/summary y cabecera X-Total-Count de GET /work-logs.

Tests de contrato de PR-07.0.
El caso de worker con modulo worker_daily_report queda fuera (decision pendiente).
"""

from datetime import date, time, timedelta
from types import SimpleNamespace

import access_policy
import main
import models
import pytest
from sqlalchemy import func
from starlette.middleware.cors import CORSMiddleware

from tests.factories import as_user, make_company, make_member, make_user

MSG_SUSPENDED = "Empresa inactiva o suspendida"
MSG_NO_ACCESS = "No tienes acceso a esta empresa"

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}

TYPES = ("particular", "tutorial", "grupo")
BASE_DAY = date(2026, 3, 1)
RANGE_START = "2026-03-01"
RANGE_END = "2026-03-30"
TOTAL_LOGS = 2500
DAYS = 30


# --- Datos de prueba ---


def _add_log(db, user, company, *, day, duration=2.0, net=40.0, gross=50.0, type="particular"):
    log = models.WorkLog(
        user_id=user.id,
        company_id=company.id,
        type=type,
        start_date=day,
        end_date=day,
        start_time=time(9, 0),
        end_time=time(11, 0),
        duration=duration,
        net_amount=net,
        gross_amount=gross,
        extra_data={},
    )
    db.add(log)
    db.commit()
    return log


@pytest.fixture
def big(db):
    """Empresa con 2500 turnos en 30 dias, 3 tipos y 4 usuarios (1 manager + 3 workers)."""
    company = make_company(db)
    manager = make_user(db)
    workers = [make_user(db) for _ in range(3)]
    make_member(db, manager, company, role="manager")
    for worker in workers:
        make_member(db, worker, company, role="worker")
    users = [manager, *workers]

    rows = []
    orm_logs = []
    for i in range(TOTAL_LOGS):
        user = users[i % 4]
        day = BASE_DAY + timedelta(days=i % DAYS)
        row = {
            "user_id": str(user.id),
            "type": TYPES[i % 3],
            "day": day,
            "duration": 1.0 + (i % 4) * 0.5,
            "net": 10.0 + (i % 7),
            "gross": 12.0 + (i % 5),
        }
        rows.append(row)
        orm_logs.append(
            models.WorkLog(
                user_id=user.id,
                company_id=company.id,
                type=row["type"],
                start_date=day,
                end_date=day,
                start_time=time(9, 0),
                end_time=time(11, 0),
                duration=row["duration"],
                net_amount=row["net"],
                gross_amount=row["gross"],
                extra_data={},
            )
        )
    db.bulk_save_objects(orm_logs)
    db.commit()

    return SimpleNamespace(company=company, manager=manager, workers=workers, users=users, rows=rows)


@pytest.fixture
def small(db):
    """Empresa activa con 3 miembros y 4 turnos repartidos."""
    company = make_company(db)
    manager = make_user(db)
    worker_a = make_user(db)
    worker_b = make_user(db)
    make_member(db, manager, company, role="manager")
    make_member(db, worker_a, company, role="worker")
    make_member(db, worker_b, company, role="worker")

    _add_log(db, worker_a, company, day=date(2026, 3, 2), duration=2.0, net=40.0, gross=50.0)
    _add_log(db, worker_a, company, day=date(2026, 3, 3), duration=2.0, net=40.0, gross=50.0)
    _add_log(db, worker_b, company, day=date(2026, 3, 2), duration=3.0, net=60.0, gross=70.0)
    _add_log(db, manager, company, day=date(2026, 3, 4), duration=1.0, net=20.0, gross=25.0)

    return SimpleNamespace(company=company, manager=manager, worker_a=worker_a, worker_b=worker_b)


def _summary_params(company_id=None, user_id=None, start_date=RANGE_START, end_date=RANGE_END):
    raw = {
        "company_id": str(company_id) if company_id else None,
        "user_id": str(user_id) if user_id else None,
        "start_date": start_date,
        "end_date": end_date,
    }
    return {k: v for k, v in raw.items() if v is not None}


def _get_summary(client, **kwargs):
    return client.get("/work-logs/summary", params=_summary_params(**kwargs))


def _sum_rows(rows):
    return {
        "logs": len(rows),
        "hours": sum(r["duration"] for r in rows),
        "net": sum(r["net"] for r in rows),
        "gross": sum(r["gross"] for r in rows),
    }


def _rows_in_range(rows, start, end):
    return [r for r in rows if start <= r["day"] <= end]


# --- 1. Agregados sobre 2500 turnos ---


def test_summary_totals_match_direct_sql_on_2500_logs(client, db, big):
    as_user(client, big.manager, big.company, claims=MANAGER_CLAIMS)

    resp = _get_summary(client, company_id=big.company.id)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    sql_count, sql_hours, sql_net, sql_gross = db.query(
        func.count(models.WorkLog.id),
        func.sum(models.WorkLog.duration),
        func.sum(models.WorkLog.net_amount),
        func.sum(models.WorkLog.gross_amount),
    ).filter(models.WorkLog.company_id == big.company.id).one()

    totals = body["totals"]
    assert totals["logsCount"] == TOTAL_LOGS
    assert totals["logsCount"] == sql_count
    assert totals["totalHours"] == pytest.approx(float(sql_hours))
    assert totals["totalNet"] == pytest.approx(float(sql_net))
    assert totals["totalGross"] == pytest.approx(float(sql_gross))
    assert totals["uniqueDays"] == DAYS
    assert totals["activeUsers"] == 4
    assert body["startDate"] == RANGE_START
    assert body["endDate"] == RANGE_END


def test_summary_breakdowns_sum_to_totals_on_2500_logs(client, db, big):
    as_user(client, big.manager, big.company, claims=MANAGER_CLAIMS)

    resp = _get_summary(client, company_id=big.company.id)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    totals = body["totals"]

    # byType
    assert {t["type"] for t in body["byType"]} == set(TYPES)
    assert sum(t["logsCount"] for t in body["byType"]) == totals["logsCount"]
    assert sum(t["hours"] for t in body["byType"]) == pytest.approx(totals["totalHours"])
    assert sum(t["net"] for t in body["byType"]) == pytest.approx(totals["totalNet"])
    assert sum(t["gross"] for t in body["byType"]) == pytest.approx(totals["totalGross"])
    for item in body["byType"]:
        type_rows = [r for r in big.rows if r["type"] == item["type"]]
        assert item["logsCount"] == len(type_rows)
        assert item["hours"] == pytest.approx(_sum_rows(type_rows)["hours"])

    # byDay
    assert len(body["byDay"]) == DAYS
    assert sum(d["logsCount"] for d in body["byDay"]) == totals["logsCount"]
    assert sum(d["hours"] for d in body["byDay"]) == pytest.approx(totals["totalHours"])
    assert sum(d["net"] for d in body["byDay"]) == pytest.approx(totals["totalNet"])
    assert sum(d["gross"] for d in body["byDay"]) == pytest.approx(totals["totalGross"])
    for item in body["byDay"]:
        day = date.fromisoformat(item["date"])
        day_rows = [r for r in big.rows if r["day"] == day]
        assert item["logsCount"] == len(day_rows)

    # byUser
    assert {u["userId"] for u in body["byUser"]} == {str(u.id) for u in big.users}
    assert sum(u["logsCount"] for u in body["byUser"]) == totals["logsCount"]
    assert sum(u["hours"] for u in body["byUser"]) == pytest.approx(totals["totalHours"])
    assert sum(u["net"] for u in body["byUser"]) == pytest.approx(totals["totalNet"])
    assert sum(u["gross"] for u in body["byUser"]) == pytest.approx(totals["totalGross"])
    for item in body["byUser"]:
        user_rows = [r for r in big.rows if r["user_id"] == item["userId"]]
        assert item["logsCount"] == len(user_rows)
        assert item["uniqueDays"] == len({r["day"] for r in user_rows})


# --- 2. Listado con X-Total-Count ---


def test_work_logs_list_reports_total_independent_of_page(client, db, big):
    as_user(client, big.manager, big.company, claims=MANAGER_CLAIMS)
    company_id = str(big.company.id)

    first = client.get("/work-logs", params={"company_id": company_id, "limit": 100, "skip": 0})
    assert first.status_code == 200, first.text
    assert "x-total-count" in first.headers, "Falta la cabecera X-Total-Count"
    assert first.headers["x-total-count"] == str(TOTAL_LOGS)
    assert len(first.json()) == 100

    last_page = client.get("/work-logs", params={"company_id": company_id, "limit": 100, "skip": 2400})
    assert last_page.status_code == 200, last_page.text
    assert len(last_page.json()) == 100
    assert last_page.headers["x-total-count"] == str(TOTAL_LOGS)

    beyond = client.get("/work-logs", params={"company_id": company_id, "limit": 100, "skip": 2500})
    assert beyond.status_code == 200, beyond.text
    assert beyond.json() == []
    assert beyond.headers["x-total-count"] == str(TOTAL_LOGS)


def test_work_logs_total_count_reflects_user_and_range_filters(client, db, big):
    as_user(client, big.manager, big.company, claims=MANAGER_CLAIMS)
    company_id = str(big.company.id)
    worker = big.workers[0]

    by_user = client.get("/work-logs", params={"company_id": company_id, "user_id": str(worker.id), "limit": 5})
    assert by_user.status_code == 200, by_user.text
    expected_user = len([r for r in big.rows if r["user_id"] == str(worker.id)])
    assert by_user.headers["x-total-count"] == str(expected_user)
    assert len(by_user.json()) == 5

    range_end = BASE_DAY + timedelta(days=9)
    by_range = client.get(
        "/work-logs",
        params={
            "company_id": company_id,
            "start_date": BASE_DAY.isoformat(),
            "end_date": range_end.isoformat(),
            "limit": 5,
        },
    )
    assert by_range.status_code == 200, by_range.text
    expected_range = len(_rows_in_range(big.rows, BASE_DAY, range_end))
    assert by_range.headers["x-total-count"] == str(expected_range)


def test_total_count_header_is_exposed_by_cors():
    cors = [m for m in main.app.user_middleware if m.cls is CORSMiddleware]
    assert cors, "CORSMiddleware no esta configurado"
    options = getattr(cors[0], "kwargs", None) or getattr(cors[0], "options", {})
    exposed = [h.lower() for h in options.get("expose_headers", [])]
    assert "x-total-count" in exposed


# --- 3. Autorizacion ---


def test_manager_sees_full_by_user_and_can_filter_by_user(client, db, big):
    as_user(client, big.manager, big.company, claims=MANAGER_CLAIMS)
    worker = big.workers[0]

    body = _get_summary(client, company_id=big.company.id).json()
    assert len(body["byUser"]) == 4

    filtered = _get_summary(client, company_id=big.company.id, user_id=worker.id)
    assert filtered.status_code == 200, filtered.text
    filtered_body = filtered.json()
    expected = len([r for r in big.rows if r["user_id"] == str(worker.id)])
    assert filtered_body["totals"]["logsCount"] == expected
    assert [u["userId"] for u in filtered_body["byUser"]] == [str(worker.id)]


def test_worker_only_receives_own_data(client, db, small):
    as_user(client, small.worker_a, small.company, claims=WORKER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert [u["userId"] for u in body["byUser"]] == [str(small.worker_a.id)]
    assert body["totals"]["logsCount"] == 2
    assert body["totals"]["totalHours"] == pytest.approx(4.0)


def test_worker_own_user_id_is_allowed(client, db, small):
    as_user(client, small.worker_a, small.company, claims=WORKER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id, user_id=small.worker_a.id)

    assert resp.status_code == 200, resp.text
    assert [u["userId"] for u in resp.json()["byUser"]] == [str(small.worker_a.id)]


def test_worker_foreign_user_id_is_forbidden(client, db, small):
    as_user(client, small.worker_a, small.company, claims=WORKER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id, user_id=small.worker_b.id)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == access_policy.MSG_FORBIDDEN


def test_manager_of_other_company_is_forbidden(client, db, small):
    other_company = make_company(db)
    other_manager = make_user(db)
    make_member(db, other_manager, other_company, role="manager")
    as_user(client, other_manager, other_company, claims=MANAGER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id)

    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == MSG_NO_ACCESS


def test_suspended_company_blocks_manager_and_allows_platform_admin(client, db, small):
    small.company.is_active = False
    db.commit()

    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)
    blocked = _get_summary(client, company_id=small.company.id)
    assert blocked.status_code == 403, blocked.text
    assert blocked.json()["detail"] == MSG_SUSPENDED

    pa = make_user(db, role="admin")
    as_user(client, pa, small.company, claims=PA_CLAIMS)
    allowed = _get_summary(client, company_id=small.company.id)
    assert allowed.status_code == 200, allowed.text
    assert allowed.json()["totals"]["logsCount"] == 4


def test_platform_admin_in_view_as_worker_is_treated_as_worker(client, db, small):
    pa = make_user(db, role="admin")
    as_user(client, pa, small.company, claims={**PA_CLAIMS, "view_as": "worker"})

    resp = _get_summary(client, company_id=small.company.id)

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert all(u["userId"] == str(pa.id) for u in body["byUser"])
    assert body["totals"]["logsCount"] == 0

    foreign = _get_summary(client, company_id=small.company.id, user_id=small.worker_a.id)
    assert foreign.status_code == 403, foreign.text


def test_platform_admin_without_view_as_sees_whole_company(client, db, small):
    pa = make_user(db, role="admin")
    as_user(client, pa, small.company, claims=PA_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id)

    assert resp.status_code == 200, resp.text
    users = {u["userId"] for u in resp.json()["byUser"]}
    assert users == {str(small.manager.id), str(small.worker_a.id), str(small.worker_b.id)}


def test_platform_admin_without_company_is_rejected(client, db, small):
    pa = make_user(db, role="admin")
    as_user(client, pa, None, claims=PA_CLAIMS)

    resp = _get_summary(client)

    assert resp.status_code == 422, resp.text


def test_without_company_or_user_returns_own_logs_of_active_companies(client, db, small):
    suspended = make_company(db, is_active=False)
    worker_c = make_user(db)
    make_member(db, worker_c, small.company, role="worker")
    make_member(db, worker_c, suspended, role="worker")
    _add_log(db, worker_c, small.company, day=date(2026, 3, 5), duration=2.0)
    _add_log(db, worker_c, suspended, day=date(2026, 3, 6), duration=5.0)
    as_user(client, worker_c, None, claims=WORKER_CLAIMS)

    resp = client.get("/work-logs/summary", params=_summary_params())

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["logsCount"] == 1
    assert body["totals"]["totalHours"] == pytest.approx(2.0)
    assert [u["userId"] for u in body["byUser"]] == [str(worker_c.id)]


# --- 4. Validacion ---


@pytest.mark.parametrize(
    "dates",
    [
        {},
        {"start_date": RANGE_START},
        {"end_date": RANGE_END},
        {"start_date": "2026-03-30", "end_date": "2026-03-01"},
        {"start_date": "1999-12-31", "end_date": RANGE_END},
        {"start_date": RANGE_START, "end_date": (date.today() + timedelta(days=731)).isoformat()},
    ],
    ids=[
        "sin_fechas",
        "sin_end_date",
        "sin_start_date",
        "start_mayor_que_end",
        "start_antes_de_2000",
        "end_mas_de_hoy_730",
    ],
)
def test_summary_rejects_invalid_dates(client, db, small, dates):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)

    resp = client.get("/work-logs/summary", params={"company_id": str(small.company.id), **dates})

    assert resp.status_code == 422, resp.text


def test_summary_accepts_boundary_dates(client, db, small):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)
    max_end = (date.today() + timedelta(days=730)).isoformat()

    lower = _get_summary(client, company_id=small.company.id, start_date="2000-01-01", end_date="2000-01-01")
    upper = _get_summary(client, company_id=small.company.id, start_date=RANGE_START, end_date=max_end)

    assert lower.status_code == 200, lower.text
    assert upper.status_code == 200, upper.text


def test_summary_empty_range_returns_zero_totals(client, db, small):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id, start_date="2020-01-01", end_date="2020-01-31")

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["totals"]["logsCount"] == 0
    assert body["totals"]["totalHours"] == 0
    assert body["totals"]["totalNet"] == 0
    assert body["totals"]["totalGross"] == 0
    assert body["totals"]["uniqueDays"] == 0
    assert body["totals"]["activeUsers"] == 0
    assert body["byType"] == []
    assert body["byDay"] == []
    assert body["byUser"] == []


# --- 5. Cache Redis ---


def _summary_cache_keys(fake_redis, company_id):
    prefix = f"dashboard_summary:{company_id}:wls:"
    return [key for key in fake_redis.store if key.startswith(prefix)]


def test_second_identical_call_is_served_from_cache(client, db, small, fake_redis):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)
    first = _get_summary(client, company_id=small.company.id)
    assert first.status_code == 200, first.text
    assert len(_summary_cache_keys(fake_redis, small.company.id)) == 1

    # Escritura directa en BD (sin invalidar cache): si la segunda llamada coincide, sale de Redis.
    _add_log(db, small.worker_b, small.company, day=date(2026, 3, 10), duration=9.0)
    second = _get_summary(client, company_id=small.company.id)

    assert second.status_code == 200, second.text
    assert second.json() == first.json()


def test_creating_work_log_invalidates_summary_cache(client, db, small, fake_redis):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)
    first = _get_summary(client, company_id=small.company.id)
    assert first.status_code == 200, first.text
    assert _summary_cache_keys(fake_redis, small.company.id)

    body = {
        "type": "particular",
        "startDate": "2026-03-05",
        "endDate": "2026-03-05",
        "startTime": "09:00:00",
        "endTime": "11:00:00",
        "netAmount": 40.0,
        "userId": str(small.worker_a.id),
        "companyId": str(small.company.id),
    }
    created = client.post("/work-logs", json=body)
    assert created.status_code == 200, created.text

    assert _summary_cache_keys(fake_redis, small.company.id) == []
    after = _get_summary(client, company_id=small.company.id)
    assert after.status_code == 200, after.text
    assert after.json()["totals"]["logsCount"] == first.json()["totals"]["logsCount"] + 1


def test_summary_works_when_redis_is_down(client, db, small, fake_redis):
    fake_redis.raise_errors = True
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)

    resp = _get_summary(client, company_id=small.company.id)

    assert resp.status_code == 200, resp.text
    assert resp.json()["totals"]["logsCount"] == 4


# --- 6. Regresion: dashboard-summary existente ---


def test_existing_dashboard_summary_still_works(client, db, small):
    as_user(client, small.manager, small.company, claims=MANAGER_CLAIMS)
    start, end = RANGE_START, RANGE_END

    resp = client.get(
        f"/companies/{small.company.id}/dashboard-summary",
        params={"start_date": start, "end_date": end},
    )

    assert resp.status_code == 200, resp.text
    summary = resp.json()
    assert "todayMetrics" in summary
    assert "workersSummary" in summary
    # small: 2 + 2 + 3 + 1 horas en el rango
    assert summary["periodMetrics"]["totalHours"] == pytest.approx(8.0)
