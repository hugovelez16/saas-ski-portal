"""elimina las columnas heredadas admin_user_id e impersonated_user_id de audit_logs

Revision ID: b7e1a0d10013
Revises: b7e1a0d10012
Create Date: 2026-11-28 12:15:00.000000

1. Antes de eliminar las columnas heredadas (R-AUD-04), conserva sus valores en las
   columnas canonicas `actor_user_id` y `target_user_id` cuando esten vacias.
2. Comprueba que ninguna vista de PostgreSQL dependa de esas columnas mediante
   `migration_helpers.dependent_views`.
3. Elimina `admin_user_id` e `impersonated_user_id` de `audit_logs`.

Downgrade: recrea ambas columnas nullable con FK a `users.id` y rellena desde
`actor_user_id` y `target_user_id` (cuando el usuario exista en `users`).
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migration_helpers import dependent_views

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10013"
down_revision: str | Sequence[str] | None = "b7e1a0d10012"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_LEGACY_COLUMNS = ("admin_user_id", "impersonated_user_id")


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()

    if bind.dialect.name == "postgresql":
        for column in _LEGACY_COLUMNS:
            views = dependent_views(bind, "audit_logs", column)
            if views:
                names = ", ".join(view.name for view in views)
                raise RuntimeError(
                    f"Las vistas {names} dependen de audit_logs.{column}. "
                    "Adaptalas o eliminalas manualmente antes de migrar."
                )

    op.execute(
        "UPDATE audit_logs "
        "SET actor_user_id = COALESCE(actor_user_id, admin_user_id) "
        "WHERE actor_user_id IS NULL AND admin_user_id IS NOT NULL"
    )
    op.execute(
        "UPDATE audit_logs "
        "SET target_user_id = COALESCE(target_user_id, impersonated_user_id) "
        "WHERE target_user_id IS NULL AND impersonated_user_id IS NOT NULL"
    )

    if bind.dialect.name == "postgresql":
        op.execute("SET LOCAL lock_timeout = '5s'")

    op.drop_column("audit_logs", "admin_user_id")
    op.drop_column("audit_logs", "impersonated_user_id")


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        "audit_logs",
        sa.Column("impersonated_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.add_column(
        "audit_logs",
        sa.Column("admin_user_id", sa.UUID(as_uuid=True), sa.ForeignKey("users.id"), nullable=True),
    )
    op.execute(
        "UPDATE audit_logs "
        "SET admin_user_id = actor_user_id "
        "WHERE admin_user_id IS NULL AND actor_user_id IS NOT NULL"
    )
    op.execute(
        "UPDATE audit_logs "
        "SET impersonated_user_id = target_user_id "
        "WHERE impersonated_user_id IS NULL AND target_user_id IS NOT NULL "
        "AND EXISTS (SELECT 1 FROM users WHERE users.id = audit_logs.target_user_id)"
    )
