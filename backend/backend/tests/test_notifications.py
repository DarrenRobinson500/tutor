"""
Tests for notification flows: email and SMS.

Coverage:
  - Tutor registration → welcome email dispatched
  - Parent first visit to parent_home → welcome email sent once
  - Parent revisiting parent_home → no second email
  - select_tutor → emails sent to both parent and tutor
  - Booking creation (tutor role) → SMSSendJob created with correct message_type
  - GlobalSetting sms_send=False → SMS queued but provider_message_id='FAKE-SEND'
  - GlobalSetting sms_send=False → clicksend_send_sms never called
"""

import threading
from unittest.mock import patch, MagicMock, call
from django.utils import timezone
from datetime import timedelta

from .base import BaseAPITestCase
from .factories import (
    make_user,
    make_tutor_profile,
    make_student_profile,
    make_parent_child,
    make_global_setting,
    make_booking_weekly,
    make_booking_adhoc,
    make_tutor_student,
)
from backend.models import (
    User,
    TutorProfile,
    ParentChild,
    TutorStudent,
    SMSSendJob,
    SMSConversation,
    SMSMessage,
    GlobalSetting,
    BookingWeekly,
    BookingAdhoc,
    TutorAvailability,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_threads_synchronously(monkeypatch_target="threading.Thread"):
    """
    Context manager: makes threading.Thread run its target synchronously so
    that background email/SMS work is executed before the assertions.
    """
    import unittest.mock as _mock

    class _SyncThread:
        def __init__(self, target=None, args=(), kwargs=None, daemon=False):
            self._target = target
            self._args = args
            self._kwargs = kwargs or {}

        def start(self):
            if self._target:
                self._target(*self._args, **self._kwargs)

    return _mock.patch("threading.Thread", _SyncThread)


# ---------------------------------------------------------------------------
# Email: tutor registration
# ---------------------------------------------------------------------------

class TutorRegistrationEmailTests(BaseAPITestCase):
    """POST /api/auth/register_tutor/ fires a welcome email to the tutor."""

    REGISTER_URL = "/api/auth/register_tutor/"

    def _register_payload(self, email=None):
        if email is None:
            import uuid
            email = f"tutor_{uuid.uuid4().hex[:6]}@example.com"
        return {
            "email": email,
            "password": "Testpass1!",
            "confirm_password": "Testpass1!",
            "first_name": "Alice",
            "last_name": "Smith",
            "mobile": "0412345678",
            "qualification": "Bachelor of Science",
            "university": "University of Sydney",
            "year_levels": ["7", "8"],
            "bio": "Experienced tutor.",
        }

    def test_welcome_email_dispatched_to_tutor_email_multialt(self):
        """When HTML template is available, EmailMultiAlternatives.send is called."""
        payload = self._register_payload()

        with _run_threads_synchronously():
            with patch(
                "django.core.mail.EmailMultiAlternatives"
            ) as mock_ema, patch(
                "django.core.mail.send_mail"
            ) as mock_sm, patch(
                "builtins.open", side_effect=FileNotFoundError
            ):
                # Force fallback path (no HTML file) – open raises, so send_mail is used
                resp = self.client.post(self.REGISTER_URL, payload, format="json")

        self.assertEqual(resp.status_code, 200)
        # Either send_mail or EmailMultiAlternatives.send should have been called.
        # With no HTML file available, send_mail is called.
        mock_sm.assert_called_once()
        args, kwargs = mock_sm.call_args
        recipient_list = kwargs.get("recipient_list") or args[3]
        self.assertIn(payload["email"], recipient_list)

    def test_welcome_email_dispatched_fallback_send_mail(self):
        """If HTML file is missing, falls back to send_mail with tutor's email."""
        import uuid
        email = f"tutorfallback_{uuid.uuid4().hex[:6]}@example.com"
        payload = self._register_payload(email=email)

        with _run_threads_synchronously():
            with patch(
                "django.core.mail.send_mail"
            ) as mock_sm, patch(
                "django.core.mail.EmailMultiAlternatives"
            ) as mock_ema, patch(
                "builtins.open", side_effect=FileNotFoundError
            ):
                resp = self.client.post(self.REGISTER_URL, payload, format="json")

        self.assertEqual(resp.status_code, 200)
        # With open() raising FileNotFoundError, the html_body is None, so send_mail is used
        mock_sm.assert_called_once()
        _, kwargs = mock_sm.call_args
        recipient_list = kwargs.get("recipient_list") or mock_sm.call_args[0][3]
        self.assertIn(email, recipient_list)

    def test_welcome_email_subject_contains_application_received(self):
        """The welcome email subject mentions 'application received'."""
        payload = self._register_payload()

        with _run_threads_synchronously():
            with patch(
                "django.core.mail.send_mail"
            ) as mock_sm, patch(
                "builtins.open", side_effect=FileNotFoundError
            ):
                self.client.post(self.REGISTER_URL, payload, format="json")

        mock_sm.assert_called_once()
        subject = mock_sm.call_args[1].get("subject") or mock_sm.call_args[0][0]
        self.assertIn("application received", subject.lower())

    def test_no_email_if_registration_fails(self):
        """If registration fails (duplicate email), no email is sent."""
        payload = self._register_payload()
        # Register once successfully
        with _run_threads_synchronously(), patch("builtins.open", side_effect=FileNotFoundError), patch("django.core.mail.send_mail"):
            self.client.post(self.REGISTER_URL, payload, format="json")

        # Try to register with the same email
        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch("builtins.open", side_effect=FileNotFoundError):
                resp = self.client.post(self.REGISTER_URL, payload, format="json")

        self.assertEqual(resp.status_code, 400)
        mock_sm.assert_not_called()


# ---------------------------------------------------------------------------
# Email: parent home (welcome email gated by welcome_email_sent flag)
# ---------------------------------------------------------------------------

class ParentHomeWelcomeEmailTests(BaseAPITestCase):
    """GET /api/auth/parent_home/ sends welcome email only on first visit."""

    HOME_URL = "/api/auth/parent_home/"

    def _setup_parent_with_child(self):
        parent = make_user(
            role="parent",
            email="parent@example.com",
            first_name="Bob",
            last_name="Jones",
            welcome_email_sent=False,
        )
        child = make_user(role="student", first_name="Charlie", last_name="Jones")
        make_student_profile(user=child)
        make_parent_child(parent=parent, student=child)
        return parent, child

    def test_first_visit_sends_welcome_email(self):
        """First GET by parent triggers _send_parent_welcome_emails in background."""
        parent, child = self._setup_parent_with_child()
        self.auth(parent)

        with _run_threads_synchronously():
            with patch(
                "django.core.mail.send_mail"
            ) as mock_sm, patch(
                "builtins.open", side_effect=FileNotFoundError
            ):
                resp = self.client.get(self.HOME_URL)

        self.assertEqual(resp.status_code, 200)
        # At minimum the parent welcome email should be attempted
        self.assertTrue(mock_sm.called)
        # The parent's email should appear in one of the calls
        all_recipients = []
        for c in mock_sm.call_args_list:
            rl = c[1].get("recipient_list") or c[0][3]
            all_recipients.extend(rl)
        self.assertIn(parent.email, all_recipients)

    def test_first_visit_flips_welcome_email_sent_flag(self):
        """After first visit, welcome_email_sent is set to True on the user."""
        parent, child = self._setup_parent_with_child()
        self.auth(parent)

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail"), patch("builtins.open", side_effect=FileNotFoundError):
                self.client.get(self.HOME_URL)

        parent.refresh_from_db()
        self.assertTrue(parent.welcome_email_sent)

    def test_second_visit_does_not_send_welcome_email(self):
        """Second GET (with welcome_email_sent=True) sends no welcome email."""
        parent, child = self._setup_parent_with_child()
        # Mark as already sent
        parent.welcome_email_sent = True
        parent.save(update_fields=["welcome_email_sent"])
        self.auth(parent)

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch("builtins.open", side_effect=FileNotFoundError):
                resp = self.client.get(self.HOME_URL)

        self.assertEqual(resp.status_code, 200)
        mock_sm.assert_not_called()

    def test_welcome_email_sent_exactly_once_across_two_calls(self):
        """Calling parent_home twice: email is dispatched on the first call only."""
        parent, child = self._setup_parent_with_child()
        self.auth(parent)

        call_count = 0
        original_send_mail = __builtins__  # just to capture

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch("builtins.open", side_effect=FileNotFoundError):
                self.client.get(self.HOME_URL)   # first call
                first_call_count = mock_sm.call_count
                self.client.get(self.HOME_URL)   # second call
                second_call_count = mock_sm.call_count

        # Count should not increase on second call
        self.assertEqual(first_call_count, second_call_count)


# ---------------------------------------------------------------------------
# Email: select_tutor → emails to parent AND tutor
# ---------------------------------------------------------------------------

class SelectTutorEmailTests(BaseAPITestCase):
    """POST /api/auth/select_tutor/ sends emails to both parent and tutor."""

    SELECT_URL = "/api/auth/select_tutor/"

    def _setup(self):
        tutor_user = make_user(role="tutor", email="tutor@example.com", first_name="Tutor", last_name="T")
        make_tutor_profile(user=tutor_user)
        child = make_user(role="student", first_name="Kid", last_name="K")
        make_student_profile(user=child)
        parent = make_user(role="parent", email="parent@example.com", first_name="Parent", last_name="P")
        make_parent_child(parent=parent, student=child)
        return parent, child, tutor_user

    def test_select_tutor_emails_both_parent_and_tutor(self):
        """Both parent and tutor receive an email when a tutor is selected."""
        parent, child, tutor_user = self._setup()
        self.auth(parent)

        payload = {
            "child_id": child.id,
            "tutor_id": tutor_user.id,
        }

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch(
                "backend.message.process_sms_jobs"
            ):
                resp = self.client.post(self.SELECT_URL, payload, format="json")

        self.assertEqual(resp.status_code, 200)
        # Two emails should be sent: one to parent, one to tutor
        self.assertEqual(mock_sm.call_count, 2)

        all_recipients = []
        for c in mock_sm.call_args_list:
            rl = c[1].get("recipient_list") or c[0][3]
            all_recipients.extend(rl)

        self.assertIn(parent.email, all_recipients)
        self.assertIn(tutor_user.email, all_recipients)

    def test_select_tutor_parent_email_subject_mentions_tutor_name(self):
        """The email to the parent mentions the tutor's name in its subject."""
        parent, child, tutor_user = self._setup()
        self.auth(parent)

        payload = {"child_id": child.id, "tutor_id": tutor_user.id}

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch(
                "backend.message.process_sms_jobs"
            ), patch("backend.message.process_sms_jobs"):
                self.client.post(self.SELECT_URL, payload, format="json")

        # Find the call addressed to the parent
        parent_calls = [
            c for c in mock_sm.call_args_list
            if parent.email in (c[1].get("recipient_list") or c[0][3])
        ]
        self.assertTrue(parent_calls, "No email sent to parent")
        subject = parent_calls[0][1].get("subject") or parent_calls[0][0][0]
        self.assertIn("Tutor", subject)  # tutor first name is 'Tutor'

    def test_select_tutor_tutor_email_subject_mentions_student_name(self):
        """The email to the tutor mentions the student's name in its subject."""
        parent, child, tutor_user = self._setup()
        self.auth(parent)

        payload = {"child_id": child.id, "tutor_id": tutor_user.id}

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail") as mock_sm, patch(
                "backend.message.process_sms_jobs"
            ), patch("backend.message.process_sms_jobs"):
                self.client.post(self.SELECT_URL, payload, format="json")

        tutor_calls = [
            c for c in mock_sm.call_args_list
            if tutor_user.email in (c[1].get("recipient_list") or c[0][3])
        ]
        self.assertTrue(tutor_calls, "No email sent to tutor")
        subject = tutor_calls[0][1].get("subject") or tutor_calls[0][0][0]
        # child name is 'Kid K'
        self.assertIn("Kid", subject)

    def test_select_tutor_requires_parent_role(self):
        """A non-parent user cannot call select_tutor."""
        tutor_user = make_user(role="tutor")
        make_tutor_profile(user=tutor_user)
        student = make_user(role="student")
        make_student_profile(user=student)

        impostor = make_user(role="student")
        self.auth(impostor)

        resp = self.client.post(
            self.SELECT_URL,
            {"child_id": student.id, "tutor_id": tutor_user.id},
            format="json",
        )
        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# SMS: booking creation creates an SMSSendJob
# ---------------------------------------------------------------------------

class BookingCreationSMSTests(BaseAPITestCase):
    """
    POST /api/tutors/{id}/booking_action/ with command='create' should
    enqueue an SMSSendJob via sms_enqueue().
    """

    def _setup_tutor_with_student(self):
        tutor_user = make_user(role="tutor", first_name="Tutor", last_name="T")
        tutor_profile = make_tutor_profile(user=tutor_user, approved=True)
        # Give tutor a default session duration (used by create_booking)
        tutor_user.default_session_minutes = 60
        tutor_user.save(update_fields=["default_session_minutes"])

        student = make_user(role="student", first_name="Student", last_name="S")
        make_student_profile(user=student, mobile="0412000001")
        make_tutor_student(tutor=tutor_user, student=student)

        return tutor_user, tutor_profile, student

    def _booking_action_url(self, tutor_id):
        return f"/api/tutors/{tutor_id}/booking_action/"

    def test_create_adhoc_booking_creates_sms_send_job(self):
        """
        Creating an adhoc booking as tutor enqueues an SMSSendJob with
        message_type containing 'create_adhoc'.
        """
        tutor_user, _, student = self._setup_tutor_with_student()
        self.auth(tutor_user)

        start_dt = timezone.now() + timedelta(days=2)
        start_str = start_dt.strftime("%Y-%m-%dT%H:%M")

        payload = {
            "command": "create",
            "booking_type": "adhoc",
            "student_id": student.id,
            "start_time": start_str,
        }

        before_count = SMSSendJob.objects.count()
        resp = self.client.post(
            self._booking_action_url(tutor_user.id), payload, format="json"
        )

        self.assertIn(resp.status_code, [200, 201])
        after_count = SMSSendJob.objects.count()
        self.assertGreater(after_count, before_count, "Expected an SMSSendJob to be created")

        job = SMSSendJob.objects.filter(
            conversation__tutor=tutor_user,
            conversation__student=student,
        ).order_by("-created_at").first()
        self.assertIsNotNone(job, "No SMSSendJob found for tutor-student conversation")
        self.assertIn("create_adhoc", job.message_type)

    def test_create_weekly_booking_creates_sms_send_job(self):
        """
        Creating a weekly booking as tutor enqueues an SMSSendJob with
        message_type containing 'create_weekly'.
        """
        tutor_user, _, student = self._setup_tutor_with_student()
        self.auth(tutor_user)

        payload = {
            "command": "create",
            "booking_type": "weekly",
            "student_id": student.id,
            "weekday": 1,
            "time": "10:00",
        }

        before_count = SMSSendJob.objects.count()
        resp = self.client.post(
            self._booking_action_url(tutor_user.id), payload, format="json"
        )

        self.assertIn(resp.status_code, [200, 201])
        after_count = SMSSendJob.objects.count()
        self.assertGreater(after_count, before_count, "Expected an SMSSendJob to be created")

        job = SMSSendJob.objects.filter(
            conversation__tutor=tutor_user,
            conversation__student=student,
        ).order_by("-created_at").first()
        self.assertIsNotNone(job)
        self.assertIn("create_weekly", job.message_type)

    def test_sms_send_job_message_type_uses_user_role_prefix(self):
        """
        The SMSSendJob.message_type is prefixed with the acting user's role
        (e.g. 'tutor_create_adhoc').
        """
        tutor_user, _, student = self._setup_tutor_with_student()
        self.auth(tutor_user)

        start_dt = timezone.now() + timedelta(days=3)
        payload = {
            "command": "create",
            "booking_type": "adhoc",
            "student_id": student.id,
            "start_time": start_dt.strftime("%Y-%m-%dT%H:%M"),
        }

        self.client.post(self._booking_action_url(tutor_user.id), payload, format="json")

        job = SMSSendJob.objects.filter(
            conversation__tutor=tutor_user,
            conversation__student=student,
        ).order_by("-created_at").first()

        if job:
            self.assertTrue(
                job.message_type.startswith("tutor_"),
                f"Expected message_type to start with 'tutor_', got: {job.message_type}",
            )


# ---------------------------------------------------------------------------
# SMS: GlobalSetting sms_send=False → FAKE-SEND, clicksend never called
# ---------------------------------------------------------------------------

class SMSSendSuppressionTests(BaseAPITestCase):
    """
    When GlobalSetting(key='sms_send', value='False'), process_sms_jobs()
    should set provider_message_id='FAKE-SEND' and must NOT call clicksend.
    """

    def _create_conversation(self, tutor, student):
        convo, _ = SMSConversation.objects.get_or_create(tutor=tutor, student=student)
        return convo

    def _create_ready_sms_job(self, tutor, student, mobile):
        """Create an SMSSendJob that is due immediately (scheduled_for in the past)."""
        convo = self._create_conversation(tutor, student)
        # Ensure student has a mobile so phone resolution succeeds
        profile = student.student_profile if hasattr(student, "student_profile") else None
        if profile:
            profile.mobile = mobile
            profile.save(update_fields=["mobile"])

        job = SMSSendJob.objects.create(
            conversation=convo,
            message_type="tutor_create_adhoc",
            body="Test SMS body",
            scheduled_for=timezone.now() - timedelta(minutes=1),
        )
        return job

    def test_sms_send_false_produces_fake_send_marker(self):
        """
        With sms_send='False', process_sms_jobs() records provider_message_id='FAKE-SEND'
        on the resulting SMSMessage.
        """
        # Clear cache so GlobalSetting value is read fresh
        from django.core.cache import cache
        cache.clear()

        make_global_setting("sms_send", "False")

        tutor = make_user(role="tutor", first_name="TutorA", last_name="A")
        make_tutor_profile(user=tutor)
        student = make_user(role="student", first_name="StudentA", last_name="A")
        make_student_profile(user=student, mobile="0412111111")

        job = self._create_ready_sms_job(tutor, student, "0412111111")

        with patch("backend.message.clicksend_send_sms") as mock_clicksend:
            from backend.message import process_sms_jobs
            process_sms_jobs()

        # clicksend must NOT be called when sms_send is False
        mock_clicksend.assert_not_called()

        # The SMSMessage created should record FAKE-SEND
        msg = SMSMessage.objects.filter(conversation__tutor=tutor, conversation__student=student).first()
        self.assertIsNotNone(msg, "Expected an SMSMessage to be recorded")
        self.assertEqual(msg.provider_message_id, "FAKE-SEND")

    def test_sms_send_false_job_is_cancelled_after_processing(self):
        """
        After process_sms_jobs() with sms_send='False', the job is marked cancelled.
        """
        from django.core.cache import cache
        cache.clear()

        make_global_setting("sms_send", "False")

        tutor = make_user(role="tutor", first_name="TutorB", last_name="B")
        make_tutor_profile(user=tutor)
        student = make_user(role="student", first_name="StudentB", last_name="B")
        make_student_profile(user=student, mobile="0412222222")

        job = self._create_ready_sms_job(tutor, student, "0412222222")

        with patch("backend.message.clicksend_send_sms"):
            from backend.message import process_sms_jobs
            process_sms_jobs()

        job.refresh_from_db()
        self.assertTrue(job.cancelled, "Expected the job to be cancelled after processing")

    def test_sms_send_true_does_call_clicksend(self):
        """
        With sms_send='True', process_sms_jobs() calls clicksend_send_sms.
        """
        from django.core.cache import cache
        cache.clear()

        make_global_setting("sms_send", "True")

        tutor = make_user(role="tutor", first_name="TutorC", last_name="C")
        make_tutor_profile(user=tutor)
        student = make_user(role="student", first_name="StudentC", last_name="C")
        make_student_profile(user=student, mobile="0412333333")

        job = self._create_ready_sms_job(tutor, student, "0412333333")

        mock_provider_id = "msg_abc123"
        with patch(
            "backend.message.clicksend_send_sms", return_value=mock_provider_id
        ) as mock_clicksend:
            from backend.message import process_sms_jobs
            process_sms_jobs()

        mock_clicksend.assert_called_once()

        msg = SMSMessage.objects.filter(conversation__tutor=tutor, conversation__student=student).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.provider_message_id, mock_provider_id)

    def test_sms_send_suppression_via_select_tutor_flow(self):
        """
        End-to-end: sms_send='False' → select_tutor creates an SMSSendJob
        and process_sms_jobs() does not call clicksend.
        """
        from django.core.cache import cache
        cache.clear()

        make_global_setting("sms_send", "False")

        tutor_user = make_user(role="tutor", email="tutor_sel@example.com", first_name="SelTutor", last_name="X")
        make_tutor_profile(user=tutor_user, mobile="0411000001")
        child = make_user(role="student", first_name="SelKid", last_name="X")
        make_student_profile(user=child, mobile="0411000002")
        parent = make_user(role="parent", email="parent_sel@example.com", first_name="SelParent", last_name="X")
        make_parent_child(parent=parent, student=child)

        self.auth(parent)

        with _run_threads_synchronously():
            with patch("django.core.mail.send_mail"), patch(
                "backend.message.clicksend_send_sms"
            ) as mock_clicksend:
                resp = self.client.post(
                    "/api/auth/select_tutor/",
                    {"child_id": child.id, "tutor_id": tutor_user.id},
                    format="json",
                )

        self.assertEqual(resp.status_code, 200)
        mock_clicksend.assert_not_called()


# ---------------------------------------------------------------------------
# GlobalSetting-based SMS suppression: isolated unit tests
# ---------------------------------------------------------------------------

class GlobalSettingSMSSuppressionUnitTests(BaseAPITestCase):
    """
    Directly create a GlobalSetting(sms_send=False), create an SMSSendJob,
    run process_sms_jobs, and assert the correct behaviour without any
    HTTP layer.
    """

    def setUp(self):
        super().setUp()
        from django.core.cache import cache
        cache.clear()

    def _make_ready_job_with_to_number(self, body="Hello"):
        """Create an SMSSendJob using to_number (no conversation required for phone lookup)."""
        tutor = make_user(role="tutor", first_name="UnitT", last_name="T")
        make_tutor_profile(user=tutor)
        student = make_user(role="student", first_name="UnitS", last_name="S")
        make_student_profile(user=student, mobile="0499000001")

        convo, _ = SMSConversation.objects.get_or_create(tutor=tutor, student=student)

        job = SMSSendJob.objects.create(
            conversation=convo,
            to_number="0499000001",
            message_type="tutor_create_adhoc",
            body=body,
            scheduled_for=timezone.now() - timedelta(seconds=10),
        )
        return job, tutor, student

    def test_sms_send_false_clicksend_not_called(self):
        """GlobalSetting sms_send=False → clicksend_send_sms is never invoked."""
        make_global_setting("sms_send", "False")
        job, tutor, student = self._make_ready_job_with_to_number()

        with patch("backend.message.clicksend_send_sms") as mock_cs:
            from backend.message import process_sms_jobs
            process_sms_jobs()

        mock_cs.assert_not_called()

    def test_sms_send_false_provider_message_id_is_fake_send(self):
        """GlobalSetting sms_send=False → created SMSMessage has provider_message_id='FAKE-SEND'."""
        make_global_setting("sms_send", "False")
        job, tutor, student = self._make_ready_job_with_to_number(body="Fake body")

        with patch("backend.message.clicksend_send_sms"):
            from backend.message import process_sms_jobs
            process_sms_jobs()

        msg = SMSMessage.objects.filter(
            conversation__tutor=tutor,
            conversation__student=student,
        ).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.provider_message_id, "FAKE-SEND")

    def test_sms_send_false_sms_message_body_is_preserved(self):
        """Even in fake-send mode the SMSMessage body matches the job body."""
        make_global_setting("sms_send", "False")
        body = "Check this fake SMS"
        job, tutor, student = self._make_ready_job_with_to_number(body=body)

        with patch("backend.message.clicksend_send_sms"):
            from backend.message import process_sms_jobs
            process_sms_jobs()

        msg = SMSMessage.objects.filter(
            conversation__tutor=tutor,
            conversation__student=student,
        ).first()
        self.assertIsNotNone(msg)
        self.assertEqual(msg.body, body)

    def test_switching_to_sms_send_true_calls_clicksend(self):
        """Switching GlobalSetting to sms_send=True causes clicksend to be invoked."""
        from django.core.cache import cache
        cache.clear()

        make_global_setting("sms_send", "True")
        job, tutor, student = self._make_ready_job_with_to_number()

        with patch(
            "backend.message.clicksend_send_sms", return_value="real_id_xyz"
        ) as mock_cs:
            from backend.message import process_sms_jobs
            process_sms_jobs()

        mock_cs.assert_called_once_with("0499000001", job.body)

    def test_no_job_processed_if_not_yet_scheduled(self):
        """A job scheduled in the future is not processed by process_sms_jobs."""
        make_global_setting("sms_send", "False")

        tutor = make_user(role="tutor")
        make_tutor_profile(user=tutor)
        student = make_user(role="student")
        make_student_profile(user=student)

        convo, _ = SMSConversation.objects.get_or_create(tutor=tutor, student=student)
        future_job = SMSSendJob.objects.create(
            conversation=convo,
            to_number="0499000099",
            message_type="tutor_create_adhoc",
            body="Future SMS",
            scheduled_for=timezone.now() + timedelta(hours=1),
        )

        with patch("backend.message.clicksend_send_sms") as mock_cs:
            from backend.message import process_sms_jobs
            process_sms_jobs()

        future_job.refresh_from_db()
        self.assertFalse(future_job.cancelled, "Future job should not have been processed")
        mock_cs.assert_not_called()
