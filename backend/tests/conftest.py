"""Configuracion comun de pytest para el backend.

Los tests nunca usan el DATABASE_URL del entorno. Usan SQLite en memoria o, si se
define TEST_DATABASE_URL, una base PostgreSQL migrada con Alembic (cada test corre
dentro de una transaccion que se revierte al final).
"""

import base64
import os

import pytest
from sqlalchemy.engine import make_url

TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL")
# Se captura antes de sobrescribir DATABASE_URL para poder comprobar que no apunta a la BD real.
ORIGINAL_DATABASE_URL = os.getenv("DATABASE_URL")

if TEST_DATABASE_URL:
    # Criterio de seguridad: el nombre de la BD debe contener "test" (acepta p. ej. ski_test_db en CI)
    # y la URL no puede ser la del entorno original. No se imprime la URL para no exponer credenciales.
    try:
        _test_db_name = make_url(TEST_DATABASE_URL).database or ""
    except Exception:
        pytest.exit("TEST_DATABASE_URL no es una URL valida. Abortando para proteger la base de datos.", returncode=3)
    if "test" not in _test_db_name.lower():
        pytest.exit(
            f"TEST_DATABASE_URL apunta a la base '{_test_db_name}', cuyo nombre no contiene 'test'. Abortando.",
            returncode=3,
        )
    if TEST_DATABASE_URL == ORIGINAL_DATABASE_URL:
        pytest.exit("TEST_DATABASE_URL coincide con DATABASE_URL del entorno. Abortando.", returncode=3)

# Debe ejecutarse ANTES de importar `database`, porque el engine de produccion se crea al importarlo.
os.environ["DATABASE_URL"] = TEST_DATABASE_URL or "sqlite://"
# Clave ficticia de pruebas, construida en ejecucion para no dejar un literal base64 en el repo.
os.environ.setdefault("ENCRYPTION_KEY", base64.b64encode(b"test_key_for_ci_validation_purposes").decode())
os.environ["ENVIRONMENT"] = "test"
os.environ.pop("DEV_LOGIN_BYPASS", None)
os.environ.pop("NODE_ENV", None)

import database  # noqa: E402
import main  # noqa: E402
import redis_config  # noqa: E402
from database import Base  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import create_engine  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402
from sqlalchemy.orm import sessionmaker  # noqa: E402
from sqlalchemy.pool import StaticPool  # noqa: E402

from tests.fakes import FakeRedisClient  # noqa: E402

# load_dotenv() (en database.py) puede reintroducir variables desde un .env; se vuelven a quitar.
os.environ.pop("DEV_LOGIN_BYPASS", None)
os.environ.pop("NODE_ENV", None)

if TEST_DATABASE_URL:
    engine = create_engine(TEST_DATABASE_URL)
else:
    engine = create_engine("sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool)

TestingSession = sessionmaker(bind=engine, autoflush=False, autocommit=False)

# Los tests antiguos hacen `from database import SessionLocal` al importarse; como este fichero
# se carga antes que ellos, reciben la sesion apuntando a la BD de test.
database.engine = engine
database.SessionLocal = TestingSession


@compiles(JSONB, "sqlite")
def _compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


def pytest_collection_modifyitems(config, items):
    if TEST_DATABASE_URL:
        return
    skip_postgres = pytest.mark.skip(reason="requiere PostgreSQL: define TEST_DATABASE_URL")
    for item in items:
        if item.get_closest_marker("postgres"):
            item.add_marker(skip_postgres)


@pytest.fixture(autouse=True)
def _schema():
    """Con SQLite crea y borra el esquema en cada test. Con PostgreSQL no toca las tablas."""
    if not TEST_DATABASE_URL:
        Base.metadata.create_all(engine)
    yield
    if not TEST_DATABASE_URL:
        Base.metadata.drop_all(engine)


@pytest.fixture
def db(_schema):
    """Sesion de SQLAlchemy sobre la BD de test. Con PostgreSQL se revierte todo al final."""
    if TEST_DATABASE_URL:
        connection = engine.connect()
        transaction = connection.begin()
        session = TestingSession(bind=connection)
        try:
            yield session
        finally:
            session.close()
            transaction.rollback()
            connection.close()
    else:
        session = TestingSession()
        try:
            yield session
        finally:
            session.close()


@pytest.fixture(autouse=True)
def fake_redis():
    """Sustituye el cliente de Redis por un doble en memoria durante cada test."""
    previous = redis_config.redis_manager._client
    fake = FakeRedisClient()
    redis_config.redis_manager._client = fake
    yield fake
    redis_config.redis_manager._client = previous


@pytest.fixture
def client(db):
    """TestClient sin `with` (no ejecuta el lifespan) y con get_db apuntando a la sesion de test."""

    def _override_get_db():
        yield db

    main.app.dependency_overrides[database.get_db] = _override_get_db
    try:
        yield TestClient(main.app)
    finally:
        main.app.dependency_overrides.clear()
