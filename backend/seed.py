"""
Modulo de Sembrado Inicial de Datos (Seed Bootstrap).

Inicializa la base de datos con un usuario administrador y empresa por defecto
si se definen las variables de entorno correspondientes y la BD se encuentra vacia.
"""
import os
import uuid
from datetime import datetime

import auth
import models
from database import SessionLocal
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session


def seed_initial_data(db: Session = None) -> bool:
    """
    Siembra los datos iniciales (empresa, usuario administrador y suscripciones a modulos).
    Es idempotente: si el usuario ya existe, no realiza modificaciones.
    """
    admin_email = os.getenv("INITIAL_ADMIN_EMAIL")
    admin_password = os.getenv("INITIAL_ADMIN_PASSWORD", "123456")
    first_name = os.getenv("INITIAL_ADMIN_FIRST_NAME", "Admin")
    last_name = os.getenv("INITIAL_ADMIN_LAST_NAME", "Vesotel")
    company_name = os.getenv("INITIAL_COMPANY_NAME", "Vesotel Ski School")

    if not admin_email:
        print("[Seed] INITIAL_ADMIN_EMAIL no configurado. Omitiendo sembrado inicial.")
        return False

    should_close = False
    if db is None:
        db = SessionLocal()
        should_close = True

    try:
        # Verificar si la tabla de usuarios existe y si el usuario ya esta registrado
        existing_user = db.query(models.User).filter(models.User.email == admin_email).first()
        if existing_user:
            print(f"[Seed] El usuario {admin_email} ya existe en la base de datos. Omitiendo sembrado.")
            return False

        print(f"[Seed] Creando empresa inicial '{company_name}' y usuario administrador '{admin_email}'...")

        # 1. Crear o recuperar empresa inicial
        company = db.query(models.Company).filter(models.Company.name == company_name).first()
        if not company:
            company = models.Company(
                name=company_name,
                fiscal_id="B00000000",
                tax_config={"social_security": 0.0648},
                worklog_definitions={
                    "particular": {
                        "unit": "hours",
                        "label": "Clase Particular",
                        "fields": []
                    },
                    "colectiva": {
                        "unit": "hours",
                        "label": "Clase Colectiva",
                        "fields": []
                    }
                },
                settings={"features": {"worker_daily_report": True}}
            )
            db.add(company)
            db.commit()
            db.refresh(company)

        # 2. Crear usuario administrador
        hashed_pw = auth.get_password_hash(admin_password)
        admin_user = models.User(
            email=admin_email,
            hashed_password=hashed_pw,
            first_name=first_name,
            last_name=last_name,
            role=models.UserRole.admin,
            is_active=True,
            is_2fa_enabled=False,
            must_change_password=False,
            default_company_id=company.id
        )
        db.add(admin_user)
        db.commit()
        db.refresh(admin_user)

        # 3. Vincular usuario a la empresa como manager/admin
        member = db.query(models.CompanyMember).filter(
            models.CompanyMember.user_id == admin_user.id,
            models.CompanyMember.company_id == company.id
        ).first()

        if not member:
            member = models.CompanyMember(
                user_id=admin_user.id,
                company_id=company.id,
                role=models.CompanyRole.manager,
                is_active=True,
                sort_order=1
            )
            db.add(member)
            db.commit()

        # 4. Activar suscripciones a modulos existentes para la empresa
        try:
            modules = db.query(models.AppModule).filter(models.AppModule.is_active == True).all()
            now = datetime.utcnow()
            for mod in modules:
                existing_sub = db.query(models.ModuleSubscription).filter(
                    models.ModuleSubscription.module_id == mod.id,
                    models.ModuleSubscription.company_id == company.id
                ).first()
                if not existing_sub:
                    sub = models.ModuleSubscription(
                        id=uuid.uuid4(),
                        module_id=mod.id,
                        company_id=company.id,
                        scope="company",
                        status="active",
                        created_at=now,
                        updated_at=now
                    )
                    db.add(sub)
            db.commit()
        except Exception as mod_err:
            print(f"[Seed] Advertencia al suscribir modulos: {mod_err}")
            db.rollback()

        print(f"[Seed] Exito: Usuario administrador creado ({admin_email}) con clave configurada.")
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
