"""Pruebas de normalizacion de email sin mayusculas y fechas timestamptz con UTC (#135)."""

from datetime import UTC

import auth
import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.factories import make_user


def test_email_normalized_to_lowercase_on_write(db):
    user = make_user(db, email="Juan@X.com")
    assert user.email == "juan@x.com"


def test_email_unique_case_insensitive_index(db):
    make_user(db, email="Juan@x.com")
    # Incluso insertando por SQL directo sin pasar por el validador ORM, el indice lower(email) lo bloquea
    with pytest.raises(IntegrityError):
        db.execute(
            text(
                "INSERT INTO users (id, email, hashed_password, role, is_active, must_change_password, is_2fa_enabled) "
                "VALUES (:id, :email, :pw, 'user', true, false, false)"
            ),
            {"id": "00000000-0000-0000-0000-000000000999", "email": "JUAN@X.COM", "pw": "x"},
        )
        db.flush()
    db.rollback()


def test_login_is_case_insensitive(client, db):
    make_user(db, email="Juan@x.com")

    resp = client.post("/token", data={"username": "JUAN@X.COM", "password": "pw12345678"})

    assert resp.status_code == 200, resp.text


def test_timestamps_are_timezone_aware_utc(db):
    user = make_user(db)
    refresh_token = auth.create_refresh_token({"sub": str(user.id)})
    session = auth.create_session(db, str(user.id), refresh_token)
    db.refresh(user)
    db.refresh(session)

    assert user.created_at.tzinfo == UTC
    assert session.created_at.tzinfo == UTC
    assert session.expires_at is not None
    assert session.expires_at.tzinfo == UTC
