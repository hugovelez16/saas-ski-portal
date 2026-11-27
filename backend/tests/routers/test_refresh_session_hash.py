"""Pruebas del almacenamiento por hash SHA-256, caducidad y revocacion de refresh tokens (#132)."""

from datetime import UTC, datetime, timedelta

import auth

from tests.factories import as_user, make_user


def test_create_session_stores_sha256_hash_and_expires_at(db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})

    session = auth.create_session(db, str(user.id), refresh_token)

    assert session.refresh_token_hash == auth.hash_refresh_token(refresh_token)
    assert session.refresh_token_hash != refresh_token
    assert len(session.refresh_token_hash) == 64
    assert session.expires_at is not None
    assert session.expires_at > datetime.now(UTC)
    assert session.revoked_at is None


def test_refresh_token_valid_returns_200(client, db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    auth.create_session(db, str(user.id), refresh_token)
    client.cookies.set("refresh_token", refresh_token)

    resp = client.post("/refresh-token")

    assert resp.status_code == 200, resp.text
    assert resp.cookies.get("access_token")


def test_refresh_token_unknown_returns_401(client, db):
    user = make_user(db)
    unknown_token = auth.create_refresh_token({"sub": str(user.id)})
    client.cookies.set("refresh_token", unknown_token)

    resp = client.post("/refresh-token")

    assert resp.status_code == 401, resp.text


def test_logout_marks_revoked_at_and_blocks_refresh(client, db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    session = auth.create_session(db, str(user.id), refresh_token)
    client.cookies.set("refresh_token", refresh_token)

    logout_resp = client.post("/logout")
    assert logout_resp.status_code == 200, logout_resp.text

    db.refresh(session)
    assert session.is_active is False
    assert session.revoked_at is not None

    client.cookies.set("refresh_token", refresh_token)
    refresh_resp = client.post("/refresh-token")
    assert refresh_resp.status_code == 401, refresh_resp.text


def test_refresh_with_revoked_at_set_returns_401(client, db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    session = auth.create_session(db, str(user.id), refresh_token)
    session.revoked_at = datetime.now(UTC) - timedelta(seconds=10)
    db.commit()
    client.cookies.set("refresh_token", refresh_token)

    resp = client.post("/refresh-token")

    assert resp.status_code == 401, resp.text


def test_refresh_with_expired_session_returns_401(client, db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    auth.create_session(
        db,
        str(user.id),
        refresh_token,
        expires_at=datetime.now(UTC) - timedelta(minutes=1),
    )
    client.cookies.set("refresh_token", refresh_token)

    resp = client.post("/refresh-token")

    assert resp.status_code == 401, resp.text


def test_delete_session_endpoint_sets_revoked_at(client, db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    session = auth.create_session(db, str(user.id), refresh_token)
    as_user(client, user)

    resp = client.delete(f"/sessions/{session.id}")

    assert resp.status_code == 200, resp.text
    db.refresh(session)
    assert session.is_active is False
    assert session.revoked_at is not None
