from celery import shared_task
from datetime import timedelta
from .message import process_sms_jobs


def _snapshot_student_progress(student, source):
    """Compute and store a WeeklyProgressSnapshot from current StudentSkillCompetency levels.

    Uses compute_overall_score so the percentage matches the syllabus display:
    all leaf skills for the student's grade are included (unstarted skills count as 0).
    """
    from .models import WeeklyProgressSnapshot
    from .competency import get_student_score

    profile = student.get_student_profile()
    grade = (profile.year_level or "").strip().lower().replace("year", "").strip()
    if not grade:
        return

    ratio = get_student_score(student, grade)
    score = round(ratio * 100, 1)
    WeeklyProgressSnapshot.objects.create(student=student, score=score, source=source)


@shared_task
def run_sms_jobs():
    try:
        process_sms_jobs()
    except Exception as e:
        print("RUN_SMS_JOBS: ERROR", e)
        raise


@shared_task
def create_post_session_jobs():
    """
    Runs every 30 minutes.  Finds BookingAdhoc and BookingWeekly occurrences
    that ended in the past 24 hours and creates post-session TutorJob records
    a single post_tuition_review job for each one.

    Uses booking_ref to prevent duplicates across task runs.
    """
    from datetime import datetime, timedelta
    from django.utils import timezone
    from .models import BookingAdhoc, BookingWeekly, TutorJob, BookingOutcome

    local_tz = timezone.get_current_timezone()
    now = timezone.now()
    window_start = now - timedelta(hours=24)
    expires_at = now + timedelta(days=14)

    def _create_job_with_outcome(tutor, student, date, time, ref):
        """Create a TutorJob + linked BookingOutcome for one booking occurrence."""
        from .models import StudentFocusArea
        job, created = TutorJob.objects.get_or_create(
            tutor=tutor,
            student=student,
            job_type='post_tuition_review',
            booking_ref=ref,
            defaults={'expires_at': expires_at},
        )
        if created:
            outcome = BookingOutcome.objects.create(
                tutor=tutor,
                student=student,
                date=date,
                time=time,
            )
            # Snapshot the student's current focus areas at the time of session
            current_skill_ids = list(
                StudentFocusArea.objects.filter(student=student)
                .values_list('skill_id', flat=True)
            )
            if current_skill_ids:
                outcome.focus_areas.set(current_skill_ids)
            job.booking_outcome = outcome
            job.save(update_fields=['booking_outcome'])
        return job, created

    # ------------------------------------------------------------------ #
    # 1. Adhoc bookings whose end_datetime fell in the last 24 hours
    # ------------------------------------------------------------------ #
    adhoc_qs = BookingAdhoc.objects.filter(
        end_datetime__gt=window_start,
        end_datetime__lte=now,
    ).select_related('tutor', 'student')

    for booking in adhoc_qs:
        ref = f"adhoc_{booking.id}"
        local_start = booking.start_datetime.astimezone(local_tz)
        _, created = _create_job_with_outcome(
            booking.tutor, booking.student,
            local_start.date(), local_start.time(),
            ref,
        )
        if created:
            _snapshot_student_progress(booking.student, 'post_session')
        print(f"POST_SESSION_JOBS: processed adhoc booking {booking.id}")

    # ------------------------------------------------------------------ #
    # 2. Weekly bookings whose most-recent occurrence ended in the window
    # ------------------------------------------------------------------ #
    for booking in BookingWeekly.objects.select_related('tutor', 'student'):
        if not booking.tutor or not booking.student:
            continue

        today = now.date()
        weekday = booking.weekday  # Mon=0 … Sun=6, same as date.weekday()

        # Most recent calendar date that had this weekday
        days_since = (today.weekday() - weekday) % 7

        if days_since == 0:
            # Today is the right weekday — check whether the session has ended
            end_today = timezone.make_aware(
                datetime.combine(today, booking.end_time), local_tz
            )
            last_date = today if end_today <= now else today - timedelta(days=7)
        else:
            last_date = today - timedelta(days=days_since)

        # Respect skip logic: if start_date > last_date, this occurrence was skipped
        if booking.start_date and booking.start_date > last_date:
            continue

        end_dt = timezone.make_aware(
            datetime.combine(last_date, booking.end_time), local_tz
        )

        if not (window_start < end_dt <= now):
            continue

        ref = f"weekly_{booking.id}_{last_date.isoformat()}"
        _, created = _create_job_with_outcome(
            booking.tutor, booking.student,
            last_date, booking.start_time,
            ref,
        )
        if created:
            _snapshot_student_progress(booking.student, 'post_session')
        print(f"POST_SESSION_JOBS: processed weekly booking {booking.id} ({last_date})")


@shared_task
def record_weekly_progress_snapshots():
    """
    Runs Sunday night. For every active student, if no WeeklyProgressSnapshot
    has been created since Monday, compute and store one now.
    """
    from django.utils import timezone
    from django.contrib.auth import get_user_model
    from .models import WeeklyProgressSnapshot

    User = get_user_model()
    now = timezone.now()
    days_since_monday = now.weekday()  # Monday=0 … Sunday=6
    week_start = (now - timedelta(days=days_since_monday)).replace(
        hour=0, minute=0, second=0, microsecond=0
    )

    for student in User.objects.filter(role='student', active=True):
        already_recorded = WeeklyProgressSnapshot.objects.filter(
            student=student,
            recorded_at__gte=week_start,
        ).exists()
        if not already_recorded:
            _snapshot_student_progress(student, 'scheduled')
            print(f"WEEKLY_PROGRESS: snapshotted student {student.id}")


@shared_task
def create_weekly_session_jobs():
    """
    Runs daily. For every active tutor-student pair that has no BookingWeekly,
    ensures there is an open 'setup_weekly_session' TutorJob.
    When a BookingWeekly is later created the job will be completed separately
    (or the tutor can dismiss it manually via the complete endpoint).
    Uses a stable booking_ref to prevent duplicates.
    """
    from django.utils import timezone
    from .models import TutorStudent, BookingWeekly, TutorJob

    now = timezone.now()
    expires_at = now + timedelta(days=365)

    links = (
        TutorStudent.objects
        .select_related('tutor', 'student')
        .filter(student__active=True)
    )

    for link in links:
        tutor = link.tutor
        student = link.student

        has_weekly = BookingWeekly.objects.filter(tutor=tutor, student=student).exists()
        if has_weekly:
            # Complete any open job if a weekly booking now exists
            TutorJob.objects.filter(
                tutor=tutor,
                student=student,
                job_type='setup_weekly_session',
                completed_at__isnull=True,
            ).update(completed_at=now)
            continue

        ref = f"setup_weekly_{tutor.id}_{student.id}"
        TutorJob.objects.get_or_create(
            tutor=tutor,
            student=student,
            job_type='setup_weekly_session',
            booking_ref=ref,
            defaults={'expires_at': expires_at},
        )
        print(f"WEEKLY_SESSION_JOBS: ensured job for tutor={tutor.id} student={student.id}")

