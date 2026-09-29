"""
Pruebas unitarias de seguridad para tokens de reseteo de contrasena y proteccion contra replay attacks.
"""
import pytest
import auth


def test_reset_token_creation_and_single_use_revocation():
    email = "usuario.seguro@vesotel.com"
    token = auth.create_reset_token(email)

    # 1. Primera verificacion debe ser valida
    verified_email = auth.verify_reset_token(token)
    assert verified_email == email

    # 2. Consumo del token
    consumed = auth.consume_reset_token(token)
    assert consumed is True

    # 3. Segunda verificacion debe fallar (replay attack prevenido)
    replayed_email = auth.verify_reset_token(token)
    assert replayed_email is None


def test_invalid_or_tampered_reset_token():
    assert auth.verify_reset_token("token_invalido_totalmente") is None
