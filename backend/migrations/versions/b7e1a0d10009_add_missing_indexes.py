"""anadir indices faltantes en tablas principales

Revision ID: b7e1a0d10009
Revises: b7e1a0d10008
Create Date: 2026-11-27 20:26:00.000000

Crea los 6 indices que faltan para consultas frecuentes:
- work_logs(company_id, start_date)
- work_logs(user_id, start_date)
- company_members(company_id)
- user_sessions(user_id)
- module_subscriptions(company_id)
- audit_logs(target_user_id)

Los 4 indices de audit_logs creados en b7e1a0d10001 ya existen en BD y se
alinean en backend/models.py sin recrearlos aqui.
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10009"
down_revision: str | Sequence[str] | None = "b7e1a0d10008"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index("ix_work_logs_company_start_date", "work_logs", ["company_id", "start_date"], unique=False)
    op.create_index("ix_work_logs_user_start_date", "work_logs", ["user_id", "start_date"], unique=False)
    op.create_index("ix_company_members_company_id", "company_members", ["company_id"], unique=False)
    op.create_index("ix_user_sessions_user_id", "user_sessions", ["user_id"], unique=False)
    op.create_index("ix_module_subscriptions_company_id", "module_subscriptions", ["company_id"], unique=False)
    op.create_index("ix_audit_logs_target_user_id", "audit_logs", ["target_user_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_audit_logs_target_user_id", table_name="audit_logs")
    op.drop_index("ix_module_subscriptions_company_id", table_name="module_subscriptions")
    op.drop_index("ix_user_sessions_user_id", table_name="user_sessions")
    op.drop_index("ix_company_members_company_id", table_name="company_members")
    op.drop_index("ix_work_logs_user_start_date", table_name="work_logs")
    op.drop_index("ix_work_logs_company_start_date", table_name="work_logs")
