"""unificar claves de tax_overrides (ss/irpf a social_security/irpf_base)

Revision ID: b7e1a0d10004
Revises: b7e1a0d10002
Create Date: 2026-10-26 10:00:00.000000

Antes de escribir nada valida en Python los impuestos de companies.tax_config y de
company_members.rates_config[tipo].tax_overrides. Si hay valores no validos (no numericos o
fuera de [0, 1], nombres incumpliendo las reglas de TaxConfig, `extra` distinto de 0 o colisiones
de claves), aborta sin cambiar nada. La reparacion es del script backend/scripts/repair_tax_values.py
(ver docs/empresa/plan-implementacion-empresa.md, seccion 9).

Despues renombra `ss` -> `social_security` e `irpf` -> `irpf_base` dentro de `tax_overrides` y
elimina `extra` cuando vale 0 y la empresa no lo define en su `tax_config`.

La migracion es autocontenida: no importa codigo de la app, para que sea inmutable.

Downgrade: renombrado inverso dentro de `tax_overrides`. No recrea los `extra` eliminados ni toca
`tax_config`. No pisa una clave destino ya existente.
"""
import json
import math
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10004'
down_revision: str | Sequence[str] | None = 'b7e1a0d10002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

TAX_NAME_MAX = 50
TAX_MAX_ENTRIES = 20

UPGRADE_RENAMES = {"ss": "social_security", "irpf": "irpf_base"}
DOWNGRADE_RENAMES = {"social_security": "ss", "irpf_base": "irpf"}


def _is_valid_rate(value) -> bool:
    """Numero (int o float, no bool), finito y dentro de [0, 1]."""
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and 0 <= value <= 1
    except OverflowError:  # entero JSON gigante: no es una tasa valida, se lista en el aborto
        return False


def _is_zero(value) -> bool:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        return False
    try:
        return math.isfinite(value) and value == 0
    except OverflowError:
        return False


def _as_json(value):
    if isinstance(value, str):
        try:
            return json.loads(value)
        except ValueError:
            return value
    return value


def _validate_tax_config(company_id, tax_config) -> list[str]:
    problems: list[str] = []
    if tax_config is None:
        return problems
    if not isinstance(tax_config, dict):
        return [f"empresa {company_id}, tax_config, {tax_config!r}"]

    if len(tax_config) > TAX_MAX_ENTRIES:
        problems.append(f"empresa {company_id}, tax_config, {len(tax_config)} entradas (maximo {TAX_MAX_ENTRIES})")
    seen: set[str] = set()
    for name, value in tax_config.items():
        stripped = name.strip()
        if not stripped or len(stripped) > TAX_NAME_MAX:
            problems.append(f"empresa {company_id}, tax_config.{name}, nombre no valido")
        if stripped in seen:
            problems.append(f"empresa {company_id}, tax_config.{name}, nombre duplicado")
        seen.add(stripped)
        if not _is_valid_rate(value):
            problems.append(f"empresa {company_id}, tax_config.{name}, {value!r}")
    return problems


def _validate_overrides(company_id, user_id, tipo, overrides, company_keys) -> list[str]:
    problems: list[str] = []
    base = f"empresa {company_id}, miembro {user_id}, rates_config.{tipo}.tax_overrides"
    for key, value in overrides.items():
        if key == "extra":
            # `null` se deja; cualquier otro valor distinto de 0 (o no numerico) no se puede migrar.
            if value is not None and not _is_zero(value):
                problems.append(f"{base}.extra, {value!r}")
            continue
        if value is not None and not _is_valid_rate(value):
            problems.append(f"{base}.{key}, {value!r}")
    for old, new in UPGRADE_RENAMES.items():
        if old in overrides and new in overrides:
            problems.append(f"{base}.{old}, colision con {new}")
    return problems


def _load_rows(bind):
    companies = {
        row.id: _as_json(row.tax_config)
        for row in bind.execute(sa.text("SELECT id, tax_config FROM companies ORDER BY id"))
    }
    members = [
        (row.user_id, row.company_id, _as_json(row.rates_config))
        for row in bind.execute(
            sa.text(
                "SELECT user_id, company_id, rates_config FROM company_members "
                "WHERE rates_config IS NOT NULL ORDER BY company_id, user_id"
            )
        )
    ]
    return companies, members


def _iter_override_entries(rates_config):
    """Devuelve (tipo, entrada) solo para valores dict con `tax_overrides` dict."""
    if not isinstance(rates_config, dict):
        return
    for tipo, entry in rates_config.items():
        if isinstance(entry, dict) and isinstance(entry.get("tax_overrides"), dict):
            yield tipo, entry


def _update_member(bind, user_id, company_id, rates_config) -> None:
    bind.execute(
        sa.text(
            "UPDATE company_members SET rates_config = CAST(:v AS jsonb) "
            "WHERE user_id = :u AND company_id = :c"
        ),
        {"v": json.dumps(rates_config), "u": user_id, "c": company_id},
    )


def upgrade() -> None:
    """Upgrade schema."""
    bind = op.get_bind()
    companies, members = _load_rows(bind)

    problems: list[str] = []
    for company_id, tax_config in companies.items():
        problems.extend(_validate_tax_config(company_id, tax_config))
    for user_id, company_id, rates_config in members:
        for tipo, entry in _iter_override_entries(rates_config):
            problems.extend(_validate_overrides(company_id, user_id, tipo, entry["tax_overrides"], None))
    if problems:
        raise RuntimeError(
            f"Hay {len(problems)} valores de impuestos no validos (empresa/miembro, ruta, valor): "
            f"{'; '.join(problems)}. "
            "Ejecuta backend/scripts/repair_tax_values.py y corrige a mano los listados antes de migrar "
            "(ver docs/empresa/plan-implementacion-empresa.md, seccion 9)"
        )

    for user_id, company_id, rates_config in members:
        company_tax = companies.get(company_id)
        company_defines_extra = isinstance(company_tax, dict) and "extra" in company_tax
        changed = False
        for _tipo, entry in _iter_override_entries(rates_config):
            overrides = entry["tax_overrides"]
            new_overrides = {}
            for key, value in overrides.items():
                if key == "extra" and _is_zero(value) and not company_defines_extra:
                    changed = True
                    continue
                new_key = UPGRADE_RENAMES.get(key, key)
                if new_key != key:
                    changed = True
                new_overrides[new_key] = value
            entry["tax_overrides"] = new_overrides
        if changed:
            _update_member(bind, user_id, company_id, rates_config)


def downgrade() -> None:
    """Downgrade schema."""
    bind = op.get_bind()
    _, members = _load_rows(bind)

    for user_id, company_id, rates_config in members:
        changed = False
        for _tipo, entry in _iter_override_entries(rates_config):
            overrides = entry["tax_overrides"]
            new_overrides = {}
            for key, value in overrides.items():
                new_key = DOWNGRADE_RENAMES.get(key, key)
                # Si la clave destino ya existe en el original no se pisa: se conserva la clave actual.
                if new_key != key and new_key in overrides:
                    new_key = key
                if new_key != key:
                    changed = True
                new_overrides[new_key] = value
            entry["tax_overrides"] = new_overrides
        if changed:
            _update_member(bind, user_id, company_id, rates_config)
