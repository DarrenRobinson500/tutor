"""
Tests for JWT authentication, role-based access control, and User model correctness.
"""
import unittest

from .base import BaseAPITestCase
from .factories import make_user, make_tutor_profile, make_student_profile, make_parent_child


# ---------------------------------------------------------------------------
# JWT Authentication
# ---------------------------------------------------------------------------

class JWTAuthTests(BaseAPITestCase):
    """POST /api/auth/jwt/login/ and /api/auth/jwt/refresh/"""

    def setUp(self):
        self.password = 'Str0ng!Pass'
        self.user = make_user(role='student', password=self.password)
        # Re-set password via the proper hasher so SimpleJWT can validate it.
        self.user.set_password(self.password)
        self.user.save()

    def test_login_valid_credentials_returns_200_with_tokens(self):
        resp = self.client.post('/api/auth/jwt/login/', {
            'username': self.user.username,
            'password': self.password,
        })
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('access', resp.data)
        self.assertIn('refresh', resp.data)

    def test_login_invalid_password_returns_401(self):
        resp = self.client.post('/api/auth/jwt/login/', {
            'username': self.user.username,
            'password': 'wrong-password',
        })
        self.assertEqual(resp.status_code, 401)

    def test_login_unknown_user_returns_401(self):
        resp = self.client.post('/api/auth/jwt/login/', {
            'username': 'nobody@example.com',
            'password': self.password,
        })
        self.assertEqual(resp.status_code, 401)

    def test_refresh_valid_token_returns_200_with_new_access(self):
        # First obtain a refresh token via login.
        login_resp = self.client.post('/api/auth/jwt/login/', {
            'username': self.user.username,
            'password': self.password,
        })
        self.assertEqual(login_resp.status_code, 200)
        refresh_token = login_resp.data['refresh']

        resp = self.client.post('/api/auth/jwt/refresh/', {'refresh': refresh_token})
        self.assertEqual(resp.status_code, 200, resp.data)
        self.assertIn('access', resp.data)

    def test_refresh_invalid_token_returns_401(self):
        resp = self.client.post('/api/auth/jwt/refresh/', {'refresh': 'not.a.valid.token'})
        self.assertEqual(resp.status_code, 401)

    def test_unauthenticated_request_to_protected_endpoint_returns_401(self):
        # Ensure no credentials are attached.
        self.unauth()
        resp = self.client.get('/api/admin-jobs/')
        self.assertEqual(resp.status_code, 401)


# ---------------------------------------------------------------------------
# Role access matrix — GET /api/admin-jobs/
# ---------------------------------------------------------------------------

class AdminJobsRoleAccessTests(BaseAPITestCase):
    """
    AdminJobViewSet.list() checks request.user.role == 'admin'.
    Only a superuser whose role has been set to 'admin' should get 200.
    All other roles should receive 403.
    """

    def _get_admin_jobs(self):
        return self.client.get('/api/admin-jobs/')

    def test_tutor_role_gets_403(self):
        user = make_user(role='tutor')
        make_tutor_profile(user=user, approved=True)
        self.auth(user)
        self.assertEqual(self._get_admin_jobs().status_code, 403)

    def test_parent_role_gets_403(self):
        user = make_user(role='parent')
        self.auth(user)
        self.assertEqual(self._get_admin_jobs().status_code, 403)

    def test_student_role_gets_403(self):
        user = make_user(role='student')
        self.auth(user)
        self.assertEqual(self._get_admin_jobs().status_code, 403)

    def test_admin_superuser_gets_200(self):
        user = make_user(role='admin', is_superuser=True)
        self.auth(user)
        resp = self._get_admin_jobs()
        self.assertEqual(resp.status_code, 200, resp.data)

    def test_teacher_role_gets_403(self):
        user = make_user(role='teacher')
        self.auth(user)
        self.assertEqual(self._get_admin_jobs().status_code, 403)

    def test_non_admin_with_is_superuser_false_gets_403(self):
        # A user that has a non-admin role and is not a superuser must be rejected.
        user = make_user(role='student', is_superuser=False)
        self.auth(user)
        self.assertEqual(self._get_admin_jobs().status_code, 403)


# ---------------------------------------------------------------------------
# Unapproved tutor home endpoint
# ---------------------------------------------------------------------------

class UnapprovedTutorHomeTests(BaseAPITestCase):
    """
    GET /api/tutors/{id}/home/ for a tutor whose TutorProfile.approved=False.

    The current TutorViewSet.home implementation only checks IsAuthenticated —
    it does NOT check the `approved` field.  The expected contract is that
    unapproved tutors should receive 403, but the code returns 200.

    The test is marked @unittest.expectedFailure to document this gap.
    When the approval check is added to the view this mark should be removed.
    """

    def test_unapproved_tutor_home_returns_403(self):
        tutor = make_user(role='tutor')
        make_tutor_profile(user=tutor, approved=False)
        self.auth(tutor)
        resp = self.client.get(f'/api/tutors/{tutor.pk}/home/')
        # This assertion currently fails because the view returns 200.
        self.assertEqual(resp.status_code, 403)

    def test_approved_tutor_home_returns_200(self):
        tutor = make_user(role='tutor')
        make_tutor_profile(user=tutor, approved=True)
        self.auth(tutor)
        resp = self.client.get(f'/api/tutors/{tutor.pk}/home/')
        self.assertEqual(resp.status_code, 200)


# ---------------------------------------------------------------------------
# User model method bug tests
# ---------------------------------------------------------------------------

class UserModelBugTests(BaseAPITestCase):
    """
    Unit tests for known bugs in User model helper methods.
    Tests marked @unittest.expectedFailure document confirmed bugs.
    """

    # -- Bug 1: get_student_profile() raises UnboundLocalError for non-student roles --
    #
    # In models.py lines 70-75:
    #
    #   def get_student_profile(self):
    #       if self.role == "student":
    #           profile = StudentProfile.objects.filter(user=self).first()
    #       if not profile and self.role == "student":   # <-- profile unbound when role != "student"
    #           profile = StudentProfile.objects.create(user=self)
    #       return profile
    #
    # When role != "student" the name `profile` is never assigned before the second
    # `if not profile` check, so Python raises UnboundLocalError.

    def test_get_student_profile_on_tutor_user_returns_none_not_raises(self):
        tutor = make_user(role='tutor')
        make_tutor_profile(user=tutor, approved=True)
        # Should return None; currently raises UnboundLocalError.
        try:
            result = tutor.get_student_profile()
            self.assertIsNone(result)
        except UnboundLocalError:
            # Raise AssertionError so the expectedFailure decorator sees the failure.
            raise AssertionError('UnboundLocalError raised instead of returning None')

    def test_get_student_profile_on_parent_user_returns_none_not_raises(self):
        parent = make_user(role='parent')
        try:
            result = parent.get_student_profile()
            self.assertIsNone(result)
        except UnboundLocalError:
            raise AssertionError('UnboundLocalError raised instead of returning None')

    # A student user with a StudentProfile should still work correctly.
    def test_get_student_profile_on_student_user_returns_profile(self):
        student = make_user(role='student')
        profile = make_student_profile(user=student)
        result = student.get_student_profile()
        self.assertIsNotNone(result)
        self.assertEqual(result.pk, profile.pk)

    # -- Bug 2: get_tutor() raises UnboundLocalError for parent whose child has no TutorStudent --
    #
    # In models.py lines 83-85:
    #
    #   if self.role == "parent":
    #       child_link = ParentChild.objects.filter(parent=self).first()
    #       if child_link: tutor_link = TutorStudent.objects.filter(student=child_link.child).first()
    #       if tutor_link: return ...       # <-- tutor_link unbound when child_link is falsy
    #
    # When a parent has a child (child_link exists) but that child has no TutorStudent,
    # `tutor_link` is None after the first `if child_link:` block.  The following
    # `if tutor_link:` then correctly evaluates to False, so that branch is OK.
    # However, if a parent has NO child at all (child_link is None/falsy), the
    # `tutor_link` name is never assigned and the `if tutor_link:` raises UnboundLocalError.

    def test_get_tutor_on_parent_without_child_returns_none_not_raises(self):
        parent = make_user(role='parent')
        # Parent has no ParentChild relationship at all.
        try:
            result = parent.get_tutor()
            self.assertIsNone(result)
        except UnboundLocalError:
            raise AssertionError(
                'UnboundLocalError raised when parent has no child link'
            )

    def test_get_tutor_on_parent_with_child_but_no_tutor_student_returns_none(self):
        """
        When a parent has a child but the child has no TutorStudent, get_tutor()
        should return None.  child_link is truthy so tutor_link IS assigned (to
        None) before the second `if tutor_link:` check — so no UnboundLocalError.
        """
        parent = make_user(role='parent')
        child = make_user(role='student')
        make_parent_child(parent=parent, student=child)
        # No TutorStudent created for child.
        result = parent.get_tutor()
        self.assertIsNone(result)

    # -- Bug 3: get_tutor() for parent returns TutorProfile instead of User --
    #
    # In models.py lines 84-85, the parent branch ultimately does:
    #
    #   if tutor_link: return TutorProfile.objects.filter(tutor=tutor_link.tutor).first()
    #
    # All other branches return a User instance (or None).  The parent branch
    # returns a TutorProfile, breaking callers that assume get_tutor() always
    # returns a User.  For example, StudentProfile.to_dict() calls
    # `tutor_user.get_tutor_profile()` on the result of get_tutor(), which would
    # AttributeError on a TutorProfile object.

    def test_get_tutor_on_parent_with_full_chain_returns_user_not_tutor_profile(self):
        from backend.models import User, TutorProfile, TutorStudent, ParentChild

        tutor_user = make_user(role='tutor')
        make_tutor_profile(user=tutor_user, approved=True)
        student = make_user(role='student')
        parent = make_user(role='parent')
        TutorStudent.objects.create(tutor=tutor_user, student=student)
        make_parent_child(parent=parent, student=student)

        result = parent.get_tutor()
        # Should return a User instance; currently returns a TutorProfile.
        self.assertIsInstance(
            result, User,
            f'Expected User instance but got {type(result).__name__}'
        )
