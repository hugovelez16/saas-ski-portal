"""guardar hash sha256 del refresh token y caducidad en user_sessions

Revision ID: b7e1a0d10008
Revises: b7e1a0d10006
Create Date: 2026-11-27 20:15:00.000000

Migracion en tres pasos:
1. Anade `refresh_token_hash`, `expires_at` y `revoked_at` como anulables.
2. Calcula el SHA-256 de los `refresh_token` existentes y rellena `expires_at` y `revoked_at`.
3. Endurece `refresh_token_hash` a NOT NULL + UNIQUE y elimina `refresh_token`.

Downgrade:
Recrea `refresh_token` NOT NULL + UNIQUE usando `refresh_token_hash` como valor provisional
y elimina las tres columnas nuevas. El token en claro no es recuperable desde el hash, por lo
que las sesiones previas quedaran invalidadas tras revertir.
"""

import hashlib
from collections.abc import Sequence
from datetime import timedelta

import sqlalchemy as sa
from alembic import op

from migration_helpers import dependent_views

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10008"
down_revision: str | Sequence[str] | None = "b7e1a0d10006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

DEFAULT_REFRESH_TTL_DAYS = 30
UNIQUE_HASH_CONSTRAINT = "uq_user_sessions_refresh_token_hash"
LEGACY_UNIQUE_CONSTRAINT = "user_sessions_refresh_token_key"


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    if bind.dialect.name == "postgresql":
        views = dependent_views(bind, "user_sessions", "refresh_token")
        if views:
            names = ", ".join(view.name for view in views)
            raise RuntimeError(
                f"Las vistas {names} dependen de user_sessions.refresh_token y la migracion no las toca. "
                "Adaptalas o eliminalas manualmente antes de migrar."
            )

    # Paso 1: anadir columnas como anulables
    op.add_column("user_sessions", sa.Column("refresh_token_hash", sa.String(length=64), nullable=True))
    op.add_column("user_sessions", sa.Column("expires_at", sa.DateTime(), nullable=True))
    op.add_column("user_sessions", sa.Column("revoked_at", sa.DateTime(), nullable=True))

    # Paso 2: rellenar hash, expires_at y revoked_at de sesiones existentes
    rows = bind.execute(
        sa.text("SELECT id, refresh_token, created_at, last_active, is_active FROM user_sessions")
    ).mappings().all()
    for row in rows:
        token_hash = hashlib.sha256(str(row["refresh_token"]).encode("utf-8")).hexdigest()
        created_at = row["created_at"]
        expires_at = created_at + timedelta(days=DEFAULT_REFRESH_TTL_DAYS) if created_at is not None else None
        revoked_at = None if row["is_active"] else (row["last_active"] or created_at)
        bind.execute(
            sa.text(
                "UPDATE user_sessions "
                "SET refresh_token_hash = :token_hash, expires_at = :expires_at, revoked_at = :revoked_at "
                "WHERE id = :id"
            ),
            {
                "id": row["id"],
                "token_hash": token_hash,
                "expires_at": expires_at,
                "revoked_at": revoked_at,
            },
        )

    # Paso 3: endurecer refresh_token_hash y eliminar refresh_token en claro
    op.alter_column("user_sessions", "refresh_token_hash", existing_type=sa.String(length=64), nullable=False)
    op.create_unique_constraint(UNIQUE_HASH_CONSTRAINT, "user_sessions", ["refresh_token_hash"])
    op.drop_column("user_sessions", "refresh_token")


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    op.add_column("user_sessions", sa.Column("refresh_token", sa.String(), nullable=True))
    bind.execute(sa.text("UPDATE user_sessions SET refresh_token = refresh_token_hash"))
    op.alter_column("user_sessions", "refresh_token", existing_type=sa.String(), nullable=False)
    op.create_unique_constraint(LEGACY_UNIQUE_CONSTRAINT, "user_sessions", ["refresh_token"])

    op.drop_constraint(UNIQUE_HASH_CONSTRAINT, "user_sessions", type_="unique")
    op.drop_column("user_sessions", "revoked_at")
    op.drop_column("user_sessions", "expires_at")
    op.drop_column("user_sessions", "refresh_token_hash")
