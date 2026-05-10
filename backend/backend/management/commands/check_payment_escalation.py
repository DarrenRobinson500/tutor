from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from backend.models import (
    SessionPayment, TutorJob, ParentJob, AdminJob, ParentChild,
)


class Command(BaseCommand):
    help = "Escalate overdue SessionPayments (7-day and 14-day thresholds). Run daily via cron."

    def handle(self, *args, **options):
        now = timezone.now()

        # ── 7-day escalation ─────────────────────────────────────────────────
        overdue_7 = SessionPayment.objects.filter(
            status='pending',
            created_at__lte=now - timedelta(days=7),
        ).select_related('session', 'session__student', 'tutor', 'parent')

        for payment in overdue_7:
            payment.status = 'overdue_7'
            payment.save(update_fields=['status'])

            ref = f'payment_{payment.id}_overdue_7'
            if not TutorJob.objects.filter(booking_ref=ref).exists():
                TutorJob.objects.create(
                    tutor=payment.tutor,
                    student=payment.session.student,
                    job_type='payment_overdue_7',
                    session=payment.session,
                    booking_ref=ref,
                    expires_at=now + timedelta(days=7),
                )
                ParentJob.objects.create(
                    parent=payment.parent,
                    payment=payment,
                    job_type='payment_overdue_7',
                )
                AdminJob.objects.create(
                    job_type='payment_overdue_7',
                    subject=payment.parent,
                )

            self.stdout.write(f'  Escalated to overdue_7: payment #{payment.id}')

        # ── 14-day escalation ────────────────────────────────────────────────
        overdue_14 = SessionPayment.objects.filter(
            status__in=['pending', 'overdue_7'],
            created_at__lte=now - timedelta(days=14),
        ).select_related('session', 'session__student', 'tutor', 'parent')

        for payment in overdue_14:
            payment.status = 'overdue_14'
            payment.save(update_fields=['status'])

            TutorJob.objects.create(
                tutor=payment.tutor,
                student=payment.session.student,
                job_type='payment_overdue_14',
                session=payment.session,
                booking_ref=f'payment_{payment.id}_overdue_14',
                expires_at=now + timedelta(days=14),
            )
            ParentJob.objects.create(
                parent=payment.parent,
                payment=payment,
                job_type='payment_overdue_14',
            )
            AdminJob.objects.create(
                job_type='payment_overdue_14',
                subject=payment.parent,
            )

            # Pause future sessions for this parent's children
            ParentChild.objects.filter(parent=payment.parent).update(sessions_paused=True)

            self.stdout.write(f'  Escalated to overdue_14 (sessions paused): payment #{payment.id}')

        self.stdout.write(self.style.SUCCESS(
            f'Done. 7-day: {overdue_7.count()}, 14-day: {overdue_14.count()}'
        ))
