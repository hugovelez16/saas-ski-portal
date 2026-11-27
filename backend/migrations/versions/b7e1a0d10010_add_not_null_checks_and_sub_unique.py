"""anadir NOT NULL, server_default, CHECK de fechas y unicidad parcial en suscripciones

Revision ID: b7e1a0d10010
Revises: b7e1a0d10009
Create Date: 2026-11-27 20:32:00.000000

Lleva a PostgreSQL las restricciones que solo existian en el ORM:
- Rellena NULL con valores por defecto y aplica server_default + NOT NULL en
  users, companies, company_members, work_logs, user_sessions, audit_logs,
  app_modules y module_subscriptions.
- work_logs: CHECK end_date >= start_date (aborta si existen filas invalidas)
  y gross_amount NOT NULL DEFAULT 0.
- module_subscriptions: indice unico parcial (module_id, company_id) para
  suscripciones activas de empresa. Las columnas user_id y scope (y el CHECK
  company_id IS NOT NULL) se mantienen hasta retirar scope=user en #142.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10010"
down_revision: str | Sequence[str] | None = "b7e1a0d10009"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

CK_WORK_LOGS_DATES = "ck_work_logs_end_date_gte_start_date"
UQ_ACTIVE_COMPANY_SUB = "uq_module_subscriptions_active_company"

_TIMESTAMP_COLUMNS: tuple[tuple[str, str], ...] = (
    ("users", "created_at"),
    ("users", "updated_at"),
    ("companies", "created_at"),
    ("companies", "updated_at"),
    ("company_members", "joined_at"),
    ("company_members", "updated_at"),
    ("work_logs", "created_at"),
    ("work_logs", "updated_at"),
    ("user_sessions", "last_active"),
    ("user_sessions", "created_at"),
    ("audit_logs", "created_at"),
    ("app_modules", "created_at"),
    ("app_modules", "updated_at"),
    ("module_subscriptions", "created_at"),
    ("module_subscriptions", "updated_at"),
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    # Comprobar invariante de fechas antes de crear el CHECK (no corregir datos en silencio)
    invalid_dates = bind.execute(sa.text("SELECT count(*) FROM work_logs WHERE end_date < start_date")).scalar()
    if invalid_dates:
        raise RuntimeError(
            f"Hay {invalid_dates} filas en work_logs con end_date < start_date. "
            "Corrigelas manualmente antes de aplicar esta migracion."
        )

    # Rellenar NULL en booleanos, role y gross_amount
    op.execute("UPDATE users SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE users SET must_change_password = false WHERE must_change_password IS NULL")
    op.execute("UPDATE users SET is_2fa_enabled = false WHERE is_2fa_enabled IS NULL")
    op.execute("UPDATE users SET role = 'user' WHERE role IS NULL")
    op.execute("UPDATE user_sessions SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE app_modules SET is_active = true WHERE is_active IS NULL")
    op.execute("UPDATE work_logs SET gross_amount = 0 WHERE gross_amount IS NULL")

    # Rellenar NULL en columnas de fecha
    for table, col in _TIMESTAMP_COLUMNS:
        op.execute(f"UPDATE {table} SET {col} = CURRENT_TIMESTAMP WHERE {col} IS NULL")

    # Aplicar server_default + NOT NULL
    op.alter_column("users", "is_active", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("true"))
    op.alter_column(
        "users", "must_change_password", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false")
    )
    op.alter_column(
        "users", "is_2fa_enabled", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("false")
    )
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("admin", "user", name="userrole"),
        nullable=False,
        server_default=sa.text("'user'"),
    )
    op.alter_column(
        "user_sessions", "is_active", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("true")
    )
    op.alter_column(
        "app_modules", "is_active", existing_type=sa.Boolean(), nullable=False, server_default=sa.text("true")
    )
    op.alter_column(
        "work_logs",
        "gross_amount",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=False,
        server_default=sa.text("0"),
    )

    for table, col in _TIMESTAMP_COLUMNS:
        op.alter_column(
            table,
            col,
            existing_type=sa.DateTime(),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        )

    # CHECK de fechas en work_logs
    op.create_check_constraint(CK_WORK_LOGS_DATES, "work_logs", "end_date >= start_date")

    # Indice unico parcial de suscripciones activas por empresa y modulo
    op.create_index(
        UQ_ACTIVE_COMPANY_SUB,
        "module_subscriptions",
        ["module_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND company_id IS NOT NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(UQ_ACTIVE_COMPANY_SUB, table_name="module_subscriptions")
    op.drop_constraint(CK_WORK_LOGS_DATES, "work_logs", type_="check")

    for table, col in reversed(_TIMESTAMP_COLUMNS):
        op.alter_column(table, col, existing_type=sa.DateTime(), nullable=True, server_default=None)

    op.alter_column(
        "work_logs",
        "gross_amount",
        existing_type=sa.Numeric(precision=10, scale=2),
        nullable=True,
        server_default=None,
    )
    op.alter_column("app_modules", "is_active", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.alter_column("user_sessions", "is_active", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.alter_column(
        "users",
        "role",
        existing_type=sa.Enum("admin", "user", name="userrole"),
        nullable=True,
        server_default=None,
    )
    op.alter_column("users", "is_2fa_enabled", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.alter_column("users", "must_change_password", existing_type=sa.Boolean(), nullable=True, server_default=None)
    op.alter_column("users", "is_active", existing_type=sa.Boolean(), nullable=True, server_default=None)
