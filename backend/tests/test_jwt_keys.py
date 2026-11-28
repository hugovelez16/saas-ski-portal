"""Tests de la carga de claves JWT (jwt_keys.load_jwt_keys)."""

import secrets

import pytest
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from jose import jwt
from jwt_keys import load_jwt_keys

# Frase generada en cada ejecucion: no se versiona ningun literal con forma de contrasena.
TEST_PASSPHRASE = secrets.token_urlsafe(16)
OTHER_PASSPHRASE = secrets.token_urlsafe(16)


def _make_pair(passphrase=None):
    """Genera un par RSA de prueba en memoria; devuelve (privada, publica) en PEM str."""
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    encryption = (
        serialization.BestAvailableEncryption(passphrase.encode()) if passphrase else serialization.NoEncryption()
    )
    private_pem = key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=encryption,
    ).decode()
    public_pem = (
        key.public_key()
        .public_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PublicFormat.SubjectPublicKeyInfo,
        )
        .decode()
    )
    return private_pem, public_pem


def _roundtrip(private_pem, public_pem):
    token = jwt.encode({"sub": "x"}, private_pem, algorithm="RS256")
    return jwt.decode(token, public_pem, algorithms=["RS256"])


def test_sin_claves_y_sin_permiso_falla(tmp_path):
    with pytest.raises(RuntimeError) as exc:
        load_jwt_keys(environ={}, keys_dir=str(tmp_path))
    assert "PRIVATE_KEY" in str(exc.value)
    assert "BEGIN" not in str(exc.value)


def test_efimeras_con_permiso_no_escriben_en_test(tmp_path):
    keys_dir = tmp_path / "keys"
    env = {"ALLOW_EPHEMERAL_JWT_KEYS": "true", "ENVIRONMENT": "test"}
    private_pem, public_pem = load_jwt_keys(environ=env, keys_dir=str(keys_dir))
    assert _roundtrip(private_pem, public_pem) == {"sub": "x"}
    assert not keys_dir.exists()


def test_efimeras_en_desarrollo_persisten(tmp_path):
    keys_dir = tmp_path / "keys"
    env = {"ALLOW_EPHEMERAL_JWT_KEYS": "1", "ENVIRONMENT": "development"}
    private_pem, public_pem = load_jwt_keys(environ=env, keys_dir=str(keys_dir))
    assert (keys_dir / "private_key.pem").exists()
    assert (keys_dir / "public_key.pem").exists()
    # Segunda carga: ahora salen del fichero y son las mismas.
    private2, public2 = load_jwt_keys(environ={}, keys_dir=str(keys_dir))
    assert public2 == public_pem
    assert _roundtrip(private2, public2) == {"sub": "x"}


def test_claves_por_variable(tmp_path):
    private_pem, public_pem = _make_pair()
    env = {"PRIVATE_KEY": private_pem, "PUBLIC_KEY": public_pem}
    got_private, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert got_public == public_pem
    assert _roundtrip(got_private, got_public) == {"sub": "x"}


def test_claves_por_variable_con_saltos_escapados(tmp_path):
    private_pem, public_pem = _make_pair()
    env = {
        "PRIVATE_KEY": private_pem.replace("\n", "\\n"),
        "PUBLIC_KEY": public_pem.replace("\n", "\\n"),
    }
    got_private, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert "\\n" not in got_public
    assert _roundtrip(got_private, got_public) == {"sub": "x"}


def test_clave_cifrada_por_variable(tmp_path):
    private_pem, public_pem = _make_pair(passphrase=TEST_PASSPHRASE)
    env = {
        "PRIVATE_KEY": private_pem,
        "PUBLIC_KEY": public_pem,
        "JWT_PRIVATE_KEY_PASSPHRASE": TEST_PASSPHRASE,
    }
    got_private, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert "ENCRYPTED" not in got_private
    assert _roundtrip(got_private, got_public) == {"sub": "x"}


def test_clave_cifrada_por_fichero(tmp_path):
    private_pem, public_pem = _make_pair(passphrase=TEST_PASSPHRASE)
    (tmp_path / "private_key.pem").write_text(private_pem)
    (tmp_path / "public_key.pem").write_text(public_pem)
    env = {"JWT_PRIVATE_KEY_PASSPHRASE": TEST_PASSPHRASE}
    got_private, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert _roundtrip(got_private, got_public) == {"sub": "x"}


def test_clave_sin_cifrar_con_passphrase_reintenta(tmp_path):
    private_pem, public_pem = _make_pair()
    (tmp_path / "private_key.pem").write_text(private_pem)
    (tmp_path / "public_key.pem").write_text(public_pem)
    env = {"JWT_PRIVATE_KEY_PASSPHRASE": OTHER_PASSPHRASE}
    got_private, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert _roundtrip(got_private, got_public) == {"sub": "x"}


def test_ficheros_tienen_prioridad_sobre_variables(tmp_path):
    file_private, file_public = _make_pair()
    env_private, env_public = _make_pair()
    (tmp_path / "private_key.pem").write_text(file_private)
    (tmp_path / "public_key.pem").write_text(file_public)
    env = {"PRIVATE_KEY": env_private, "PUBLIC_KEY": env_public}
    _, got_public = load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert got_public == file_public
    assert got_public != env_public


def test_clave_corrupta_no_se_oculta_con_efimeras(tmp_path):
    _, public_pem = _make_pair()
    (tmp_path / "private_key.pem").write_text("contenido-corrupto")
    (tmp_path / "public_key.pem").write_text(public_pem)
    env = {"ALLOW_EPHEMERAL_JWT_KEYS": "true", "ENVIRONMENT": "test"}
    with pytest.raises(RuntimeError) as exc:
        load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert "BEGIN" not in str(exc.value)


def test_publica_que_no_corresponde_a_la_privada_impide_arrancar(tmp_path):
    private_pem, _ = _make_pair()
    _, otra_publica = _make_pair()
    env = {"PRIVATE_KEY": private_pem, "PUBLIC_KEY": otra_publica}
    with pytest.raises(RuntimeError) as exc:
        load_jwt_keys(environ=env, keys_dir=str(tmp_path))
    assert "BEGIN" not in str(exc.value)


def test_publica_invalida_impide_arrancar(tmp_path):
    private_pem, _ = _make_pair()
    env = {"PRIVATE_KEY": private_pem, "PUBLIC_KEY": "no-es-un-pem"}
    with pytest.raises(RuntimeError):
        load_jwt_keys(environ=env, keys_dir=str(tmp_path))


def test_publica_de_fichero_que_no_corresponde_impide_arrancar(tmp_path):
    private_pem, _ = _make_pair()
    _, otra_publica = _make_pair()
    (tmp_path / "private_key.pem").write_text(private_pem)
    (tmp_path / "public_key.pem").write_text(otra_publica)
    with pytest.raises(RuntimeError):
        load_jwt_keys(environ={}, keys_dir=str(tmp_path))


def test_variable_corrupta_no_se_oculta_con_efimeras(tmp_path):
    env = {
        "PRIVATE_KEY": "contenido-corrupto",
        "PUBLIC_KEY": "otro-contenido",
        "ALLOW_EPHEMERAL_JWT_KEYS": "true",
    }
    with pytest.raises(RuntimeError):
        load_jwt_keys(environ=env, keys_dir=str(tmp_path))
