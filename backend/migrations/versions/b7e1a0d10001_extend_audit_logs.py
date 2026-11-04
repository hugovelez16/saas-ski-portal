"""extender audit_logs con actor, empresa, valores y motivo

Revision ID: b7e1a0d10001
Revises: 8f10a2b3c4d5
Create Date: 2026-10-18 10:00:00.000000

Downgrade: no es destructivo con los datos de auditoria. Antes de eliminar
actor_user_id rellena admin_user_id e impersonated_user_id cuando estan vacios.
Si hay filas con actor_user_id nulo y admin_user_id o impersonated_user_id
tambien nulos (sin target_user_id que cubra el segundo), el downgrade falla
porque ambas columnas pasan a NOT NULL: hay que corregir o eliminar esas filas
antes de revertir.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10001'
down_revision: str | Sequence[str] | None = '8f10a2b3c4d5'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'audit_logs',
        sa.Column('actor_user_id', sa.UUID(as_uuid=True), sa.ForeignKey('users.id'), nullable=True)
    )
    op.add_column(
        'audit_logs',
        sa.Column('company_id', sa.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'audit_logs',
        sa.Column('target_user_id', sa.UUID(as_uuid=True), nullable=True)
    )
    op.add_column(
        'audit_logs',
        sa.Column('old_value', postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        'audit_logs',
        sa.Column('new_value', postgresql.JSONB(), nullable=True)
    )
    op.add_column(
        'audit_logs',
        sa.Column('reason', sa.Text(), nullable=True)
    )

    op.alter_column('audit_logs', 'impersonated_user_id', nullable=True)
    op.alter_column('audit_logs', 'admin_user_id', nullable=True)

    op.execute("UPDATE audit_logs SET actor_user_id = admin_user_id")

    op.create_index('ix_audit_logs_actor_user_id', 'audit_logs', ['actor_user_id'], unique=False)
    op.create_index('ix_audit_logs_company_id', 'audit_logs', ['company_id'], unique=False)
    op.create_index('ix_audit_logs_company_created', 'audit_logs', ['company_id', 'created_at'], unique=False)
    op.create_index('ix_audit_logs_action', 'audit_logs', ['action'], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(
        "UPDATE audit_logs SET admin_user_id = COALESCE(admin_user_id, actor_user_id)"
    )
    op.execute(
        "UPDATE audit_logs SET impersonated_user_id = "
        "COALESCE(impersonated_user_id, target_user_id, actor_user_id)"
    )

    op.drop_index('ix_audit_logs_action', table_name='audit_logs')
    op.drop_index('ix_audit_logs_company_created', table_name='audit_logs')
    op.drop_index('ix_audit_logs_company_id', table_name='audit_logs')
    op.drop_index('ix_audit_logs_actor_user_id', table_name='audit_logs')

    op.alter_column('audit_logs', 'admin_user_id', nullable=False)
    op.alter_column('audit_logs', 'impersonated_user_id', nullable=False)

    op.drop_column('audit_logs', 'reason')
    op.drop_column('audit_logs', 'new_value')
    op.drop_column('audit_logs', 'old_value')
    op.drop_column('audit_logs', 'target_user_id')
    op.drop_column('audit_logs', 'company_id')
    op.drop_column('audit_logs', 'actor_user_id')
