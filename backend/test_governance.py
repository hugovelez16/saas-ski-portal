import os
import unittest
import uuid

# Ensure SQLite in-memory database for testing
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

import models  # noqa: E402
import schemas  # noqa: E402
from database import Base, SessionLocal, engine  # noqa: E402
from fastapi import HTTPException  # noqa: E402
from routers.companies import read_company, update_company_member  # noqa: E402
from routers.work_logs import create_work_log, delete_work_log, update_work_log  # noqa: E402
from sqlalchemy.dialects.postgresql import JSONB  # noqa: E402
from sqlalchemy.ext.compiler import compiles  # noqa: E402


@compiles(JSONB, "sqlite")
def compile_jsonb_sqlite(type_, compiler, **kw):
    return "JSON"


class TestCompanyGovernance(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        Base.metadata.create_all(bind=engine)

    def setUp(self):
        self.db = SessionLocal()

        # 1. Platform admin
        self.platform_admin = models.User(
            id=uuid.uuid4(),
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="pw",
            first_name="Platform",
            last_name="Admin",
            role=models.UserRole.admin,
            is_active=True,
        )
        self.platform_admin.is_platform_admin = True

        # 2. Company manager user
        self.manager_user = models.User(
            id=uuid.uuid4(),
            email=f"manager_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="pw",
            first_name="Manager",
            last_name="User",
            role=models.UserRole.user,
            is_active=True,
        )
        self.manager_user.is_platform_admin = False

        # 3. Worker user
        self.worker_user = models.User(
            id=uuid.uuid4(),
            email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="pw",
            first_name="Worker",
            last_name="User",
            role=models.UserRole.user,
            is_active=True,
        )
        self.worker_user.is_platform_admin = False

        # 4. Another worker
        self.other_worker = models.User(
            id=uuid.uuid4(),
            email=f"other_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="pw",
            first_name="Other",
            last_name="Worker",
            role=models.UserRole.user,
            is_active=True,
        )
        self.other_worker.is_platform_admin = False

        # Managed Company (is_managed=True, is_active=True)
        self.managed_company = models.Company(id=uuid.uuid4(), name="Managed Corp", is_active=True, is_managed=True)

        # Autonomous Company (is_managed=False, is_active=True)
        self.autonomous_company = models.Company(
            id=uuid.uuid4(), name="Autonomous Freelancers", is_active=True, is_managed=False
        )

        # Inactive Company (is_active=False)
        self.inactive_company = models.Company(
            id=uuid.uuid4(), name="Suspended Company", is_active=False, is_managed=False
        )

        self.db.add_all(
            [
                self.platform_admin,
                self.manager_user,
                self.worker_user,
                self.other_worker,
                self.managed_company,
                self.autonomous_company,
                self.inactive_company,
            ]
        )
        self.db.commit()

        # Memberships in Managed Company
        self.m_manager = models.CompanyMember(
            company_id=self.managed_company.id,
            user_id=self.manager_user.id,
            role=models.CompanyRole.manager,
            is_active=True,
        )
        self.m_worker = models.CompanyMember(
            company_id=self.managed_company.id,
            user_id=self.worker_user.id,
            role=models.CompanyRole.worker,
            is_active=True,
            rates_config={"particular": 30.0},
        )
        self.m_other = models.CompanyMember(
            company_id=self.managed_company.id,
            user_id=self.other_worker.id,
            role=models.CompanyRole.worker,
            is_active=True,
        )

        # Memberships in Autonomous Company
        self.m_auto_worker = models.CompanyMember(
            company_id=self.autonomous_company.id,
            user_id=self.worker_user.id,
            role=models.CompanyRole.worker,
            is_active=True,
            rates_config={"particular": 25.0},
        )

        # Memberships in Inactive Company
        self.m_inactive_worker = models.CompanyMember(
            company_id=self.inactive_company.id,
            user_id=self.worker_user.id,
            role=models.CompanyRole.worker,
            is_active=True,
        )

        self.db.add_all([self.m_manager, self.m_worker, self.m_other, self.m_auto_worker, self.m_inactive_worker])
        self.db.commit()

        # Set active scopes on user objects
        self.manager_user.active_company_id = str(self.managed_company.id)
        self.manager_user.active_role = "manager"

        self.worker_user.active_company_id = str(self.managed_company.id)
        self.worker_user.active_role = "worker"

    def tearDown(self):
        self.db.close()

    def test_manager_cannot_change_member_role(self):
        """Un manager de empresa no debe poder ascender o cambiar el rol de un miembro."""
        update_data = schemas.CompanyMemberUpdate(role="admin")
        with self.assertRaises(HTTPException) as ctx:
            update_company_member(
                company_id=str(self.managed_company.id),
                user_id=str(self.other_worker.id),
                member_data=update_data,
                db=self.db,
                current_user=self.manager_user,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Solo los administradores", ctx.exception.detail)

    def test_platform_admin_can_change_member_role(self):
        """Un admin de plataforma si debe poder cambiar el rol de un miembro."""
        update_data = schemas.CompanyMemberUpdate(role="admin")
        result = update_company_member(
            company_id=str(self.managed_company.id),
            user_id=str(self.other_worker.id),
            member_data=update_data,
            db=self.db,
            current_user=self.platform_admin,
        )
        self.assertEqual(result.role, "admin")

    def test_worker_cannot_edit_rates_in_managed_company(self):
        """En una empresa gestionada (is_managed=True), un trabajador no puede modificar sus tarifas."""
        update_data = schemas.CompanyMemberUpdate(ratesConfig={"particular": 50.0})
        with self.assertRaises(HTTPException) as ctx:
            update_company_member(
                company_id=str(self.managed_company.id),
                user_id=str(self.worker_user.id),
                member_data=update_data,
                db=self.db,
                current_user=self.worker_user,
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("tarifas son fijadas por los administradores", ctx.exception.detail)

    def test_worker_can_edit_rates_in_autonomous_company(self):
        """En una empresa autonoma (is_managed=False), el trabajador si puede modificar sus tarifas."""
        self.worker_user.active_company_id = str(self.autonomous_company.id)
        update_data = schemas.CompanyMemberUpdate(ratesConfig={"particular": 45.0})
        result = update_company_member(
            company_id=str(self.autonomous_company.id),
            user_id=str(self.worker_user.id),
            member_data=update_data,
            db=self.db,
            current_user=self.worker_user,
        )
        self.assertEqual(result.rates_config, {"particular": 45.0})

    def test_inactive_company_blocks_access_to_non_admin(self):
        """Una empresa inactiva (is_active=False) rechaza el acceso a usuarios no plataforma."""
        with self.assertRaises(HTTPException) as ctx:
            read_company(company_id=str(self.inactive_company.id), db=self.db, current_user=self.worker_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Empresa inactiva o suspendida", ctx.exception.detail)

    def test_inactive_company_allows_access_to_platform_admin(self):
        """Un admin de plataforma si puede acceder a una empresa inactiva."""
        comp = read_company(company_id=str(self.inactive_company.id), db=self.db, current_user=self.platform_admin)
        self.assertEqual(comp.id, self.inactive_company.id)

    def test_cannot_create_work_log_in_inactive_company(self):
        """No se pueden crear turnos de trabajo en empresas inactivas."""
        log_data = schemas.WorkLogCreate(
            company_id=self.inactive_company.id,
            user_id=self.worker_user.id,
            type="particular",
            startDate="2026-09-28",
            endDate="2026-09-28",
            duration=2.0,
        )
        with self.assertRaises(HTTPException) as ctx:
            create_work_log(work_log=log_data, db=self.db, current_user=self.worker_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("Empresa inactiva o suspendida", ctx.exception.detail)

    def test_worker_cannot_edit_or_delete_shifts_in_managed_company(self):
        """En una empresa gestionada, un trabajador no puede modificar ni borrar turnos directamente."""
        # Creamos un turno en managed_company usando platform_admin
        log = models.WorkLog(
            id=uuid.uuid4(),
            company_id=self.managed_company.id,
            user_id=self.worker_user.id,
            type="particular",
            start_date=models.datetime.utcnow().date(),
            end_date=models.datetime.utcnow().date(),
            duration=2.0,
        )
        self.db.add(log)
        self.db.commit()

        # Intentar borrar como trabajador
        with self.assertRaises(HTTPException) as ctx:
            delete_work_log(work_log_id=str(log.id), db=self.db, current_user=self.worker_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("no pueden eliminar turnos", ctx.exception.detail)

        # Intentar actualizar como trabajador
        update_data = schemas.WorkLogCreate(
            company_id=self.managed_company.id,
            user_id=self.worker_user.id,
            type="particular",
            startDate="2026-09-28",
            endDate="2026-09-28",
            duration=3.0,
        )
        with self.assertRaises(HTTPException) as ctx:
            update_work_log(work_log_id=str(log.id), work_log=update_data, db=self.db, current_user=self.worker_user)
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertIn("no pueden modificar turnos", ctx.exception.detail)


if __name__ == "__main__":
    unittest.main()
