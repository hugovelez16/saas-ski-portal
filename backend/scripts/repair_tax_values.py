"""Reparacion de valores de impuestos previa a la migracion de claves libres (PR-10).

Recorre `Company.tax_config` y `CompanyMember.rates_config[tipo].tax_overrides`.

Reglas (docs/empresa/plan-implementacion-empresa.md, seccion 9):
- Numero (int/float, no bool) finito en [0, 1] -> correcto.
- Cadena que parsea a un numero finito en [0, 1] -> CAMBIO: --apply la guarda como float.
- Cualquier otro valor -> MANUAL: no se toca. En `tax_overrides` null es valido.
- Nombres de `tax_config`: vacios, de mas de 50 caracteres tras strip o duplicados tras strip,
  y mas de 20 entradas -> MANUAL.
- Claves `ss` / `irpf` de overrides: aviso de renombrado (lo hace la migracion); colision -> MANUAL.
- Clave `extra` de overrides: distinto de 0 o no numerico -> MANUAL; 0 que la empresa no define se
  eliminara en la migracion (aviso).
- Claves de overrides desconocidas para la empresa: aviso (no bloquea).

Las reglas son autocontenidas: no se importa contracts.py.

Uso (desde backend/): python3 -m scripts.repair_tax_values [--dry-run | --apply] [--backup-dir PATH]
"""

from __future__ import annotations

import copy
import math
import sys
from pathlib import Path

import database
import models
from sqlalchemy.orm import Session

from scripts.repair_common import (
    RepairReport,
    ensure_backup_dir,
    parse_args,
    print_report,
    write_backup,
)

TOPIC = "tax_values"
TAX_NAME_MAX = 50
TAX_MAX_ENTRIES = 20
RENAMED_KEYS = {"ss": "social_security", "irpf": "irpf_base"}
EXTRA_KEY = "extra"
EXTRA_REASON = "extra distinto de 0 o no numerico"

_OK = "ok"
_CHANGE = "change"
_MANUAL = "manual"


def _classify(value, *, allow_null: bool) -> tuple[str, float | None, str]:
    """Devuelve (estado, valor_nuevo, motivo) para un valor de impuesto."""
    if value is None:
        if allow_null:
            return _OK, None, ""
        return _MANUAL, None, "valor null no permitido"
    if isinstance(value, bool):
        return _MANUAL, None, "valor booleano"
    if isinstance(value, (int, float)):
        try:
            number = float(value)
        except OverflowError:
            return _MANUAL, None, "numero fuera de rango"
        if not math.isfinite(number):
            return _MANUAL, None, "numero no finito"
        if not 0 <= number <= 1:
            return _MANUAL, None, "numero fuera de [0, 1]"
        return _OK, None, ""
    if isinstance(value, str):
        try:
            number = float(value)
        except (ValueError, OverflowError):
            return _MANUAL, None, "cadena no numerica"
        if not math.isfinite(number):
            return _MANUAL, None, "cadena no finita"
        if not 0 <= number <= 1:
            return _MANUAL, None, "cadena fuera de [0, 1]"
        return _CHANGE, number, ""
    return _MANUAL, None, f"tipo no admitido ({type(value).__name__})"


def _repair_tax_config(company: models.Company, report: RepairReport, updates: list) -> dict:
    """Revisa tax_config. Devuelve el dict de claves de la empresa (vacio si no es dict)."""
    config = company.tax_config
    cid = str(company.id)
    if config is None:
        return {}
    if not isinstance(config, dict):
        report.manual.append(
            {"company_id": cid, "ruta": "tax_config", "valor": config, "motivo": "tax_config no es un objeto"}
        )
        return {}

    if len(config) > TAX_MAX_ENTRIES:
        report.manual.append(
            {
                "company_id": cid,
                "ruta": "tax_config",
                "valor": f"{len(config)} entradas",
                "motivo": f"mas de {TAX_MAX_ENTRIES} entradas",
            }
        )

    new_config = dict(config)
    changed = False
    seen: set[str] = set()
    for key, value in config.items():
        ruta = f"tax_config.{key}"
        name = str(key).strip()
        if not name:
            report.manual.append(
                {"company_id": cid, "ruta": ruta, "valor": value, "motivo": "nombre vacio o solo espacios"}
            )
        elif len(name) > TAX_NAME_MAX:
            report.manual.append(
                {
                    "company_id": cid,
                    "ruta": ruta,
                    "valor": value,
                    "motivo": f"nombre de mas de {TAX_NAME_MAX} caracteres",
                }
            )
        if name in seen:
            report.manual.append(
                {"company_id": cid, "ruta": ruta, "valor": value, "motivo": "nombre duplicado tras strip"}
            )
        seen.add(name)

        state, new_value, reason = _classify(value, allow_null=False)
        if state == _MANUAL:
            report.manual.append({"company_id": cid, "ruta": ruta, "valor": value, "motivo": reason})
        elif state == _CHANGE:
            report.changes.append({"company_id": cid, "ruta": ruta, "antes": value, "despues": new_value})
            new_config[key] = new_value
            changed = True

    if changed:
        updates.append((company, "tax_config", new_config))
    return config


def _repair_member(
    member: models.CompanyMember,
    company_config: dict,
    report: RepairReport,
    updates: list,
    extra_stats: dict,
) -> None:
    rates = member.rates_config
    if not isinstance(rates, dict):
        return
    cid = str(member.company_id)
    uid = str(member.user_id)
    company_names = {str(k).strip() for k in company_config} | {str(k) for k in company_config}
    company_defines_extra = EXTRA_KEY in company_config

    new_rates = None  # copia profunda perezosa, solo si hay cambios

    def ident(ruta: str) -> dict:
        return {"company_id": cid, "user_id": uid, "ruta": ruta}

    for tipo, entry in rates.items():
        if not isinstance(entry, dict):
            continue
        overrides = entry.get("tax_overrides")
        if not isinstance(overrides, dict):
            continue
        for key, value in overrides.items():
            ruta = f"rates_config.{tipo}.tax_overrides.{key}"
            new_value = None
            is_change = False

            if key == EXTRA_KEY:
                extra_stats["total"] += 1
                if value is None:
                    continue
                if isinstance(value, bool):
                    state, parsed, reason = _MANUAL, None, EXTRA_REASON
                else:
                    state, parsed, reason = _classify(value, allow_null=False)
                is_zero = False
                if state == _OK:
                    is_zero = float(value) == 0
                elif state == _CHANGE:
                    is_zero = parsed == 0
                    if is_zero:
                        is_change, new_value = True, 0.0
                if state == _MANUAL or not is_zero:
                    report.manual.append({**ident(ruta), "valor": value, "motivo": EXTRA_REASON})
                    continue
                extra_stats["a_cero"] += 1
                if is_change:
                    report.changes.append({**ident(ruta), "antes": value, "despues": new_value})
                if not company_defines_extra:
                    extra_stats["eliminables"] += 1
                    report.informational.append({"tipo": "extra_se_eliminara", **ident(ruta)})
            else:
                state, parsed, reason = _classify(value, allow_null=True)
                if state == _MANUAL:
                    report.manual.append({**ident(ruta), "valor": value, "motivo": reason})
                elif state == _CHANGE:
                    is_change, new_value = True, parsed
                    report.changes.append({**ident(ruta), "antes": value, "despues": new_value})

                if key in RENAMED_KEYS:
                    target = RENAMED_KEYS[key]
                    if target in overrides:
                        report.manual.append(
                            {**ident(ruta), "valor": value, "motivo": f"colision con la clave {target}"}
                        )
                    else:
                        report.informational.append({"tipo": "renombrara", **ident(ruta), "nueva": target})
                elif key not in company_names:
                    report.informational.append({"tipo": "clave_desconocida", **ident(ruta)})

            if is_change:
                if new_rates is None:
                    new_rates = copy.deepcopy(rates)
                new_rates[tipo]["tax_overrides"][key] = new_value

    if new_rates is not None:
        updates.append((member, "rates_config", new_rates))


def run(db: Session, *, apply: bool, backup_dir: Path | None) -> RepairReport:
    report = RepairReport(topic=TOPIC)
    updates: list = []
    extra_stats = {"total": 0, "a_cero": 0, "eliminables": 0}

    configs: dict = {}
    for company in db.query(models.Company).order_by(models.Company.id).all():
        configs[company.id] = _repair_tax_config(company, report, updates)

    members = db.query(models.CompanyMember).order_by(models.CompanyMember.company_id, models.CompanyMember.user_id)
    for member in members.all():
        _repair_member(member, configs.get(member.company_id) or {}, report, updates, extra_stats)

    if extra_stats["total"]:
        report.informational.append({"tipo": "resumen_extra", **extra_stats})

    if not apply or (not report.changes and not report.manual):
        return report

    directory = ensure_backup_dir(backup_dir, required=True)
    try:
        if report.changes:
            report.backup_files.append(write_backup(directory, "tax_values_before", report.changes))
        if report.manual:
            report.backup_files.append(write_backup(directory, "tax_values_manual", report.manual))
        for obj, attr, new_value in updates:
            setattr(obj, attr, new_value)
        db.commit()
    except BaseException:
        db.rollback()
        raise
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "--apply" if args.apply else "--dry-run (no se escribe nada)"
    print(f"[INFO] Modo: {mode}")
    try:
        backup_dir = ensure_backup_dir(args.backup_dir, required=False) if args.apply else None
        db = database.SessionLocal()
        try:
            report = run(db, apply=args.apply, backup_dir=backup_dir)
        finally:
            db.close()
    except SystemExit as exc:
        message = exc.code if isinstance(exc.code, str) else "[ERROR] Salida anticipada."
        print(message, file=sys.stderr)
        return 1
    except Exception as exc:  # error de BD u otro: ya hubo rollback en run()
        print(f"[ERROR] La reparacion ha fallado: {type(exc).__name__}. No se han aplicado cambios.", file=sys.stderr)
        return 1
    print_report(report)
    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
