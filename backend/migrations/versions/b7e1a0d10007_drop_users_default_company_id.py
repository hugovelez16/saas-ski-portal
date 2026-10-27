"""eliminar users.default_company_id

Revision ID: b7e1a0d10007
Revises: b7e1a0d10001
Create Date: 2026-10-19 10:00:00.000000

La vista manual "Usuarios" (no esta en el repo) lee users.default_company_id y bloquea el DROP:
si existe, se elimina y se recrea sin la columna (default_company_name pierde sentido), con su
propietario y privilegios. Si otra vista depende de la columna, la migracion aborta nombrandola:
adaptarla es una decision manual (docs/empresa/plan-implementacion-empresa.md, seccion 10).

Downgrade: recrea la columna nullable con su FK a companies.id y SIN datos y, si "Usuarios"
existe, vuelve a su definicion original con el LEFT JOIN a companies. El rollback correcto con
datos es restaurar el backup previo al despliegue.
"""
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from migration_helpers import create_views, dependent_views, drop_views, view_snapshot, with_definition

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10007'
down_revision: str | Sequence[str] | None = 'b7e1a0d10001'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

USUARIOS_VIEW = "Usuarios"
USUARIOS_WITHOUT_COMPANY_SQL = """
    SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_active, u.created_at
    FROM users u
"""
USUARIOS_WITH_COMPANY_SQL = """
    SELECT u.id, u.email, u.first_name, u.last_name, u.role, u.is_active,
           c.name AS default_company_name, u.created_at
    FROM users u LEFT JOIN companies c ON u.default_company_id = c.id
"""


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    views = dependent_views(bind, 'users', 'default_company_id')
    foreign = [view.name for view in views if view.name != USUARIOS_VIEW]
    if foreign:
        raise RuntimeError(
            f"Las vistas {', '.join(foreign)} dependen (directa o a traves de otra vista) de users.default_company_id y la migracion no las "
            "toca. Adaptalas o eliminalas manualmente antes de migrar "
            "(ver docs/empresa/plan-implementacion-empresa.md, seccion 10)"
        )

    drop_views(bind, views)
    # En PostgreSQL, al borrar la columna se elimina tambien su clave foranea.
    op.drop_column('users', 'default_company_id')
    create_views(bind, [with_definition(view, USUARIOS_WITHOUT_COMPANY_SQL.strip()) for view in views])


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    usuarios = view_snapshot(bind, USUARIOS_VIEW)
    if usuarios is not None:
        drop_views(bind, [usuarios])
    op.add_column(
        'users',
        sa.Column(
            'default_company_id',
            sa.UUID(as_uuid=True),
            sa.ForeignKey('companies.id'),
            nullable=True,
        ),
    )
    if usuarios is not None:
        create_views(bind, [with_definition(usuarios, USUARIOS_WITH_COMPANY_SQL.strip())])
