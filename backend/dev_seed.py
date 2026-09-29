"""
Modulo de inicializacion automatica de usuario administrador y empresa para desarrollo local.
"""
import os

import auth
import models
from sqlalchemy.orm import Session


def is_dev_mode() -> bool:
    """Comprueba si el entorno actual esta en modo desarrollo o tiene activo el bypass."""
    env = os.getenv("ENVIRONMENT", "").lower()
    node_env = os.getenv("NODE_ENV", "").lower()
    bypass = os.getenv("DEV_LOGIN_BYPASS", "").lower()
    return env == "development" or node_env == "development" or bypass in ["true", "1", "yes"]

def ensure_dev_admin_user(db: Session) -> models.User:
    """
    Garantiza que exista un usuario administrador y una empresa asociada para el entorno de desarrollo.
    Lee los valores configurados en las variables de entorno o utiliza valores por defecto.
    """
    admin_email = os.getenv("DEV_ADMIN_EMAIL", "admin@vesotel.com").strip().lower()
    admin_password = os.getenv("DEV_ADMIN_PASSWORD", "admin")
    admin_company_name = os.getenv("DEV_ADMIN_COMPANY", "Vesotel Ski School").strip()
    admin_first_name = os.getenv("DEV_ADMIN_FIRST_NAME", "Admin").strip()
    admin_last_name = os.getenv("DEV_ADMIN_LAST_NAME", "Vesotel").strip()

    # 1. Buscar o crear empresa por defecto
    company = db.query(models.Company).filter(models.Company.name == admin_company_name).first()
    if not company:
        # Intentar obtener cualquier primera empresa existente
        company = db.query(models.Company).first()
        if not company:
            company = models.Company(
                name=admin_company_name,
                fiscal_id="B00000000",
                tax_config={"social_security": 0.0648},
                worklog_definitions={},
                settings={}
            )
            db.add(company)
            db.commit()
            db.refresh(company)
            print(f"[DevSeed] Empresa '{admin_company_name}' creada exitosamente.")

    # 2. Buscar o crear usuario administrador
    user = db.query(models.User).filter(models.User.email == admin_email).first()
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
            default_company_id=company.id
        )
        db.add(user)
        db.commit()
        db.refresh(user)
        print(f"[DevSeed] Usuario administrador '{admin_email}' creado exitosamente.")
    else:
        # Asegurar permisos de administrador y estado activo
        updated = False
        if user.role != models.UserRole.admin:
            user.role = models.UserRole.admin
            updated = True
        if not user.is_active:
            user.is_active = True
            updated = True
        if user.is_2fa_enabled:
            user.is_2fa_enabled = False
            updated = True
        if not user.default_company_id and company:
            user.default_company_id = company.id
            updated = True
        if updated:
            db.commit()
            db.refresh(user)
            print(f"[DevSeed] Usuario administrador '{admin_email}' actualizado.")

    # 3. Asegurar membresia en la empresa
    if company:
        membership = db.query(models.CompanyMember).filter(
            models.CompanyMember.user_id == user.id,
            models.CompanyMember.company_id == company.id
        ).first()
        if not membership:
            membership = models.CompanyMember(
                user_id=user.id,
                company_id=company.id,
                role=models.CompanyRole.admin,
                is_active=True,
                rates_config={},
                settings={}
            )
            db.add(membership)
            db.commit()
            print(f"[DevSeed] Membresia creada para '{admin_email}' en '{company.name}'.")

    return user
