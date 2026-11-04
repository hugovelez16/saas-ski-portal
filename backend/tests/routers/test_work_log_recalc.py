"""
Recalculo de turnos al editar (T5): PUT /work-logs/{id} con y sin `recalculate_with_current_rates`.

Contrato nuevo:
- Por defecto, una edicion usa el snapshot del turno (rate_applied, definition, tax_applied). Cambiar
  la tarifa o la definicion del miembro/empresa despues de crear el turno no altera sus importes.
- Un cambio de `type` recalcula con la tarifa vigente del miembro. Si la membresia esta inactiva -> 422.
  Si no hay tarifa ni importe manual -> 400.
- Un importe manual (`netAmount` o `amount`) en el PUT manda siempre.
- `?recalculate_with_current_rates=true` (solo manager/PA) recalcula con tarifa y definicion vigentes.

Los turnos se crean por POST sin importe manual para que tengan snapshot real.
Tests escritos antes de la implementacion: los casos que fallan describen el contrato nuevo.
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


def test_resending_stored_net_amount_does_not_turn_log_into_manual(client, db):
    """Importe no representable en binario (33.3): reenviar el netAmount guardado no es un importe manual."""
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates={"particular": {"base_rate": 16.65, "is_gross": False, "tax_overrides": {}}})
    log_id = _create(client, db, manager, company, worker)
    stored_net = _stored(db, log_id).net_amount
    assert round(float(stored_net), 2) == 33.3
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"netAmount": float(stored_net), "description": "x"})

    assert resp.status_code == 200, resp.text
    assert _snapshot(db, log_id).get("type") != "manual_override"


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


def test_type_change_with_inactive_membership_returns_422(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    _set_member_active(db, worker, company, False)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"type": "tutorial"})

    assert resp.status_code == 422, resp.text
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


def test_type_change_without_rate_but_with_manual_amount_is_accepted(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company, rates=_rates())  # sin tarifa para "tutorial"
    log_id = _create(client, db, manager, company, worker)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={"type": "tutorial", "netAmount": 99.0})

    assert resp.status_code == 200, resp.text
    stored = _stored(db, log_id)
    assert stored.type == "tutorial"
    assert float(stored.net_amount) == pytest.approx(99.0, abs=0.01)


# --- Importe manual explicito ---


@pytest.mark.parametrize("amount_key", ["netAmount", "amount"])
def test_explicit_manual_amount_always_wins_over_recalculation(client, db, amount_key):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create(client, db, manager, company, worker)
    as_user(client, manager, company, claims=MANAGER_CLAIMS)

    resp = client.put(f"/work-logs/{log_id}", json={amount_key: 77.0, "endTime": "12:00:00"})

    assert resp.status_code == 200, resp.text
    assert float(_stored(db, log_id).net_amount) == pytest.approx(77.0, abs=0.01)


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


# --- Turno manual: el cliente elige conservar el importe o calcular por tarifa (409) ---


def _create_manual(client, db, manager, company, worker, amount=50.0):
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    resp = client.post("/work-logs", json={**_calc_body(worker, company), "netAmount": amount})
    assert resp.status_code == 200, resp.text
    return uuid.UUID(resp.json()["id"])


def test_manual_log_time_change_without_choice_returns_409_and_changes_nothing(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)
    before = _amounts(db, log_id)
    before_snapshot = _snapshot(db, log_id)

    resp = client.put(f"/work-logs/{log_id}", json={"endTime": "13:00:00"})

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"]["code"] == "manual_amount_choice"
    assert str(_stored(db, log_id).end_time) == "11:00:00"
    assert _amounts(db, log_id) == pytest.approx(before, abs=0.01)
    assert _snapshot(db, log_id) == before_snapshot


def test_manual_log_description_only_does_not_ask(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)

    resp = client.put(f"/work-logs/{log_id}", json={"description": "Nota"})

    assert resp.status_code == 200, resp.text
    assert _amounts(db, log_id)["net"] == pytest.approx(50.0, abs=0.01)


def test_manual_log_time_change_keeping_amount_stays_manual(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)

    resp = client.put(f"/work-logs/{log_id}", json={"endTime": "13:00:00", "netAmount": 50.0})

    assert resp.status_code == 200, resp.text
    assert str(_stored(db, log_id).end_time) == "13:00:00"
    assert _amounts(db, log_id)["net"] == pytest.approx(50.0, abs=0.01)
    assert _snapshot(db, log_id).get("type") == "manual_override"


def test_manual_log_time_change_with_recalculate_flag_uses_rate(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)

    resp = client.put(
        f"/work-logs/{log_id}", params={"recalculate_with_current_rates": "true"}, json={"endTime": "13:00:00"}
    )

    assert resp.status_code == 200, resp.text
    assert _snapshot(db, log_id).get("type") != "manual_override"
    # 4 h x 20 EUR bruto con 6,48 % de impuestos
    assert _amounts(db, log_id)["net"] == pytest.approx(80 * (1 - 0.0648), abs=0.01)


def test_worker_cannot_recalculate_manual_log_only_keep_amount(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    asks = client.put(f"/work-logs/{log_id}", json={"endTime": "13:00:00"})
    forced = client.put(
        f"/work-logs/{log_id}", params={"recalculate_with_current_rates": "true"}, json={"endTime": "13:00:00"}
    )
    keeps = client.put(f"/work-logs/{log_id}", json={"endTime": "13:00:00", "netAmount": 50.0})

    assert asks.status_code == 409, asks.text
    assert forced.status_code == 403, forced.text
    assert keeps.status_code == 200, keeps.text
    assert _snapshot(db, log_id).get("type") == "manual_override"


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

    assert resp.status_code == 422, resp.text
    assert "Test User" in resp.json()["detail"]
    for log_id in log_ids:
        assert _stored(db, log_id).type == "particular"
        assert _amounts(db, log_id) == pytest.approx(before[log_id], abs=0.01)


def test_worker_keep_manual_amount_flag_resolves_409(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    worker = _member(db, company)
    log_id = _create_manual(client, db, manager, company, worker)
    as_user(client, worker, company, claims=WORKER_CLAIMS)

    resp = client.put(
        f"/work-logs/{log_id}", params={"keep_manual_amount": "true"}, json={"endTime": "13:00:00"}
    )

    assert resp.status_code == 200, resp.text
    assert str(_stored(db, log_id).end_time) == "13:00:00"
    assert _amounts(db, log_id)["net"] == pytest.approx(50.0, abs=0.01)
    assert _snapshot(db, log_id).get("type") == "manual_override"


def test_group_edit_keep_amount_does_not_overwrite_other_manual_amounts(client, db):
    company = make_company(db, worklog_definitions=_definitions())
    manager = _member(db, company, role="manager")
    workers = [_member(db, company), _member(db, company)]
    as_user(client, manager, company, claims=MANAGER_CLAIMS)
    body = {k: v for k, v in _calc_body(workers[0], company).items() if k != "userId"}
    body.update({"userIds": [str(w.id) for w in workers], "netAmount": 50.0})
    resp = client.post("/work-logs/bulk", json=body)
    assert resp.status_code == 200, resp.text
    logs = db.query(models.WorkLog).filter(models.WorkLog.company_id == company.id).all()
    primary = next(log for log in logs if log.user_id == workers[0].id)
    other = next(log for log in logs if log.user_id == workers[1].id)
    other.net_amount = 70.0
    db.commit()

    asks = client.put(f"/work-logs/{primary.id}", params={"apply_to_group": "true"}, json={"endTime": "13:00:00"})
    keeps = client.put(
        f"/work-logs/{primary.id}",
        params={"apply_to_group": "true", "keep_manual_amount": "true"},
        json={"endTime": "13:00:00"},
    )

    assert asks.status_code == 409, asks.text
    assert keeps.status_code == 200, keeps.text
    assert _amounts(db, primary.id)["net"] == pytest.approx(50.0, abs=0.01)
    assert _amounts(db, other.id)["net"] == pytest.approx(70.0, abs=0.01)
    assert str(_stored(db, other.id).end_time) == "13:00:00"


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
