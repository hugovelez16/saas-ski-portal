"""drop_client_and_rate_applied_from_work_logs

Revision ID: a1b2c3d4e5f6
Revises: 32a6a8b2c9ff
Create Date: 2026-05-08 11:30:00.000000

Rationale:
- `client` is not a fixed field — it belongs to company-defined extraData (worklog_definitions).
- `rate_applied` is redundant: the same value is already stored inside `calculation_snapshot->rate_applied`,
  which also provides the full historic context (definition, taxes, display lines, etc.).
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: str | Sequence[str] | None = '32a6a8b2c9ff'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Drop client and rate_applied columns from work_logs.
    
    The 'Work Logs' view depends on wl.client, so we drop it first and recreate it
    without that column. rate_applied data is preserved inside calculation_snapshot.
    """
    # 1. Drop the dependent view
    op.execute('DROP VIEW IF EXISTS "Work Logs"')

    # 2. Drop the columns
    op.drop_column('work_logs', 'client')
    op.drop_column('work_logs', 'rate_applied')

    # 3. Recreate the view without client and rate_applied
    op.execute("""
        CREATE VIEW "Work Logs" AS
        SELECT
            wl.id,
            u.email AS worker_email,
            c.name AS company_name,
            wl.type,
            wl.start_date,
            wl.duration,
            wl.net_amount,
            wl.description,
            wl.user_id,
            wl.company_id
        FROM work_logs wl
        JOIN users u ON wl.user_id = u.id
        JOIN companies c ON wl.company_id = c.id
    """)


def downgrade() -> None:
    """Restore client and rate_applied columns (data will be lost)."""
    # 1. Drop the updated view
    op.execute('DROP VIEW IF EXISTS "Work Logs"')

    # 2. Restore columns
    op.add_column('work_logs', sa.Column('rate_applied', sa.Numeric(10, 2), nullable=True))
    op.add_column('work_logs', sa.Column('client', sa.String(), nullable=True))

    # 3. Recreate original view with client
    op.execute("""
        CREATE VIEW "Work Logs" AS
        SELECT
            wl.id,
            u.email AS worker_email,
            c.name AS company_name,
            wl.type,
            wl.start_date,
            wl.duration,
            wl.net_amount,
            wl.client,
            wl.description,
            wl.user_id,
            wl.company_id
        FROM work_logs wl
        JOIN users u ON wl.user_id = u.id
        JOIN companies c ON wl.company_id = c.id
    """)
