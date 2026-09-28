"""seed_default_modules

Revision ID: 2314c15d1a0f
Revises: 923b0452b91d
Create Date: 2026-07-13 10:45:04.676741

"""
import uuid
from collections.abc import Sequence
from datetime import datetime

from alembic import op
from sqlalchemy import text

# revision identifiers, used by Alembic.
revision: str = '2314c15d1a0f'
down_revision: str | Sequence[str] | None = '923b0452b91d'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

MODULES_TO_SEED = [
    {
        "code_name": "worker_daily_report",
        "name": "Parte Diario para Trabajadores",
        "description": "Permite a los empleados ver y completar sus partes desde el panel principal.",
        "target_scope": "company",
        "is_active": True,
        "seed_subs": True,
        "legacy_default": True,
    },
]


def upgrade() -> None:
    conn = op.get_bind()
    now = datetime.utcnow()

    for mod_def in MODULES_TO_SEED:
        # 1. Insertar el módulo en el catálogo
        mod_id = str(uuid.uuid4())
        conn.execute(text("""
            INSERT INTO app_modules (id, code_name, name, description, is_active, target_scope, created_at, updated_at)
            VALUES (:id, :code_name, :name, :description, :is_active, :target_scope, :now, :now)
            ON CONFLICT (code_name) DO NOTHING
        """), {
            "id": mod_id, "code_name": mod_def["code_name"], "name": mod_def["name"],
            "description": mod_def["description"], "is_active": mod_def["is_active"],
            "target_scope": mod_def["target_scope"], "now": now
        })

        if not mod_def["seed_subs"]:
            continue

        # 2. Re-fetch real module_id (may already exist)
        result = conn.execute(
            text("SELECT id FROM app_modules WHERE code_name = :code_name"),
            {"code_name": mod_def["code_name"]}
        ).first()
        if not result:
            continue
        real_mod_id = str(result[0])

        # 3. Para cada empresa, leer su JSONB y crear sub si corresponde
        companies = conn.execute(text("SELECT id, settings FROM companies")).fetchall()
        for company in companies:
            company_id = str(company[0])
            settings = company[1] or {}
            modules_dict = settings.get("modules", {})
            features_dict = settings.get("features", {})

            legacy_val = modules_dict.get(mod_def["code_name"])
            feat_val = features_dict.get(mod_def["code_name"])
            is_enabled = legacy_val if legacy_val is not None else (
                feat_val if feat_val is not None else mod_def["legacy_default"]
            )

            if is_enabled:
                conn.execute(text("""
                    INSERT INTO module_subscriptions
                        (id, module_id, company_id, user_id, scope, status, created_at, updated_at)
                    VALUES (:id, :module_id, :company_id, NULL, 'company', 'active', :now, :now)
                    ON CONFLICT DO NOTHING
                """), {
                    "id": str(uuid.uuid4()), "module_id": real_mod_id,
                    "company_id": company_id, "now": now
                })


def downgrade() -> None:
    conn = op.get_bind()
    code_names = [m["code_name"] for m in MODULES_TO_SEED]
    for code_name in code_names:
        conn.execute(text("""
            DELETE FROM module_subscriptions
            WHERE module_id IN (SELECT id FROM app_modules WHERE code_name = :code_name)
        """), {"code_name": code_name})
    for code_name in code_names:
        conn.execute(text("DELETE FROM app_modules WHERE code_name = :code_name"), {"code_name": code_name})
