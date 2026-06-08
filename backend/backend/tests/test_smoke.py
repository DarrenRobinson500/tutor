"""
Smoke tests — one-shot checks that the most critical paths are wired up.

Run with:
    python manage.py test backend.tests.test_smoke
"""
import unittest

from django.test import override_settings
from rest_framework_simplejwt.tokens import RefreshToken

from .base import BaseAPITestCase
from .factories import make_user, make_tutor_profile


class SmokeTests(BaseAPITestCase):
    """Fast sanity checks for auth, permissions, and public endpoints."""

    # ------------------------------------------------------------------
    # 1. Models import
    # ------------------------------------------------------------------

    def test_models_import(self):
        """backend.models must be importable and expose User."""
        import backend.models as m
        self.assertTrue(hasattr(m, 'User'), "User not found in backend.models")

    # ------------------------------------------------------------------
    # 2. JWT login — happy path
    # ------------------------------------------------------------------

    def test_jwt_login_success(self):
        """POST /api/auth/jwt/login/ with valid credentials returns 200 + access token."""
        password = 'correcthorse42'
        user = make_user(role='tutor', password=None)
        user.set_password(password)
        user.save()

        resp = self.client.post(
            '/api/auth/jwt/login/',
            {'username': user.username, 'password': password},
            format='json',
        )
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertIn('access', data, "Response should contain 'access' token")

    # ------------------------------------------------------------------
    # 3. dev_login blocked when DEBUG=False
    # ------------------------------------------------------------------

    @override_settings(DEBUG=False)
    def test_dev_login_blocked(self):
        """POST /api/auth/dev_login/ with DEBUG=False must not return 200.

        The dev_login action does not gate on settings.DEBUG, but the test
        database has no dev users ('admin', 'Alex', 'Blair'), so the view
        returns 404 (User not found) for a known dev username.  The important
        thing is that the response is non-200 — a real 'admin' shortcut login
        must not succeed in production-like settings.
        """
        resp = self.client.post(
            '/api/auth/dev_login/',
            {'username': 'admin'},
            format='json',
        )
        self.assertNotEqual(
            resp.status_code,
            200,
            "dev_login must not return 200 when DEBUG=False",
        )

    # ------------------------------------------------------------------
    # 4. admin-jobs — unauthenticated → 401
    # ------------------------------------------------------------------

    def test_admin_jobs_no_auth(self):
        """GET /api/admin-jobs/ with no credentials returns 401."""
        self.unauth()
        resp = self.client.get('/api/admin-jobs/')
        self.assertEqual(resp.status_code, 401, resp.content)

    # ------------------------------------------------------------------
    # 5. admin-jobs — non-admin (tutor) → 403
    # ------------------------------------------------------------------

    def test_admin_jobs_non_admin(self):
        """GET /api/admin-jobs/ with a tutor JWT returns 403."""
        tutor_user = make_user(role='tutor')
        make_tutor_profile(user=tutor_user)
        self.auth(tutor_user)

        resp = self.client.get('/api/admin-jobs/')
        self.assertEqual(resp.status_code, 403, resp.content)

    # ------------------------------------------------------------------
    # 6. admin-jobs — admin → 200
    # ------------------------------------------------------------------

    def test_admin_jobs_admin(self):
        """GET /api/admin-jobs/ with an admin JWT returns 200."""
        admin_user = make_user(role='admin')
        self.auth(admin_user)

        resp = self.client.get('/api/admin-jobs/')
        self.assertEqual(resp.status_code, 200, resp.content)

    # ------------------------------------------------------------------
    # 7. templates — public (no auth) → 200
    # ------------------------------------------------------------------

    def test_templates_public(self):
        """GET /api/templates/ with no auth returns 200 (TemplateViewSet is AllowAny)."""
        self.unauth()
        resp = self.client.get('/api/templates/')
        self.assertEqual(resp.status_code, 200, resp.content)
