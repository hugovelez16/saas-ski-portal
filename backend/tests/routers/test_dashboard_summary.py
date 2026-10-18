import unittest
import uuid
from datetime import date

import crud
import models
from database import SessionLocal
from fastapi import HTTPException
from routers.companies import get_company_dashboard_summary


class TestDashboardSummary(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # 1. Create test company
        self.company = models.Company(
            name=f"Test Dashboard Company {uuid.uuid4().hex[:6]}",
            worklog_definitions={
                "particular": {"unit": "hours", "label": "Particular"},
                "tutorial": {"unit": "days", "label": "Tutorial"}
            }
        )
        self.db.add(self.company)
        self.db.flush()

        # 2. Create users
        self.manager_user = models.User(
            email=f"mgr_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="hashed_pass_test",
            first_name="Carlos",
            last_name="Manager",
            role=models.UserRole.user
        )
        self.worker_user1 = models.User(
            email=f"w1_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="hashed_pass_test",
            first_name="Ana",
            last_name="Monitora",
            role=models.UserRole.user
        )
        self.worker_user2 = models.User(
            email=f"w2_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="hashed_pass_test",
            first_name="David",
            last_name="Profesor",
            role=models.UserRole.user
        )
        self.unauthorized_user = models.User(
            email=f"unauth_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="hashed_pass_test",
            first_name="Pedro",
            last_name="Ajeno",
            role=models.UserRole.user
        )
        self.db.add_all([self.manager_user, self.worker_user1, self.worker_user2, self.unauthorized_user])
        self.db.flush()

        # 3. Create memberships with strict sort_order
        self.mem_manager = models.CompanyMember(
            user_id=self.manager_user.id,
            company_id=self.company.id,
            role=models.CompanyRole.manager,
            is_active=True,
            sort_order=1
        )
        self.mem_worker1 = models.CompanyMember(
            user_id=self.worker_user1.id,
            company_id=self.company.id,
            role=models.CompanyRole.worker,
            is_active=True,
            sort_order=10
        )
        self.mem_worker2 = models.CompanyMember(
            user_id=self.worker_user2.id,
            company_id=self.company.id,
            role=models.CompanyRole.worker,
            is_active=True,
            sort_order=20
        )
        self.db.add_all([self.mem_manager, self.mem_worker1, self.mem_worker2])
        self.db.flush()

        # 4. Create Work Logs
        today = date.today()
        self.log_today_w1 = models.WorkLog(
            user_id=self.worker_user1.id,
            company_id=self.company.id,
            type="particular",
            start_date=today,
            end_date=today,
            duration=3.0,
            net_amount=75.0,
            gross_amount=90.0
        )
        self.log_today_w2 = models.WorkLog(
            user_id=self.worker_user2.id,
            company_id=self.company.id,
            type="particular",
            start_date=today,
            end_date=today,
            duration=2.0,
            net_amount=50.0,
            gross_amount=60.0
        )
        self.db.add_all([self.log_today_w1, self.log_today_w2])
        self.db.commit()

    def tearDown(self):
        self.db.query(models.WorkLog).filter(models.WorkLog.company_id == self.company.id).delete()
        self.db.query(models.CompanyMember).filter(models.CompanyMember.company_id == self.company.id).delete()
        self.db.query(models.User).filter(models.User.id.in_([
            self.manager_user.id, self.worker_user1.id, self.worker_user2.id, self.unauthorized_user.id
        ])).delete()
        self.db.query(models.Company).filter(models.Company.id == self.company.id).delete()
        self.db.commit()
        self.db.close()

    def test_get_dashboard_summary_metrics(self):
        today = date.today()
        summary = crud.get_dashboard_summary(
            db=self.db,
            company_id=self.company.id,
            start_date=today,
            end_date=today
        )

        # Check today metrics
        self.assertEqual(summary["today_metrics"]["today_hours"], 5.0)
        self.assertEqual(summary["today_metrics"]["today_logs_count"], 2)
        self.assertEqual(summary["today_metrics"]["today_active_members_count"], 2)

        # Check period metrics
        self.assertEqual(summary["period_metrics"]["total_hours"], 5.0)
        self.assertEqual(summary["period_metrics"]["total_net"], 125.0)
        self.assertEqual(summary["period_metrics"]["total_gross"], 150.0)

        # Check workers summary follows sort order (manager=1, worker1=10, worker2=20)
        workers = summary["workers_summary"]
        self.assertEqual(len(workers), 3)
        self.assertEqual(workers[0]["user_id"], self.manager_user.id)
        self.assertEqual(workers[1]["user_id"], self.worker_user1.id)
        self.assertEqual(workers[2]["user_id"], self.worker_user2.id)

    def test_unauthorized_access_denied(self):
        today = date.today()
        with self.assertRaises(HTTPException) as ctx:
            get_company_dashboard_summary(
                company_id=str(self.company.id),
                start_date=today,
                end_date=today,
                db=self.db,
                current_user=self.unauthorized_user
            )
        self.assertEqual(ctx.exception.status_code, 403)


if __name__ == "__main__":
    unittest.main()
