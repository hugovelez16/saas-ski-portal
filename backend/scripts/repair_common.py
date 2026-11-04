"""Utilidades comunes a los scripts de reparacion de datos (docs/empresa, seccion 9).

Los scripts se ejecutan con `python3 -m scripts.<nombre>` desde backend/ (en el contenedor, /app).
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
ENV_BACKUP_DIR = "REPAIR_BACKUP_DIR"


@dataclass
class RepairReport:
    topic: str
    changes: list[dict] = field(default_factory=list)  # lo que --apply escribe (o escribiria)
    manual: list[dict] = field(default_factory=list)  # decisiones manuales: no se tocan
    informational: list[dict] = field(default_factory=list)  # avisos que no bloquean
    backup_files: list[Path] = field(default_factory=list)  # ficheros escritos

    def exit_code(self) -> int:
        return 0 if not self.manual else 2


def parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python3 -m scripts.<nombre>",
        description="Reparacion de datos previa a una migracion. Por defecto solo muestra los cambios.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", help="no escribe nada (defecto)")
    mode.add_argument("--apply", action="store_true", help="escribe los cambios en la BD")
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


def _repo_scope() -> Path:
    """Raiz del repositorio: el directorio que contiene backend/.

    En el contenedor backend/ es la raiz del sistema de ficheros (/app), por lo que la
    raiz seria "/" y no permitiria ningun backup. En ese caso se usa backend/ como ambito.
    """
    root = BACKEND_DIR.parent.resolve()
    if root == Path(root.anchor):
        return BACKEND_DIR.resolve()
    return root


def ensure_backup_dir(path: Path | None, *, required: bool) -> Path | None:
    if path is None:
        if required:
            raise SystemExit(
                f"[ERROR] Hace falta --backup-dir (o la variable {ENV_BACKUP_DIR}) para escribir el backup."
            )
        return None
    target = Path(path).expanduser().resolve()
    scope = _repo_scope()
    if target == scope or scope in target.parents:
        raise SystemExit(f"[ERROR] El directorio de backup no puede estar dentro del repositorio: {target}")
    target.mkdir(mode=0o700, parents=True, exist_ok=True)
    return target


def write_backup(directory: Path, topic: str, payload: object) -> Path:
    """Escribe un JSON nuevo con permisos 0600. El payload no debe contener secretos."""
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    path = directory / f"{topic}_{stamp}.json"
    text = json.dumps(payload, ensure_ascii=False, indent=2, default=str)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except BaseException:
        path.unlink(missing_ok=True)  # no dejar un backup parcial que parezca valido
        raise
    return path


def print_report(report: RepairReport) -> None:
    print(f"[INFO] Reparacion: {report.topic}")
    print(f"[INFO] Cambios: {len(report.changes)}")
    for change in report.changes:
        print("  - " + ", ".join(f"{key}={value}" for key, value in change.items()))
    print(f"[INFO] Pendientes de decision manual: {len(report.manual)}")
    for item in report.manual:
        print("  - " + ", ".join(f"{key}={value}" for key, value in item.items()))
    print(f"[INFO] Avisos: {len(report.informational)}")
    for item in report.informational:
        print("  - " + ", ".join(f"{key}={value}" for key, value in item.items()))
    for backup in report.backup_files:
        print(f"[INFO] Backup escrito: {backup}")
    print(f"[INFO] Codigo de salida: {report.exit_code()}")
