import unittest
import uuid
from datetime import date

import models
from database import SessionLocal
from fastapi import HTTPException
from routers.work_logs import get_billing_summary


class TestBillingSummaryEndpoint(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # Create a test company
        self.company = models.Company(
            name=f"Test Billing Company {uuid.uuid4().hex[:6]}"
        )
        self.db.add(self.company)
        self.db.flush()

        # Create user 1 (the manager)
        self.user_manager = models.User(
            email=f"manager_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Manager",
            last_name="Test",
            role=models.UserRole.user
        )
        self.db.add(self.user_manager)
        self.db.flush()

        # Create user 2 (the worker)
        self.user_worker = models.User(
            email=f"worker_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Worker",
            last_name="Test",
            role=models.UserRole.user
        )
        self.db.add(self.user_worker)
        self.db.flush()

        # Create company memberships with rates_config in JSONB format
        self.membership1 = models.CompanyMember(
            user_id=self.user_manager.id,
            company_id=self.company.id,
            role=models.CompanyRole.manager,
            is_active=True
        )
        self.membership2 = models.CompanyMember(
            user_id=self.user_worker.id,
            company_id=self.company.id,
            role=models.CompanyRole.worker,
            is_active=True,
            rates_config={
                "particular": {
                    "base_rate": 20.0,
                    "is_gross": False,
                    "tax_overrides": {
                        "deduction_ss": 0.05,
                        "deduction_irpf": 0.15
                    }
                }
            }
        )
        self.db.add(self.membership1)
        self.db.add(self.membership2)
        self.db.flush()

        # Create a work log for the worker
        self.log = models.WorkLog(
            user_id=self.user_worker.id,
            company_id=self.company.id,
            start_date=date(2026, 7, 14),
            end_date=date(2026, 7, 14),
            duration=8.0,
            net_amount=160.0,
            gross_amount=200.0,
            type="particular"
        )
        self.db.add(self.log)
        self.db.flush()

        # Set up active contexts
        self.user_manager.active_company_id = str(self.company.id)
        self.user_manager.active_role = "manager"
        self.user_manager.is_platform_admin = False

        self.user_worker.active_company_id = str(self.company.id)
        self.user_worker.active_role = "worker"
        self.user_worker.is_platform_admin = False

        # Platform Admin user
        self.user_admin = models.User(
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Admin",
            last_name="Test",
            role=models.UserRole.user
        )
        self.db.add(self.user_admin)
        self.db.flush()
        self.user_admin.is_platform_admin = True
        self.user_admin.active_company_id = None
        self.user_admin.active_role = None

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_manager_can_access_billing_summary(self):
        """
        A company manager should be allowed to view the billing summary.
        """
        response = get_billing_summary(
            company_id=self.company.id,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            db=self.db,
            current_user=self.user_manager
        )
        self.assertIsInstance(response, list)
        self.assertGreaterEqual(len(response), 2)

        # Find the items by user_id
        worker_item = next((x for x in response if x.user_id == self.user_worker.id), None)
        manager_item = next((x for x in response if x.user_id == self.user_manager.id), None)

        self.assertIsNotNone(worker_item)
        self.assertEqual(worker_item.type, "particular")
        self.assertEqual(worker_item.total_hours, 8.0)
        self.assertEqual(worker_item.total_net, 160.0)
        self.assertEqual(worker_item.total_gross, 200.0)
        self.assertEqual(worker_item.unique_days, 1)
        self.assertEqual(worker_item.logs_count, 1)

        self.assertIsNotNone(manager_item)
        self.assertIsNone(manager_item.type)
        self.assertEqual(manager_item.total_hours, 0.0)
        self.assertEqual(manager_item.total_net, 0.0)
        self.assertEqual(manager_item.total_gross, 0.0)
        self.assertEqual(manager_item.unique_days, 0)
        self.assertEqual(manager_item.logs_count, 0)

    def test_worker_cannot_access_billing_summary(self):
        """
        A regular worker should get a 403 Forbidden.
        """
        with self.assertRaises(HTTPException) as context:
            get_billing_summary(
                company_id=self.company.id,
                start_date=date(2026, 7, 1),
                end_date=date(2026, 7, 31),
                db=self.db,
                current_user=self.user_worker
            )
        self.assertEqual(context.exception.status_code, 403)

    def test_admin_can_access_billing_summary(self):
        """
        A platform admin should be allowed to view the billing summary for any company.
        """
        response = get_billing_summary(
            company_id=self.company.id,
            start_date=date(2026, 7, 1),
            end_date=date(2026, 7, 31),
            db=self.db,
            current_user=self.user_admin
        )
        self.assertIsInstance(response, list)
        self.assertGreaterEqual(len(response), 2)

if __name__ == "__main__":
    unittest.main()
