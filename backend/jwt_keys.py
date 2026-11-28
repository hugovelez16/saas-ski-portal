"""
Carga de las claves RSA usadas para firmar y verificar los JWT (RS256).

Orden de resolucion:
1. Ficheros private_key.pem y public_key.pem en keys_dir.
2. Variables de entorno PRIVATE_KEY y PUBLIC_KEY.
3. Par efimero en memoria, solo si ALLOW_EPHEMERAL_JWT_KEYS es verdadero.
4. Si nada de lo anterior aplica, el arranque falla.

Los mensajes de error nunca incluyen el contenido de ninguna clave.
"""

import os

from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

_TRUE_VALUES = ("1", "true", "yes")


def _default_keys_dir() -> str:
    return os.path.join(os.path.dirname(__file__), "keys")


def _normalize_pem(value: str) -> str:
    """Acepta saltos de linea escapados (\\n) como suelen venir en variables de entorno."""
    return value.replace("\\n", "\n")


def _load_private_pem(data: bytes, passphrase: str | None, origin: str) -> str:
    """Carga un PEM privado (cifrado o no) y lo devuelve como PKCS8 sin cifrar."""
    try:
        try:
            key_obj = serialization.load_pem_private_key(data, password=passphrase.encode() if passphrase else None)
        except TypeError:
            # Clave sin cifrar y se dio passphrase: se reintenta sin contrasena.
            key_obj = serialization.load_pem_private_key(data, password=None)
    except (ValueError, TypeError) as err:
        raise RuntimeError(
            f"No se pudo cargar la clave privada JWT ({origin}): formato invalido o JWT_PRIVATE_KEY_PASSPHRASE "
            f"incorrecta ({type(err).__name__}). No se generan claves de respaldo."
        ) from None
    return key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    ).decode("utf-8")


def _check_pair(private_pem: str, public_pem: str, origin: str) -> None:
    """Comprueba que la publica es un PEM valido y corresponde a la privada."""
    try:
        private_obj = serialization.load_pem_private_key(private_pem.encode("utf-8"), password=None)
        public_obj = serialization.load_pem_public_key(public_pem.encode("utf-8"))
        same = private_obj.public_key().public_numbers() == public_obj.public_numbers()
    except (ValueError, TypeError, AttributeError):
        same = False
    if not same:
        raise RuntimeError(
            f"La clave publica JWT ({origin}) no es un PEM valido o no corresponde a la clave privada. "
            "Revise PUBLIC_KEY y PRIVATE_KEY (en una sola linea, los saltos de linea se escriben como \\n)."
        ) from None


def _generate_ephemeral(environ, keys_dir: str) -> tuple[str, str]:
    key_obj = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_private = key_obj.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.PKCS8,
        encryption_algorithm=serialization.NoEncryption(),
    )
    pem_public = key_obj.public_key().public_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PublicFormat.SubjectPublicKeyInfo,
    )

    persisted = False
    if environ.get("ENVIRONMENT") == "development":
        try:
            os.makedirs(keys_dir, exist_ok=True)
            with open(os.path.join(keys_dir, "private_key.pem"), "wb") as f:
                f.write(pem_private)
            with open(os.path.join(keys_dir, "public_key.pem"), "wb") as f:
                f.write(pem_public)
            persisted = True
        except OSError:
            persisted = False

    destino = "guardadas en keys/" if persisted else "solo en memoria"
    print(
        "[WARNING] Claves JWT efimeras generadas porque ALLOW_EPHEMERAL_JWT_KEYS esta activo "
        f"({destino}). No usar fuera de desarrollo local."
    )
    return pem_private.decode("utf-8"), pem_public.decode("utf-8")


def load_jwt_keys(environ=None, keys_dir=None) -> tuple[str, str]:
    """Devuelve (private_pem, public_pem) como str. Lanza RuntimeError si no hay claves validas."""
    if environ is None:
        environ = os.environ
    if keys_dir is None:
        keys_dir = _default_keys_dir()

    passphrase = environ.get("JWT_PRIVATE_KEY_PASSPHRASE")

    private_path = os.path.join(keys_dir, "private_key.pem")
    public_path = os.path.join(keys_dir, "public_key.pem")
    if os.path.isfile(private_path) and os.path.isfile(public_path):
        with open(private_path, "rb") as f:
            private_data = f.read()
        with open(public_path, "r") as f:
            public_pem = f.read()
        private_pem = _load_private_pem(private_data, passphrase, "fichero private_key.pem")
        _check_pair(private_pem, public_pem, "fichero public_key.pem")
        return private_pem, public_pem

    env_private = environ.get("PRIVATE_KEY", "")
    env_public = environ.get("PUBLIC_KEY", "")
    if env_private.strip() and env_public.strip():
        private_pem = _load_private_pem(
            _normalize_pem(env_private).encode("utf-8"), passphrase, "variable PRIVATE_KEY"
        )
        public_pem = _normalize_pem(env_public)
        _check_pair(private_pem, public_pem, "variable PUBLIC_KEY")
        return private_pem, public_pem

    if environ.get("ALLOW_EPHEMERAL_JWT_KEYS", "").lower() in _TRUE_VALUES:
        return _generate_ephemeral(environ, keys_dir)

    raise RuntimeError(
        "No hay claves JWT configuradas. Defina las variables PRIVATE_KEY y PUBLIC_KEY "
        "(o los ficheros private_key.pem y public_key.pem en backend/keys/). "
        "En desarrollo local puede usar ALLOW_EPHEMERAL_JWT_KEYS=true para generar un par efimero."
    )
