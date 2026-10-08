"""add_get_billing_summary_function

Revision ID: 7d19bd7c379c
Revises: 0fb22f01dd7d
Create Date: 2026-07-17 10:36:58.859801

"""
from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = '7d19bd7c379c'
down_revision: str | Sequence[str] | None = '0fb22f01dd7d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("""
    CREATE OR REPLACE FUNCTION get_billing_summary(comp_id UUID, s_date DATE, e_date DATE)
    RETURNS TABLE (
        user_id UUID,
        first_name VARCHAR,
        last_name VARCHAR,
        email VARCHAR,
        type VARCHAR,
        total_hours NUMERIC,
        total_net NUMERIC,
        total_gross NUMERIC,
        unique_days INT,
        logs_count INT
    ) AS $$
    BEGIN
        RETURN QUERY
        WITH active_members AS (
            SELECT cm.user_id, u.first_name, u.last_name, u.email
            FROM company_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.company_id = comp_id
              AND cm.is_active = true
        ),
        filtered_logs AS (
            SELECT * FROM work_logs
            WHERE company_id = comp_id
              AND end_date >= s_date AND start_date <= e_date
        ),
        unique_days_cte AS (
            SELECT wl.user_id, wl.type, COUNT(DISTINCT d.day) AS unique_days
            FROM filtered_logs wl,
            LATERAL generate_series(wl.start_date::timestamp, wl.end_date::timestamp, '1 day'::interval) d(day)
            GROUP BY wl.user_id, wl.type
        ),
        metrics_cte AS (
            SELECT wl.user_id, wl.type, 
                   SUM(wl.duration) AS total_hours,
                   SUM(wl.net_amount) AS total_net, 
                   SUM(wl.gross_amount) AS total_gross,
                   COUNT(*) AS logs_count
            FROM filtered_logs wl
            GROUP BY wl.user_id, wl.type
        )
        SELECT
            am.user_id,
            am.first_name::VARCHAR,
            am.last_name::VARCHAR,
            am.email::VARCHAR,
            m.type::VARCHAR,
            COALESCE(m.total_hours, 0)::NUMERIC AS total_hours,
            COALESCE(m.total_net, 0)::NUMERIC AS total_net,
            COALESCE(m.total_gross, 0)::NUMERIC AS total_gross,
            COALESCE(u.unique_days, 0)::INT AS unique_days,
            COALESCE(m.logs_count, 0)::INT AS logs_count
        FROM active_members am
        LEFT JOIN metrics_cte m ON am.user_id = m.user_id
        LEFT JOIN unique_days_cte u ON am.user_id = u.user_id AND m.type = u.type;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_billing_summary(UUID, DATE, DATE);")
