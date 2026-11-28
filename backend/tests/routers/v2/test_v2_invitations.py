"""Pruebas HTTP y de reglas de negocio para invitaciones por correo (#139: R-MEM-07, R-MEM-23 a R-MEM-25)."""

import uuid
from datetime import UTC, datetime, timedelta

import email_utils
import models
import pytest
from domain.entities.company_invitation import ensure_utc, hash_invitation_token
from sqlalchemy.exc import IntegrityError

from tests.factories import as_user, make_company, make_member, make_user


@pytest.fixture
def sent_emails(monkeypatch):
    """Captura correos enviados por `email_utils.send_company_invitation_email` sin usar SMTP."""
    captured: list[dict] = []

    async def _fake_send(email, *, company_name: str, inviter_name: str, token: str):
        captured.append(
            {
                "email": str(email),
                "company_name": company_name,
                "inviter_name": inviter_name,
                "token": token,
            }
        )

    monkeypatch.setattr(email_utils, "send_company_invitation_email", _fake_send)
    return captured


def _setup_company(db, *, settings=None):
    company = make_company(db, name="Escuela Sierra Alta", settings=settings or {})
    manager = make_user(db, email="manager@sierra.es")
    worker = make_user(db, email="worker@sierra.es")
    pa = make_user(db, email="pa@vesotel.com", role="admin")
    make_member(db, manager, company, role="manager")
    make_member(db, worker, company, role="worker")
    return company, manager, worker, pa


def _audit_rows(db, action):
    db.expire_all()
    return db.query(models.AuditLog).filter(models.AuditLog.action == action).all()


# --- Creacion de invitaciones y respuesta neutra ---


def test_manager_invites_existing_and_nonexistent_email_with_identical_neutral_response(client, db, sent_emails):
    """R-MEM-07: respuesta neutra exista o no la cuenta; guarda token_hash, caducidad 7 dias y audita."""
    company, manager, _, _ = _setup_company(db)
    existing_user = make_user(db, email="existente@sierra.es")
    as_user(client, manager, company)

    resp_unknown = client.post(
        f"/v2/companies/{company.id}/invitations",
        json={"email": "  NuevoMonitor@Sierra.ES "},
    )
    resp_existing = client.post(
        f"/v2/companies/{company.id}/invitations",
        json={"email": existing_user.email},
    )

    assert resp_unknown.status_code == 201, resp_unknown.text
    assert resp_existing.status_code == 201, resp_existing.text

    body_unknown = resp_unknown.json()
    body_existing = resp_existing.json()
    assert set(body_unknown) == set(body_existing)
    assert "token" not in body_unknown
    assert "token_hash" not in body_unknown
    assert body_unknown["email"] == "nuevomonitor@sierra.es"
    assert body_unknown["status"] == "pending"
    assert body_existing["email"] == "existente@sierra.es"
    assert body_existing["status"] == "pending"

    assert len(sent_emails) == 2
    raw_token = sent_emails[0]["token"]
    assert sent_emails[0]["company_name"] == company.name

    db.expire_all()
    inv = db.query(models.CompanyInvitation).filter_by(id=uuid.UUID(body_unknown["id"])).one()
    assert inv.token_hash == hash_invitation_token(raw_token)
    assert inv.token_hash != raw_token
    assert inv.email == "nuevomonitor@sierra.es"
    delta = ensure_utc(inv.expires_at) - datetime.now(UTC)
    assert timedelta(days=6, hours=23) < delta <= timedelta(days=7, minutes=1)

    audits = _audit_rows(db, "member.invited")
    assert len(audits) == 2
    assert all(row.actor_user_id == manager.id and row.company_id == company.id for row in audits)
    assert all(row.target_user_id is None for row in audits)


def test_worker_cannot_invite_or_list_or_cancel_invitations(client, db, sent_emails):
    company, manager, worker, _ = _setup_company(db)
    as_user(client, manager, company)
    created = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "otro@sierra.es"})
    inv_id = created.json()["id"]

    as_user(client, worker, company)
    assert client.get(f"/v2/companies/{company.id}/invitations").status_code == 403
    assert client.post(f"/v2/companies/{company.id}/invitations", json={"email": "x@sierra.es"}).status_code == 403
    assert client.post(f"/v2/companies/{company.id}/invitations/{inv_id}/resend").status_code == 403
    assert client.delete(f"/v2/companies/{company.id}/invitations/{inv_id}").status_code == 403


def test_invite_rejects_reserved_email_domains_with_422(client, db, sent_emails):
    company, manager, _, _ = _setup_company(db)
    as_user(client, manager, company)

    for bad in ("a@demo.invalid", "b@demo.test", "c@demo.local"):
        resp = client.post(f"/v2/companies/{company.id}/invitations", json={"email": bad})
        assert resp.status_code == 422, resp.text
    assert sent_emails == []


def test_email_delivery_failure_rolls_back_invitation_and_audit(client, db, monkeypatch):
    company, manager, _, _ = _setup_company(db)

    async def _fail_send(*args, **kwargs):
        raise RuntimeError("SMTP caido")

    monkeypatch.setattr(email_utils, "send_company_invitation_email", _fail_send)
    as_user(client, manager, company)

    resp = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "fallo@sierra.es"})

    assert resp.status_code == 500, resp.text
    db.expire_all()
    assert db.query(models.CompanyInvitation).count() == 0
    assert db.query(models.AuditLog).filter_by(action="member.invited").count() == 0


def test_reinviting_same_pending_email_renews_token_without_duplicate_row(client, db, sent_emails):
    company, manager, _, _ = _setup_company(db)
    as_user(client, manager, company)

    first = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "repetido@sierra.es"})
    second = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "REPETIDO@sierra.es"})

    assert first.status_code == 201
    assert second.status_code == 200
    assert first.json()["id"] == second.json()["id"]
    db.expire_all()
    assert db.query(models.CompanyInvitation).filter_by(company_id=company.id).count() == 1
    first_token, second_token = sent_emails[0]["token"], sent_emails[1]["token"]
    assert first_token != second_token
    assert client.get("/v2/invitations/preview", params={"token": first_token}).status_code == 404
    assert client.get("/v2/invitations/preview", params={"token": second_token}).status_code == 200


def test_partial_unique_index_blocks_duplicate_pending_invitations_at_db_level(db):
    company, manager, _, _ = _setup_company(db)
    expires = datetime.now(UTC) + timedelta(days=7)
    inv1 = models.CompanyInvitation(
        company_id=company.id,
        email="dup@sierra.es",
        token_hash=hash_invitation_token("token-1"),
        invited_by_user_id=manager.id,
        expires_at=expires,
    )
    inv2 = models.CompanyInvitation(
        company_id=company.id,
        email="DUP@sierra.es",
        token_hash=hash_invitation_token("token-2"),
        invited_by_user_id=manager.id,
        expires_at=expires,
    )
    db.add(inv1)
    db.flush()
    db.add(inv2)
    with pytest.raises(IntegrityError):
        db.flush()
    db.rollback()


# --- Listado, reenvio y cancelacion ---


def test_list_resend_and_cancel_invitations_flow(client, db, sent_emails):
    company, manager, _, pa = _setup_company(db)
    as_user(client, manager, company)

    c1 = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "uno@sierra.es"})
    inv_id = c1.json()["id"]
    first_token = sent_emails[0]["token"]

    listed = client.get(f"/v2/companies/{company.id}/invitations")
    assert listed.status_code == 200
    assert [i["id"] for i in listed.json()] == [inv_id]

    resent = client.post(f"/v2/companies/{company.id}/invitations/{inv_id}/resend")
    assert resent.status_code == 200
    second_token = sent_emails[1]["token"]
    assert second_token != first_token
    assert client.get("/v2/invitations/preview", params={"token": first_token}).status_code == 404
    assert client.get("/v2/invitations/preview", params={"token": second_token}).status_code == 200

    cancelled = client.delete(f"/v2/companies/{company.id}/invitations/{inv_id}")
    assert cancelled.status_code == 200
    assert cancelled.json()["status"] == "cancelled"
    assert cancelled.json()["cancelled_at"] is not None

    # Ya no aparece en la lista por defecto, si con status=cancelled
    assert client.get(f"/v2/companies/{company.id}/invitations").json() == []
    assert len(client.get(f"/v2/companies/{company.id}/invitations", params={"status": "cancelled"}).json()) == 1
    assert len(_audit_rows(db, "member.invitation_cancelled")) == 1

    # Reenviar una cancelada falla 409; el enlace cancelado ya no vale
    assert client.post(f"/v2/companies/{company.id}/invitations/{inv_id}/resend").status_code == 409
    assert client.get("/v2/invitations/preview", params={"token": second_token}).status_code == 409

    # El PA tambien puede gestionar invitaciones desde /v2/admin/companies/{id}/invitations
    as_user(client, pa)
    admin_create = client.post(f"/v2/admin/companies/{company.id}/invitations", json={"email": "uno@sierra.es"})
    assert admin_create.status_code == 201
    assert len(client.get(f"/v2/admin/companies/{company.id}/invitations").json()) == 1


# --- Aceptacion y validaciones ---


def test_accept_invitation_happy_path_case_insensitive_and_single_use(client, db, sent_emails):
    """R-MEM-23, R-MEM-24: correo case-insensitive, crea worker, un solo uso y audita member.added."""
    company, manager, _, _ = _setup_company(db)
    invited = make_user(db, email="Monitora@Sierra.es")
    as_user(client, manager, company)
    client.post(f"/v2/companies/{company.id}/invitations", json={"email": "monitora@sierra.es"})
    token = sent_emails[0]["token"]

    # Preview publico funciona sin sesion y no expone el email
    client.cookies.clear()
    preview = client.get("/v2/invitations/preview", params={"token": token})
    assert preview.status_code == 200, preview.text
    assert preview.json()["company_name"] == company.name
    assert "email" not in preview.json()

    # Aceptar sin sesion devuelve 401
    assert client.post("/v2/invitations/accept", json={"token": token}).status_code == 401

    # Aceptar con el usuario correcto crea membresia worker activa
    as_user(client, invited, None)
    accepted = client.post("/v2/invitations/accept", json={"token": token})
    assert accepted.status_code == 200, accepted.text
    payload = accepted.json()
    assert payload["company_id"] == str(company.id)
    assert payload["membership"]["role"] == "worker"
    assert payload["membership"]["is_active"] is True
    assert payload["membership"]["sort_order"] == 1000

    # No se puede reutilizar el enlace
    reuse = client.post("/v2/invitations/accept", json={"token": token})
    assert reuse.status_code == 409, reuse.text

    audits = _audit_rows(db, "member.added")
    assert len(audits) == 1
    assert audits[0].actor_user_id == invited.id
    assert audits[0].target_user_id == invited.id
    assert audits[0].company_id == company.id


def test_accept_invitation_rejects_wrong_email_with_403_and_keeps_token_valid(client, db, sent_emails):
    company, manager, _, _ = _setup_company(db)
    intended = make_user(db, email="destinatario@sierra.es")
    other = make_user(db, email="intruso@sierra.es")
    as_user(client, manager, company)
    client.post(f"/v2/companies/{company.id}/invitations", json={"email": intended.email})
    token = sent_emails[0]["token"]

    as_user(client, other, None)
    resp = client.post("/v2/invitations/accept", json={"token": token})
    assert resp.status_code == 403, resp.text
    assert resp.json()["detail"] == "Esta invitacion es para otro correo"

    # El destinatario real sigue pudiendo aceptar con el mismo token
    as_user(client, intended, None)
    ok = client.post("/v2/invitations/accept", json={"token": token})
    assert ok.status_code == 200, ok.text


def test_accept_expired_invitation_returns_422(client, db, sent_emails):
    company, manager, _, _ = _setup_company(db)
    invited = make_user(db, email="tarde@sierra.es")
    as_user(client, manager, company)
    inv_id = client.post(f"/v2/companies/{company.id}/invitations", json={"email": invited.email}).json()["id"]
    token = sent_emails[0]["token"]

    orm_inv = db.get(models.CompanyInvitation, uuid.UUID(inv_id))
    orm_inv.expires_at = datetime.now(UTC) - timedelta(minutes=1)
    db.commit()

    assert client.get("/v2/invitations/preview", params={"token": token}).status_code == 422
    as_user(client, invited, None)
    resp = client.post("/v2/invitations/accept", json={"token": token})
    assert resp.status_code == 422, resp.text


def test_accept_invitation_reactivates_inactive_manager_preserving_role(client, db, sent_emails):
    """R-MEM-12, R-MEM-23: aceptar una invitacion con membresia inactiva previa conserva su rol."""
    company, manager, _, _ = _setup_company(db)
    former_manager = make_user(db, email="exmanager@sierra.es")
    make_member(db, former_manager, company, role="manager", is_active=False)

    as_user(client, manager, company)
    client.post(f"/v2/companies/{company.id}/invitations", json={"email": former_manager.email})
    token = sent_emails[0]["token"]

    as_user(client, former_manager, None)
    resp = client.post("/v2/invitations/accept", json={"token": token})

    assert resp.status_code == 200, resp.text
    assert resp.json()["membership"]["role"] == "manager"
    assert resp.json()["membership"]["is_active"] is True
    audits = _audit_rows(db, "member.reactivated")
    assert len(audits) == 1
    assert audits[0].old_value == {"is_active": False, "role": "manager"}
    assert audits[0].new_value == {"is_active": True, "role": "manager"}


def test_accept_invitation_when_already_active_member_succeeds_without_audit(client, db, sent_emails):
    """R-MEM-06, R-MEM-21, R-MEM-23: si ya es miembro activo no falla ni emite evento de alta."""
    company, manager, worker, _ = _setup_company(db)
    as_user(client, manager, company)
    client.post(f"/v2/companies/{company.id}/invitations", json={"email": worker.email})
    token = sent_emails[0]["token"]

    as_user(client, worker, company)
    resp = client.post("/v2/invitations/accept", json={"token": token})

    assert resp.status_code == 200, resp.text
    assert resp.json()["membership"]["role"] == "worker"
    assert _audit_rows(db, "member.added") == []
    assert _audit_rows(db, "member.reactivated") == []


def test_accept_invitation_rejects_platform_admin_with_422(client, db, sent_emails):
    """R-ACC-26: un PA no puede convertirse en miembro aceptando una invitacion."""
    company, manager, _, pa = _setup_company(db)
    as_user(client, manager, company)
    client.post(f"/v2/companies/{company.id}/invitations", json={"email": pa.email})
    token = sent_emails[0]["token"]

    as_user(client, pa)
    resp = client.post("/v2/invitations/accept", json={"token": token})

    assert resp.status_code == 422, resp.text
    assert db.query(models.CompanyMember).filter_by(user_id=pa.id).count() == 0


def test_plan_limits_checked_on_invite_and_accept_and_pending_do_not_count(client, db, sent_emails):
    """R-MEM-24, R-MEM-25: limite de plan al invitar y al aceptar; las pendientes no ocupan plaza."""
    # Limite: max_monitors = 2 (ya hay 1 worker en _setup_company -> queda 1 plaza libre)
    company, manager, _, _ = _setup_company(
        db,
        settings={"_platform": {"limits": {"max_monitors": 2}}},
    )
    u1 = make_user(db, email="candidato1@sierra.es")
    u2 = make_user(db, email="candidato2@sierra.es")

    as_user(client, manager, company)
    # Se envian 2 invitaciones mientras hay 1/2 workers: las pendientes no cuentan para el limite
    r1 = client.post(f"/v2/companies/{company.id}/invitations", json={"email": u1.email})
    r2 = client.post(f"/v2/companies/{company.id}/invitations", json={"email": u2.email})
    assert r1.status_code == 201, r1.text
    assert r2.status_code == 201, r2.text
    token1, token2 = sent_emails[0]["token"], sent_emails[1]["token"]

    # El primero que acepta ocupa la 2a plaza
    as_user(client, u1, None)
    assert client.post("/v2/invitations/accept", json={"token": token1}).status_code == 200

    # El segundo al aceptar choca con el limite (409)
    as_user(client, u2, None)
    second_accept = client.post("/v2/invitations/accept", json={"token": token2})
    assert second_accept.status_code == 409, second_accept.text

    # Ahora con 2/2 workers activos, invitar a un tercero ya bloquea al invitar (409)
    as_user(client, manager, company)
    third_invite = client.post(f"/v2/companies/{company.id}/invitations", json={"email": "tercero@sierra.es"})
    assert third_invite.status_code == 409, third_invite.text
