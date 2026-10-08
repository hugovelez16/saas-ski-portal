"""
Sembrado de datos de demostracion (video de presentacion y pruebas manuales).

Crea una empresa ficticia, un manager de demo, varios monitores y jornadas
semialeatorias de los ultimos 60 dias. Es reproducible (semilla fija) e
idempotente: si el usuario demo ya existe, no hace nada.

Uso: ./bin/seed-demo
"""

import os
import random
import uuid
from datetime import date, datetime, time, timedelta

import auth
import crud
import models
import schemas
from database import SessionLocal
from sqlalchemy.orm import Session

DEMO_COMPANY_NAME = os.getenv("DEMO_COMPANY_NAME", "Escuela de Esqui Nieve Sur")
DEMO_MANAGER_EMAIL = os.getenv("DEMO_MANAGER_EMAIL", "demo@nievesur.es")
DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo2026!")
DEMO_DAYS = int(os.getenv("DEMO_DAYS", "60"))
DEMO_SEED = int(os.getenv("DEMO_SEED", "2026"))

WORKLOG_DEFINITIONS = {
    "particular": {"unit": "hours", "label": "Clase Particular", "fields": []},
    "colectiva": {"unit": "hours", "label": "Clase Colectiva", "fields": []},
    "forfait_guiado": {"unit": "days", "label": "Jornada de Guiado", "fields": []},
}

MANAGER = ("Marta", "Quintana Ortega")
WORKERS = [
    ("Javier", "Molina Cano"),
    ("Lucia", "Ferrer Bosch"),
    ("Diego", "Navarro Gil"),
    ("Carmen", "Ibanez Prats"),
    ("Sergio", "Ramos Vidal"),
    ("Elena", "Castro Lopez"),
]

# Franjas horarias tipicas de una escuela de esqui: (inicio, horas)
SLOTS = [(time(9, 30), 2.0), (time(10, 0), 1.0), (time(11, 30), 2.0), (time(12, 0), 1.0), (time(15, 0), 2.0)]
NOTES = [
    "Grupo de iniciacion, nivel verde",
    "Perfeccionamiento de giro paralelo",
    "Clase familiar con dos menores",
    "Repaso de tecnica en pista azul",
    "Snowboard, primer dia",
    "Grupo adulto, nivel intermedio",
    "Clase privada, cliente habitual",
    None,
    None,
]


def _email(first: str, last: str) -> str:
    return f"{first}.{last.split()[0]}".lower() + "@nievesur.es"


def _build_rates(rng: random.Random) -> dict:
    return {
        "particular": {"base_rate": float(rng.choice([28, 30, 32, 35])), "is_gross": True},
        "colectiva": {"base_rate": float(rng.choice([18, 20, 22])), "is_gross": True},
        "forfait_guiado": {"base_rate": float(rng.choice([95, 110, 120])), "is_gross": True},
    }


def _make_user(db: Session, first: str, last: str, email: str, company_id, role: models.UserRole) -> models.User:
    user = models.User(
        email=email,
        hashed_password=auth.get_password_hash(DEMO_PASSWORD),
        first_name=first,
        last_name=last,
        role=role,
        is_active=True,
        is_2fa_enabled=False,
        must_change_password=False,
        default_company_id=company_id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def _seed_work_logs(db: Session, company: models.Company, user_id, rng: random.Random):
    today = date.today()
    created = 0
    for offset in range(DEMO_DAYS, 0, -1):
        day = today - timedelta(days=offset)
        # Mas actividad en fin de semana, algunos dias libres al azar
        weekend = day.weekday() >= 5
        if rng.random() > (0.85 if weekend else 0.45):
            continue

        if rng.random() < 0.12:
            payload = {"type": "forfait_guiado", "start_date": day, "end_date": day}
        else:
            start, hours = rng.choice(SLOTS)
            end_dt = datetime.combine(day, start) + timedelta(hours=hours)
            payload = {
                "type": rng.choice(["particular", "colectiva", "colectiva"]),
                "start_date": day,
                "end_date": day,
                "start_time": start,
                "end_time": end_dt.time(),
            }

        log = schemas.WorkLogCreate(
            user_id=user_id,
            company_id=company.id,
            description=rng.choice(NOTES),
            **payload,
        )
        crud.create_work_log(db, log)
        created += 1
    return created


def seed_demo_data(db: Session = None) -> bool:
    should_close = db is None
    if db is None:
        db = SessionLocal()

    try:
        if db.query(models.User).filter(models.User.email == DEMO_MANAGER_EMAIL).first():
            print(f"[DemoSeed] {DEMO_MANAGER_EMAIL} ya existe. Omitiendo.")
            return False

        rng = random.Random(DEMO_SEED)

        company = models.Company(
            name=DEMO_COMPANY_NAME,
            fiscal_id="B12345674",
            tax_config={"social_security": 0.0648, "irpf_base": 0.15},
            worklog_definitions=WORKLOG_DEFINITIONS,
            settings={"features": {"worker_daily_report": True}},
        )
        db.add(company)
        db.commit()
        db.refresh(company)

        # Suscripcion a todos los modulos activos para ver la app completa
        now = datetime.utcnow()
        for mod in db.query(models.AppModule).filter(models.AppModule.is_active == True).all():  # noqa: E712
            db.add(
                models.ModuleSubscription(
                    id=uuid.uuid4(),
                    module_id=mod.id,
                    company_id=company.id,
                    scope="company",
                    status="active",
                    created_at=now,
                    updated_at=now,
                )
            )
        db.commit()

        manager = _make_user(db, *MANAGER, DEMO_MANAGER_EMAIL, company.id, models.UserRole.user)
        db.add(
            models.CompanyMember(
                user_id=manager.id,
                company_id=company.id,
                role=models.CompanyRole.manager,
                is_active=True,
                sort_order=1,
                rates_config=_build_rates(rng),
            )
        )
        db.commit()

        total_logs = 0
        for idx, (first, last) in enumerate(WORKERS, start=2):
            worker = _make_user(db, first, last, _email(first, last), company.id, models.UserRole.user)
            member = models.CompanyMember(
                user_id=worker.id,
                company_id=company.id,
                role=models.CompanyRole.worker,
                is_active=True,
                sort_order=idx,
                rates_config=_build_rates(rng),
            )
            db.add(member)
            db.commit()
            db.refresh(member)
            total_logs += _seed_work_logs(db, company, worker.id, rng)

        # El manager tambien imparte algunas clases
        total_logs += _seed_work_logs(db, company, manager.id, rng)

        print(f"[DemoSeed] OK empresa '{DEMO_COMPANY_NAME}', {len(WORKERS) + 1} usuarios, {total_logs} jornadas.")
        print(f"[DemoSeed] Login manager: {DEMO_MANAGER_EMAIL}")
        return True
    except Exception as exc:
        db.rollback()
        print(f"[DemoSeed] [ERROR] {exc}")
        raise
    finally:
        if should_close:
            db.close()


if __name__ == "__main__":
    seed_demo_data()
