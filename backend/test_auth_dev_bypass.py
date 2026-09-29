"""
Pruebas unitarias para el bypass de autenticacion y sembrado de desarrollo local.
"""
import os
import unittest

import auth
import dev_seed
import models
from database import SessionLocal


class TestDevAuthBypass(unittest.TestCase):
    def setUp(self):
        self.db = SessionLocal()
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEV_LOGIN_BYPASS"] = "true"
        os.environ["DEV_ADMIN_EMAIL"] = "admin@vesotel.com"
        os.environ["DEV_ADMIN_PASSWORD"] = "admin"
        os.environ["DEV_ADMIN_COMPANY"] = "Vesotel Ski School"

    def tearDown(self):
        self.db.close()

    def test_is_dev_mode(self):
        self.assertTrue(dev_seed.is_dev_mode())

        os.environ["ENVIRONMENT"] = "production"
        os.environ["NODE_ENV"] = "production"
        os.environ["DEV_LOGIN_BYPASS"] = "false"
        self.assertFalse(dev_seed.is_dev_mode())

        # Restaurar
        os.environ["ENVIRONMENT"] = "development"
        os.environ["DEV_LOGIN_BYPASS"] = "true"

    def test_ensure_dev_admin_user_creates_and_returns_admin(self):
        user = dev_seed.ensure_dev_admin_user(self.db)
        self.assertIsNotNone(user)
        self.assertEqual(user.email, "admin@vesotel.com")
        self.assertEqual(user.role, models.UserRole.admin)
        self.assertTrue(user.is_active)
        self.assertFalse(user.is_2fa_enabled)

        # Verificar generacion de tokens
        access_token, refresh_token = auth.generate_user_tokens(self.db, user)
        self.assertIsNotNone(access_token)
        self.assertIsNotNone(refresh_token)

        # Decodificar token y comprobar permisos
        payload = auth.jwt.decode(access_token, auth.PUBLIC_KEY, algorithms=[auth.ALGORITHM])
        self.assertEqual(payload.get("sub"), str(user.id))
        self.assertTrue(payload.get("is_admin"))

    def test_dev_seed_is_idempotent(self):
        user1 = dev_seed.ensure_dev_admin_user(self.db)
        user2 = dev_seed.ensure_dev_admin_user(self.db)
        self.assertEqual(user1.id, user2.id)
        self.assertEqual(user1.email, user2.email)
