"""limitar companies.name a 120 caracteres

Revision ID: b7e1a0d10002
Revises: b7e1a0d10007
Create Date: 2026-10-20 10:00:00.000000

Solo comprueba y altera; no repara datos. Si hay nombres vacios, con espacios sobrantes o de
mas de 120 caracteres, la migracion aborta sin cambiar nada. La reparacion es del script
backend/scripts/repair_company_names.py (ver docs/empresa/plan-implementacion-empresa.md, seccion 9).

Las vistas que leen companies.name ("Work Logs" y las manuales de produccion, tambien las que
dependen de otras vistas) se eliminan antes del ALTER y se recrean despues con su definicion,
propietario y privilegios (migration_helpers.recreate_dependent_views).

Downgrade: vuelve a `VARCHAR` sin longitud. No restaura datos.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migration_helpers import recreate_dependent_views

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10002'
down_revision: str | Sequence[str] | None = 'b7e1a0d10007'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _alter_name(new_type: sa.types.TypeEngine) -> None:
    # El ALTER toma ACCESS EXCLUSIVE sobre companies: si no obtiene el bloqueo, falla en vez de encolar peticiones.
    op.execute("SET LOCAL lock_timeout = '5s'")
    # PostgreSQL no permite cambiar el tipo de una columna leida por una vista ("Work Logs" y las
    # vistas manuales de produccion): se eliminan, se altera y se recrean con la misma definicion.
    with recreate_dependent_views(op.get_bind(), 'companies', 'name'):
        op.alter_column(
            'companies',
            'name',
            existing_type=sa.String(),
            type_=new_type,
            existing_nullable=False,
        )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    invalid_ids = bind.execute(
        sa.text(
            "SELECT id FROM companies "
            "WHERE name IS NULL OR length(btrim(name)) = 0 OR name <> btrim(name) OR length(name) > 120 "
            "ORDER BY id"
        )
    ).scalars().all()
    if invalid_ids:
        ids = ", ".join(str(company_id) for company_id in invalid_ids)
        raise RuntimeError(
            f"Hay {len(invalid_ids)} empresas con nombre no valido (ids: {ids}). "
            "Ejecuta backend/scripts/repair_company_names.py --apply antes de migrar "
            "(ver docs/empresa/plan-implementacion-empresa.md, seccion 9)"
        )

    _alter_name(sa.String(120))


def downgrade() -> None:
    """Downgrade schema."""
    _alter_name(sa.String())
