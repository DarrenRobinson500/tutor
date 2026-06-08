"""
Tests for backend/tasks.py Celery tasks.

tasks.py defines four @shared_task functions that are tested here by calling
them directly (not via .delay()) so no broker is required:

    create_post_session_jobs      – creates TutorJob(post_tuition_review) after sessions end
    send_session_reminders        – creates SMSSendJob ~24 h before a booking starts
    flag_overdue_tutor_reviews    – creates AdminJob when a review is 2+ days old
    record_weekly_progress_snapshots – snapshots student progress once per week
"""

import unittest
from datetime import timedelta
from unittest.mock import patch

from django.test import TestCase, override_settings
from django.utils import timezone


# ---------------------------------------------------------------------------
# Helper factory functions
# ---------------------------------------------------------------------------

def _make_tutor(username="tutor1"):
    from django.contrib.auth import get_user_model
    User = get_user_model()
    return User.objects.create_user(
        username=username,
        password="pass",
        role="tutor",
        first_name="Tom",
        last_name="Tutor",
    )


def _make_student(username="student1", mobile="0412345678"):
    from django.contrib.auth import get_user_model
    from backend.models import StudentProfile
    User = get_user_model()
    user = User.objects.create_user(
        username=username,
        password="pass",
        role="student",
        first_name="Sally",
        last_name="Student",
    )
    # StudentProfile is expected by send_session_reminders via student.student_profile.mobile
    profile, _ = StudentProfile.objects.get_or_create(user=user)
    profile.mobile = mobile
    profile.save()
    return user


def _make_tutor_student_link(tutor, student):
    from backend.models import TutorStudent
    link, _ = TutorStudent.objects.get_or_create(tutor=tutor, student=student)
    return link


def _make_adhoc_booking(tutor, student, start_dt, duration_minutes=60):
    from backend.models import BookingAdhoc
    return BookingAdhoc.objects.create(
        tutor=tutor,
        student=student,
        start_datetime=start_dt,
        end_datetime=start_dt + timedelta(minutes=duration_minutes),
        status="confirmed",
    )


def _make_tutor_job(tutor, student, job_type, booking_ref=None, triggered_at=None):
    from backend.models import TutorJob
    now = timezone.now()
    return TutorJob.objects.create(
        tutor=tutor,
        student=student,
        job_type=job_type,
        booking_ref=booking_ref,
        triggered_at=triggered_at or now,
        expires_at=now + timedelta(days=14),
    )


# ---------------------------------------------------------------------------
# 1. Post-session job creation  (create_post_session_jobs)
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestCreatePostSessionJobs(TestCase):
    """
    create_post_session_jobs finds BookingAdhoc records whose end_datetime
    falls in the last 24 hours and creates TutorJob(post_tuition_review).
    """

    def setUp(self):
        self.tutor = _make_tutor("tutor_ps")
        self.student = _make_student("student_ps")

    @patch("backend.tasks._snapshot_student_progress")
    def test_ended_1h_ago_creates_tutor_job(self, mock_snap):
        """A booking that ended 1 hour ago → TutorJob created."""
        from backend.models import TutorJob
        from backend.tasks import create_post_session_jobs

        now = timezone.now()
        start = now - timedelta(hours=2)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start, duration_minutes=60)

        create_post_session_jobs()

        job = TutorJob.objects.filter(
            tutor=self.tutor,
            student=self.student,
            job_type="post_tuition_review",
        ).first()
        self.assertIsNotNone(job, "Expected a TutorJob(post_tuition_review) to be created")
        mock_snap.assert_called_once()

    @patch("backend.tasks._snapshot_student_progress")
    def test_ended_25h_ago_no_job(self, mock_snap):
        """A booking that ended 25 hours ago is outside the 24-hour window → no job."""
        from backend.models import TutorJob
        from backend.tasks import create_post_session_jobs

        now = timezone.now()
        start = now - timedelta(hours=26)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start, duration_minutes=60)

        create_post_session_jobs()

        count = TutorJob.objects.filter(
            tutor=self.tutor,
            student=self.student,
            job_type="post_tuition_review",
        ).count()
        self.assertEqual(count, 0, "No TutorJob should be created for booking outside window")
        mock_snap.assert_not_called()

    @patch("backend.tasks._snapshot_student_progress")
    def test_idempotent_no_duplicate_job(self, mock_snap):
        """Running the task twice for the same booking creates only one TutorJob."""
        from backend.models import TutorJob
        from backend.tasks import create_post_session_jobs

        now = timezone.now()
        start = now - timedelta(hours=2)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start, duration_minutes=60)

        create_post_session_jobs()
        create_post_session_jobs()

        count = TutorJob.objects.filter(
            tutor=self.tutor,
            student=self.student,
            job_type="post_tuition_review",
        ).count()
        self.assertEqual(count, 1, "Running the task twice must not create duplicate TutorJobs")
        # Snapshot should only be called once (only on creation)
        self.assertEqual(mock_snap.call_count, 1)

    @patch("backend.tasks._snapshot_student_progress")
    def test_booking_outcome_linked_to_job(self, mock_snap):
        """The TutorJob created for a post-session review has a linked BookingOutcome."""
        from backend.models import TutorJob
        from backend.tasks import create_post_session_jobs

        now = timezone.now()
        start = now - timedelta(hours=2)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start, duration_minutes=60)

        create_post_session_jobs()

        job = TutorJob.objects.get(
            tutor=self.tutor,
            student=self.student,
            job_type="post_tuition_review",
        )
        self.assertIsNotNone(job.booking_outcome, "TutorJob should have a linked BookingOutcome")


# ---------------------------------------------------------------------------
# 2. SMS reminder jobs  (send_session_reminders)
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestSendSessionReminders(TestCase):
    """
    send_session_reminders queues an SMSSendJob for students whose booking
    starts in 23–25 hours from now.
    """

    def setUp(self):
        self.tutor = _make_tutor("tutor_sms")
        self.student = _make_student("student_sms", mobile="0411222333")
        from backend.models import TutorProfile
        TutorProfile.objects.get_or_create(tutor=self.tutor)

    def test_booking_in_24h_creates_sms_job(self):
        """BookingAdhoc starting in ~24 hours → SMSSendJob created."""
        from backend.models import SMSSendJob
        from backend.tasks import send_session_reminders

        now = timezone.now()
        start = now + timedelta(hours=24)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start)

        send_session_reminders()

        count = SMSSendJob.objects.filter(
            message_type__startswith="reminder_24h_adhoc_"
        ).count()
        self.assertEqual(count, 1, "Expected one SMSSendJob for the upcoming booking")

    def test_idempotent_no_duplicate_sms_job(self):
        """Running the task twice for the same booking creates only one SMSSendJob."""
        from backend.models import SMSSendJob
        from backend.tasks import send_session_reminders

        now = timezone.now()
        start = now + timedelta(hours=24)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start)

        send_session_reminders()
        send_session_reminders()

        count = SMSSendJob.objects.filter(
            message_type__startswith="reminder_24h_adhoc_"
        ).count()
        self.assertEqual(count, 1, "Running the task twice must not create duplicate SMSSendJobs")

    def test_no_mobile_no_sms_job(self):
        """Student with no mobile number → no SMSSendJob created."""
        from backend.models import SMSSendJob, StudentProfile
        from backend.tasks import send_session_reminders

        # Remove mobile from student profile
        profile = StudentProfile.objects.get(user=self.student)
        profile.mobile = None
        profile.save()

        now = timezone.now()
        start = now + timedelta(hours=24)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start)

        send_session_reminders()

        count = SMSSendJob.objects.filter(
            message_type__startswith="reminder_24h_adhoc_"
        ).count()
        self.assertEqual(count, 0, "No SMSSendJob should be created for a student with no mobile")

    def test_booking_too_far_away_no_sms_job(self):
        """Booking starting in 30 hours is outside the 23–25 h window → no job."""
        from backend.models import SMSSendJob
        from backend.tasks import send_session_reminders

        now = timezone.now()
        start = now + timedelta(hours=30)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start)

        send_session_reminders()

        count = SMSSendJob.objects.filter(
            message_type__startswith="reminder_24h_adhoc_"
        ).count()
        self.assertEqual(count, 0, "Booking outside window should not produce an SMSSendJob")

    def test_booking_too_soon_no_sms_job(self):
        """Booking starting in 1 hour is inside the past side of the window → no job."""
        from backend.models import SMSSendJob
        from backend.tasks import send_session_reminders

        now = timezone.now()
        start = now + timedelta(hours=1)
        _make_adhoc_booking(self.tutor, self.student, start_dt=start)

        send_session_reminders()

        count = SMSSendJob.objects.filter(
            message_type__startswith="reminder_24h_adhoc_"
        ).count()
        self.assertEqual(count, 0, "Booking starting in 1 h is outside the reminder window")


# ---------------------------------------------------------------------------
# 3. Overdue review flagging  (flag_overdue_tutor_reviews)
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestFlagOverdueTutorReviews(TestCase):
    """
    flag_overdue_tutor_reviews creates an AdminJob(call_tutor_overdue_review)
    when a TutorJob(post_tuition_review) has been incomplete for 2+ days.
    """

    def setUp(self):
        self.tutor = _make_tutor("tutor_overdue")
        self.student = _make_student("student_overdue")

    def test_3_day_old_incomplete_review_creates_admin_job(self):
        """TutorJob not completed after 3 days → AdminJob created."""
        from backend.models import AdminJob
        from backend.tasks import flag_overdue_tutor_reviews

        triggered_at = timezone.now() - timedelta(days=3)
        job = _make_tutor_job(
            self.tutor, self.student, "post_tuition_review",
            triggered_at=triggered_at,
        )
        # Force triggered_at backward (auto_now_add prevents setting it in create)
        from backend.models import TutorJob
        TutorJob.objects.filter(pk=job.pk).update(triggered_at=triggered_at)

        flag_overdue_tutor_reviews()

        admin_job = AdminJob.objects.filter(
            job_type="call_tutor_overdue_review",
            subject=self.tutor,
        ).first()
        self.assertIsNotNone(admin_job, "Expected an AdminJob for the overdue tutor review")
        self.assertIn(f"tutor_job_id:{job.id}", admin_job.notes)

    def test_fresh_incomplete_review_no_admin_job(self):
        """TutorJob that is only 1 hour old → no AdminJob."""
        from backend.models import AdminJob
        from backend.tasks import flag_overdue_tutor_reviews

        job = _make_tutor_job(self.tutor, self.student, "post_tuition_review")

        flag_overdue_tutor_reviews()

        count = AdminJob.objects.filter(
            job_type="call_tutor_overdue_review",
            subject=self.tutor,
        ).count()
        self.assertEqual(count, 0, "A fresh TutorJob should not trigger an AdminJob")

    def test_completed_review_no_admin_job(self):
        """TutorJob completed 3 days ago → no AdminJob."""
        from backend.models import TutorJob, AdminJob
        from backend.tasks import flag_overdue_tutor_reviews

        triggered_at = timezone.now() - timedelta(days=3)
        job = _make_tutor_job(
            self.tutor, self.student, "post_tuition_review",
            triggered_at=triggered_at,
        )
        TutorJob.objects.filter(pk=job.pk).update(
            triggered_at=triggered_at,
            completed_at=timezone.now() - timedelta(days=1),
        )

        flag_overdue_tutor_reviews()

        count = AdminJob.objects.filter(
            job_type="call_tutor_overdue_review",
            subject=self.tutor,
        ).count()
        self.assertEqual(count, 0, "A completed review should not trigger an AdminJob")

    def test_idempotent_no_duplicate_admin_job(self):
        """Running the task twice for the same overdue review creates only one AdminJob."""
        from backend.models import TutorJob, AdminJob
        from backend.tasks import flag_overdue_tutor_reviews

        triggered_at = timezone.now() - timedelta(days=3)
        job = _make_tutor_job(
            self.tutor, self.student, "post_tuition_review",
            triggered_at=triggered_at,
        )
        TutorJob.objects.filter(pk=job.pk).update(triggered_at=triggered_at)

        flag_overdue_tutor_reviews()
        flag_overdue_tutor_reviews()

        count = AdminJob.objects.filter(
            job_type="call_tutor_overdue_review",
            subject=self.tutor,
        ).count()
        self.assertEqual(count, 1, "Running the task twice must not create duplicate AdminJobs")


# ---------------------------------------------------------------------------
# 4. Weekly progress snapshots  (record_weekly_progress_snapshots)
# ---------------------------------------------------------------------------

@override_settings(CELERY_TASK_ALWAYS_EAGER=True)
class TestRecordWeeklyProgressSnapshots(TestCase):
    """
    record_weekly_progress_snapshots creates a WeeklyProgressSnapshot for
    every active student that does not already have one this week.
    """

    def setUp(self):
        self.student = _make_student("student_snap")
        # Give the student a year_level so _snapshot_student_progress can compute a grade
        from backend.models import StudentProfile
        profile = StudentProfile.objects.get(user=self.student)
        profile.year_level = "Year 7"
        profile.save()

    @patch("backend.tasks._snapshot_student_progress")
    def test_active_student_no_snapshot_this_week_creates_snapshot(self, mock_snap):
        """Active student with no snapshot this week → _snapshot_student_progress called."""
        from backend.tasks import record_weekly_progress_snapshots

        record_weekly_progress_snapshots()

        mock_snap.assert_called_once_with(self.student, "scheduled")

    @patch("backend.tasks._snapshot_student_progress")
    def test_idempotent_existing_snapshot_skipped(self, mock_snap):
        """
        If a snapshot already exists for this week, running the task again
        must not create another one.
        """
        from backend.models import WeeklyProgressSnapshot
        from backend.tasks import record_weekly_progress_snapshots

        # Manually create a snapshot that falls in the current week
        WeeklyProgressSnapshot.objects.create(
            student=self.student,
            score=72.5,
            source="scheduled",
        )

        record_weekly_progress_snapshots()

        mock_snap.assert_not_called()

    @patch("backend.tasks._snapshot_student_progress")
    def test_inactive_student_skipped(self, mock_snap):
        """Inactive student → not snapshotted."""
        from django.contrib.auth import get_user_model
        from backend.tasks import record_weekly_progress_snapshots

        User = get_user_model()
        User.objects.filter(pk=self.student.pk).update(active=False)

        record_weekly_progress_snapshots()

        # _snapshot_student_progress should not be called for the inactive student
        for call_args in mock_snap.call_args_list:
            self.assertNotEqual(
                call_args[0][0].pk, self.student.pk,
                "Inactive student should not be snapshotted",
            )

    @patch("backend.tasks._snapshot_student_progress")
    def test_snapshot_from_previous_week_triggers_new_snapshot(self, mock_snap):
        """A snapshot from last week does not count — a fresh one should be created."""
        from backend.models import WeeklyProgressSnapshot
        from backend.tasks import record_weekly_progress_snapshots

        # Create a snapshot dated before Monday of the current week
        old_snap = WeeklyProgressSnapshot.objects.create(
            student=self.student,
            score=60.0,
            source="scheduled",
        )
        # Push recorded_at back 8 days so it is definitely in a prior week
        WeeklyProgressSnapshot.objects.filter(pk=old_snap.pk).update(
            recorded_at=timezone.now() - timedelta(days=8)
        )

        record_weekly_progress_snapshots()

        mock_snap.assert_called_once_with(self.student, "scheduled")
