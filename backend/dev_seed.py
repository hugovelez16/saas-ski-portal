"""
Modulo de inicializacion automatica de usuario administrador de plataforma y empresa Demo para desarrollo local.
"""
import os

import audit
import auth
import models
from contracts import validate_allowed_email_domain
from sqlalchemy import func
from sqlalchemy.orm import Session


def _dev_bypass_flag() -> bool:
    """Indica si DEV_LOGIN_BYPASS esta activado (true, 1 o yes)."""
    return os.getenv("DEV_LOGIN_BYPASS", "").lower() in ["true", "1", "yes"]


def is_dev_mode() -> bool:
    """Modo desarrollo: requiere ENVIRONMENT=development Y DEV_LOGIN_BYPASS activado."""
    env = os.getenv("ENVIRONMENT", "").lower()
    return env == "development" and _dev_bypass_flag()


def assert_dev_bypass_safe() -> None:
    """Aborta el arranque si el bypass de desarrollo esta activo fuera de ENVIRONMENT=development."""
    env = os.getenv("ENVIRONMENT", "").lower()
    if _dev_bypass_flag() and env != "development":
        raise RuntimeError("DEV_LOGIN_BYPASS esta activo fuera de ENVIRONMENT=development. Aborting startup.")


def _ensure_demo_member(
    db: Session,
    *,
    email: str,
    password: str,
    first_name: str,
    last_name: str,
    company: models.Company,
    member_role: models.CompanyRole,
    sort_order: int,
) -> models.User:
    """Garantiza la existencia de un usuario demo y su membresia activa en la empresa Demo."""
    clean_email = validate_allowed_email_domain(email.strip().lower())
    user = db.query(models.User).filter(func.lower(models.User.email) == clean_email).first()
    if not user:
        user = models.User(
            email=clean_email,
            hashed_password=auth.get_password_hash(password),
            first_name=first_name,
            last_name=last_name,
            role=models.UserRole.user,
            is_active=True,
            is_2fa_enabled=False,
            must_change_password=False,
        )
        db.add(user)
        db.commit()
        db.refresh(user)

    membership = (
        db.query(models.CompanyMember)
        .filter(models.CompanyMember.user_id == user.id, models.CompanyMember.company_id == company.id)
        .first()
    )
    if not membership:
        membership = models.CompanyMember(
            user_id=user.id,
            company_id=company.id,
            role=member_role,
            is_active=True,
            sort_order=sort_order,
            rates_config={},
            settings={},
        )
        db.add(membership)
        db.commit()

    return user


def ensure_dev_admin_user(db: Session) -> models.User:
    """
    Garantiza que exista un PA (sin membresias, R-ACC-26) y la empresa normal Demo con
    un manager demo y un worker demo (R-ACC-69) para el entorno de desarrollo.
    """
    admin_email = os.getenv("DEV_ADMIN_EMAIL", "admin@vesotel.com").strip().lower()
    admin_password = os.getenv("DEV_ADMIN_PASSWORD", "admin")
    admin_company_name = os.getenv("DEV_ADMIN_COMPANY", "Demo").strip()
    admin_first_name = os.getenv("DEV_ADMIN_FIRST_NAME", "Admin").strip()
    admin_last_name = os.getenv("DEV_ADMIN_LAST_NAME", "Vesotel").strip()
    demo_manager_email = os.getenv("DEV_DEMO_MANAGER_EMAIL", "manager.demo@vesotel.com")
    demo_worker_email = os.getenv("DEV_DEMO_WORKER_EMAIL", "worker.demo@vesotel.com")
    demo_password = os.getenv("DEV_DEMO_PASSWORD", admin_password)

    # 1. Buscar o crear empresa normal por defecto ("Demo")
    company = db.query(models.Company).filter(models.Company.name == admin_company_name).first()
    if not company:
        company = db.query(models.Company).first()
        if not company:
            company = models.Company(
                name=admin_company_name,
                tax_config={"social_security": 0.0648},
                worklog_definitions={},
                settings={},
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"[DevSeed] Empresa '{admin_company_name}' creada exitosamente.")

    # 2. Buscar o crear usuario administrador de plataforma (sin membresia en ninguna empresa)
    user = db.query(models.User).filter(func.lower(models.User.email) == admin_email).first()
    if not user:
        hashed_password = auth.get_password_hash(admin_password)
        user = models.User(
            email=admin_email,
            hashed_password=hashed_password,
            first_name=admin_first_name,
            last_name=admin_last_name,
            role=models.UserRole.admin,
            is_active=True,
            is_2fa_enabled=False,
            must_change_password=False,
        )
        db.add(user)
        db.flush()
        audit.record_audit(
            db,
            action=audit.AuditAction.USER_PLATFORM_ADMIN_GRANTED,
            actor_id=None,
            target_user_id=user.id,
            new_value={"role": models.UserRole.admin.value},
            extra={"source": "dev_seed", "email": user.email},
        )
        db.commit()
        db.refresh(user)
        print(f"[DevSeed] Usuario administrador '{admin_email}' creado exitosamente.")
    else:
        updated = False
        if user.role != models.UserRole.admin:
            old_role = user.role.value
            user.role = models.UserRole.admin
            audit.record_audit(
                db,
                action=audit.AuditAction.USER_PLATFORM_ADMIN_GRANTED,
                actor_id=None,
                target_user_id=user.id,
                old_value={"role": old_role},
                new_value={"role": models.UserRole.admin.value},
                extra={"source": "dev_seed", "email": user.email},
            )
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if user.is_2fa_enabled:
            user.is_2fa_enabled = False
            updated = True
        if updated:
            db.commit()
            db.refresh(user)
            print(f"[DevSeed] Usuario administrador '{admin_email}' actualizado.")

    # 3. Asegurar manager y worker demo en la empresa (sin correo de bienvenida)
    if company:
        _ensure_demo_member(
            db,
            email=demo_manager_email,
            password=demo_password,
            first_name="Manager",
            last_name="Demo",
            company=company,
            member_role=models.CompanyRole.manager,
            sort_order=1,
        )
        _ensure_demo_member(
            db,
            email=demo_worker_email,
            password=demo_password,
            first_name="Worker",
            last_name="Demo",
            company=company,
            member_role=models.CompanyRole.worker,
            sort_order=2,
        )

    return user
