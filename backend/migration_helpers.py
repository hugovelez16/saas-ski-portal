"""Apoyo para migraciones Alembic con vistas de PostgreSQL que dependen de columnas alteradas.

PostgreSQL no permite cambiar el tipo ni borrar una columna leida por una vista. En las bases
reales hay vistas creadas a mano que el repo no conoce, asi que las migraciones que alteran o
borran columnas deben localizarlas, eliminarlas, aplicar el DDL y recrearlas con la misma
definicion, propietario y privilegios (DROP VIEW pierde los GRANT).

Solo cubre vistas del esquema `public`. No restaura privilegios por columna, comentarios, triggers ni
el `grantor` de cada GRANT. Las vistas materializadas dependientes abortan la
migracion. Se importa desde las versiones (`prepend_sys_path = .` en alembic.ini).
"""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass, replace

from sqlalchemy import text

SCHEMA = "public"

# Vistas (cualquier nivel) que dependen de una columna, con su profundidad maxima de dependencia:
# profundidad 1 lee la columna; mayor, lee otra vista dependiente. Se crea de menor a mayor.
_DEPENDENT_VIEWS_SQL = """
WITH RECURSIVE target AS (
    SELECT a.attrelid AS rel, a.attnum
    FROM pg_attribute a
    WHERE a.attrelid = to_regclass(:qualified_table) AND a.attname = :column AND NOT a.attisdropped
), deps AS (
    SELECT r.ev_class AS view_oid, 1 AS depth
    FROM pg_depend d
    JOIN pg_rewrite r ON r.oid = d.objid
    JOIN target t ON t.rel = d.refobjid AND t.attnum = d.refobjsubid
    WHERE d.classid = 'pg_rewrite'::regclass AND d.refclassid = 'pg_class'::regclass
      AND r.ev_class <> d.refobjid
    UNION
    SELECT r.ev_class, deps.depth + 1
    FROM deps
    JOIN pg_depend d ON d.refobjid = deps.view_oid AND d.refclassid = 'pg_class'::regclass
        AND d.classid = 'pg_rewrite'::regclass
    JOIN pg_rewrite r ON r.oid = d.objid
    WHERE r.ev_class <> deps.view_oid
)
SELECT c.relname, c.relkind, max(deps.depth) AS depth
FROM deps
JOIN pg_class c ON c.oid = deps.view_oid
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :schema
GROUP BY c.relname, c.relkind
ORDER BY max(deps.depth), c.relname
"""

_SNAPSHOT_SQL = """
SELECT pg_get_viewdef(c.oid, true) AS definition,
       pg_get_userbyid(c.relowner) AS owner,
       coalesce(c.reloptions, ARRAY[]::text[]) AS options,
       c.oid AS oid
FROM pg_class c
JOIN pg_namespace n ON n.oid = c.relnamespace
WHERE n.nspname = :schema AND c.relname = :name AND c.relkind = 'v'
"""

# grantee 0 es PUBLIC. Se omiten los privilegios del propietario: la vista nueva ya los tiene.
_GRANTS_SQL = """
SELECT CASE WHEN acl.grantee = 0 THEN NULL ELSE pg_get_userbyid(acl.grantee) END AS grantee,
       acl.privilege_type, acl.is_grantable
FROM pg_class c, LATERAL aclexplode(c.relacl) acl
WHERE c.oid = :oid AND acl.grantee <> c.relowner
ORDER BY 1 NULLS FIRST, 2
"""


@dataclass(frozen=True)
class ViewSnapshot:
    name: str
    definition: str
    owner: str
    options: tuple[str, ...]
    grants: tuple[tuple[str | None, str, bool], ...]  # (rol o None=PUBLIC, privilegio, con GRANT OPTION)


def _quote(bind, identifier: str) -> str:
    return bind.dialect.identifier_preparer.quote(identifier)


def view_snapshot(bind, name: str) -> ViewSnapshot | None:
    """Definicion, propietario, opciones y privilegios de la vista `public.<name>`; None si no existe."""
    row = bind.execute(text(_SNAPSHOT_SQL), {"schema": SCHEMA, "name": name}).mappings().first()
    if row is None:
        return None
    grants = bind.execute(text(_GRANTS_SQL), {"oid": row["oid"]}).all()
    return ViewSnapshot(
        name=name,
        definition=row["definition"].strip().rstrip(";").strip(),
        owner=row["owner"],
        options=tuple(row["options"]),
        grants=tuple((grantee, privilege, grantable) for grantee, privilege, grantable in grants),
    )


def dependent_views(bind, table: str, column: str) -> list[ViewSnapshot]:
    """Vistas de `public` que dependen de `table.column`, directa o indirectamente, en orden de creacion."""
    rows = bind.execute(
        text(_DEPENDENT_VIEWS_SQL),
        {"qualified_table": f"{SCHEMA}.{table}", "column": column, "schema": SCHEMA},
    ).all()
    materialized = [name for name, kind, _ in rows if kind != "v"]
    if materialized:
        raise RuntimeError(
            f"Las vistas materializadas {', '.join(materialized)} dependen de {table}.{column}: "
            "la migracion no las trata. Eliminalas o adaptalas manualmente antes de migrar."
        )
    snapshots = [view_snapshot(bind, name) for name, _, _ in rows]
    return [snapshot for snapshot in snapshots if snapshot is not None]


def drop_views(bind, views: list[ViewSnapshot]) -> None:
    """Elimina las vistas en orden inverso al de creacion (las que dependen de otras, primero)."""
    for view in reversed(views):
        bind.execute(text(f"DROP VIEW {SCHEMA}.{_quote(bind, view.name)}"))


def create_views(bind, views: list[ViewSnapshot]) -> None:
    """Crea las vistas en orden y restaura opciones, propietario y privilegios."""
    current_user = bind.execute(text("SELECT current_user")).scalar()
    for view in views:
        name = f"{SCHEMA}.{_quote(bind, view.name)}"
        # Los ":" de la definicion (casts, literales) se escapan para que text() no los tome por parametros.
        bind.execute(text(f"CREATE VIEW {name} AS {view.definition}".replace(":", r"\:")))
        if view.options:
            bind.execute(text(f"ALTER VIEW {name} SET ({', '.join(view.options)})"))
        # Los GRANT van antes del cambio de propietario: despues, un usuario sin privilegios de superusuario ya no podria concederlos.
        for grantee, privilege, grantable in view.grants:
            target = "PUBLIC" if grantee is None else _quote(bind, grantee)
            option = " WITH GRANT OPTION" if grantable else ""
            bind.execute(text(f"GRANT {privilege} ON {name} TO {target}{option}"))
        if view.owner != current_user:
            bind.execute(text(f"ALTER VIEW {name} OWNER TO {_quote(bind, view.owner)}"))


@contextmanager
def recreate_dependent_views(bind, table: str, column: str) -> Generator[list[ViewSnapshot]]:
    """Elimina las vistas que dependen de `table.column`, cede el control para el DDL y las recrea."""
    views = dependent_views(bind, table, column)
    drop_views(bind, views)
    yield views
    create_views(bind, views)


def with_definition(view: ViewSnapshot, definition: str) -> ViewSnapshot:
    """Misma vista (propietario y privilegios) con otra definicion."""
    return replace(view, definition=definition)
