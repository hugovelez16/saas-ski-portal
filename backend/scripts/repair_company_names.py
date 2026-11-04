"""Reparacion de nombres de empresa previa a la migracion de longitud (PR-06).

Reglas (docs/empresa/plan-implementacion-empresa.md, seccion 9.2):
- Nombre vacio o solo espacios -> "Empresa " + str(id)[:8].
- Espacios sobrantes al inicio o al final -> strip().
- Mas de 120 caracteres tras strip -> recorte a 120. El nombre original completo
  se guarda en el backup antes de escribir.

Uso (desde backend/): python3 -m scripts.repair_company_names [--dry-run | --apply] [--backup-dir PATH]
"""

from __future__ import annotations

import sys
from dataclasses import dataclass
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

TOPIC = "company_names"
NAME_MAX_LENGTH = 120
FALLBACK_PREFIX = "Empresa "


@dataclass
class _Plan:
    company: models.Company
    original: str
    new_name: str
    reason: str
    truncated: bool


def _target_name(company_id, original: str) -> tuple[str, list[str], bool]:
    stripped = original.strip()
    if not stripped:
        return f"{FALLBACK_PREFIX}{str(company_id)[:8]}", ["nombre vacio o solo espacios"], False

    reasons: list[str] = []
    if stripped != original:
        reasons.append("espacios sobrantes")
    truncated = len(stripped) > NAME_MAX_LENGTH
    name = stripped
    if truncated:
        # El rstrip evita terminar en espacio tras el recorte; sin el, una segunda ejecucion
        # volveria a cambiar el nombre (no seria idempotente).
        name = stripped[:NAME_MAX_LENGTH].rstrip()
        reasons.append(f"recorte a {NAME_MAX_LENGTH} caracteres")
    return name, reasons, truncated


def _build_plans(db: Session) -> list[_Plan]:
    plans: list[_Plan] = []
    for company in db.query(models.Company).order_by(models.Company.id).all():
        original = company.name or ""
        new_name, reasons, truncated = _target_name(company.id, original)
        if new_name == original:
            continue
        plans.append(
            _Plan(
                company=company,
                original=original,
                new_name=new_name,
                reason=", ".join(reasons),
                truncated=truncated,
            )
        )
    return plans


def run(db: Session, *, apply: bool, backup_dir: Path | None) -> RepairReport:
    report = RepairReport(topic=TOPIC)
    plans = _build_plans(db)
    for plan in plans:
        report.changes.append(
            {
                "company_id": str(plan.company.id),
                "motivo": plan.reason,
                "antes": plan.original,
                "despues": plan.new_name,
            }
        )

    if not apply or not plans:
        return report

    truncations = [plan for plan in plans if plan.truncated]
    if truncations and backup_dir is None:
        raise SystemExit(
            f"[ERROR] Hay {len(truncations)} nombre(s) a recortar. "
            "Indica --backup-dir (o REPAIR_BACKUP_DIR) para guardar los originales. No se ha escrito nada."
        )

    try:
        if truncations:
            directory = ensure_backup_dir(backup_dir, required=True)
            payload = [{"company_id": str(plan.company.id), "original_name": plan.original} for plan in truncations]
            report.backup_files.append(write_backup(directory, TOPIC, payload))
        for plan in plans:
            plan.company.name = plan.new_name
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
