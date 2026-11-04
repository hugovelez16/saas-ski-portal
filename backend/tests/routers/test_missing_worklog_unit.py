"""
Tipo de turno sin `unit` en su definicion: la API responde 422 con mensaje claro (no 500).

Cubre crear, editar y crear en lote por HTTP, y el contrato de `crud.get_worklog_unit`
(sigue siendo ValueError, pero con la subclase MissingWorklogUnitError).
"""

import crud
import pytest
from contracts import MissingWorklogUnitError

from tests.factories import as_user, make_company, make_member, make_user, make_work_log

MSG_MISSING_UNIT = "El tipo de turno no tiene unidad definida (unit)"

# Definicion del tipo de turno sin la clave `unit` (insertada directamente en la BD de prueba).
DEFS_WITHOUT_UNIT = {"particular": {"label": "Particular", "fields": []}}

WORKER_CLAIMS = {"role": "worker"}
MANAGER_CLAIMS = {"role": "manager"}


def _body(user, company, **extra):
    body = {
        "type": "particular",
        "startDate": "2026-01-10",
        "endDate": "2026-01-10",
        "startTime": "09:00:00",
        "endTime": "11:00:00",
        "netAmount": 40.0,
        "userId": str(user.id),
        "companyId": str(company.id),
    }
    body.update(extra)
    return body


def _bulk_body(company, users):
    body = _body(users[0], company)
    body.pop("userId")
    body["userIds"] = [str(u.id) for u in users]
    return body


def test_create_work_log_without_unit_returns_422(client, db):
    company = make_company(db, worklog_definitions=DEFS_WITHOUT_UNIT)
    worker = make_user(db)
    make_member(db, worker, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post("/work-logs", json=_body(worker, company))

    assert resp.status_code == 422, resp.text
    assert resp.json() == {"detail": MSG_MISSING_UNIT}


def test_update_work_log_without_unit_returns_422(client, db):
    company = make_company(db, worklog_definitions=DEFS_WITHOUT_UNIT)
    worker = make_user(db)
    make_member(db, worker, company)
    log = make_work_log(db, worker, company)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(f"/work-logs/{log.id}", json=_body(worker, company, netAmount=55.0))

    assert resp.status_code == 422, resp.text
    assert resp.json() == {"detail": MSG_MISSING_UNIT}


def test_bulk_create_without_unit_returns_422(client, db):
    company = make_company(db, worklog_definitions=DEFS_WITHOUT_UNIT)
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post("/work-logs/bulk", json=_bulk_body(company, [worker]))

    assert resp.status_code == 422, resp.text
    assert resp.json() == {"detail": MSG_MISSING_UNIT}


def test_get_worklog_unit_raises_missing_unit_error():
    with pytest.raises(MissingWorklogUnitError, match="no tiene unidad definida") as exc_info:
        crud.get_worklog_unit({"label": "Particular", "fields": []})

    assert isinstance(exc_info.value, ValueError)
    assert str(exc_info.value) == MSG_MISSING_UNIT


def test_get_worklog_unit_returns_unit_when_defined():
    assert crud.get_worklog_unit({"unit": "days"}) == "days"
