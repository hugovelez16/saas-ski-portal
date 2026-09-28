"""anadir is_active e is_managed a companies

Revision ID: 8f10a2b3c4d5
Revises: 737f741df8a7
Create Date: 2026-09-28 22:50:00.000000

"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '8f10a2b3c4d5'
down_revision: str | Sequence[str] | None = '737f741df8a7'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'companies',
        sa.Column('is_active', sa.Boolean(), server_default='true', nullable=False)
    )
    op.add_column(
        'companies',
        sa.Column('is_managed', sa.Boolean(), server_default='false', nullable=False)
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('companies', 'is_managed')
    op.drop_column('companies', 'is_active')
