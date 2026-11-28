"""
Recalculo de turnos al editar (R-TUR-19, R-TUR-20, R-TUR-21): PUT /work-logs/{id} y
POST /work-logs/{id}/recalculate-preview.

Contrato vigente:
- Por defecto, una edicion usa el snapshot del turno (rate_applied, definition, tax_applied). Cambiar
  la tarifa o la definicion del miembro/empresa despues de crear el turno no altera sus importes.
- Un cambio de `type` recalcula con la tarifa vigente del miembro. Si la membresia esta inactiva -> 403.
  Si no hay tarifa -> 400. Si el tipo no existe en worklog_definitions -> 400.
- `?recalculate_with_current_rates=true` (solo manager/PA) recalcula con tarifa y definicion vigentes.
- `POST /work-logs/{id}/recalculate-preview` calcula el importe actual frente al nuevo sin guardar cambios.
"""

import copy
import uuid

import models
import pytest

from tests.factories import as_user, make_company, make_member, make_user

PA_CLAIMS = {"is_admin": True}
MANAGER_CLAIMS = {"role": "manager"}
WORKER_CLAIMS = {"role": "worker"}

MSG_NO_RATE = "No se ha encontrado un precio (rate) configurado"


# --- Helpers ---


def _definitions(particular_unit="hours"):
    return {
        "particular": {"unit": particular_unit, "label": "Particular", "fields": []},
        "tutorial": {"unit": "days", "label": "Tutorial", "fields": []},
    }


def _rates(particular_base=20.0, tutorial_base=None, tax_overrides=None):
    rates = {
        "particular": {"base_rate": particular_base, "is_gross": True, "tax_overrides": tax_overrides or {}},
    }
    if tutorial_base is not None:
        rates["tutorial"] = {"base_rate": tutorial_base, "is_gross": False, "tax_overrides": {}}
    return rates


def _member(db, company, *, role="worker", is_active=True, rates=None):
    user = make_user(db)
    make_member(
        db,
        user,
        company,
        role=role,
        is_active=is_active,
        rates_config=rates if rates is not None else _rates(tutorial_base=100.0),
    )
    return user


def _calc_body(user, company):
    """Turno de 09:00 a 11:00 sin importe manual: el importe sale de la tarifa del miembro."""
    return {
        "type": "particular",
        "startDate": "2026-01-10",
        "endDate": "2026-01-10",
        "startTime": "09:00:00",
        "endTime": "11:00:00",
        "userId": str(user.id),
        "companyId": str(company.id),
    }


def _create(client, db, manager, company, worker):
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    resp = client.post("/work-logs", json=_calc_body(worker, company))
    assert resp.status_code == 200, resp.text
    return uuid.UUID(resp.json()["id"])


def _stored(db, log_id):
    """Relee el turno desde la BD (la sesion de test es la misma que usa la app)."""
    db.expire_all()
    return db.get(models.WorkLog, log_id)


def _amounts(db, log_id):
    log = _stored(db, log_id)
    return {"net": float(log.net_amount), "gross": float(log.gross_amount), "duration": float(log.duration)}


def _snapshot(db, log_id):
    return copy.deepcopy(_stored(db, log_id).calculation_snapshot)


def _set_snapshot(db, log_id, snapshot):
    log = db.get(models.WorkLog, log_id)
    log.calculation_snapshot = snapshot
    db.commit()


def _set_member_rates(db, worker, company, rates):
    member = db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one()
    member.rates_config = rates
    db.commit()


def _set_member_active(db, worker, company, is_active):
    member = db.query(models.CompanyMember).filter_by(user_id=worker.id, company_id=company.id).one()
    member.is_active = is_active
    db.commit()


def _set_company(db, company, **fields):
    for name, value in fields.items():
        setattr(company, name, value)
    db.commit()


# --- Edicion de campos sin recalculo ---


def test_description_only_keeps_amounts_and_snapshot_after_rate_change(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    before_amounts = _amounts(db, log_id)
    before_snapshot = _snapshot(db, log_id)
    _set_member_rates(db, worker, company, _rates(particular_base=50.0, tutorial_base=100.0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"description": "Correccion de texto"})

    assert resp.status_code == 200, resp.text
    assert _stored(db, log_id).description == "Correccion de texto"
    assert _amounts(db, log_id) == pytest.approx(before_amounts, abs=0.01)
    assert _stored(db, log_id).calculation_snapshot == before_snapshot


def test_resending_stored_net_amount_is_ignored_and_keeps_snapshot(client, db):
    """Importe no representable en binario (33.3): reenviar netAmount se ignora y conserva el snapshot."""
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates={"particular": {"base_rate": 16.65, "is_gross": False, "tax_overrides": {}}})
    log_id = _create(client, db, manager, company, worker)
    before_snapshot = _snapshot(db, log_id)
    stored_net = _stored(db, log_id).net_amount
    assert round(float(stored_net), 2) == 33.3
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"netAmount": 999.0, "description": "x"})

    assert resp.status_code == 200, resp.text
    assert round(float(_stored(db, log_id).net_amount), 2) == 33.3
    assert _snapshot(db, log_id) == before_snapshot


# --- Cambio de endTime: snapshot del turno ---


def test_end_time_change_uses_snapshot_rate_and_definition(client, db):
    company = make_company(db, worklog_definitions=_definitions(particular_unit="hours"))
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    # Tarifa vigente y definicion vigente distintas de las del snapshot
    _set_member_rates(db, worker, company, _rates(particular_base=50.0, tutorial_base=100.0))
    _set_company(db, company, worklog_definitions=_definitions(particular_unit="fixed"))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"endTime": "12:00:00"})

    assert resp.status_code == 200, resp.text
    amounts = _amounts(db, log_id)
    # 3 h x 20 EUR/h = 60 bruto; neto = 60 * (1 - 0.0648)
    assert amounts["duration"] == pytest.approx(3.0)
    assert amounts["gross"] == pytest.approx(60.0, abs=0.01)
    assert amounts["net"] == pytest.approx(56.112, abs=0.01)
    snapshot = _stored(db, log_id).calculation_snapshot
    assert snapshot["rate_applied"]["base_rate"] == 20.0
    assert snapshot["definition"]["unit"] == "hours"


def test_end_time_change_uses_snapshot_tax_applied_even_if_company_taxes_change(client, db):
    company = make_company(db, tax_config={"social_security": 0.0648})
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_company(db, company, tax_config={"social_security": 0.30})
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"endTime": "12:00:00"})

    assert resp.status_code == 200, resp.text
    # Con el impuesto del snapshot (0.0648) el neto es 60 * 0.9352 = 56.112; con el vigente seria 42.0
    assert _amounts(db, log_id)["net"] == pytest.approx(56.112, abs=0.01)
    assert _stored(db, log_id).calculation_snapshot["tax_applied"] == {"social_security": 0.0648}


def test_old_snapshot_without_tax_applied_uses_resolve_taxes(client, db):
    company = make_company(db, tax_config={"social_security": 0.0648})
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates=_rates(tax_overrides={"irpf": 0.15}, tutorial_base=100.0))
    log_id = _create(client, db, manager, company, worker)
    # Turno antiguo: el snapshot no tiene tax_applied
    snapshot = _snapshot(db, log_id)
    snapshot.pop("tax_applied", None)
    _set_snapshot(db, log_id, snapshot)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"endTime": "12:00:00"})

    assert resp.status_code == 200, resp.text
    # resolve_taxes(company.tax_config, rate_applied.tax_overrides) = 0.0648 + 0.15 = 0.2148
    # neto = 60 * (1 - 0.2148) = 47.112
    assert _amounts(db, log_id)["net"] == pytest.approx(47.112, abs=0.01)


# --- Cambio de type: tarifa vigente del miembro ---


def test_type_change_uses_current_member_rate(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_member_rates(db, worker, company, _rates(particular_base=20.0, tutorial_base=120.0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"type": "tutorial"})

    assert resp.status_code == 200, resp.text
    stored = _stored(db, log_id)
    assert stored.type == "tutorial"
    # Tutorial por dias: 1 dia x 120 EUR, tarifa neta
    assert float(stored.net_amount) == pytest.approx(120.0, abs=0.01)
    assert stored.calculation_snapshot["rate_applied"]["base_rate"] == 120.0
    assert stored.calculation_snapshot["definition"]["unit"] == "days"


def test_type_change_with_inactive_membership_returns_403(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_member_active(db, worker, company, False)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"type": "tutorial"})

    assert resp.status_code == 403, resp.text
    assert _stored(db, log_id).type == "particular"


def test_type_change_without_rate_returns_400(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates=_rates())  # sin tarifa para "tutorial"
    log_id = _create(client, db, manager, company, worker)
    before = _amounts(db, log_id)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"type": "tutorial"})

    assert resp.status_code == 400, resp.text
    assert MSG_NO_RATE in str(resp.json()["detail"])
    assert _stored(db, log_id).type == "particular"
    assert _amounts(db, log_id) == pytest.approx(before, abs=0.01)


# --- ?recalculate_with_current_rates ---


@pytest.mark.parametrize("role", ["manager", "pa"])
def test_recalculate_flag_uses_current_rate_and_definition(client, db, role):
    company = make_company(db, worklog_definitions=_definitions(particular_unit="hours"))
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_member_rates(db, worker, company, _rates(particular_base=50.0, tutorial_base=100.0))
    _set_company(db, company, worklog_definitions=_definitions(particular_unit="fixed"))
    editor = manager if role == "manager" else make_user(db, role="admin")
    claims = MANAGER_CLAIMS if role == "manager" else PA_CLAIMS
    as_user(client, editor, company, claims=claims)

    resp = client.put(
        f"/work-logs/{log_id}",
        params={"recalculate_with_current_rates": "true"},
        json={"description": "Recalculo con tarifa vigente"},
    )

    assert resp.status_code == 200, resp.text
    # Definicion fixed: duracion 1 y base = 50 EUR; bruto 50, neto 50 * 0.9352 = 46.76
    assert _amounts(db, log_id)["net"] == pytest.approx(46.76, abs=0.01)
    snapshot = _stored(db, log_id).calculation_snapshot
    assert snapshot["rate_applied"]["base_rate"] == 50.0
    assert snapshot["definition"]["unit"] == "fixed"


def test_recalculate_flag_is_forbidden_for_worker(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    before_amounts = _amounts(db, log_id)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(
        f"/work-logs/{log_id}",
        params={"recalculate_with_current_rates": "true"},
        json={"description": "Intento de recalculo"},
    )

    assert resp.status_code == 403, resp.text
    assert _stored(db, log_id).description is None
    assert _amounts(db, log_id) == pytest.approx(before_amounts, abs=0.01)


# --- Previsualizacion de recalculo (POST /work-logs/{id}/recalculate-preview) ---


@pytest.mark.parametrize("role", ["manager", "pa"])
def test_preview_recalculate_with_current_rates_compares_without_saving(client, db, role):
    company = make_company(db, worklog_definitions=_definitions(particular_unit="hours"))
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    before_amounts = _amounts(db, log_id)
    before_snapshot = _snapshot(db, log_id)

    _set_member_rates(db, worker, company, _rates(particular_base=50.0, tutorial_base=100.0))
    _set_company(db, company, worklog_definitions=_definitions(particular_unit="fixed"))
    editor = manager if role == "manager" else make_user(db, role="admin")
    claims = MANAGER_CLAIMS if role == "manager" else PA_CLAIMS
    as_user(client, editor, company, claims=claims)

    resp = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "true"},
        json={},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["workLogId"] == str(log_id)
    assert body["currentNetAmount"] == pytest.approx(before_amounts["net"], abs=0.01)
    assert body["currentGrossAmount"] == pytest.approx(before_amounts["gross"], abs=0.01)
    assert body["newGrossAmount"] == pytest.approx(50.0, abs=0.01)
    assert body["newNetAmount"] == pytest.approx(46.76, abs=0.01)
    assert body["newDuration"] == pytest.approx(1.0)
    # No persiste cambios en BD
    assert _amounts(db, log_id) == pytest.approx(before_amounts, abs=0.01)
    assert _snapshot(db, log_id) == before_snapshot


def test_preview_type_change_is_allowed_for_autonomous_worker(client, db):
    company = make_company(db, is_managed=False, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates=_rates(particular_base=20.0, tutorial_base=120.0))
    log_id = _create(client, db, manager, company, worker)
    before_amounts = _amounts(db, log_id)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "false"},
        json={"type": "tutorial"},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["currentNetAmount"] == pytest.approx(before_amounts["net"], abs=0.01)
    assert body["newNetAmount"] == pytest.approx(120.0, abs=0.01)
    assert _stored(db, log_id).type == "particular"


def test_preview_recalculate_with_current_rates_is_forbidden_for_worker(client, db):
    company = make_company(db, is_managed=False, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "true"},
        json={},
    )

    assert resp.status_code == 403, resp.text


def test_preview_with_inactive_membership_returns_403(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_member_active(db, worker, company, False)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "true"},
        json={},
    )

    assert resp.status_code == 403, resp.text


def test_preview_with_unknown_type_or_missing_rate_returns_400(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates=_rates())  # sin tarifa de tutorial
    log_id = _create(client, db, manager, company, worker)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    unknown = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "false"},
        json={"type": "inexistente"},
    )
    missing_rate = client.post(
        f"/work-logs/{log_id}/recalculate-preview",
        params={"recalculate_with_current_rates": "false"},
        json={"type": "tutorial"},
    )

    assert unknown.status_code == 400, unknown.text
    assert missing_rate.status_code == 400, missing_rate.text


def test_preview_group_recalculate_returns_group_totals(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    workers = [_member(db, company), _member(db, company)]
    log_ids = _create_group(client, db, manager, company, workers)
    _set_member_rates(db, workers[0], company, _rates(particular_base=30.0, tutorial_base=100.0))
    _set_member_rates(db, workers[1], company, _rates(particular_base=40.0, tutorial_base=100.0))
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.post(
        f"/work-logs/{log_ids[0]}/recalculate-preview",
        params={"apply_to_group": "true", "recalculate_with_current_rates": "true"},
        json={},
    )

    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["applyToGroup"] is True
    assert body["groupCount"] == 2
    assert body["newGroupGrossAmount"] == pytest.approx(140.0, abs=0.01)


# --- Edicion de grupo: todo o nada ---


def _create_group(client, db, manager, company, workers):
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    body = {k: v for k, v in _calc_body(workers[0], company).items() if k != "userId"}
    body["userIds"] = [str(w.id) for w in workers]
    resp = client.post("/work-logs/bulk", json=body)
    assert resp.status_code == 200, resp.text
    group_id = resp.json()["groupId"]
    logs = db.query(models.WorkLog).filter(models.WorkLog.company_id == company.id).all()
    return [log.id for log in logs if (log.extra_data or {}).get("group_id") == group_id]


def test_group_edit_failure_rolls_back_whole_group_and_names_the_worker(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker_ok = _member(db, company)
    worker_inactive = _member(db, company)
    log_ids = _create_group(client, db, manager, company, [worker_ok, worker_inactive])
    assert len(log_ids) == 2
    _set_member_active(db, worker_inactive, company, False)
    before = {i: _amounts(db, i) for i in log_ids}
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_ids[0]}", params={"apply_to_group": "true"}, json={"type": "tutorial"})

    assert resp.status_code == 403, resp.text
    assert "Test User" in resp.json()["detail"]
    for log_id in log_ids:
        assert _stored(db, log_id).type == "particular"
        assert _amounts(db, log_id) == pytest.approx(before[log_id], abs=0.01)


def test_group_edit_success_updates_every_log(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    workers = [_member(db, company), _member(db, company)]
    log_ids = _create_group(client, db, manager, company, workers)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_ids[0]}", params={"apply_to_group": "true"}, json={"endTime": "13:00:00"})

    assert resp.status_code == 200, resp.text
    for log_id in log_ids:
        assert str(_stored(db, log_id).end_time) == "13:00:00"
