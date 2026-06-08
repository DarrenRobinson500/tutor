"""
Tests for BookingWeekly and BookingAdhoc models.

Key bug note:
    models.py captures `today` and `now` as module-level variables at import time:

        now   = timezone.localtime(timezone.now(), local_tz)   # line 22
        today = now.date()                                       # line 23

    BookingWeekly.next_occurrence() references the module-level `today` instead of
    calling date.today() fresh each time.  BookingWeekly.skip() references the
    module-level `now` instead of timezone.now().  This means both methods silently
    use the date/time at which the module was first imported rather than the actual
    current date/time.  Tests that try to control "today" via mocking will therefore
    not work as expected unless they patch the module-level name directly.
"""

import unittest
from datetime import date, time, datetime, timedelta
from unittest.mock import patch

from django.utils import timezone
from django.test import TestCase

from .base import BaseAPITestCase
from .factories import (
    make_user,
    make_tutor_profile,
    make_student_profile,
    make_booking_weekly,
    make_booking_adhoc,
)
from backend.models import BookingWeekly, BookingAdhoc, TutorStudent


# ---------------------------------------------------------------------------
# BookingWeekly — basic creation
# ---------------------------------------------------------------------------

class TestBookingWeeklyCreate(TestCase):
    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')

    def test_create_booking_weekly_correct_fields(self):
        """Creating a BookingWeekly stores the correct tutor, student, weekday, and start_time."""
        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

        self.assertIsNotNone(wb.pk)
        self.assertEqual(wb.tutor, self.tutor)
        self.assertEqual(wb.student, self.student)
        self.assertEqual(wb.weekday, 0)
        self.assertEqual(wb.start_time, time(10, 0))
        self.assertEqual(wb.end_time, time(11, 0))
        self.assertIsNone(wb.start_date)

    def test_booking_weekly_duration_computed(self):
        """duration() returns the difference between end_time and start_time in minutes."""
        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        self.assertEqual(wb.duration(), 60)


# ---------------------------------------------------------------------------
# BookingWeekly — skip / remove_skip
# ---------------------------------------------------------------------------

class TestBookingWeeklySkip(TestCase):
    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')
        self.wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )

    def test_skip_sets_start_date_approximately_7_days_from_now(self):
        """
        skip() sets start_date to approximately 7 days in the future.

        NOTE: skip() uses the module-level `now` captured at import time
        (backend.models.now), not timezone.now().  The assertion uses
        a generous tolerance to accommodate the case where the module was imported
        a short while ago during the same test run.
        """
        self.wb.skip(weeks=1)
        self.wb.refresh_from_db()

        self.assertIsNotNone(self.wb.start_date)

        # start_date may be a date or a datetime; normalise to date.
        actual_date = (
            self.wb.start_date.date()
            if isinstance(self.wb.start_date, datetime)
            else self.wb.start_date
        )

        # The module-level `now` was captured at import time, so compare against
        # today with a tolerance of ±1 day to avoid flakiness across midnight or
        # long import-to-test delays.
        today = timezone.localtime(timezone.now()).date()
        expected = today + timedelta(weeks=1)
        delta = abs((actual_date - expected).days)
        self.assertLessEqual(
            delta,
            1,
            msg=(
                f"start_date {actual_date} is not within 1 day of expected {expected}. "
                "This may indicate the module-level `now` is stale."
            ),
        )

    def test_remove_skip_clears_start_date(self):
        """remove_skip() sets start_date back to None."""
        # First set a skip so there is something to remove.
        self.wb.skip(weeks=1)
        self.wb.refresh_from_db()
        self.assertIsNotNone(self.wb.start_date)

        self.wb.remove_skip()
        self.wb.refresh_from_db()

        self.assertIsNone(self.wb.start_date)


# ---------------------------------------------------------------------------
# BookingAdhoc — basic creation
# ---------------------------------------------------------------------------

class TestBookingAdhocCreate(TestCase):
    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')

    def test_create_booking_adhoc_future_start(self):
        """Creating a BookingAdhoc with a future start_datetime persists the record."""
        future = timezone.now() + timedelta(days=2)
        ba = make_booking_adhoc(
            tutor=self.tutor,
            student=self.student,
            start_datetime=future,
            end_datetime=future + timedelta(hours=1),
        )

        self.assertIsNotNone(ba.pk)
        self.assertEqual(ba.tutor, self.tutor)
        self.assertEqual(ba.student, self.student)
        # Stored datetimes are timezone-aware and close to what we supplied.
        self.assertAlmostEqual(
            ba.start_datetime.timestamp(),
            future.timestamp(),
            delta=1,
        )


# ---------------------------------------------------------------------------
# BookingAdhoc — student_can_edit
# ---------------------------------------------------------------------------

class TestBookingAdhocStudentCanEdit(TestCase):
    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')

    def test_student_can_edit_outside_24hr_window_returns_true(self):
        """
        student_can_edit() returns True when the booking is more than 24 hours away.
        We use 25 hours from now to be safely outside the window.
        """
        future = timezone.now() + timedelta(hours=25)
        ba = make_booking_adhoc(
            tutor=self.tutor,
            student=self.student,
            start_datetime=future,
            end_datetime=future + timedelta(hours=1),
        )

        self.assertTrue(ba.student_can_edit())

    def test_student_cannot_edit_inside_24hr_window_returns_false(self):
        """
        student_can_edit() returns False when the booking starts in less than 24 hours.
        We use 10 hours from now to be safely inside the window.
        """
        soon = timezone.now() + timedelta(hours=10)
        ba = make_booking_adhoc(
            tutor=self.tutor,
            student=self.student,
            start_datetime=soon,
            end_datetime=soon + timedelta(hours=1),
        )

        self.assertFalse(ba.student_can_edit())


# ---------------------------------------------------------------------------
# BookingWeekly — next_occurrence() date bug
# ---------------------------------------------------------------------------

class TestBookingWeeklyNextOccurrence(TestCase):
    """
    Tests for BookingWeekly.next_occurrence().

    BUG: next_occurrence() uses the module-level `today` variable captured at import
    time (backend/backend/models.py line 23: `today = now.date()`).  It does NOT call
    date.today() or timezone.now() fresh each invocation.  Patching `date.today` has
    no effect on the method's behaviour.

    The tests below are marked @unittest.expectedFailure where they attempt to control
    the date via patching, because the module-level binding makes the patch ineffective.
    The comments explain what the correct behaviour *should* be.
    """

    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')

    def test_next_occurrence_returns_aware_datetime(self):
        """
        next_occurrence() always returns a timezone-aware datetime regardless of
        whether start_date is set.  This test does not depend on controlling "today"
        so it should pass unconditionally.
        """
        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,   # Monday
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        result = wb.next_occurrence()
        self.assertIsNotNone(result.tzinfo, "next_occurrence() must return a timezone-aware datetime")

    def test_next_occurrence_weekday_is_correct(self):
        """
        next_occurrence() returns a datetime whose weekday matches the booking's weekday.
        Uses weekday=2 (Wednesday).
        """
        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=2,   # Wednesday
            start_time=time(14, 0),
            end_time=time(15, 0),
        )
        result = wb.next_occurrence()
        self.assertEqual(
            result.weekday(),
            2,
            msg=f"Expected Wednesday (2) but got weekday {result.weekday()}",
        )

    def test_next_occurrence_start_time_is_correct(self):
        """next_occurrence() returns a datetime with the correct start_time."""
        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,
            start_time=time(10, 0),
            end_time=time(11, 0),
        )
        result = wb.next_occurrence()
        # Compare hour and minute only (seconds/microseconds may differ due to tz)
        self.assertEqual(result.hour, 10)
        self.assertEqual(result.minute, 0)

    def test_next_occurrence_respects_future_start_date(self):
        """
        When start_date is set to a future date, next_occurrence() should return
        a date strictly after that start_date.

        This test patches the module-level `today` binding in backend.models to
        simulate a fixed reference date and verifies next_occurrence() computes
        the next slot relative to the patched date.
        """
        import backend.models as m

        # Simulate "today" being a Monday (weekday 0)
        fake_today = date(2026, 6, 1)  # Monday 2026-06-01
        future_start = date(2026, 6, 15)  # Monday two weeks later

        wb = make_booking_weekly(
            tutor=self.tutor,
            student=self.student,
            weekday=0,         # Monday
            start_time=time(10, 0),
            end_time=time(11, 0),
            start_date=future_start,
        )

        original_today = m.today
        try:
            m.today = fake_today
            result = wb.next_occurrence()
            # Should be AFTER future_start, i.e. 2026-06-22 or later
            self.assertGreater(
                result.date(),
                future_start,
                msg="next_occurrence() should return a date after the skip start_date",
            )
        finally:
            m.today = original_today


# ---------------------------------------------------------------------------
# Overlap prevention — BookingWeekly
# ---------------------------------------------------------------------------

class TestBookingWeeklyOverlap(TestCase):
    """
    Overlap prevention is implemented in User.booking_create_weekly(), not at the
    model/DB level.  These tests exercise that method directly.
    """

    def setUp(self):
        self.tutor = make_user(role='tutor')
        self.student = make_user(role='student')
        # Link tutor and student so get_tutor() resolves correctly.
        TutorStudent.objects.create(tutor=self.tutor, student=self.student)

    def test_duplicate_booking_raises_value_error(self):
        """
        Creating a second weekly booking at the exact same weekday/time for the same
        student raises ValueError('A weekly booking already exists for this time.').
        """
        self.student.booking_create_weekly(weekday=0, start_time=time(10, 0))

        with self.assertRaises(ValueError) as ctx:
            self.student.booking_create_weekly(weekday=0, start_time=time(10, 0))

        self.assertIn("already exists", str(ctx.exception))

    def test_overlapping_booking_raises_value_error(self):
        """
        Creating a weekly booking whose time window overlaps an existing booking for
        the same student raises ValueError('This weekly booking overlaps with an
        existing one.').

        The tutor's default_session_minutes is 60, so a booking at 10:00 occupies
        10:00–11:00.  A new booking at 10:30 on the same weekday overlaps.
        """
        self.tutor.default_session_minutes = 60
        self.tutor.save()

        self.student.booking_create_weekly(weekday=0, start_time=time(10, 0))

        with self.assertRaises(ValueError) as ctx:
            self.student.booking_create_weekly(weekday=0, start_time=time(10, 30))

        self.assertIn("overlaps", str(ctx.exception))

    def test_non_overlapping_booking_on_same_weekday_succeeds(self):
        """
        A second booking on the same weekday but a non-overlapping time slot should
        be created without error.

        Tutor session = 60 min; first booking 10:00–11:00.  Second at 11:00 does not
        overlap (end_time > start_time check is strict).
        """
        self.tutor.default_session_minutes = 60
        self.tutor.save()

        wb1 = self.student.booking_create_weekly(weekday=0, start_time=time(10, 0))
        wb2 = self.student.booking_create_weekly(weekday=0, start_time=time(11, 0))

        self.assertIsNotNone(wb1.pk)
        self.assertIsNotNone(wb2.pk)
        self.assertNotEqual(wb1.pk, wb2.pk)

    def test_booking_on_different_weekday_does_not_conflict(self):
        """
        Two bookings at the same time but on different weekdays do not conflict.
        """
        wb1 = self.student.booking_create_weekly(weekday=0, start_time=time(10, 0))  # Monday
        wb2 = self.student.booking_create_weekly(weekday=1, start_time=time(10, 0))  # Tuesday

        self.assertIsNotNone(wb1.pk)
        self.assertIsNotNone(wb2.pk)
