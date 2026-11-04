"""eliminar companies.fiscal_id

Revision ID: b7e1a0d10006
Revises: b7e1a0d10005
Create Date: 2026-10-29 10:00:00.000000

Solo comprueba y borra; no exporta. Si hay empresas con fiscal_id real (no nulo, no vacio tras
strip y distinto del valor de semilla B00000000) y FISCAL_ID_EXPORTED no vale exactamente 1, la
migracion aborta sin cambiar nada. La exportacion es del script backend/scripts/repair_fiscal_id.py
(ver docs/empresa/plan-implementacion-empresa.md, secciones 9 y 10).

Ninguna vista del repo lee companies.fiscal_id. Si una vista (manual, de produccion) depende de la
columna, directa o a traves de otra vista, no se puede recrear sin ella: la migracion aborta
nombrandola, y adaptarla o eliminarla es una decision manual.

Downgrade: recrea la columna nullable y SIN datos. El rollback correcto con datos es restaurar el
backup previo al despliegue (seccion 10, paso d).
"""
import os
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migration_helpers import dependent_views

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10006'
down_revision: str | Sequence[str] | None = 'b7e1a0d10005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

# Misma definicion de "valor real" que backend/scripts/repair_fiscal_id.py (la migracion no importa el script).
REAL_FISCAL_ID_SQL = (
    "SELECT count(*) FROM companies "
    "WHERE fiscal_id IS NOT NULL AND btrim(fiscal_id) <> '' AND btrim(fiscal_id) <> 'B00000000'"
)


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    real_count = bind.execute(sa.text(REAL_FISCAL_ID_SQL)).scalar()
    if real_count and os.environ.get("FISCAL_ID_EXPORTED") != "1":
        raise RuntimeError(
            f"Hay {real_count} empresas con fiscal_id real. "
            "Exporta con backend/scripts/repair_fiscal_id.py --apply y define FISCAL_ID_EXPORTED=1 "
            "para confirmar (ver docs/empresa/plan-implementacion-empresa.md, secciones 9 y 10)"
        )

    views = dependent_views(bind, 'companies', 'fiscal_id')
    if views:
        raise RuntimeError(
            f"Las vistas {', '.join(view.name for view in views)} dependen (directa o a traves de otra vista) "
            "de companies.fiscal_id y la migracion no puede recrearlas sin la columna. "
            "Adaptalas o eliminalas manualmente antes de migrar "
            "(ver docs/empresa/plan-implementacion-empresa.md, seccion 10)"
        )

    # El DROP toma ACCESS EXCLUSIVE sobre companies: si no obtiene el bloqueo, falla en vez de encolar peticiones.
    op.execute("SET LOCAL lock_timeout = '5s'")
    op.drop_column('companies', 'fiscal_id')


def downgrade() -> None:
    """Downgrade schema."""
    op.add_column('companies', sa.Column('fiscal_id', sa.String(), nullable=True))
