"""Script unico e idempotente para crear la empresa propia a usuarios sin ninguna (R-EMP-15).

Crea una empresa autonoma normal (`is_managed = false`, `is_active = true`) de un solo miembro
(`role = worker`, `is_active = true`) para cada usuario normal (`users.role == 'user'`) que no
tenga ninguna fila en `company_members`. Excluye administradores de plataforma (`users.role == 'admin'`,
R-ACC-26).

Por defecto corre en modo `--dry-run` (solo informa). Con `--apply` persiste los cambios en BD.

Uso (desde backend/): python3 -m scripts.create_personal_companies [--dry-run | --apply] [--backup-dir PATH]
"""

from __future__ import annotations

import sys
import uuid
from dataclasses import dataclass
from pathlib import Path

import audit
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

TOPIC = "create_personal_companies"
COMPANY_NAME_MAX = 120
DEFAULT_WORKLOG_DEFINITIONS = {
    "particular": {
        "unit": "hours",
        "label": "Particular",
        "options": [],
        "is_active": True,
    }
}
DEFAULT_COMPANY_SETTINGS = {"default_is_gross": False}
DEFAULT_MEMBER_SORT_ORDER = 1000


@dataclass(frozen=True)
class _TargetUser:
    user: models.User
    company_name: str


def build_personal_company_name(user: models.User) -> str:
    """Construye el nombre 'Empresa de <Nombre> <Apellido>' respetando el tope de 120 caracteres (R-ACC-75)."""
    parts = [part.strip() for part in (user.first_name, user.last_name) if isinstance(part, str) and part.strip()]
    display = " ".join(parts)
    if not display and isinstance(user.email, str) and user.email.strip():
        display = user.email.strip().split("@", 1)[0]
    name = f"Empresa de {display}".strip() if display else "Empresa propia"
    if len(name) > COMPANY_NAME_MAX:
        name = name[:COMPANY_NAME_MAX].rstrip()
    return name


def _find_users_without_company(db: Session) -> list[_TargetUser]:
    users = (
        db.query(models.User)
        .filter(
            models.User.role == models.UserRole.user,
            ~models.User.company_memberships.any(),
        )
        .order_by(models.User.id.asc())
        .all()
    )
    return [_TargetUser(user=user, company_name=build_personal_company_name(user)) for user in users]


def run(db: Session, *, apply: bool, backup_dir: Path | None = None) -> RepairReport:
    report = RepairReport(topic=TOPIC)
    targets = _find_users_without_company(db)
    for target in targets:
        report.changes.append(
            {
                "user_id": str(target.user.id),
                "email": target.user.email,
                "company_name": target.company_name,
            }
        )

    if not apply or not targets:
        return report

    created_records: list[dict] = []
    try:
        for target in targets:
            company_id = uuid.uuid4()
            company = models.Company(
                id=company_id,
                name=target.company_name,
                tax_config={},
                worklog_definitions={k: dict(v) for k, v in DEFAULT_WORKLOG_DEFINITIONS.items()},
                settings=dict(DEFAULT_COMPANY_SETTINGS),
                is_active=True,
                is_managed=False,
            )
            member = models.CompanyMember(
                user_id=target.user.id,
                company_id=company_id,
                role=models.CompanyRole.worker,
                is_active=True,
                sort_order=DEFAULT_MEMBER_SORT_ORDER,
                rates_config={},
                settings={},
            )
            db.add(company)
            db.add(member)
            audit.record_audit(
                db,
                action=audit.AuditAction.COMPANY_CREATED,
                actor_id=None,
                company_id=company_id,
                new_value={"name": company.name, "is_active": True, "is_managed": False},
                extra={"script": TOPIC, "user_id": str(target.user.id)},
            )
            audit.record_audit(
                db,
                action=audit.AuditAction.MEMBER_ADDED,
                actor_id=None,
                company_id=company_id,
                target_user_id=target.user.id,
                new_value={"is_active": True, "role": models.CompanyRole.worker.value},
                extra={"script": TOPIC},
            )
            created_records.append(
                {
                    "user_id": str(target.user.id),
                    "email": target.user.email,
                    "company_id": str(company_id),
                    "company_name": company.name,
                }
            )

        if backup_dir is not None:
            directory = ensure_backup_dir(backup_dir, required=True)
            report.backup_files.append(write_backup(directory, TOPIC, created_records))
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
    except Exception as exc:
        print(f"[ERROR] El script ha fallado: {type(exc).__name__}. No se han aplicado cambios.", file=sys.stderr)
        return 1
    print_report(report)
    return report.exit_code()


if __name__ == "__main__":
    raise SystemExit(main())
