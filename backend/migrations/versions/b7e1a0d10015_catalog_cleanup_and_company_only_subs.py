"""limpiar catalogo de modulos y restringir suscripciones a empresa

Revision ID: b7e1a0d10015
Revises: b7e1a0d10014
Create Date: 2026-11-28 13:00:00.000000

Alinea `app_modules` y `module_subscriptions` con R-MOD-03, R-MOD-04, R-MOD-17 y R-MOD-18:
- Actualiza `worker_daily_report` a "Cuadrante compartido" y siembra `push_notifications` inactivo.
- Elimina el modulo `billing` del catalogo y sus suscripciones dependientes.
- Elimina suscripciones de usuario, retira `user_id` y `scope` de `module_subscriptions`
  (y el tipo enum `subscriptionscope`), retira `target_scope` y `price_monthly` de `app_modules`,
  y endurece `module_subscriptions.company_id` a `NOT NULL` con restriccion `CHECK`.
"""

import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from migration_helpers import dependent_views
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10015"
down_revision: str | Sequence[str] | None = "b7e1a0d10014"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UQ_ACTIVE_COMPANY_SUB = "uq_module_subscriptions_active_company"
CK_COMPANY_NOT_NULL = "ck_module_subscriptions_company_id_not_null"

_DROPPED_COLUMNS: tuple[tuple[str, str], ...] = (
    ("app_modules", "target_scope"),
    ("app_modules", "price_monthly"),
    ("module_subscriptions", "user_id"),
    ("module_subscriptions", "scope"),
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    for table, col in _DROPPED_COLUMNS:
        views = dependent_views(bind, table, col)
        if views:
            raise RuntimeError(
                f"Las vistas {', '.join(view.name for view in views)} dependen (directa o a traves de otra vista) "
                f"de {table}.{col} y la migracion no puede recrearlas sin la columna. "
                "Adaptalas o eliminalas manualmente antes de migrar."
            )

    # 1. Retirar el modulo `billing` y cualquier suscripcion asociada (R-MOD-04)
    bind.execute(
        sa.text(
            "DELETE FROM module_subscriptions "
            "WHERE module_id IN (SELECT id FROM app_modules WHERE code_name = 'billing')"
        )
    )
    bind.execute(sa.text("DELETE FROM app_modules WHERE code_name = 'billing'"))

    # 2. Eliminar suscripciones de usuario o sin empresa (R-MOD-17)
    bind.execute(
        sa.text(
            "DELETE FROM module_subscriptions "
            "WHERE user_id IS NOT NULL OR scope::text = 'user' OR company_id IS NULL"
        )
    )

    # 3. Actualizar indice parcial antes de retirar columnas y endurecer company_id
    op.drop_index(UQ_ACTIVE_COMPANY_SUB, table_name="module_subscriptions")

    # 4. Retirar columnas obsoletas en app_modules y module_subscriptions (R-MOD-17, R-MOD-18)
    op.drop_column("module_subscriptions", "user_id")
    op.drop_column("module_subscriptions", "scope")
    op.execute("DROP TYPE IF EXISTS subscriptionscope")

    op.drop_column("app_modules", "target_scope")
    op.drop_column("app_modules", "price_monthly")

    # 5. Endurecer module_subscriptions.company_id a NOT NULL + CHECK
    op.alter_column(
        "module_subscriptions",
        "company_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=False,
    )
    op.create_check_constraint(CK_COMPANY_NOT_NULL, "module_subscriptions", "company_id IS NOT NULL")
    op.create_index(
        UQ_ACTIVE_COMPANY_SUB,
        "module_subscriptions",
        ["module_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active'"),
    )

    # 6. Actualizar catalogo: renombrar worker_daily_report y crear push_notifications inactivo (R-MOD-03)
    bind.execute(
        sa.text(
            "UPDATE app_modules "
            "SET name = :name, description = :description, updated_at = CURRENT_TIMESTAMP "
            "WHERE code_name = 'worker_daily_report'"
        ),
        {
            "name": "Cuadrante compartido",
            "description": "Permite a los monitores ver el cuadrante diario compartido de la empresa sin importes.",
        },
    )
    bind.execute(
        sa.text(
            "INSERT INTO app_modules (id, code_name, name, description, is_active, created_at, updated_at) "
            "VALUES (:id, 'push_notifications', :name, :description, false, CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "ON CONFLICT (code_name) DO NOTHING"
        ),
        {
            "id": str(uuid.uuid4()),
            "name": "Notificaciones push",
            "description": "Notificaciones push para avisos y recordatorios en la plataforma.",
        },
    )


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()

    # 1. Revertir catalogo de modulos
    bind.execute(
        sa.text(
            "DELETE FROM module_subscriptions "
            "WHERE module_id IN (SELECT id FROM app_modules WHERE code_name = 'push_notifications')"
        )
    )
    bind.execute(sa.text("DELETE FROM app_modules WHERE code_name = 'push_notifications'"))
    bind.execute(
        sa.text(
            "UPDATE app_modules "
            "SET name = :name, description = :description, updated_at = CURRENT_TIMESTAMP "
            "WHERE code_name = 'worker_daily_report'"
        ),
        {
            "name": "Parte Diario para Trabajadores",
            "description": "Permite a los empleados ver y completar sus partes desde el panel principal.",
        },
    )

    # 2. Revertir CHECK, NOT NULL e indice parcial de module_subscriptions
    op.drop_index(UQ_ACTIVE_COMPANY_SUB, table_name="module_subscriptions")
    op.drop_constraint(CK_COMPANY_NOT_NULL, "module_subscriptions", type_="check")
    op.alter_column(
        "module_subscriptions",
        "company_id",
        existing_type=postgresql.UUID(as_uuid=True),
        nullable=True,
    )
    op.create_index(
        UQ_ACTIVE_COMPANY_SUB,
        "module_subscriptions",
        ["module_id", "company_id"],
        unique=True,
        postgresql_where=sa.text("status = 'active' AND company_id IS NOT NULL"),
    )

    # 3. Recrear columnas en app_modules y module_subscriptions
    op.add_column("app_modules", sa.Column("price_monthly", sa.Numeric(precision=10, scale=2), nullable=True))
    op.add_column(
        "app_modules",
        sa.Column("target_scope", sa.String(), nullable=True, server_default=sa.text("'both'")),
    )
    op.alter_column("app_modules", "target_scope", server_default=None)

    subscriptionscope_enum = postgresql.ENUM("company", "user", name="subscriptionscope")
    subscriptionscope_enum.create(bind, checkfirst=True)

    op.add_column(
        "module_subscriptions",
        sa.Column(
            "scope",
            sa.Enum("company", "user", name="subscriptionscope"),
            nullable=False,
            server_default=sa.text("'company'"),
        ),
    )
    op.alter_column("module_subscriptions", "scope", server_default=None)
    op.add_column(
        "module_subscriptions",
        sa.Column("user_id", postgresql.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )

    # 4. Restaurar fila de billing en el catalogo
    bind.execute(
        sa.text(
            "INSERT INTO app_modules "
            "(id, code_name, name, description, is_active, target_scope, created_at, updated_at) "
            "VALUES (:id, 'billing', :name, :description, true, 'company', CURRENT_TIMESTAMP, CURRENT_TIMESTAMP) "
            "ON CONFLICT (code_name) DO NOTHING"
        ),
        {
            "id": str(uuid.uuid4()),
            "name": "Facturación y Cobros",
            "description": "Permite a los administradores de la empresa gestionar planes, facturas y métodos de pago.",
        },
    )
