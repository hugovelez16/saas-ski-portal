"""
Administracion de empresas solo de plataforma (PR-06.0).

Describen el comportamiento objetivo de PR-06.1: solo el administrador de la plataforma (PA)
crea, edita y borra empresas; validacion de `name` (E1); borrado con motivos de bloqueo y sin
cascadas (E4); suspension y reactivacion con motivo (E5); `isManaged` (E6); eventos de
auditoria de empresa (A1); PUT sin cambios rechazado sin auditoria (E8); invalidacion de cache de acceso tras suspender; y empresa sin manager
como estado valido (E7). Tambien cubren la capa de servicio de P3 (`crud.update_company` y
`crud.get_company_for_actor`).

Hasta implementar PR-06.1 estas pruebas deben fallar por funcionalidad ausente.
"""

import copy
import uuid
from types import SimpleNamespace

import crud
import models
import pytest
import schemas
from access_policy import PolicyError

from tests.factories import as_user, make_company, make_member, make_token, make_user, make_work_log

MSG_NO_CHANGES = "No hay cambios que guardar"
MSG_DELETE_BLOCKED_PREFIX = "No se puede borrar la empresa"
MAX_NAME = "x" * 120
LONG_NAME = "x" * 121

# Matriz por actor: (nombre del actor, estado esperado en lectura/escritura de empresas)
ROLE_MATRIX = [
    pytest.param("manager", 403, id="manager"),
    pytest.param("worker", 403, id="worker"),
    pytest.param("pa", 200, id="pa"),
]

MANAGER_FORBIDDEN_UPDATES = [
    pytest.param({"name": "Cambiada"}, id="name"),
    pytest.param({"taxConfig": {"social_security": 0.1}}, id="tax_config"),
    pytest.param({"worklogDefinitions": {"guardia": {"unit": "hours", "label": "G", "fields": []}}}, id="worklog"),
    pytest.param({"settings": {"x": 1}}, id="settings"),
]

# payload del PUT del PA -> (accion de auditoria, campo del modelo que cambia)
EVENT_CASES = [
    pytest.param({"taxConfig": {"social_security": 0.1}}, "company.tax_config_changed", "tax_config", id="tax_config"),
    pytest.param({"settings": {"modules": {"coordination": True}}}, "company.settings_changed", "settings", id="settings"),
    pytest.param(
        {"worklogDefinitions": {"guardia": {"unit": "hours", "label": "Guardia", "fields": []}}},
        "company.worklog_definitions_changed",
        "worklog_definitions",
        id="worklog_definitions",
    ),
    pytest.param({"name": "Renombrada"}, "company.updated", "name", id="name"),
]


# --- Fixtures y helpers ---


@pytest.fixture
def world(db):
    """Empresa con manager y worker, PA de plataforma y una segunda empresa con su propio manager."""
    company = make_company(db, name="Escuela Norte")
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    worker = make_user(db)
    make_member(db, worker, company, role="worker")
    pa = make_user(db, role="admin")

    other = make_company(db, name="Escuela Sur")
    other_manager = make_user(db)
    make_member(db, other_manager, other, role="manager")

    return SimpleNamespace(
        company=company,
        manager=manager,
        worker=worker,
        pa=pa,
        other=other,
        other_manager=other_manager,
    )


def _actor(world, name):
    """Usuario y empresa del token para cada actor de la matriz."""
    return {
        "manager": (world.manager, world.company),
        "worker": (world.worker, world.company),
        "pa": (world.pa, world.company),
    }[name]


def _fresh_company(db, company_id):
    db.expire_all()
    return db.get(models.Company, company_id)


def _company_count(db):
    db.expire_all()
    return db.query(models.Company).count()


def _audit(db, action, company_id=None):
    db.expire_all()
    query = db.query(models.AuditLog).filter(models.AuditLog.action == action)
    if company_id is not None:
        query = query.filter(models.AuditLog.company_id == company_id)
    return query.all()


def _audit_count(db):
    db.expire_all()
    return db.query(models.AuditLog).count()


def _use_token(client, token):
    """Reutiliza un token ya emitido (mismo jti) en el cliente."""
    client.cookies.clear()
    client.cookies.set("access_token", token)


# --- 1. Matriz de permisos: solo PA gestiona empresas ---


@pytest.mark.parametrize("actor_name, expected", ROLE_MATRIX)
def test_get_companies_is_platform_admin_only(client, db, world, actor_name, expected):
    user, company = _actor(world, actor_name)
    as_user(client, user, company)

    resp = client.get("/companies")

    assert resp.status_code == expected, resp.text


@pytest.mark.parametrize("actor_name, expected", ROLE_MATRIX)
def test_create_company_is_platform_admin_only(client, db, world, actor_name, expected):
    user, company = _actor(world, actor_name)
    as_user(client, user, company)
    before = _company_count(db)

    resp = client.post("/companies", json={"name": "Nueva Escuela", "taxConfig": {}})

    assert resp.status_code == expected, resp.text
    assert _company_count(db) == before + (1 if expected == 200 else 0)


@pytest.mark.parametrize("actor_name, expected", ROLE_MATRIX)
def test_update_company_is_platform_admin_only(client, db, world, actor_name, expected):
    user, company = _actor(world, actor_name)
    as_user(client, user, company)
    cid = world.company.id

    resp = client.put(f"/companies/{cid}", json={"name": "Renombrada"})

    assert resp.status_code == expected, resp.text
    expected_name = "Renombrada" if expected == 200 else "Escuela Norte"
    assert _fresh_company(db, cid).name == expected_name


@pytest.mark.parametrize("payload", MANAGER_FORBIDDEN_UPDATES)
def test_manager_cannot_change_name_tax_definitions_or_settings(client, db, world, payload):
    cid = world.company.id
    before = copy.deepcopy(
        {
            "name": world.company.name,
            "tax_config": world.company.tax_config,
            "worklog_definitions": world.company.worklog_definitions,
            "settings": world.company.settings,
        }
    )
    as_user(client, world.manager, world.company)

    resp = client.put(f"/companies/{cid}", json=payload)

    assert resp.status_code == 403, resp.text
    company = _fresh_company(db, cid)
    after = {
        "name": company.name,
        "tax_config": company.tax_config,
        "worklog_definitions": company.worklog_definitions,
        "settings": company.settings,
    }
    assert after == before


VIEW_AS_WRITES = [
    pytest.param(lambda c, cid: c.post("/companies", json={"name": "Nueva", "taxConfig": {}}), id="create"),
    pytest.param(lambda c, cid: c.put(f"/companies/{cid}", json={"name": "Otra"}), id="update"),
    pytest.param(lambda c, cid: c.delete(f"/companies/{cid}"), id="delete"),
]


@pytest.mark.parametrize("write", VIEW_AS_WRITES)
def test_pa_in_view_as_mode_cannot_write_companies(client, db, world, write):
    cid = world.company.id
    as_user(client, world.pa, world.company, claims={"view_as": "worker"})

    resp = write(client, cid)

    assert resp.status_code == 403, resp.text
    company = _fresh_company(db, cid)
    assert company is not None
    assert company.name == "Escuela Norte"


# --- 2. E1: validacion de name ---


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(None, id="null"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="only_spaces"),
        pytest.param(LONG_NAME, id="over_120_chars"),
    ],
)
def test_create_company_rejects_invalid_name(client, db, world, name):
    as_user(client, world.pa)
    before = _company_count(db)

    resp = client.post("/companies", json={"name": name})

    assert resp.status_code == 422, resp.text
    assert _company_count(db) == before


def test_create_company_accepts_name_of_exactly_120_chars(client, db, world):
    as_user(client, world.pa)

    resp = client.post("/companies", json={"name": MAX_NAME, "taxConfig": {}})

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == MAX_NAME


def test_create_company_strips_surrounding_spaces_from_name(client, db, world):
    as_user(client, world.pa)

    resp = client.post("/companies", json={"name": " Nueva  ", "taxConfig": {}})

    assert resp.status_code == 200, resp.text
    assert resp.json()["name"] == "Nueva"
    assert _fresh_company(db, uuid.UUID(resp.json()["id"])).name == "Nueva"


@pytest.mark.parametrize(
    "name",
    [
        pytest.param(None, id="null"),
        pytest.param("", id="empty"),
        pytest.param("   ", id="only_spaces"),
        pytest.param(LONG_NAME, id="over_120_chars"),
    ],
)
def test_update_company_rejects_invalid_name_with_422(client, db, world, name):
    """Un PUT con name nulo debe responder 422, nunca 500 por violar NOT NULL."""
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"/companies/{cid}", json={"name": name})

    assert resp.status_code == 422, resp.text
    assert _fresh_company(db, cid).name == "Escuela Norte"


# --- 3. E4: borrado de empresas ---


def test_pa_deletes_empty_company_and_audits_snapshot(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, name="Vacia", is_active=True, is_managed=False)
    cid = company.id
    as_user(client, pa, company)

    resp = client.delete(f"/companies/{cid}")

    assert resp.status_code == 204, resp.text
    assert _fresh_company(db, cid) is None
    rows = _audit(db, "company.deleted")
    assert len(rows) == 1
    assert rows[0].old_value == {"name": "Vacia", "is_active": True, "is_managed": False}
    assert rows[0].actor_user_id == pa.id


def test_delete_company_with_members_and_shifts_returns_409_without_cascade(client, db, world):
    cid = world.company.id
    for _ in range(10):
        make_work_log(db, world.worker, world.company)
    as_user(client, world.pa, world.company)

    resp = client.delete(f"/companies/{cid}")

    assert resp.status_code == 409, resp.text
    assert resp.json()["detail"] == "No se puede borrar la empresa: tiene 2 miembros, 10 turnos"
    db.expire_all()
    assert db.get(models.Company, cid) is not None
    assert db.query(models.CompanyMember).filter_by(company_id=cid).count() == 2
    assert db.query(models.WorkLog).filter_by(company_id=cid).count() == 10
    assert _audit(db, "company.deleted") == []


def test_delete_company_with_module_subscription_returns_409(client, db, world):
    cid = world.company.id
    module = models.AppModule(code_name="export_pdf", name="Exportar PDF", is_active=True)
    db.add(module)
    db.commit()
    db.add(
        models.ModuleSubscription(
            module_id=module.id,
            company_id=cid,
            user_id=None,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
        )
    )
    db.commit()
    as_user(client, world.pa, world.company)

    resp = client.delete(f"/companies/{cid}")

    assert resp.status_code == 409, resp.text
    detail = resp.json()["detail"]
    assert detail.startswith(MSG_DELETE_BLOCKED_PREFIX)
    assert "suscripci" in detail
    assert _fresh_company(db, cid) is not None


def test_manager_cannot_delete_company(client, db, world):
    cid = world.company.id
    as_user(client, world.manager, world.company)

    resp = client.delete(f"/companies/{cid}")

    assert resp.status_code == 403, resp.text
    assert _fresh_company(db, cid) is not None


# --- 4. E5: suspension y reactivacion con motivo ---


def test_suspend_company_audits_actor_and_reason(client, db, world):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"/companies/{cid}", json={"isActive": False, "reason": "Impago"})

    assert resp.status_code == 200, resp.text
    rows = _audit(db, "company.suspended", cid)
    assert len(rows) == 1
    assert rows[0].actor_user_id == world.pa.id
    assert rows[0].reason == "Impago"
    assert _fresh_company(db, cid).is_active is False


def test_reactivate_company_audits_reactivated(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, is_active=False)
    cid = company.id
    as_user(client, pa, company)

    resp = client.put(f"/companies/{cid}", json={"isActive": True})

    assert resp.status_code == 200, resp.text
    rows = _audit(db, "company.reactivated", cid)
    assert len(rows) == 1
    assert rows[0].actor_user_id == pa.id
    assert _audit(db, "company.suspended", cid) == []
    assert _fresh_company(db, cid).is_active is True


# --- 5. E6: isManaged ---


def test_managed_change_audits_flag_and_does_not_recalculate_shifts(client, db, world):
    cid = world.company.id
    shift = make_work_log(db, world.worker, world.company, net_amount=40.0)
    shift_id = shift.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"/companies/{cid}", json={"isManaged": True})

    assert resp.status_code == 200, resp.text
    rows = _audit(db, "company.managed_changed", cid)
    assert len(rows) == 1
    assert rows[0].old_value == {"is_managed": False}
    assert rows[0].new_value == {"is_managed": True}
    assert rows[0].actor_user_id == world.pa.id
    db.expire_all()
    assert db.get(models.WorkLog, shift_id).net_amount == 40.0


# --- 6. A1: eventos de auditoria de empresa ---


@pytest.mark.parametrize("payload, action, field", EVENT_CASES)
def test_pa_update_emits_event_with_only_the_changed_field(client, db, world, payload, action, field):
    cid = world.company.id
    as_user(client, world.pa, world.company)

    resp = client.put(f"/companies/{cid}", json=payload)

    assert resp.status_code == 200, resp.text
    rows = _audit(db, action, cid)
    assert len(rows) == 1
    assert set(rows[0].old_value) == {field}
    assert set(rows[0].new_value) == {field}
    assert rows[0].new_value[field] == next(iter(payload.values()))
    assert rows[0].actor_user_id == world.pa.id


def test_create_company_emits_company_created(client, db, world):
    as_user(client, world.pa)

    resp = client.post("/companies", json={"name": "Nueva", "taxConfig": {}})

    assert resp.status_code == 200, resp.text
    rows = _audit(db, "company.created", uuid.UUID(resp.json()["id"]))
    assert len(rows) == 1
    assert rows[0].actor_user_id == world.pa.id


# --- 7. E8: PUT sin cambios ---


@pytest.mark.parametrize(
    "payload",
    [
        pytest.param({}, id="empty_body"),
        pytest.param({"name": "Escuela Norte"}, id="same_name"),
        pytest.param({"isActive": True}, id="same_is_active"),
        pytest.param({"taxConfig": {"social_security": 0.0648}}, id="same_tax_config"),
    ],
)
def test_update_without_changes_returns_422_and_writes_no_audit(client, db, world, payload):
    as_user(client, world.pa, world.company)
    before = _audit_count(db)

    resp = client.put(f"/companies/{world.company.id}", json=payload)

    assert resp.status_code == 422, resp.text
    assert resp.json()["detail"] == MSG_NO_CHANGES
    assert _audit_count(db) == before


# --- 8. P3: capa de servicio ---


def test_update_company_service_rejects_non_platform_admin_actor(db, world):
    cid = world.company.id

    for actor in (world.manager, world.worker):
        with pytest.raises(PolicyError) as exc:
            crud.update_company(db, cid, schemas.CompanyUpdate(name="Otra"), actor=actor)
        assert exc.value.status_code == 403

    assert _fresh_company(db, cid).name == "Escuela Norte"


def test_get_company_for_actor_scopes_by_membership(db, world):
    own = crud.get_company_for_actor(db, world.company.id, actor=world.manager)
    assert own is not None
    assert own.id == world.company.id

    assert crud.get_company_for_actor(db, world.company.id, actor=world.other_manager) is None


def test_pa_user_companies_include_is_active_and_is_managed(client, db):
    pa = make_user(db, role="admin")
    company = make_company(db, is_active=False, is_managed=True)
    cid = str(company.id)
    make_member(db, pa, company, role="manager")
    as_user(client, pa)

    resp = client.get("/users/me/companies")

    assert resp.status_code == 200, resp.text
    entries = {item["id"]: item for item in resp.json()}
    assert cid in entries, resp.text
    assert entries[cid]["isActive"] is False
    assert entries[cid]["isManaged"] is True


# --- 10. Cache de acceso tras suspension ---


def test_suspension_blocks_manager_with_token_still_valid(client, db, world):
    cid = world.company.id
    manager_token = make_token(world.manager, world.company)
    _use_token(client, manager_token)
    assert client.get(f"/companies/{cid}/members").status_code == 200

    as_user(client, world.pa, world.company)
    resp = client.put(f"/companies/{cid}", json={"isActive": False, "reason": "Impago"})
    assert resp.status_code == 200, resp.text

    _use_token(client, manager_token)
    resp = client.get(f"/companies/{cid}/members")

    assert resp.status_code == 403, resp.text


# --- 11. E7: empresa sin manager es un estado valido ---


def test_company_without_manager_is_readable_by_platform_admin(client, db):
    company = make_company(db)
    pa = make_user(db, role="admin")
    as_user(client, pa, company)

    resp = client.get(f"/companies/{company.id}")

    assert resp.status_code == 200, resp.text


def test_pa_adds_manager_to_company_without_one(client, db):
    company = make_company(db)
    cid = company.id
    pa = make_user(db, role="admin")
    candidate = make_user(db)
    as_user(client, pa, company)

    resp = client.post(f"/companies/{cid}/members/add", json={"email": candidate.email})
    assert resp.status_code == 200, resp.text
    resp = client.put(f"/companies/{cid}/members/{candidate.id}/role", json={"role": "manager"})

    assert resp.status_code == 200, resp.text
    assert resp.json()["role"] == "manager"


def test_deactivating_sole_manager_is_allowed(client, db):
    company = make_company(db)
    cid = company.id
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    pa = make_user(db, role="admin")
    as_user(client, pa, company)

    resp = client.put(f"/companies/{cid}/members/{manager.id}/status", params={"status": "inactive"})

    assert resp.status_code == 200, resp.text


def test_demoting_sole_manager_is_allowed(client, db):
    company = make_company(db)
    cid = company.id
    manager = make_user(db)
    make_member(db, manager, company, role="manager")
    pa = make_user(db, role="admin")
    as_user(client, pa, company)

    resp = client.put(f"/companies/{cid}/members/{manager.id}/role", json={"role": "worker"})

    assert resp.status_code == 200, resp.text
