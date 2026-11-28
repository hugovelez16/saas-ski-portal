"""anade tabla company_invitations para invitaciones por correo

Revision ID: b7e1a0d10014
Revises: b7e1a0d10013
Create Date: 2026-11-28 12:30:00.000000

Crea la tabla `company_invitations` con hash SHA-256 del token (`token_hash`),
email normalizado en minusculas, caducidad `timestamptz` e indice unico parcial
para evitar invitaciones pendientes duplicadas por empresa y correo.
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10014"
down_revision: str | Sequence[str] | None = "b7e1a0d10013"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TABLE_NAME = "company_invitations"
IX_COMPANY = "ix_company_invitations_company_id"
UQ_PENDING_EMAIL = "uq_company_invitations_pending_company_email"


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        TABLE_NAME,
        sa.Column("id", sa.UUID(as_uuid=True), primary_key=True, nullable=False),
        sa.Column(
            "company_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("companies.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("token_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column(
            "invited_by_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=False,
        ),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("accepted_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "accepted_by_user_id",
            sa.UUID(as_uuid=True),
            sa.ForeignKey("users.id"),
            nullable=True,
        ),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
    )
    op.create_index(IX_COMPANY, TABLE_NAME, ["company_id"], unique=False)
    op.create_index(
        UQ_PENDING_EMAIL,
        TABLE_NAME,
        ["company_id", sa.text("lower(email)")],
        unique=True,
        postgresql_where=sa.text("accepted_at IS NULL AND cancelled_at IS NULL"),
        sqlite_where=sa.text("accepted_at IS NULL AND cancelled_at IS NULL"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(UQ_PENDING_EMAIL, table_name=TABLE_NAME)
    op.drop_index(IX_COMPANY, table_name=TABLE_NAME)
    op.drop_table(TABLE_NAME)
