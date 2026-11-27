"""unicidad de email en minusculas y migracion de DateTime a timestamptz

Revision ID: b7e1a0d10011
Revises: b7e1a0d10010
Create Date: 2026-11-27 20:42:00.000000

1. Comprueba que no existan emails duplicados al ignorar mayusculas (si los hay,
   aborta con mensaje claro), normaliza los emails existentes a minusculas y crea
   el indice unico funcional `uq_users_email_lower` sobre `lower(email)`.
2. Pasa las 18 columnas DateTime a `timestamptz` interpretando los valores
   existentes como UTC (`USING <col> AT TIME ZONE 'UTC'`), eliminando y recreando
   las vistas dependientes con `migration_helpers` (incluidas las vistas manuales).
3. `audit_logs.admin_user_id` e `impersonated_user_id` siguen escribiendose en
   `backend/audit.py`, `backend/routers/users.py` y `backend/routers/work_logs.py`,
   por lo que se conservan hasta su retirada en #143.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migration_helpers import ViewSnapshot, create_views, dependent_views, drop_views

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10011"
down_revision: str | Sequence[str] | None = "b7e1a0d10010"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UQ_EMAIL_LOWER = "uq_users_email_lower"

_DATETIME_COLUMNS: tuple[tuple[str, str, bool], ...] = (
    # (table, column, nullable)
    ("users", "created_at", False),
    ("users", "updated_at", False),
    ("companies", "created_at", False),
    ("companies", "updated_at", False),
    ("company_members", "joined_at", False),
    ("company_members", "updated_at", False),
    ("work_logs", "created_at", False),
    ("work_logs", "updated_at", False),
    ("user_sessions", "expires_at", True),
    ("user_sessions", "revoked_at", True),
    ("user_sessions", "last_active", False),
    ("user_sessions", "created_at", False),
    ("audit_logs", "created_at", False),
    ("app_modules", "created_at", False),
    ("app_modules", "updated_at", False),
    ("module_subscriptions", "expires_at", True),
    ("module_subscriptions", "created_at", False),
    ("module_subscriptions", "updated_at", False),
)


def _collect_all_dependent_views(bind) -> list[ViewSnapshot]:
    """Recoge las vistas que dependen de cualquiera de las columnas DateTime sin duplicar."""
    if bind.dialect.name != "postgresql":
        return []
    seen: dict[str, ViewSnapshot] = {}
    for table, col, _ in _DATETIME_COLUMNS:
        for view in dependent_views(bind, table, col):
            # Si una vista aparece varias veces (p. ej. transitiva), mantener su posicion mas tardia
            if view.name in seen:
                del seen[view.name]
            seen[view.name] = view
    return list(seen.values())


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # 1. Comprobar colisiones de email por mayusculas/minusculas
    dups = (
        bind.execute(
            sa.text(
                "SELECT lower(btrim(email)) AS norm, count(*) AS cnt "
                "FROM users GROUP BY lower(btrim(email)) HAVING count(*) > 1"
            )
        )
        .mappings()
        .all()
    )
    if dups:
        sample = ", ".join(row["norm"] for row in dups[:10])
        raise RuntimeError(
            f"Existen usuarios con emails duplicados al ignorar mayusculas ({sample}). "
            "Resuelvelos manualmente antes de aplicar esta migracion."
        )

    op.execute("UPDATE users SET email = lower(btrim(email)) WHERE email <> lower(btrim(email))")
    op.create_index(UQ_EMAIL_LOWER, "users", [sa.text("lower(email)")], unique=True)

    # 2. Migrar todas las columnas DateTime a timestamptz recreando vistas dependientes
    views = _collect_all_dependent_views(bind)
    drop_views(bind, views)
    for table, col, nullable in _DATETIME_COLUMNS:
        op.alter_column(
            table,
            col,
            existing_type=sa.DateTime(timezone=False),
            type_=sa.DateTime(timezone=True),
            existing_nullable=nullable,
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )
    create_views(bind, views)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    views = _collect_all_dependent_views(bind)
    drop_views(bind, views)
    for table, col, nullable in reversed(_DATETIME_COLUMNS):
        op.alter_column(
            table,
            col,
            existing_type=sa.DateTime(timezone=True),
            type_=sa.DateTime(timezone=False),
            existing_nullable=nullable,
            postgresql_using=f"{col} AT TIME ZONE 'UTC'",
        )
    create_views(bind, views)
    op.drop_index(UQ_EMAIL_LOWER, table_name="users")
