"""Comando de servidor para conceder el rol de administrador de plataforma (R-ACC-65, R-AUD-25).

Uso (desde backend/):
    python3 -m scripts.grant_platform_admin --email usuario@dominio.com [--reason "motivo"]
"""

from __future__ import annotations

import argparse
import sys

import audit
import crud
import database
import models
from sqlalchemy.orm import Session


def grant_platform_admin(db: Session, *, email: str, reason: str | None = None) -> tuple[models.User, bool]:
    """Concede el rol de plataforma `admin` a un usuario existente y registra la auditoria.

    Devuelve `(user, granted)` donde `granted` es False si el usuario ya era PA (idempotente).
    Rechaza usuarios inexistentes o con membresias en empresas (R-ACC-26).
    """
    clean_email = email.strip().lower()
    if not clean_email:
        raise ValueError("El email es obligatorio")

    user = crud.get_user_by_email(db, clean_email)
    if user is None:
        raise ValueError(f"No existe ningun usuario con el email '{clean_email}'")

    if user.role == models.UserRole.admin:
        return user, False

    has_membership = db.query(models.CompanyMember.user_id).filter(models.CompanyMember.user_id == user.id).first()
    if has_membership is not None:
        raise ValueError("Un administrador de plataforma no puede tener membresias en empresas (R-ACC-26)")

    old_role = user.role.value
    user.role = models.UserRole.admin
    audit.record_audit(
        db,
        action=audit.AuditAction.USER_PLATFORM_ADMIN_GRANTED,
        actor_id=None,
        target_user_id=user.id,
        old_value={"role": old_role},
        new_value={"role": models.UserRole.admin.value},
        reason=reason,
        extra={"source": "cli", "email": user.email},
    )
    db.commit()
    db.refresh(user)
    return user, True


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python3 -m scripts.grant_platform_admin",
        description="Concede el rol de administrador de plataforma a un usuario existente y lo audita.",
    )
    parser.add_argument("--email", required=True, help="Email del usuario al que conceder el rol de PA")
    parser.add_argument("--reason", default=None, help="Motivo de la concesion (opcional, max 500 caracteres)")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    db = database.SessionLocal()
    try:
        user, granted = grant_platform_admin(db, email=args.email, reason=args.reason)
    except ValueError as exc:
        db.rollback()
        print(f"[ERROR] {exc}", file=sys.stderr)
        return 1
    except Exception as exc:
        db.rollback()
        print(f"[ERROR] No se pudo conceder el rol de PA: {type(exc).__name__}", file=sys.stderr)
        return 1
    finally:
        db.close()

    if granted:
        print(f"[OK] Rol de administrador de plataforma concedido a '{user.email}'.")
    else:
        print(f"[INFO] El usuario '{user.email}' ya era administrador de plataforma.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
