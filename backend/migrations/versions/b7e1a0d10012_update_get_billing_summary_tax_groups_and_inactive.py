"""actualiza get_billing_summary con miembros inactivos y neto agrupado por impuestos

Revision ID: b7e1a0d10012
Revises: b7e1a0d10011
Create Date: 2026-11-28 12:00:00.000000

1. Incluye miembros inactivos con turnos en el periodo consultado, devolviendo `is_active`
   para que la vista pueda marcarlos como inactivos (R-TAR-29).
2. Calcula `total_net` (por miembro y tipo) y `user_total_net` (por miembro en el periodo)
   agrupando por trabajador y conjunto efectivo de impuestos (`calculation_snapshot->'tax_applied'`),
   sumando el bruto del grupo y aplicando la retencion una sola vez antes de redondear (R-TAR-27, R-TAR-30).
"""

from collections.abc import Sequence

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "b7e1a0d10012"
down_revision: str | Sequence[str] | None = "b7e1a0d10011"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_billing_summary(UUID, DATE, DATE);")
    op.execute("""
    CREATE FUNCTION get_billing_summary(comp_id UUID, s_date DATE, e_date DATE)
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
        logs_count INT,
        is_active BOOLEAN,
        user_total_net NUMERIC
    ) AS $$
    BEGIN
        RETURN QUERY
        WITH filtered_logs AS (
            SELECT
                wl.user_id,
                wl.type,
                wl.start_date,
                wl.end_date,
                wl.duration,
                wl.gross_amount,
                wl.net_amount,
                wl.calculation_snapshot
            FROM work_logs wl
            WHERE wl.company_id = comp_id
              AND wl.end_date >= s_date
              AND wl.start_date <= e_date
        ),
        billing_members AS (
            SELECT cm.user_id, u.first_name, u.last_name, u.email, cm.is_active
            FROM company_members cm
            JOIN users u ON cm.user_id = u.id
            WHERE cm.company_id = comp_id
              AND (
                  cm.is_active = true
                  OR EXISTS (
                      SELECT 1 FROM filtered_logs fl WHERE fl.user_id = cm.user_id
                  )
              )
        ),
        logs_enriched AS (
            SELECT
                fl.user_id,
                fl.type,
                fl.duration,
                fl.gross_amount,
                fl.net_amount,
                (
                    fl.calculation_snapshot IS NOT NULL
                    AND jsonb_typeof(fl.calculation_snapshot->'tax_applied') = 'object'
                    AND (
                        CASE
                            WHEN fl.calculation_snapshot ? 'rate_applied'
                                 AND jsonb_typeof(fl.calculation_snapshot->'rate_applied') = 'object'
                                THEN COALESCE((fl.calculation_snapshot->'rate_applied'->>'is_gross')::boolean, false)
                            WHEN fl.calculation_snapshot ? 'metadata'
                                 AND jsonb_typeof(fl.calculation_snapshot->'metadata') = 'object'
                                THEN COALESCE((fl.calculation_snapshot->'metadata'->>'is_gross')::boolean, false)
                            ELSE true
                        END
                    )
                ) AS use_grouped,
                CASE
                    WHEN fl.calculation_snapshot IS NOT NULL
                         AND jsonb_typeof(fl.calculation_snapshot->'tax_applied') = 'object'
                    THEN COALESCE(
                        (
                            SELECT jsonb_object_agg(kv.key, trim_scale(kv.value::numeric))
                            FROM jsonb_each_text(fl.calculation_snapshot->'tax_applied') AS kv(key, value)
                            WHERE kv.value IS NOT NULL
                              AND kv.value ~ '^-?[0-9]+(\\.[0-9]+)?([eE][+-]?[0-9]+)?$'
                              AND kv.value::numeric <> 0
                        ),
                        '{}'::jsonb
                    )
                    ELSE NULL
                END AS tax_key,
                CASE
                    WHEN fl.calculation_snapshot IS NOT NULL
                         AND jsonb_typeof(fl.calculation_snapshot->'tax_applied') = 'object'
                    THEN COALESCE(
                        (
                            SELECT SUM(kv.value::numeric)
                            FROM jsonb_each_text(fl.calculation_snapshot->'tax_applied') AS kv(key, value)
                            WHERE kv.value IS NOT NULL
                              AND kv.value ~ '^-?[0-9]+(\\.[0-9]+)?([eE][+-]?[0-9]+)?$'
                              AND kv.value::numeric <> 0
                        ),
                        0::numeric
                    )
                    ELSE 0::numeric
                END AS tax_sum
            FROM filtered_logs fl
        ),
        type_tax_groups AS (
            SELECT
                le.user_id,
                le.type,
                CASE
                    WHEN le.use_grouped THEN ROUND(SUM(le.gross_amount) * GREATEST(0::numeric, 1::numeric - le.tax_sum), 2)
                    ELSE ROUND(SUM(le.net_amount), 2)
                END AS group_net
            FROM logs_enriched le
            GROUP BY le.user_id, le.type, le.use_grouped, le.tax_key, le.tax_sum
        ),
        type_nets_cte AS (
            SELECT ttg.user_id, ttg.type, SUM(ttg.group_net) AS total_net
            FROM type_tax_groups ttg
            GROUP BY ttg.user_id, ttg.type
        ),
        user_tax_groups AS (
            SELECT
                le.user_id,
                CASE
                    WHEN le.use_grouped THEN ROUND(SUM(le.gross_amount) * GREATEST(0::numeric, 1::numeric - le.tax_sum), 2)
                    ELSE ROUND(SUM(le.net_amount), 2)
                END AS group_net
            FROM logs_enriched le
            GROUP BY le.user_id, le.use_grouped, le.tax_key, le.tax_sum
        ),
        user_nets_cte AS (
            SELECT utg.user_id, SUM(utg.group_net) AS user_total_net
            FROM user_tax_groups utg
            GROUP BY utg.user_id
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
                   SUM(wl.gross_amount) AS total_gross,
                   COUNT(*) AS logs_count
            FROM filtered_logs wl
            GROUP BY wl.user_id, wl.type
        )
        SELECT
            bm.user_id,
            bm.first_name::VARCHAR,
            bm.last_name::VARCHAR,
            bm.email::VARCHAR,
            m.type::VARCHAR,
            COALESCE(m.total_hours, 0)::NUMERIC AS total_hours,
            COALESCE(tn.total_net, 0)::NUMERIC AS total_net,
            COALESCE(m.total_gross, 0)::NUMERIC AS total_gross,
            COALESCE(u.unique_days, 0)::INT AS unique_days,
            COALESCE(m.logs_count, 0)::INT AS logs_count,
            bm.is_active::BOOLEAN AS is_active,
            COALESCE(un.user_total_net, 0)::NUMERIC AS user_total_net
        FROM billing_members bm
        LEFT JOIN metrics_cte m ON bm.user_id = m.user_id
        LEFT JOIN type_nets_cte tn ON bm.user_id = tn.user_id AND m.type = tn.type
        LEFT JOIN unique_days_cte u ON bm.user_id = u.user_id AND m.type = u.type
        LEFT JOIN user_nets_cte un ON bm.user_id = un.user_id;
    END;
    $$ LANGUAGE plpgsql;
    """)


def downgrade() -> None:
    op.execute("DROP FUNCTION IF EXISTS get_billing_summary(UUID, DATE, DATE);")
    op.execute("""
    CREATE FUNCTION get_billing_summary(comp_id UUID, s_date DATE, e_date DATE)
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
