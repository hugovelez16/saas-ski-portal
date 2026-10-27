"""Migraciones b7e1a0d10007 y b7e1a0d10002 sobre bases con vistas manuales (PostgreSQL real).

Requiere TEST_DATABASE_URL. Cada test crea una base desechable (`<base de test>_mig_<hex>`) en el
mismo servidor, la lleva a 8f10a2b3c4d5 con Alembic, crea las vistas que en produccion existen
fuera del repo y ejecuta `alembic upgrade head` / `downgrade` en un subproceso. Nunca toca la base
de TEST_DATABASE_URL ni DATABASE_URL.
"""

import os
import subprocess
import sys
import uuid
from pathlib import Path

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url

pytestmark = pytest.mark.postgres

BACKEND_DIR = Path(__file__).resolve().parents[1]
BASE_REVISION = "8f10a2b3c4d5"

USUARIOS_ORIGINAL_SQL = (
    'CREATE VIEW "Usuarios" AS '
    "SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_active, "
    "c.name AS default_company_name, u.created_at "
    "FROM users u LEFT JOIN companies c ON u.default_company_id = c.id"
)
COMPANIES_MEMBERS_SQL = (
    'CREATE VIEW "Companies Members" AS '
    "SELECT c.id AS company_id, c.name AS company_name, u.id AS user_id, u.email, u.first_name, u.last_name, "
    "cm.role, cm.is_active, cm.joined_at "
    "FROM company_members cm JOIN companies c ON c.id = cm.company_id JOIN users u ON u.id = cm.user_id"
)
# Depende de companies.name solo a traves de "Companies Members": fija el orden de recreacion.
ACTIVE_MEMBERS_SQL = 'CREATE VIEW "Miembros Activos" AS SELECT company_name, email, \'a:b\'::text AS marca FROM "Companies Members" WHERE is_active'
USERS_SESSIONS_SQL = (
    'CREATE VIEW "Users Sessions" AS '
    "SELECT u.id, u.email, s.id AS session_id FROM users u JOIN user_sessions s ON s.user_id = u.id"
)
FOREIGN_VIEW_SQL = 'CREATE VIEW "Ficha Usuario" AS SELECT u.id, u.default_company_id FROM users u'


def _admin_engine(database: str | None = None):
    url = make_url(os.environ["TEST_DATABASE_URL"])
    if database:
        url = url.set(database=database)
    return create_engine(url, isolation_level="AUTOCOMMIT")


@pytest.fixture
def scratch():
    """Base desechable en el servidor de test. Devuelve (url, nombre de rol de lectura, nombre de rol propietario)."""
    suffix = uuid.uuid4().hex[:8]
    base_name = make_url(os.environ["TEST_DATABASE_URL"]).database
    db_name = f"{base_name}_mig_{suffix}"
    reader, owner = f"mig_reader_{suffix}", f"mig_owner_{suffix}"
    admin = _admin_engine()
    url = make_url(os.environ["TEST_DATABASE_URL"]).set(database=db_name).render_as_string(hide_password=False)
    try:
        with admin.connect() as conn:
            conn.execute(text(f'CREATE DATABASE "{db_name}"'))
            conn.execute(text(f'CREATE ROLE "{reader}"'))
            conn.execute(text(f'CREATE ROLE "{owner}"'))
        _alembic(url, "upgrade", BASE_REVISION)
        yield url, reader, owner
    finally:
        with admin.connect() as conn:
            conn.execute(text(f'DROP DATABASE IF EXISTS "{db_name}" WITH (FORCE)'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{reader}"'))
            conn.execute(text(f'DROP ROLE IF EXISTS "{owner}"'))
        admin.dispose()


def _alembic(url: str, *args: str, check: bool = True) -> subprocess.CompletedProcess:
    env = {**os.environ, "DATABASE_URL": url}
    result = subprocess.run(
        [sys.executable, "-m", "alembic", *args],
        cwd=BACKEND_DIR,
        env=env,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise AssertionError(f"alembic {' '.join(args)} fallo:\n{result.stderr[-2000:]}")
    return result


def _execute(url: str, *statements: str) -> None:
    engine = create_engine(url, isolation_level="AUTOCOMMIT")
    with engine.connect() as conn:
        for statement in statements:
            conn.execute(text(statement))
    engine.dispose()


def _scalar(url: str, query: str):
    engine = create_engine(url)
    with engine.connect() as conn:
        value = conn.execute(text(query)).scalar()
    engine.dispose()
    return value


def _view_columns(url: str, view: str) -> list[str]:
    engine = create_engine(url)
    with engine.connect() as conn:
        rows = conn.execute(
            text(
                "SELECT column_name FROM information_schema.columns "
                "WHERE table_schema = 'public' AND table_name = :v ORDER BY ordinal_position"
            ),
            {"v": view},
        ).scalars().all()
    engine.dispose()
    return list(rows)


def _view_exists(url: str, view: str) -> bool:
    return _scalar(url, f"SELECT to_regclass('public.\"{view}\"') IS NOT NULL")


def _name_max_length(url: str):
    return _scalar(
        url,
        "SELECT character_maximum_length FROM information_schema.columns "
        "WHERE table_name = 'companies' AND column_name = 'name'",
    )


def _has_column(url: str, table: str, column: str) -> bool:
    return bool(
        _scalar(
            url,
            f"SELECT count(*) FROM information_schema.columns WHERE table_name = '{table}' AND column_name = '{column}'",
        )
    )


def _version(url: str) -> str:
    return _scalar(url, "SELECT version_num FROM alembic_version")


def _can_select(url: str, role: str, view: str) -> bool:
    return _scalar(url, f"SELECT has_table_privilege('{role}', 'public.\"{view}\"', 'SELECT')")


def _owner(url: str, view: str) -> str:
    return _scalar(url, f"SELECT pg_get_userbyid(relowner) FROM pg_class WHERE oid = 'public.\"{view}\"'::regclass")


def test_upgrade_and_downgrade_with_manual_views(scratch):
    url, reader, owner = scratch
    _execute(
        url,
        USUARIOS_ORIGINAL_SQL,
        COMPANIES_MEMBERS_SQL,
        ACTIVE_MEMBERS_SQL,
        USERS_SESSIONS_SQL,
        f'GRANT SELECT ON "Companies Members" TO "{reader}"',
        f'GRANT SELECT ON "Miembros Activos" TO "{reader}"',
        f'GRANT SELECT ON "Usuarios" TO "{reader}"',
        f'ALTER VIEW "Companies Members" OWNER TO "{owner}"',
    )
    members_definition = _scalar(url, "SELECT pg_get_viewdef('public.\"Companies Members\"'::regclass, true)")

    _alembic(url, "upgrade", "head")

    assert _name_max_length(url) == 120
    assert not _has_column(url, "users", "default_company_id")
    assert _view_columns(url, "Usuarios") == [
        "id", "email", "first_name", "last_name", "role", "is_active", "created_at",
    ]
    assert _scalar(url, "SELECT pg_get_viewdef('public.\"Companies Members\"'::regclass, true)") == members_definition
    for view in ("Work Logs", "Users Sessions", "Miembros Activos"):
        assert _view_exists(url, view)
    assert _can_select(url, reader, "Companies Members")
    assert _can_select(url, reader, "Miembros Activos")
    assert _can_select(url, reader, "Usuarios")
    assert not _can_select(url, reader, "Users Sessions")
    assert _owner(url, "Companies Members") == owner

    _alembic(url, "downgrade", BASE_REVISION)

    assert _version(url) == BASE_REVISION
    assert _has_column(url, "users", "default_company_id")
    assert _name_max_length(url) is None
    assert _view_columns(url, "Usuarios") == [
        "id", "email", "first_name", "last_name", "role", "is_active", "default_company_name", "created_at",
    ]
    assert _can_select(url, reader, "Usuarios")
    assert _can_select(url, reader, "Companies Members")
    assert _owner(url, "Companies Members") == owner
    assert _view_exists(url, "Miembros Activos")


def test_clean_database_upgrade_and_downgrade(scratch):
    url, _, _ = scratch

    _alembic(url, "upgrade", "head")

    assert _name_max_length(url) == 120
    assert not _has_column(url, "users", "default_company_id")
    assert _view_exists(url, "Work Logs")
    assert not _view_exists(url, "Usuarios")

    _alembic(url, "downgrade", BASE_REVISION)

    assert _has_column(url, "users", "default_company_id")
    assert _name_max_length(url) is None
    assert _view_exists(url, "Work Logs")
    assert not _view_exists(url, "Usuarios")


def test_upgrade_aborts_when_foreign_view_depends_on_default_company_id(scratch):
    url, _, _ = scratch
    _execute(url, USUARIOS_ORIGINAL_SQL, FOREIGN_VIEW_SQL)

    result = _alembic(url, "upgrade", "head", check=False)

    assert result.returncode != 0
    assert "RuntimeError" in result.stderr
    assert "Ficha Usuario" in result.stderr
    assert _version(url) == BASE_REVISION
    assert _has_column(url, "users", "default_company_id")
    assert _name_max_length(url) is None
    assert _view_columns(url, "Usuarios")[-2] == "default_company_name"
    assert _view_exists(url, "Ficha Usuario")
