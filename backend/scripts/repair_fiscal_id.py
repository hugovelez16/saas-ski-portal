"""Exportacion de companies.fiscal_id previa a la migracion que borra la columna (PR-23).

No modifica la BD. Reglas (docs/empresa/plan-implementacion-empresa.md, secciones 5 y 9.2):
- Valor real: no nulo, no vacio tras strip() y distinto del valor de semilla B00000000.
- --dry-run (defecto): cuenta las empresas con valor real y las que solo tienen el de semilla.
- --apply (exige --backup-dir): escribe fiscal_id_export_<ts>.json fuera del repo con todas las
  empresas con valor real y las de semilla marcadas con "seed_value": true. El fichero contiene
  datos fiscales de empresas, no secretos de acceso. Se escribe siempre, tambien vacio: es la
  constancia de que la exportacion se ejecuto antes de definir FISCAL_ID_EXPORTED=1.

models.Company ya no tiene la columna, por lo que el script consulta la tabla con SQLAlchemy Core.

Uso (desde backend/): python3 -m scripts.repair_fiscal_id [--dry-run | --apply] [--backup-dir PATH]
"""

from __future__ import annotations

import sys
from pathlib import Path

import database
import sqlalchemy as sa
from sqlalchemy.orm import Session

from scripts.repair_common import (
    RepairReport,
    ensure_backup_dir,
    parse_args,
    print_report,
    write_backup,
)

TOPIC = "fiscal_id_export"
SEED_VALUE = "B00000000"  # seed.py y dev_seed.py lo ponian por defecto

COMPANIES = sa.table(
    "companies",
    sa.column("id", sa.Uuid(as_uuid=True)),
    sa.column("name", sa.String()),
    sa.column("fiscal_id", sa.String()),
)


def _has_fiscal_id_column(db: Session) -> bool:
    columns = sa.inspect(db.connection()).get_columns("companies")
    return any(column["name"] == "fiscal_id" for column in columns)


def _classify(fiscal_id: str | None) -> str | None:
    """'real', 'seed' o None (nulo o vacio tras strip: se ignora)."""
    # strip(" ") equivale al btrim de la migracion: ambas deben coincidir en que es un valor real.
    value = (fiscal_id or "").strip(" ")
    if not value:
        return None
    return "seed" if value == SEED_VALUE else "real"


def run(db: Session, *, apply: bool, backup_dir: Path | None) -> RepairReport:
    report = RepairReport(topic=TOPIC)
    if not _has_fiscal_id_column(db):
        report.informational.append({"aviso": "companies.fiscal_id no existe: no hay nada que exportar"})
        return report

    rows = db.execute(sa.select(COMPANIES.c.id, COMPANIES.c.name, COMPANIES.c.fiscal_id).order_by(COMPANIES.c.id)).all()
    exported: list[dict] = []
    real = seed = 0
    for company_id, name, fiscal_id in rows:
        kind = _classify(fiscal_id)
        if kind is None:
            continue
        entry = {"company_id": str(company_id), "company_name": name, "fiscal_id": fiscal_id}
        if kind == "seed":
            seed += 1
            entry["seed_value"] = True
        else:
            real += 1
            report.changes.append({"company_id": entry["company_id"], "company_name": name})
        exported.append(entry)

    report.informational.append({"real": real, "semilla": seed})
    if seed:
        report.informational.append({"aviso": f"{seed} empresa(s) solo con el valor de semilla {SEED_VALUE}: descartable"})

    if not apply:
        return report

    directory = ensure_backup_dir(backup_dir, required=True)
    report.backup_files.append(write_backup(directory, TOPIC, exported))
    report.informational.append({"registros_exportados": len(exported)})
    return report


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    mode = "--apply" if args.apply else "--dry-run (no se escribe nada)"
    print(f"[INFO] Modo: {mode}")
    try:
        backup_dir = ensure_backup_dir(args.backup_dir, required=True) if args.apply else None
        db = database.SessionLocal()
        try:
            report = run(db, apply=args.apply, backup_dir=backup_dir)
        finally:
            db.close()
    except SystemExit as exc:
        message = exc.code if isinstance(exc.code, str) else "[ERROR] Salida anticipada."
        print(message, file=sys.stderr)
        return 1
    except Exception as exc:
        print(f"[ERROR] La exportacion ha fallado: {type(exc).__name__}. No se ha modificado la BD.", file=sys.stderr)
        return 1
    print_report(report)
    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
