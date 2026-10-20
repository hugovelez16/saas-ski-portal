"""eliminar users.default_company_id

Revision ID: b7e1a0d10007
Revises: b7e1a0d10001
Create Date: 2026-10-19 10:00:00.000000

Downgrade: recrea la columna nullable con su FK a companies.id y SIN datos. El
rollback correcto con datos es restaurar el backup previo al despliegue.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10007'
down_revision: str | Sequence[str] | None = 'b7e1a0d10001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    # En PostgreSQL, al borrar la columna se elimina tambien su clave foranea.
    op.drop_column('users', 'default_company_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column(
        'users',
        sa.Column(
            'default_company_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('companies.id'),
            nullable=True,
        ),
    )
