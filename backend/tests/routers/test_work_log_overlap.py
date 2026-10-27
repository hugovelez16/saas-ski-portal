"""
Avisos de solape de turnos (T7).

POST /work-logs, POST /work-logs/bulk y PUT /work-logs/{id} devuelven `warnings`: una lista de
{"code": "overlap", "message": ..., "conflictingLogIds": [...]} y, solo en bulk, "userId".
Solo avisan: el turno se crea o edita igualmente (status 200).

Incluye tests puros de work_log_rules.find_overlaps. El import se hace dentro de un helper para que
los tests HTTP se reporten individualmente aunque el modulo aun no exista.
Tests escritos antes de la implementacion.
"""

from datetime import date, time

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

OVERLAP_MESSAGE = "Este turno se solapa con otro del mismo trabajador"
MANAGER_CLAIMS = {"role": "manager"}


# --- Helpers ---


def _definitions():
    return {
        "particular": {"unit": "hours", "label": "Particular", "fields": []},
        "tutorial": {"unit": "days", "label": "Tutorial", "fields": []},
    }


def _company(db):
    return make_company(db, worklog_definitions=_definitions())


def _member(db, company, *, role="worker"):
    user = make_user(db)
    make_member(db, user, company, role=role)
    return user


def _body(user, company, **extra):
    """Turno con importe manual (no necesita tarifa). Por defecto 10:00-11:00 del 2026-01-10."""
    body = {
        "type": "particular",
        "startDate": "2026-01-10",
        "endDate": "2026-01-10",
        "startTime": "10:00:00",
        "endTime": "11:00:00",
        "netAmount": 40.0,
        "userId": str(user.id),
        "companyId": str(company.id),
    }
    body.update(extra)
    return body


def _without(body, *keys):
    return {k: v for k, v in body.items() if k not in keys}


def _bulk_body(company, users, **extra):
    body = _without(_body(users[0], company), "userId")
    body["userIds"] = [str(u.id) for u in users]
    body.update(extra)
    return body


def _overlap_warning(*conflicting_ids, user_id=None):
    warning = {
        "code": "overlap",
        "message": OVERLAP_MESSAGE,
        "conflictingLogIds": [str(i) for i in conflicting_ids],
        # WorkLogWarning.user_id es opcional: null fuera de bulk
        "userId": str(user_id) if user_id is not None else None,
    }
    return warning


def _find_overlaps(candidate, existing):
    # Import diferido: work_log_rules puede no existir todavia.
    from work_log_rules import find_overlaps

    return find_overlaps(candidate, existing)


# --- POST /work-logs ---


def test_post_overlap_warns_and_still_creates_the_log(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    existing = make_work_log(db, worker, company, start_time=time(9, 0), end_time=time(11, 0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == [_overlap_warning(existing.id)]
    assert db.query(models.WorkLog).filter(models.WorkLog.user_id == worker.id).count() == 2


def test_post_without_overlap_returns_empty_warnings(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    make_work_log(db, worker, company, start_time=time(9, 0), end_time=time(11, 0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, startTime="12:00:00", endTime="13:00:00"))

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == []


def test_post_contiguous_logs_do_not_overlap(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    make_work_log(db, worker, company, start_time=time(9, 0), end_time=time(10, 0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company, startTime="10:00:00", endTime="11:00:00"))

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == []


@pytest.mark.parametrize(
    "start_hour, end_hour, expect_overlap",
    [(1, 3, True), (3, 5, False)],
    ids=["solapa_01_03", "no_solapa_03_05"],
)
def test_post_cross_midnight_is_compared_as_datetime_interval(client, db, start_hour, end_hour, expect_overlap):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    # Turno del dia siguiente, de start_hour a end_hour
    existing = make_work_log(
        db,
        worker,
        company,
        start_date=date(2026, 1, 11),
        start_time=time(start_hour, 0),
        end_time=time(end_hour, 0),
    )
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    # Turno 22:00 del 10 a 02:00 (cruza medianoche)
    resp = client.post(
        "/work-logs",
        json=_body(worker, company, startTime="22:00:00", endTime="02:00:00"),
    )

    assert resp.status_code == 200, resp.text
    expected = [_overlap_warning(existing.id)] if expect_overlap else []
    assert resp.json()["warnings"] == expected


@pytest.mark.parametrize(
    "start, end, expect_overlap",
    [("2026-01-12", "2026-01-13", True), ("2026-01-13", "2026-01-14", False)],
    ids=["solapa_por_fecha", "no_solapa_por_fecha"],
)
def test_post_days_unit_overlaps_by_date_range(client, db, start, end, expect_overlap):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    # Tutorial por dias del 10 al 12 (sin horas)
    existing = make_work_log(
        db,
        worker,
        company,
        type="tutorial",
        start_date=date(2026, 1, 10),
        end_date=date(2026, 1, 12),
        start_time=None,
        end_time=None,
    )
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    body = _without(_body(worker, company, type="tutorial", startDate=start, endDate=end), "startTime", "endTime")
    resp = client.post("/work-logs", json=body)

    assert resp.status_code == 200, resp.text
    expected = [_overlap_warning(existing.id)] if expect_overlap else []
    assert resp.json()["warnings"] == expected


def test_post_same_user_in_other_company_does_not_warn(client, db):
    company_a = _company(db)
    company_b = _company(db)
    manager_a = _member(db, company_a, role="manager")
    worker = make_user(db)
    make_member(db, worker, company_a)
    make_member(db, worker, company_b)
    make_work_log(db, worker, company_b, start_time=time(9, 0), end_time=time(11, 0))
    as_user(client, manager_a, company_a, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company_a))

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == []


# --- PUT /work-logs/{id} ---


def test_put_does_not_overlap_with_itself(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log = make_work_log(db, worker, company, start_time=time(9, 0), end_time=time(11, 0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json={"endTime": "11:30:00"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == []


def test_put_moved_onto_other_log_warns_with_that_log_only(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    other = make_work_log(db, worker, company, start_time=time(9, 0), end_time=time(11, 0))
    moved = make_work_log(db, worker, company, start_time=time(12, 0), end_time=time(13, 0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{moved.id}", json={"startTime": "10:00:00", "endTime": "10:30:00"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["warnings"] == [_overlap_warning(other.id)]


# --- POST /work-logs/bulk ---


def test_bulk_warns_once_per_overlapping_user_with_user_id(client, db):
    company = _company(db)
    manager = _member(db, company, role="manager")
    worker_1 = _member(db, company)
    worker_2 = _member(db, company)
    worker_free = _member(db, company)
    log_1 = make_work_log(db, worker_1, company, start_time=time(9, 0), end_time=time(11, 0))
    log_2 = make_work_log(db, worker_2, company, start_time=time(9, 30), end_time=time(10, 30))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs/bulk", json=_bulk_body(company, [worker_1, worker_2, worker_free]))

    assert resp.status_code == 200, resp.text
    warnings = resp.json()["warnings"]
    assert len(warnings) == 2
    by_user = {w["userId"]: w for w in warnings}
    assert by_user[str(worker_1.id)] == _overlap_warning(log_1.id, user_id=worker_1.id)
    assert by_user[str(worker_2.id)] == _overlap_warning(log_2.id, user_id=worker_2.id)
    assert str(worker_free.id) not in by_user


# --- find_overlaps (funcion pura) ---


def _interval(item_id, start_date, end_date, start_time=None, end_time=None):
    return {
        "id": item_id,
        "start_date": start_date,
        "end_date": end_date,
        "start_time": start_time,
        "end_time": end_time,
    }


def test_find_overlaps_same_day_intervals_overlap():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 10), time(10, 0), time(12, 0))
    existing = [_interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(11, 0))]

    assert _find_overlaps(candidate, existing) == ["a"]


def test_find_overlaps_contiguous_intervals_do_not_overlap():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 10), time(10, 0), time(11, 0))
    existing = [_interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(10, 0))]

    assert _find_overlaps(candidate, existing) == []


def test_find_overlaps_excludes_candidate_itself_by_id():
    candidate = _interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(11, 0))
    existing = [_interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(11, 0))]

    assert _find_overlaps(candidate, existing) == []


def test_find_overlaps_candidate_without_id_matches_every_existing_log():
    candidate = {
        "start_date": date(2026, 1, 10),
        "end_date": date(2026, 1, 10),
        "start_time": time(10, 0),
        "end_time": time(11, 0),
    }
    existing = [_interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(11, 0))]

    assert _find_overlaps(candidate, existing) == ["a"]


def test_find_overlaps_cross_midnight_candidate_overlaps_next_day_interval():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 11), time(22, 0), time(2, 0))
    existing = [
        _interval("a", date(2026, 1, 11), date(2026, 1, 11), time(1, 0), time(3, 0)),
        _interval("b", date(2026, 1, 11), date(2026, 1, 11), time(2, 0), time(4, 0)),
    ]

    # "b" empieza justo cuando termina el candidato: contiguo, no solapa
    assert _find_overlaps(candidate, existing) == ["a"]


def test_find_overlaps_days_unit_without_times_compares_date_range():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 12))
    existing = [
        _interval("a", date(2026, 1, 12), date(2026, 1, 12)),
        _interval("b", date(2026, 1, 13), date(2026, 1, 13)),
    ]

    assert _find_overlaps(candidate, existing) == ["a"]


def test_find_overlaps_empty_existing_returns_empty_list():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 10), time(10, 0), time(11, 0))

    assert _find_overlaps(candidate, []) == []


def test_find_overlaps_returns_every_conflicting_id():
    candidate = _interval("c", date(2026, 1, 10), date(2026, 1, 10), time(10, 0), time(12, 0))
    existing = [
        _interval("a", date(2026, 1, 10), date(2026, 1, 10), time(9, 0), time(11, 0)),
        _interval("b", date(2026, 1, 10), date(2026, 1, 10), time(11, 0), time(13, 0)),
        _interval("d", date(2026, 1, 10), date(2026, 1, 10), time(13, 0), time(14, 0)),
    ]

    assert sorted(_find_overlaps(candidate, existing)) == ["a", "b"]
