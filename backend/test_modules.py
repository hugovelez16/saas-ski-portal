import unittest
import uuid

import models
from database import SessionLocal
from fastapi import HTTPException
from routers.modules import get_my_modules


class TestModulesMeLogic(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()

        # Clean existing test data / or just generate unique names to prevent collision
        # Create two modules: one active, one inactive
        self.module_active_1 = models.AppModule(
            code_name=f"module_active_1_{uuid.uuid4().hex[:6]}",
            name="Active Module 1",
            is_active=True
        )
        self.module_active_2 = models.AppModule(
            code_name=f"module_active_2_{uuid.uuid4().hex[:6]}",
            name="Active Module 2",
            is_active=True
        )
        self.module_inactive = models.AppModule(
            code_name=f"module_inactive_{uuid.uuid4().hex[:6]}",
            name="Inactive Module",
            is_active=False
        )
        self.db.add_all([self.module_active_1, self.module_active_2, self.module_inactive])
        self.db.flush()

        # Create two companies
        self.company_a = models.Company(name=f"Company A {uuid.uuid4().hex[:6]}")
        self.company_b = models.Company(name=f"Company B {uuid.uuid4().hex[:6]}")
        self.db.add_all([self.company_a, self.company_b])
        self.db.flush()

        # Create platform admin user
        self.admin = models.User(
            email=f"admin_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="Admin",
            last_name="Test",
            role=models.UserRole.admin,
            is_active=True
        )
        self.admin.is_platform_admin = True
        self.db.add(self.admin)
        self.db.flush()

        # Create regular user
        self.user = models.User(
            email=f"user_{uuid.uuid4().hex[:6]}@test.com",
            hashed_password="dummy_password",
            first_name="User",
            last_name="Test",
            role=models.UserRole.user,
            is_active=True
        )
        self.user.is_platform_admin = False
        self.db.add(self.user)
        self.db.flush()

        # Set user membership in Company A
        self.membership_a = models.CompanyMember(
            user_id=self.user.id,
            company_id=self.company_a.id,
            role=models.CompanyRole.worker,
            is_active=True
        )
        self.db.add(self.membership_a)
        self.db.flush()

        # Subscribe Company A to active module 1
        self.sub_company_a = models.ModuleSubscription(
            module_id=self.module_active_1.id,
            company_id=self.company_a.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
            expires_at=None
        )
        # Subscribe Company B to active module 2
        self.sub_company_b = models.ModuleSubscription(
            module_id=self.module_active_2.id,
            company_id=self.company_b.id,
            scope=models.SubscriptionScope.company,
            status=models.SubscriptionStatus.active,
            expires_at=None
        )
        # User has a personal subscription to active module 2
        self.sub_user = models.ModuleSubscription(
            module_id=self.module_active_2.id,
            user_id=self.user.id,
            scope=models.SubscriptionScope.user,
            status=models.SubscriptionStatus.active,
            expires_at=None
        )

        self.db.add_all([self.sub_company_a, self.sub_company_b, self.sub_user])
        self.db.flush()

    def tearDown(self):
        self.db.rollback()
        self.db.close()

    def test_regular_user_no_company_context(self):
        """
        Regular user without active_company_id or company_id query parameter
        should only get their personal active subscriptions.
        """
        self.user.active_company_id = None
        modules = get_my_modules(
            company_id=None,
            db=self.db,
            current_user=self.user
        )
        module_codes = {m.code_name for m in modules}
        self.assertIn(self.module_active_2.code_name, module_codes)
        self.assertNotIn(self.module_active_1.code_name, module_codes)

    def test_regular_user_active_company_id_context(self):
        """
        Regular user with active_company_id should get personal + active company modules.
        """
        self.user.active_company_id = str(self.company_a.id)
        modules = get_my_modules(
            company_id=None,
            db=self.db,
            current_user=self.user
        )
        module_codes = {m.code_name for m in modules}
        self.assertIn(self.module_active_1.code_name, module_codes)
        self.assertIn(self.module_active_2.code_name, module_codes)

    def test_regular_user_explicit_company_id_context(self):
        """
        Regular user with explicit company_id parameter should get personal + explicit company modules.
        """
        self.user.active_company_id = None
        modules = get_my_modules(
            company_id=str(self.company_a.id),
            db=self.db,
            current_user=self.user
        )
        module_codes = {m.code_name for m in modules}
        self.assertIn(self.module_active_1.code_name, module_codes)
        self.assertIn(self.module_active_2.code_name, module_codes)

    def test_regular_user_explicit_company_id_not_member(self):
        """
        Regular user requesting a company they are not a member of should receive 403.
        """
        with self.assertRaises(HTTPException) as ctx:
            get_my_modules(
                company_id=str(self.company_b.id),
                db=self.db,
                current_user=self.user
            )
        self.assertEqual(ctx.exception.status_code, 403)
        self.assertEqual(ctx.exception.detail, "No autorizado.")

    def test_regular_user_explicit_company_id_inactive_member(self):
        """
        Regular user requesting a company where their membership is inactive should receive 403.
        """
        self.membership_a.is_active = False
        self.db.flush()
        with self.assertRaises(HTTPException) as ctx:
            get_my_modules(
                company_id=str(self.company_a.id),
                db=self.db,
                current_user=self.user
            )
        self.assertEqual(ctx.exception.status_code, 403)

    def test_platform_admin_no_company_context(self):
        """
        Platform admin with no company context should get all active modules in the catalog.
        """
        self.admin.active_company_id = None
        modules = get_my_modules(
            company_id=None,
            db=self.db,
            current_user=self.admin
        )
        module_codes = {m.code_name for m in modules}
        # Inactive modules should not be returned
        self.assertNotIn(self.module_inactive.code_name, module_codes)
        # But both active modules should be returned
        self.assertIn(self.module_active_1.code_name, module_codes)
        self.assertIn(self.module_active_2.code_name, module_codes)

    def test_platform_admin_with_active_company_id_context(self):
        """
        Platform admin with active_company_id set should get only modules subscribed by that company.
        """
        self.admin.active_company_id = str(self.company_a.id)
        modules = get_my_modules(
            company_id=None,
            db=self.db,
            current_user=self.admin
        )
        module_codes = {m.code_name for m in modules}
        self.assertIn(self.module_active_1.code_name, module_codes)
        self.assertNotIn(self.module_active_2.code_name, module_codes)

    def test_platform_admin_with_explicit_company_id_context(self):
        """
        Platform admin with explicit company_id parameter should get only modules subscribed by that company.
        """
        self.admin.active_company_id = None
        modules = get_my_modules(
            company_id=str(self.company_b.id),
            db=self.db,
            current_user=self.admin
        )
        module_codes = {m.code_name for m in modules}
        self.assertIn(self.module_active_2.code_name, module_codes)
        self.assertNotIn(self.module_active_1.code_name, module_codes)

if __name__ == "__main__":
    unittest.main()
