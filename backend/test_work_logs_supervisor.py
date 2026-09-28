import unittest
import uuid
from datetime import date

import models
from database import SessionLocal
from routers.work_logs import read_work_logs


class TestWorkLogsSupervisorLogic(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # Create a test company
        self.company = models.Company(
            name=f"Test Company {uuid.uuid4().hex[:6]}"
        )
        self.db.add(self.company)
        self.db.flush()

        # Create user 1 (the manager)
        self.user1 = models.User(
            email=f"manager_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Manager",
            last_name="Test",
            role=models.UserRole.user
        )
        self.db.add(self.user1)
        self.db.flush()

        # Create user 2 (the worker)
        self.user2 = models.User(
            email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Worker",
            last_name="Test",
            role=models.UserRole.user
        )
        self.db.add(self.user2)
        self.db.flush()

        # Create company memberships
        self.membership1 = models.CompanyMember(
            user_id=self.user1.id,
            company_id=self.company.id,
            role=models.CompanyRole.manager,
            is_active=True
        )
        self.membership2 = models.CompanyMember(
            user_id=self.user2.id,
            company_id=self.company.id,
            role=models.CompanyRole.worker,
            is_active=True
        )
        self.db.add(self.membership1)
        self.db.add(self.membership2)
        self.db.flush()

        # Create a work log for user 1
        self.log1 = models.WorkLog(
            user_id=self.user1.id,
            company_id=self.company.id,
            start_date=date(2026, 7, 14),
            end_date=date(2026, 7, 14),
            duration=8.0,
            type="particular"
        )
        # Create a work log for user 2
        self.log2 = models.WorkLog(
            user_id=self.user2.id,
            company_id=self.company.id,
            start_date=date(2026, 7, 14),
            end_date=date(2026, 7, 14),
            duration=6.0,
            type="particular"
        )
        self.db.add(self.log1)
        self.db.add(self.log2)
        self.db.flush()

        # Set up active company and role contexts on the users
        # manager context
        self.user1.active_company_id = str(self.company.id)
        self.user1.active_role = "manager"
        self.user1.is_platform_admin = False

        # worker context
        self.user2.active_company_id = str(self.company.id)
        self.user2.active_role = "worker"
        self.user2.is_platform_admin = False

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_supervisor_with_explicit_company_id(self):
        """
        If company_id is explicitly passed, a manager should see logs for all users.
        """
        logs = read_work_logs(
            company_id=self.company.id,
            db=self.db,
            current_user=self.user1
        )
        log_ids = [str(log.id) for log in logs]
        self.assertIn(str(self.log1.id), log_ids)
        self.assertIn(str(self.log2.id), log_ids)

    def test_supervisor_with_implicit_company_id(self):
        """
        If company_id is NOT passed, a manager should ONLY see their own logs.
        """
        logs = read_work_logs(
            company_id=None,
            db=self.db,
            current_user=self.user1
        )
        log_ids = [str(log.id) for log in logs]
        self.assertIn(str(self.log1.id), log_ids)
        # In the desired behavior, log2 (worker's log) must NOT be returned!
        self.assertNotIn(str(self.log2.id), log_ids)

    def test_worker_with_daily_report_module_explicit_company_id(self):
        """
        Check if a worker can read company logs if worker_daily_report module is subscribed,
        but only when company_id is explicitly provided.
        """
        # Check if a module named "worker_daily_report" exists in app_modules (or create one if it doesn't)
        module = self.db.query(models.AppModule).filter(models.AppModule.code_name == "worker_daily_report").first()
        if not module:
            module = models.AppModule(code_name="worker_daily_report", name="Worker Daily Report", is_active=True)
            self.db.add(module)
            self.db.flush()

        # Add a models.ModuleSubscription for the company to that module
        subscription = models.ModuleSubscription(
            module_id=module.id,
            company_id=self.company.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active
        )
        self.db.add(subscription)
        self.db.flush()

        # Call read_work_logs as self.user2 (worker) passing company_id=self.company.id explicitly.
        # Verify they receive all logs (both self.log1 and self.log2)
        logs_explicit = read_work_logs(
            company_id=self.company.id,
            db=self.db,
            current_user=self.user2
        )
        log_ids_explicit = [str(log.id) for log in logs_explicit]
        self.assertIn(str(self.log1.id), log_ids_explicit)
        self.assertIn(str(self.log2.id), log_ids_explicit)

        # Call read_work_logs as self.user2 passing company_id=None.
        # Verify they ONLY receive their own log (self.log2) and NOT self.log1
        logs_implicit = read_work_logs(
            company_id=None,
            db=self.db,
            current_user=self.user2
        )
        log_ids_implicit = [str(log.id) for log in logs_implicit]
        self.assertNotIn(str(self.log1.id), log_ids_implicit)
        self.assertIn(str(self.log2.id), log_ids_implicit)

if __name__ == "__main__":
    unittest.main()
