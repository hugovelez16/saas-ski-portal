"""
Modulo de Sembrado Inicial de Datos (Seed Bootstrap).

Inicializa la base de datos con un usuario administrador de plataforma (sin membresias)
y una empresa normal "Demo" con sus usuarios demo (manager y worker) si se definen las
variables de entorno correspondientes y no existe aun un PA.
"""

import os
import secrets
import uuid
from datetime import UTC, datetime

import auth
import models
from contracts import validate_allowed_email_domain
from database import SessionLocal
from sqlalchemy import func
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session


def _ensure_demo_user(
    db: Session,
    *,
    email: str,
    first_name: str,
    last_name: str,
    password: str,
    company: models.Company,
    member_role: models.CompanyRole,
    sort_order: int,
) -> models.User:
    """Crea o recupera un usuario demo normal y garantiza su membresia en la empresa Demo."""
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

    member = (
        db.query(models.CompanyMember)
        .filter(models.CompanyMember.user_id == user.id, models.CompanyMember.company_id == company.id)
        .first()
    )
    if not member:
        member = models.CompanyMember(
            user_id=user.id,
            company_id=company.id,
            role=member_role,
            is_active=True,
            sort_order=sort_order,
        )
        db.add(member)
        db.commit()
    return user


def seed_initial_data(db: Session = None) -> bool:
    """
    Siembra los datos iniciales (PA sin membresia, empresa Demo con manager y worker demo, y modulos).
    Es idempotente: si ya existe un administrador de plataforma, no realiza modificaciones.
    """
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL")
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD")
    first_name = os.getenv("INITIAL_ADMIN_FIRST_NAME", "Admin")
    last_name = os.getenv("INITIAL_ADMIN_LAST_NAME", "Vesotel")
    company_name = os.getenv("INITIAL_COMPANY_NAME", "Demo")
    demo_manager_email = os.getenv("DEMO_MANAGER_EMAIL", "manager.demo@vesotel.com")
    demo_worker_email = os.getenv("DEMO_WORKER_EMAIL", "worker.demo@vesotel.com")
    demo_password = os.getenv("DEMO_USER_PASSWORD") or secrets.token_urlsafe(32)

    if not admin_email or not admin_password:
        print("[Seed] INITIAL_ADMIN_EMAIL o INITIAL_ADMIN_PASSWORD no configurados. Omitiendo sembrado inicial.")
        return False

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Solo se siembra si no existe ningun administrador de plataforma
        if db.query(models.User).filter(models.User.role == models.UserRole.admin).first():
            print("[Seed] Ya existe un administrador de plataforma. Omitiendo sembrado.")
            return False

        print(f"[Seed] Creando empresa inicial '{company_name}' y usuario administrador '{admin_email}'...")

        # 1. Crear o recuperar empresa normal inicial ("Demo" por defecto)
        company = db.query(models.Company).filter(models.Company.name == company_name).first()
        if not company:
            company = models.Company(
                name=company_name,
                tax_config={"social_security": 0.0648},
                worklog_definitions={
                    "particular": {"unit": "hours", "label": "Clase Particular", "fields": []},
                    "colectiva": {"unit": "hours", "label": "Clase Colectiva", "fields": []},
                },
                settings={"modules": {"worker_daily_report": True}},
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        # 2. Crear usuario administrador de plataforma (sin membresia en ninguna empresa, R-ACC-26)
        hashed_pw = auth.get_password_hash(admin_password)
        admin_user = models.User(
            email=admin_email.strip().lower(),
            hashed_password=hashed_pw,
            first_name=first_name,
            last_name=last_name,
            role=models.UserRole.admin,
            is_active=True,
            is_2fa_enabled=False,
            must_change_password=False,
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # 3. Crear usuarios demo (manager y worker) en la empresa Demo sin correo de bienvenida (R-ACC-69)
        _ensure_demo_user(
            db,
            email=demo_manager_email,
            first_name="Manager",
            last_name="Demo",
            password=demo_password,
            company=company,
            member_role=models.CompanyRole.manager,
            sort_order=1,
        )
        _ensure_demo_user(
            db,
            email=demo_worker_email,
            first_name="Worker",
            last_name="Demo",
            password=demo_password,
            company=company,
            member_role=models.CompanyRole.worker,
            sort_order=2,
        )

        # 4. Activar suscripciones a modulos existentes para la empresa
        try:
            modules = db.query(models.AppModule).filter(models.AppModule.is_active == True).all()
            now = datetime.now(UTC)
            for mod in modules:
                existing_sub = (
                    db.query(models.ModuleSubscription)
                    .filter(
                        models.ModuleSubscription.module_id == mod.id,
                        models.ModuleSubscription.company_id == company.id,
                    )
                    .first()
                )
                if not existing_sub:
                    sub = models.ModuleSubscription(
                        id=uuid.uuid4(),
                        module_id=mod.id,
                        company_id=company.id,
                        scope="company",
                        status="active",
                        created_at=now,
                        updated_at=now,
                    )
                    db.add(sub)
            db.commit()
        except Exception as mod_err:
            print(f"[Seed] Advertencia al suscribir modulos: {mod_err}")
            db.rollback()

        print(f"[Seed] Exito: Usuario administrador creado ({admin_email}) sin membresia y empresa '{company_name}'.")
        return True

    except (OperationalError, ProgrammingError) as e:
        print(f"[Seed] Tablas no disponibles aun para sembrado: {e}")
        db.rollback()
        return False
    except Exception as e:
        print(f"[Seed] Error inesperado durante el sembrado inicial: {e}")
        db.rollback()
        return False
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_initial_data()
