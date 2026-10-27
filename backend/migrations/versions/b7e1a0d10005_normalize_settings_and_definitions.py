"""normalizar settings y tipos de turno (features, billing, input_mode, is_range)

Revision ID: b7e1a0d10005
Revises: b7e1a0d10004
Create Date: 2026-10-27 10:00:00.000000

Solo modifica datos JSONB de companies.settings y companies.worklog_definitions. No cambia el esquema.

Antes de escribir nada valida en Python ambos campos de cada empresa. Si encuentra claves de settings
desconocidas, billing con claves ajenas, billing.price_type fuera de net/gross, input_mode fuera de
manual_single/timer/bulk, modules o features con valores no booleanos, unit distinto de hours/days/fixed,
unit "hours" con is_range true, label vacio o de mas de 60 caracteres, o bloques que no son objetos,
aborta con RuntimeError sin cambiar nada. La reparacion es del script backend/scripts/repair_settings_definitions.py (ver
docs/empresa/plan-implementacion-empresa.md, seccion 9).

Upgrade:
- features -> modules, billing.price_type -> business_logic.price_type, input_mode (raiz) ->
  worker_experience.input_mode. Un mapeo nunca pisa un valor ya presente en la ruta destino.
- Retira allow_tutorial, allow_coordination, is_managed, business_logic.cost_markup y
  billing.cost_markup_percent. billing y features desaparecen tras mapear.
- worklog_definitions: si falta unit se fija days (is_range true) u hours (en otro caso). Siempre se
  borra is_range.

Downgrade: INCOMPLETO. Solo restaura is_range: true en los tipos con unit "days" que no lo tengan.
No recrea las claves retiradas, ni features, billing ni input_mode, ni los settings antiguos. El
rollback correcto tras aplicar esta migracion es RESTAURAR EL BACKUP de la BD tomado antes del
despliegue (docs/empresa/plan-implementacion-empresa.md, seccion 10, paso d).

La migracion es autocontenida: no importa codigo de la app ni de scripts, para que sea inmutable.
"""

import copy
import json
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = 'b7e1a0d10005'
down_revision: str | Sequence[str] | None = 'b7e1a0d10004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

UNITS = ("hours", "days", "fixed")
LABEL_MAX = 60
VALID_SETTINGS_KEYS = {"business_logic", "worker_experience", "ui_customization", "modules", "allowed_rates"}
MAPPED_KEYS = {"features", "billing", "input_mode"}
RETIRED_KEYS = {"allow_tutorial", "allow_coordination", "is_managed"}
BILLING_KNOWN_KEYS = {"price_type", "cost_markup_percent"}
OBJECT_BLOCKS = ("features", "billing", "business_logic", "worker_experience", "ui_customization", "modules")
PRICE_TYPES = ("net", "gross")
INPUT_MODES = ("manual_single", "timer", "bulk")

UPDATE_SQL = {
    "settings": sa.text("UPDATE companies SET settings = CAST(:v AS jsonb) WHERE id = :c"),
    "worklog_definitions": sa.text("UPDATE companies SET worklog_definitions = CAST(:v AS jsonb) WHERE id = :c"),
}


def _settings_problems(settings) -> list[str]:
    if settings is None:
        return []
    if not isinstance(settings, dict):
        return ["settings no es un objeto"]
    problems: list[str] = []
    for key in settings:
        if key not in VALID_SETTINGS_KEYS | MAPPED_KEYS | RETIRED_KEYS:
            problems.append(f"settings.{key}, clave desconocida")
    for block in OBJECT_BLOCKS:
        value = settings.get(block)
        if value is not None and not isinstance(value, dict):
            problems.append(f"settings.{block}, debe ser un objeto")
    billing = settings.get("billing")
    if isinstance(billing, dict):
        for sub in billing:
            if sub not in BILLING_KNOWN_KEYS:
                problems.append(f"settings.billing.{sub}, clave desconocida")
        if "price_type" in billing and not _in_enum(billing["price_type"], PRICE_TYPES):
            problems.append(f"settings.billing.price_type, valor no soportado ({billing['price_type']!r})")
    input_mode = settings.get("input_mode")
    if input_mode is not None and not _in_enum(input_mode, INPUT_MODES):
        problems.append(f"settings.input_mode, valor no soportado ({input_mode!r})")
    for block in ("features", "modules"):
        value = settings.get(block)
        if isinstance(value, dict):
            for name, flag in value.items():
                if not isinstance(flag, bool):
                    problems.append(f"settings.{block}.{name}, debe ser booleano ({flag!r})")
    return problems


def _in_enum(value, allowed: tuple) -> bool:
    """Pertenencia a un enum de cadenas. Un valor no hashable (objeto, lista) nunca pertenece."""
    return isinstance(value, str) and value in allowed


def _definition_problems(defs) -> list[str]:
    if defs is None:
        return []
    if not isinstance(defs, dict):
        return ["worklog_definitions no es un objeto"]
    problems: list[str] = []
    for name, definition in defs.items():
        ruta = f"worklog_definitions.{name}"
        if not isinstance(definition, dict):
            problems.append(f"{ruta}, no es un objeto")
            continue
        unit = definition.get("unit")
        if unit is not None and unit not in UNITS:
            problems.append(f"{ruta}, unit no soportado ({unit!r})")
        elif unit == "hours" and definition.get("is_range") is True:
            problems.append(f"{ruta}, unit hours con is_range true")
        label = definition.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > LABEL_MAX:
            problems.append(f"{ruta}.label, vacio o de mas de {LABEL_MAX} caracteres")
    return problems


def _block(settings: dict, name: str) -> dict:
    if settings.get(name) is None:
        settings[name] = {}
    return settings[name]


def _normalize_settings(settings: dict) -> dict:
    new = copy.deepcopy(settings)

    features = new.pop("features", None)
    if features is not None:
        modules = _block(new, "modules")
        for name, value in features.items():
            modules.setdefault(name, value)

    billing = new.pop("billing", None)
    if billing is not None and "price_type" in billing:
        _block(new, "business_logic").setdefault("price_type", billing["price_type"])

    if "input_mode" in new:
        input_mode = new.pop("input_mode")
        if input_mode is not None:
            _block(new, "worker_experience").setdefault("input_mode", input_mode)

    for key in RETIRED_KEYS:
        new.pop(key, None)
    business_logic = new.get("business_logic")
    if isinstance(business_logic, dict):
        business_logic.pop("cost_markup", None)
    return new


def _normalize_definitions(defs: dict) -> dict:
    new = copy.deepcopy(defs)
    for definition in new.values():
        if definition.get("unit") is None:
            definition["unit"] = "days" if definition.get("is_range") is True else "hours"
        definition.pop("is_range", None)
    return new


def _load_rows(bind):
    return [
        (row.id, row.settings, row.worklog_definitions)
        for row in bind.execute(sa.text("SELECT id, settings, worklog_definitions FROM companies ORDER BY id FOR UPDATE"))
    ]


def upgrade() -> None:
    """Upgrade data: mapea y retira claves de settings, y normaliza tipos de turno."""
    bind = op.get_bind()
    rows = _load_rows(bind)

    problems: list[tuple[str, str]] = []
    for company_id, settings, defs in rows:
        problems.extend((str(company_id), text) for text in _settings_problems(settings))
        problems.extend((str(company_id), text) for text in _definition_problems(defs))
    if problems:
        companies = {company_id for company_id, _ in problems}
        detail = "; ".join(f"empresa {company_id}, {text}" for company_id, text in problems)
        raise RuntimeError(
            f"Hay {len(companies)} empresas con settings o tipos de turno que la migracion no puede normalizar: "
            f"{detail}. Ejecuta backend/scripts/repair_settings_definitions.py y resuelve los listados antes de "
            "migrar (ver docs/empresa/plan-implementacion-empresa.md, seccion 9)"
        )

    for company_id, settings, defs in rows:
        if isinstance(settings, dict):
            new_settings = _normalize_settings(settings)
            if new_settings != settings:
                bind.execute(UPDATE_SQL["settings"], {"v": json.dumps(new_settings), "c": company_id})
        if isinstance(defs, dict):
            new_defs = _normalize_definitions(defs)
            if new_defs != defs:
                bind.execute(UPDATE_SQL["worklog_definitions"], {"v": json.dumps(new_defs), "c": company_id})


def downgrade() -> None:
    """Downgrade data (INCOMPLETO): restaura is_range solo en tipos con unit "days".

    No recrea las claves retiradas ni features, billing o input_mode, ni los settings antiguos. El
    rollback correcto es restaurar el backup previo al despliegue (docs/empresa/plan-implementacion-empresa.md,
    seccion 10, paso d).
    """
    bind = op.get_bind()
    for company_id, _settings, defs in _load_rows(bind):
        if not isinstance(defs, dict):
            continue
        new_defs = copy.deepcopy(defs)
        changed = False
        for definition in new_defs.values():
            if isinstance(definition, dict) and definition.get("unit") == "days" and "is_range" not in definition:
                definition["is_range"] = True
                changed = True
        if changed:
            bind.execute(UPDATE_SQL["worklog_definitions"], {"v": json.dumps(new_defs), "c": company_id})
