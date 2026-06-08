"""
Security tests for the tutor platform API.

These tests verify that:
  - Dev-only endpoints are blocked in production (DEBUG=False).
  - Cross-user data isolation is enforced (or documents known gaps with expectedFailure).
  - The template preview sandbox does not execute arbitrary code.
"""
import unittest

from django.test import override_settings

from .base import BaseAPITestCase
from .factories import (
    make_user,
    make_tutor_profile,
    make_student_profile,
    make_parent_child,
    make_template,
)


# ---------------------------------------------------------------------------
# Dev endpoint guard
# ---------------------------------------------------------------------------

@override_settings(DEBUG=False)
class DevEndpointGuardTests(BaseAPITestCase):
    """
    Dev-only endpoints must not be accessible when DEBUG=False.

    The views (dev_login, dev_switch_to_parent) have no built-in DEBUG guard;
    these tests document the expected production behaviour and will fail (and
    flag the gap) if the endpoints ever become openly accessible.
    """

    def test_dev_login_blocked_in_production(self):
        """POST /api/auth/dev_login/ must return 404 or 403 when DEBUG=False."""
        response = self.client.post(
            "/api/auth/dev_login/",
            data={"username": "admin"},
            format="json",
        )
        self.assertIn(
            response.status_code,
            [403, 404],
            msg=(
                f"Expected dev_login to be blocked (403/404) in production, "
                f"got {response.status_code}. "
                "The endpoint is currently open without a DEBUG guard."
            ),
        )

    def test_dev_switch_to_parent_blocked_in_production(self):
        """POST /api/auth/dev_switch_to_parent/ must return 404 or 403 when DEBUG=False."""
        response = self.client.post(
            "/api/auth/dev_switch_to_parent/",
            data={"student_id": 1},
            format="json",
        )
        self.assertIn(
            response.status_code,
            [403, 404],
            msg=(
                f"Expected dev_switch_to_parent to be blocked (403/404) in production, "
                f"got {response.status_code}. "
                "The endpoint is currently open without a DEBUG guard."
            ),
        )


# ---------------------------------------------------------------------------
# Cross-user isolation
# ---------------------------------------------------------------------------

@override_settings(DEBUG=False)
class CrossUserIsolationTests(BaseAPITestCase):
    """
    Verify that authenticated users cannot access or mutate data belonging to
    other users.  Where the API currently lacks enforcement the test is marked
    with @unittest.expectedFailure so the suite still passes while clearly
    documenting the gap.
    """

    # -- /api/questions/record/ -----------------------------------------------

    def test_parent_cannot_record_for_other_parents_child(self):
        """
        Parent A's JWT must not be able to POST /api/questions/record/ for a
        student that belongs to Parent B.

        KNOWN GAP: the view does not check whether the authenticated user owns
        the student_id.  This test is marked expectedFailure to document the
        gap; remove the decorator once ownership validation is added.

        Setup: parent A + child A, parent B + child B.
        Action: authenticate as parent A, submit a record for child B.
        Expected: 403 or 400.
        """
        # Parent A and their child
        parent_a = make_user(role="parent")
        child_a = make_user(role="student")
        make_parent_child(parent=parent_a, student=child_a)
        make_student_profile(user=child_a)

        # Parent B and their child
        parent_b = make_user(role="parent")
        child_b = make_user(role="student")
        make_parent_child(parent=parent_b, student=child_b)
        make_student_profile(user=child_b)

        # A template is required for a well-formed request
        template = make_template()

        # Authenticate as parent A
        self.auth(parent_a)

        response = self.client.post(
            "/api/questions/record/",
            data={
                "student_id": child_b.id,
                "template_id": template.id,
                "params": {},
                "question_text": "Test question",
                "correct_answer": "4",
                "selected_answer": "4",
                "correct": True,
            },
            format="json",
        )

        self.assertIn(
            response.status_code,
            [400, 403],
            msg=(
                f"Parent A should not be able to record answers for Parent B's child, "
                f"but got HTTP {response.status_code}."
            ),
        )

    # -- /api/tutors/{id}/edit/ -----------------------------------------------

    def test_tutor_a_cannot_edit_tutor_b_profile(self):
        """
        Tutor A must not be able to PUT/POST /api/tutors/{tutor_b_id}/edit/.

        KNOWN GAP: TutorViewSet.edit does not verify that the requesting tutor
        matches the target pk.  Marked expectedFailure to document the gap.
        """
        tutor_a_user = make_user(role="tutor")
        make_tutor_profile(user=tutor_a_user)

        tutor_b_user = make_user(role="tutor")
        make_tutor_profile(user=tutor_b_user)

        self.auth(tutor_a_user)

        response = self.client.post(
            f"/api/tutors/{tutor_b_user.id}/edit/",
            data={"fields": {"first_name": "Hacked"}},
            format="json",
        )

        self.assertIn(
            response.status_code,
            [403, 404],
            msg=(
                f"Tutor A should not be able to edit Tutor B's profile, "
                f"but got HTTP {response.status_code}."
            ),
        )

    # -- DELETE /api/templates/{id}/ ------------------------------------------

    def test_unauthenticated_delete_template_denied(self):
        """
        Unauthenticated DELETE /api/templates/{id}/ must return 401 or 403.

        Currently fails because TemplateViewSet has permission_classes = [AllowAny],
        allowing anonymous deletions. This test documents the security gap.
        """
        template = make_template()

        # Ensure no credentials are sent
        self.unauth()

        response = self.client.delete(f"/api/templates/{template.id}/")

        self.assertIn(
            response.status_code,
            [401, 403],
            msg=(
                f"Unauthenticated DELETE /api/templates/{template.id}/ should be denied "
                f"(401/403), but got HTTP {response.status_code}. "
                "TemplateViewSet is currently AllowAny — consider restricting."
            ),
        )

    # -- GET /api/students/ ---------------------------------------------------

    def test_unauthenticated_list_students_denied(self):
        """
        Unauthenticated GET /api/students/ must return 401 or 403.

        KNOWN GAP: StudentViewSet uses AllowAny, so unauthenticated requests
        currently return 200.  Marked expectedFailure to document this.
        Remove the decorator once the view is restricted to authenticated users.
        """
        self.unauth()

        response = self.client.get("/api/students/")

        self.assertIn(
            response.status_code,
            [401, 403],
            msg=(
                f"Unauthenticated GET /api/students/ should be denied (401/403), "
                f"but got HTTP {response.status_code}. "
                "StudentViewSet is currently AllowAny."
            ),
        )


# ---------------------------------------------------------------------------
# Eval sandbox
# ---------------------------------------------------------------------------

@override_settings(DEBUG=False)
class EvalSandboxTests(BaseAPITestCase):
    """
    Verify that the template preview endpoint does not execute arbitrary code
    embedded in the content field.
    """

    def test_preview_with_import_os_does_not_crash_or_execute(self):
        """
        POST /api/templates/preview/ with content containing
        __import__('os').system('id') must not return 500 and must not
        execute shell commands.

        Currently fails because template_utilities._fix_parameters_indentation
        calls parsed.get() assuming YAML content is always a dict, crashing
        on plain-string content with AttributeError (500).
        """
        import unittest.mock as mock

        malicious_content = "__import__('os').system('id')"

        with mock.patch("os.system") as mock_system:
            mock_system.return_value = 0

            response = self.client.post(
                "/api/templates/preview/",
                data={"content": malicious_content},
                format="json",
            )

            self.assertNotEqual(
                response.status_code,
                500,
                msg=(
                    "POST /api/templates/preview/ with a malicious payload "
                    "must not crash the server (returned 500)."
                ),
            )

            mock_system.assert_not_called()

        # Also check the response body does not contain shell command output
        # (e.g. "uid=0(root)") in case the patch was bypassed somehow.
        response_text = response.content.decode("utf-8", errors="replace")
        self.assertNotIn(
            "uid=",
            response_text,
            msg=(
                "Response body contains 'uid=' which suggests shell command "
                "output was returned — the eval sandbox may not be effective."
            ),
        )
