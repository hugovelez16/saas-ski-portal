"""Reparacion de settings y tipos de turno previa a la migracion b7e1a0d10005 (PR-11).

Clasifica las claves de `companies.settings` en mapeadas (features, billing.price_type, input_mode),
retiradas (allow_tutorial, allow_coordination, is_managed, business_logic.cost_markup,
billing.cost_markup_percent), validas (modelo CompanySettings) y desconocidas. Clasifica los tipos de
`companies.worklog_definitions` por su `unit` e `is_range`.

Reglas (docs/empresa/plan-implementacion-empresa.md, seccion 9):
- Claves desconocidas de primer nivel -> MANUAL (bloquean la migracion). Solo se eliminan con
  --apply --drop-unknown CLAVE[,CLAVE]. Nunca se eliminan mapeadas, retiradas ni validas.
- billing con claves distintas de price_type y cost_markup_percent -> MANUAL (billing desaparece).
- Valores fuera de contrato (billing.price_type fuera de net/gross, input_mode fuera de
  manual_single/timer/bulk, modules o features con valores no booleanos) -> MANUAL: la migracion los rechaza.
- unit distinto de hours/days/fixed, unit hours con is_range true, label vacio o de mas de 60
  caracteres -> MANUAL.
- is_range sin unit, o ni unit ni is_range -> informativo (la migracion fija days/hours).
- cost_markup y billing.cost_markup_percent se informan con su valor; el backup conserva el original.

--dry-run (defecto) no escribe nada. --apply escribe primero el backup
settings_definitions_before_<ts>.json con settings y worklog_definitions ORIGINALES de todas las
empresas (permisos 0600, fuera del repo) y despues, solo con --drop-unknown, elimina esas claves.
Un unico commit al final.

La migracion no importa de scripts: duplica la logica minima de validacion.

Uso (desde backend/): python3 -m scripts.repair_settings_definitions [--dry-run | --apply]
    [--drop-unknown CLAVE[,CLAVE]] [--backup-dir PATH]
Codigo de salida: 0 sin pendientes, 2 con pendientes de decision manual, 1 error.
"""

from __future__ import annotations

import argparse
import copy
import os
import sys
from collections.abc import Iterable
from pathlib import Path
from typing import NoReturn

import database
import models
from contracts import CompanySettings
from sqlalchemy.orm import Session

from scripts.repair_common import (
    ENV_BACKUP_DIR,
    RepairReport,
    ensure_backup_dir,
    print_report,
    write_backup,
)

TOPIC = "settings_definitions"
BACKUP_TOPIC = "settings_definitions_before"
UNITS = ("hours", "days", "fixed")
LABEL_MAX = 60
PRICE_TYPES = ("net", "gross")
INPUT_MODES = ("manual_single", "timer", "bulk")

MAPPED_TOP = {"features": "modules", "input_mode": "worker_experience.input_mode", "billing": "business_logic"}
RETIRED_TOP = ("allow_tutorial", "allow_coordination", "is_managed")
BILLING_KNOWN = frozenset({"price_type", "cost_markup_percent"})
VALID_TOP = frozenset(CompanySettings.model_fields)
KNOWN_TOP = VALID_TOP | frozenset(MAPPED_TOP) | frozenset(RETIRED_TOP)
# Bloques que deben ser objetos (o null) para poder mapear o validar sin fallo.
OBJECT_BLOCKS = ("features", "billing", "business_logic", "worker_experience", "ui_customization", "modules")


def _in_enum(value, allowed: tuple) -> bool:
    """Pertenencia a un enum de cadenas. Un valor no hashable (objeto, lista) nunca pertenece."""
    return isinstance(value, str) and value in allowed


def parse_drop_unknown(names: Iterable[str] | str) -> frozenset[str]:
    """Normaliza CLAVE[,CLAVE] y rechaza claves mapeadas, retiradas o validas."""
    if isinstance(names, str):
        names = [names]
    result: set[str] = set()
    for raw in names:
        for part in str(raw).split(","):
            name = part.strip()
            if not name:
                continue
            if name in KNOWN_TOP:
                raise ValueError(
                    f"[ERROR] '{name}' no es una clave desconocida (es mapeada, retirada o valida del modelo): "
                    "no se puede eliminar con --drop-unknown"
                )
            result.add(name)
    return frozenset(result)


def _analyze_billing(cid: str, name: str, billing: dict, settings: dict, report: RepairReport, counts: dict) -> None:
    for sub, value in billing.items():
        ruta = f"settings.billing.{sub}"
        if sub not in BILLING_KNOWN:
            report.manual.append(
                {
                    "company_id": cid,
                    "ruta": ruta,
                    "valor": value,
                    "motivo": "clave desconocida dentro de billing (billing desaparece tras mapear): editar a mano",
                }
            )
        elif sub == "price_type":
            if not _in_enum(value, PRICE_TYPES):
                continue  # valor fuera de contrato: decision manual en _check_values
            counts["mapeadas"] += 1
            report.informational.append({"tipo": "mapeada", "company_id": cid, "ruta": ruta, "destino": "business_logic.price_type"})
            logic = settings.get("business_logic")
            if isinstance(logic, dict) and "price_type" in logic:
                report.informational.append(
                    {"tipo": "conflicto", "company_id": cid, "ruta": ruta, "motivo": "destino ya presente: se conserva business_logic.price_type"}
                )
        else:
            counts["retiradas"] += 1
            report.informational.append(
                {"tipo": "retirada", "company_id": cid, "empresa": name, "ruta": ruta, "valor": value}
            )


def _check_values(cid: str, settings: dict, report: RepairReport) -> None:
    """Valores fuera de contrato que la migracion rechaza: decision manual, el script no los reescribe."""
    billing = settings.get("billing")
    if isinstance(billing, dict) and "price_type" in billing and not _in_enum(billing["price_type"], PRICE_TYPES):
        report.manual.append(
            {
                "company_id": cid,
                "ruta": "settings.billing.price_type",
                "valor": billing["price_type"],
                "motivo": f"valor no soportado (validos: {', '.join(PRICE_TYPES)})",
            }
        )
    input_mode = settings.get("input_mode")
    if input_mode is not None and not _in_enum(input_mode, INPUT_MODES):
        report.manual.append(
            {
                "company_id": cid,
                "ruta": "settings.input_mode",
                "valor": input_mode,
                "motivo": f"valor no soportado (validos: {', '.join(INPUT_MODES)})",
            }
        )
    for block in ("features", "modules"):
        value = settings.get(block)
        if isinstance(value, dict):
            for name, flag in value.items():
                if not isinstance(flag, bool):
                    report.manual.append(
                        {
                            "company_id": cid,
                            "ruta": f"settings.{block}.{name}",
                            "valor": flag,
                            "motivo": "el modulo debe ser booleano",
                        }
                    )


def _analyze_settings(cid: str, name: str, settings, report: RepairReport, counts: dict) -> list[tuple[str, object]]:
    """Clasifica settings de una empresa. Devuelve las claves desconocidas de primer nivel (clave, valor)."""
    unknown: list[tuple[str, object]] = []
    if settings is None:
        return unknown
    if not isinstance(settings, dict):
        report.manual.append({"company_id": cid, "ruta": "settings", "valor": settings, "motivo": "settings no es un objeto"})
        return unknown
    for block in OBJECT_BLOCKS:
        value = settings.get(block)
        if value is not None and not isinstance(value, dict):
            report.manual.append({"company_id": cid, "ruta": f"settings.{block}", "valor": value, "motivo": "debe ser un objeto"})
    _check_values(cid, settings, report)

    for key, value in settings.items():
        ruta = f"settings.{key}"
        if key in VALID_TOP:
            counts["validas"] += 1
        elif key in RETIRED_TOP:
            counts["retiradas"] += 1
            report.informational.append({"tipo": "retirada", "company_id": cid, "empresa": name, "ruta": ruta, "valor": value})
        elif key == "billing":
            if isinstance(value, dict):
                _analyze_billing(cid, name, value, settings, report, counts)
        elif key in MAPPED_TOP:
            counts["mapeadas"] += 1
            report.informational.append({"tipo": "mapeada", "company_id": cid, "ruta": ruta, "destino": MAPPED_TOP[key]})
            _report_conflicts(cid, key, value, settings, report)
        else:
            counts["desconocidas"] += 1
            unknown.append((key, value))

    logic = settings.get("business_logic")
    if isinstance(logic, dict) and "cost_markup" in logic:
        counts["retiradas"] += 1
        report.informational.append(
            {
                "tipo": "retirada",
                "company_id": cid,
                "empresa": name,
                "ruta": "settings.business_logic.cost_markup",
                "valor": logic["cost_markup"],
            }
        )
    return unknown


def _report_conflicts(cid: str, key: str, value, settings: dict, report: RepairReport) -> None:
    """Avisa cuando la ruta destino ya tiene valor: la migracion no lo pisa y descarta el origen."""
    if key == "features" and isinstance(value, dict):
        modules = settings.get("modules")
        present = modules if isinstance(modules, dict) else {}
        for name in value:
            if name in present:
                report.informational.append(
                    {"tipo": "conflicto", "company_id": cid, "ruta": f"settings.features.{name}",
                     "motivo": "destino modules ya presente: se conserva modules"}
                )
    elif key == "input_mode":
        experience = settings.get("worker_experience")
        if isinstance(experience, dict) and "input_mode" in experience:
            report.informational.append(
                {"tipo": "conflicto", "company_id": cid, "ruta": "settings.input_mode",
                 "motivo": "destino worker_experience.input_mode ya presente: se conserva el destino"}
            )


def _analyze_definitions(cid: str, defs, report: RepairReport, counts: dict) -> None:
    if defs is None:
        return
    if not isinstance(defs, dict):
        report.manual.append({"company_id": cid, "ruta": "worklog_definitions", "valor": defs, "motivo": "no es un objeto"})
        return
    for name, definition in defs.items():
        ruta = f"worklog_definitions.{name}"
        counts["tipos"] += 1
        if not isinstance(definition, dict):
            report.manual.append({"company_id": cid, "ruta": ruta, "valor": definition, "motivo": "la definicion no es un objeto"})
            continue
        unit = definition.get("unit")
        is_range = definition.get("is_range")
        if unit is not None and unit not in UNITS:
            report.manual.append({"company_id": cid, "ruta": ruta, "valor": unit, "motivo": f"unit no soportado ({unit!r})"})
        elif unit == "hours" and is_range is True:
            report.manual.append(
                {"company_id": cid, "ruta": ruta, "valor": unit, "motivo": "unit hours con is_range true (contradiccion)"}
            )
        label = definition.get("label")
        if not isinstance(label, str) or not label.strip() or len(label) > LABEL_MAX:
            report.manual.append(
                {"company_id": cid, "ruta": f"{ruta}.label", "valor": label, "motivo": f"label vacio o de mas de {LABEL_MAX} caracteres"}
            )
        if unit is not None and "is_range" in definition:
            report.informational.append({"tipo": "is_range_borrado", "company_id": cid, "ruta": ruta, "unit": unit})
        if unit is None:
            if "is_range" in definition:
                destino = "days" if is_range is True else "hours"
                report.informational.append(
                    {"tipo": "is_range_sin_unit", "company_id": cid, "ruta": ruta, "destino": destino}
                )
            else:
                report.informational.append({"tipo": "sin_unit_ni_is_range", "company_id": cid, "ruta": ruta, "destino": "hours"})


def run(
    db: Session,
    *,
    apply: bool,
    backup_dir: Path | None,
    drop_unknown: Iterable[str] | str = (),
) -> RepairReport:
    drop = parse_drop_unknown(drop_unknown)
    report = RepairReport(topic=TOPIC)
    counts = {"validas": 0, "mapeadas": 0, "retiradas": 0, "desconocidas": 0, "tipos": 0}
    originals: list[dict] = []
    updates: list[tuple[models.Company, dict]] = []
    found: set[str] = set()

    for company in db.query(models.Company).order_by(models.Company.id).all():
        cid = str(company.id)
        originals.append(
            {
                "company_id": cid,
                "name": company.name,
                "settings": copy.deepcopy(company.settings),
                "worklog_definitions": copy.deepcopy(company.worklog_definitions),
            }
        )
        unknown = _analyze_settings(cid, company.name, company.settings, report, counts)
        _analyze_definitions(cid, company.worklog_definitions, report, counts)

        to_remove: set[str] = set()
        for key, value in unknown:
            found.add(key)
            if key in drop:
                to_remove.add(key)
                report.changes.append({"company_id": cid, "ruta": f"settings.{key}", "antes": value, "despues": "(eliminada)"})
            else:
                report.manual.append(
                    {
                        "company_id": cid,
                        "ruta": f"settings.{key}",
                        "valor": value,
                        "motivo": "clave desconocida: la migracion la rechaza (usar --drop-unknown o anadirla al modelo)",
                    }
                )
        if to_remove:
            updates.append((company, {k: v for k, v in company.settings.items() if k not in to_remove}))

    for key in sorted(drop - found):
        report.informational.append({"tipo": "clave_no_presente", "clave": key})
    report.informational.append({"tipo": "resumen", **counts})

    if not apply:
        return report

    directory = ensure_backup_dir(backup_dir, required=True)
    try:
        payload = {"drop_unknown": sorted(drop), "empresas": originals}
        report.backup_files.append(write_backup(directory, BACKUP_TOPIC, payload))
        for company, new_settings in updates:
            company.settings = new_settings
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return report


class _ArgumentParser(argparse.ArgumentParser):
    def error(self, message: str) -> NoReturn:  # argparse usaria 2, que aqui significa pendientes
        self.print_usage(sys.stderr)
        print(f"[ERROR] {message}", file=sys.stderr)
        raise SystemExit(1)


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = _ArgumentParser(
        prog="python3 -m scripts.repair_settings_definitions",
        description="Reparacion de settings y tipos de turno (PR-11). Por defecto solo muestra los cambios.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="no escribe nada (defecto)")
    mode.add_argument("--apply", action="store_true", help="escribe el backup y elimina las claves de --drop-unknown")
    parser.add_argument(
        "--drop-unknown",
        action="append",
        default=None,
        metavar="CLAVE[,CLAVE]",
        help="elimina claves desconocidas de primer nivel de settings (sin --apply solo se previsualiza)",
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=None,
        help=f"directorio de backups fuera del repo (defecto: variable {ENV_BACKUP_DIR})",
    )
    args = parser.parse_args(argv)
    args.apply = bool(args.apply)
    if args.backup_dir is None:
        env_value = os.environ.get(ENV_BACKUP_DIR)
        if env_value:
            args.backup_dir = Path(env_value)
    return args


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    mode = "--apply" if args.apply else "--dry-run (no se escribe nada)"
    print(f"[INFO] Modo: {mode}")
    try:
        drop = parse_drop_unknown(args.drop_unknown or [])
        backup_dir = ensure_backup_dir(args.backup_dir, required=False) if args.apply else None
        db = database.SessionLocal()
        try:
            report = run(db, apply=args.apply, backup_dir=backup_dir, drop_unknown=drop)
        finally:
            db.close()
    except ValueError as exc:
        print(exc, file=sys.stderr)
        return 1
    except SystemExit as exc:
        message = exc.code if isinstance(exc.code, str) else "[ERROR] Salida anticipada."
        print(message, file=sys.stderr)
        return 1
    except Exception as exc:  # error de BD u otro: ya hubo rollback en run()
        detail = f" ({exc})" if isinstance(exc, OSError) else ""
        print(
            f"[ERROR] La reparacion ha fallado: {type(exc).__name__}{detail}. No se han aplicado cambios.",
            file=sys.stderr,
        )
        return 1
    print_report(report)
    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
