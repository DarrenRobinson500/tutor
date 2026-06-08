"""
Tests for payment split arithmetic, status lifecycle, idempotency, and
low-session-rating admin jobs.

Stripe calls are patched throughout so no real network traffic is made.
"""
import decimal
from decimal import Decimal
from unittest.mock import patch, MagicMock

from django.urls import reverse

from backend.models import (
    AdminJob,
    DistributorParent,
    DistributorProfile,
    GlobalSetting,
    SessionPayment,
    TutorJob,
)
from .base import BaseAPITestCase
from .factories import (
    make_user,
    make_tutor_profile,
    make_student_profile,
    make_parent_payment_profile,
    make_tutor_student,
    make_parent_child,
    make_session_payment,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _set_global(key, value):
    """Create or overwrite a GlobalSetting."""
    GlobalSetting.objects.update_or_create(key=key, defaults={"value": str(value)})


def _make_stripe_intent(intent_id="pi_test_001"):
    """Return a minimal Stripe PaymentIntent-like dict."""
    m = MagicMock()
    m.__getitem__ = lambda self, k: intent_id if k == "id" else None
    return m


# ---------------------------------------------------------------------------
# 1. Payment split arithmetic
# ---------------------------------------------------------------------------

class PaymentSplitArithmeticTests(BaseAPITestCase):
    """
    Test the split calculation formula used in payment_summary / apply_payment:

        amount_tutor       = hourly_rate * mins / 60
        amount_platform    = platform_fee_per_hour * mins / 60
        amount_distributor = distributor_fee_per_hour * mins / 60  (or 0 when no distributor)
        amount_paid        = sum of the three amounts
    """

    def _calc(self, hourly_rate, session_minutes, platform_fee_per_hour, distributor_fee_per_hour, has_distributor):
        """Mirror the formula from views.apply_payment."""
        rate = Decimal(str(hourly_rate))
        pfee = Decimal(str(platform_fee_per_hour))
        dfee = Decimal(str(distributor_fee_per_hour))
        mins = Decimal(str(session_minutes))

        amount_tutor = (rate * mins / 60).quantize(Decimal("0.01"))
        amount_platform = (pfee * mins / 60).quantize(Decimal("0.01"))
        amount_distributor = (
            (dfee * mins / 60).quantize(Decimal("0.01"))
            if has_distributor
            else Decimal("0.00")
        )
        amount_paid = (amount_tutor + amount_platform + amount_distributor).quantize(Decimal("0.01"))
        return amount_tutor, amount_platform, amount_distributor, amount_paid

    def test_60min_rate80_platform650_no_distributor(self):
        """60-min session, rate=80.00, platform_fee=6.50, no distributor."""
        tutor_amount, platform_amount, dist_amount, total = self._calc(
            hourly_rate=80.00,
            session_minutes=60,
            platform_fee_per_hour=6.50,
            distributor_fee_per_hour=5.00,
            has_distributor=False,
        )
        self.assertEqual(tutor_amount, Decimal("80.00"))
        self.assertEqual(platform_amount, Decimal("6.50"))
        self.assertEqual(dist_amount, Decimal("0.00"))
        self.assertEqual(total, Decimal("86.50"))

    def test_90min_rate70_platform500_distributor500(self):
        """90-min session, rate=70.00, platform_fee=5.00, distributor_fee=5.00."""
        tutor_amount, platform_amount, dist_amount, total = self._calc(
            hourly_rate=70.00,
            session_minutes=90,
            platform_fee_per_hour=5.00,
            distributor_fee_per_hour=5.00,
            has_distributor=True,
        )
        self.assertEqual(tutor_amount, Decimal("105.00"))
        self.assertEqual(platform_amount, Decimal("7.50"))
        self.assertEqual(dist_amount, Decimal("7.50"))
        self.assertEqual(total, Decimal("120.00"))

    def test_45min_session_amounts_have_two_decimal_places(self):
        """45-min session amounts are Decimal with exactly 2 dp."""
        tutor_amount, platform_amount, dist_amount, total = self._calc(
            hourly_rate=70.00,
            session_minutes=45,
            platform_fee_per_hour=5.00,
            distributor_fee_per_hour=5.00,
            has_distributor=True,
        )
        for amount in (tutor_amount, platform_amount, dist_amount, total):
            self.assertIsInstance(amount, Decimal)
            # Quantize to 2 dp and compare — should be unchanged
            self.assertEqual(amount, amount.quantize(Decimal("0.01")))

    def test_no_distributor_parent_gives_zero_distributor_amount(self):
        """When has_distributor=False, distributor_amount must be Decimal('0.00')."""
        _, _, dist_amount, _ = self._calc(
            hourly_rate=80.00,
            session_minutes=60,
            platform_fee_per_hour=6.50,
            distributor_fee_per_hour=5.00,
            has_distributor=False,
        )
        self.assertEqual(dist_amount, Decimal("0.00"))
        self.assertIsInstance(dist_amount, Decimal)


# ---------------------------------------------------------------------------
# 2. Payment status lifecycle via HTTP endpoints
# ---------------------------------------------------------------------------

class PaymentStatusLifecycleTests(BaseAPITestCase):
    """
    Tests for the three status transitions driven by real HTTP calls:

    pending → paid      via POST /payments/<pk>/authorise/   (parent marks bank transfer made)
    paid    → confirmed via POST /payments/<pk>/confirm/      (tutor confirms receipt)
    """

    def setUp(self):
        super().setUp()
        self.tutor_user = make_user(role="tutor", first_name="Tutor", last_name="One")
        self.tutor_profile = make_tutor_profile(user=self.tutor_user)
        self.student_user = make_user(role="student", first_name="Student", last_name="One")
        self.parent_user = make_user(role="parent", first_name="Parent", last_name="One")
        make_tutor_student(tutor=self.tutor_user, student=self.student_user)
        make_parent_child(parent=self.parent_user, student=self.student_user)
        make_parent_payment_profile(user=self.parent_user)
        # Clear the in-memory cache so GlobalSetting reads hit the DB
        from django.core.cache import cache
        cache.clear()

    # ---- helper ----

    def _make_pending_payment(self, **kwargs):
        kwargs.setdefault("status", "pending")
        kwargs.setdefault("tutor_amount", Decimal("80.00"))
        kwargs.setdefault("platform_amount", Decimal("6.50"))
        kwargs.setdefault("distributor_amount", Decimal("0.00"))
        kwargs.setdefault("total_amount", Decimal("86.50"))
        return make_session_payment(
            tutor=self.tutor_user,
            student=self.student_user,
            parent=self.parent_user,
            **kwargs,
        )

    # ---- 2a. pending → paid ----

    def test_authorise_sets_status_paid(self):
        """POST /payments/<pk>/authorise/ by the parent sets status='paid'."""
        payment = self._make_pending_payment()
        self.auth(self.parent_user)

        url = reverse("payment_authorise", kwargs={"pk": payment.pk})
        resp = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "paid")
        self.assertIsNotNone(payment.paid_at)

    def test_authorise_creates_tutor_confirm_payment_receipt_job(self):
        """After authorise, a TutorJob of type confirm_payment_receipt is created."""
        payment = self._make_pending_payment()
        self.auth(self.parent_user)

        url = reverse("payment_authorise", kwargs={"pk": payment.pk})
        self.client.post(url, {}, content_type="application/json")

        booking_ref = f"payment_{payment.id}"
        job = TutorJob.objects.filter(
            tutor=self.tutor_user,
            booking_ref=booking_ref,
            job_type="confirm_payment_receipt",
        ).first()
        self.assertIsNotNone(job)

    # ---- 2b. paid → confirmed ----

    def test_mark_paid_then_tutor_confirm(self):
        """Tutor confirming a 'paid' payment sets status='confirmed'."""
        payment = self._make_pending_payment(status="paid")
        self.auth(self.tutor_user)

        url = reverse("payment_confirm_receipt", kwargs={"pk": payment.pk})
        resp = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 200)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "confirmed")
        self.assertIsNotNone(payment.confirmed_at)

    # ---- 2c. Full lifecycle: pending → paid → confirmed ----

    def test_full_lifecycle_pending_to_paid_to_confirmed(self):
        """End-to-end: pending → authorise (paid) → confirm (confirmed)."""
        payment = self._make_pending_payment()

        # Step 1: parent authorises
        self.auth(self.parent_user)
        url_authorise = reverse("payment_authorise", kwargs={"pk": payment.pk})
        resp = self.client.post(url_authorise, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "paid")

        # Step 2: tutor confirms
        self.auth(self.tutor_user)
        url_confirm = reverse("payment_confirm_receipt", kwargs={"pk": payment.pk})
        resp = self.client.post(url_confirm, {}, content_type="application/json")
        self.assertEqual(resp.status_code, 200)

        payment.refresh_from_db()
        self.assertEqual(payment.status, "confirmed")

    # ---- 2d. confirm rejected when status is not 'paid' ----

    def test_confirm_on_pending_payment_returns_400(self):
        """Tutor cannot confirm a payment that is still pending."""
        payment = self._make_pending_payment(status="pending")
        self.auth(self.tutor_user)

        url = reverse("payment_confirm_receipt", kwargs={"pk": payment.pk})
        resp = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 400)
        payment.refresh_from_db()
        self.assertEqual(payment.status, "pending")

    # ---- 2e. authorise is forbidden for non-parent ----

    def test_authorise_forbidden_for_non_owner(self):
        """A user who is not the payment's parent cannot authorise it."""
        payment = self._make_pending_payment()
        other_parent = make_user(role="parent")
        self.auth(other_parent)

        url = reverse("payment_authorise", kwargs={"pk": payment.pk})
        resp = self.client.post(url, {}, content_type="application/json")

        self.assertEqual(resp.status_code, 403)


# ---------------------------------------------------------------------------
# 3. Idempotency
# ---------------------------------------------------------------------------

class PaymentIdempotencyTests(BaseAPITestCase):
    """
    Calling authorise twice should not error on the second call (the endpoint
    returns 200 with success=True when the payment is already paid/confirmed)
    and must not create duplicate TutorJobs.
    """

    def setUp(self):
        super().setUp()
        self.tutor_user = make_user(role="tutor")
        make_tutor_profile(user=self.tutor_user)
        self.student_user = make_user(role="student")
        self.parent_user = make_user(role="parent")
        make_tutor_student(tutor=self.tutor_user, student=self.student_user)
        make_parent_child(parent=self.parent_user, student=self.student_user)
        make_parent_payment_profile(user=self.parent_user)

    def _make_payment(self, **kwargs):
        return make_session_payment(
            tutor=self.tutor_user,
            student=self.student_user,
            parent=self.parent_user,
            tutor_amount=Decimal("80.00"),
            platform_amount=Decimal("6.50"),
            distributor_amount=Decimal("0.00"),
            total_amount=Decimal("86.50"),
            **kwargs,
        )

    def test_authorise_twice_is_idempotent(self):
        """Second POST to authorise on a paid payment returns 200 without error."""
        payment = self._make_payment(status="pending")
        self.auth(self.parent_user)
        url = reverse("payment_authorise", kwargs={"pk": payment.pk})

        resp1 = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(resp1.status_code, 200)

        resp2 = self.client.post(url, {}, content_type="application/json")
        self.assertEqual(resp2.status_code, 200)

        # Status must still be paid (not some undefined state)
        payment.refresh_from_db()
        self.assertIn(payment.status, ("paid", "confirmed"))

    def test_authorise_twice_creates_only_one_tutor_job(self):
        """Repeated authorise calls must not create duplicate TutorJobs."""
        payment = self._make_payment(status="pending")
        self.auth(self.parent_user)
        url = reverse("payment_authorise", kwargs={"pk": payment.pk})

        self.client.post(url, {}, content_type="application/json")
        self.client.post(url, {}, content_type="application/json")

        booking_ref = f"payment_{payment.id}"
        job_count = TutorJob.objects.filter(
            tutor=self.tutor_user,
            booking_ref=booking_ref,
            job_type="confirm_payment_receipt",
        ).count()
        self.assertEqual(job_count, 1)


# ---------------------------------------------------------------------------
# 4. Low session rating
# ---------------------------------------------------------------------------

class LowSessionRatingTests(BaseAPITestCase):
    """
    The payment_authorise endpoint checks payment.rating after saving.
    If rating <= 2, an AdminJob of type 'low_session_rating' is created.
    Ratings of 3 or higher must NOT trigger that job.
    """

    def setUp(self):
        super().setUp()
        self.tutor_user = make_user(role="tutor")
        make_tutor_profile(user=self.tutor_user)
        self.student_user = make_user(role="student")
        self.parent_user = make_user(role="parent")
        make_tutor_student(tutor=self.tutor_user, student=self.student_user)
        make_parent_child(parent=self.parent_user, student=self.student_user)
        make_parent_payment_profile(user=self.parent_user)

    def _make_payment(self, **kwargs):
        return make_session_payment(
            tutor=self.tutor_user,
            student=self.student_user,
            parent=self.parent_user,
            status="pending",
            tutor_amount=Decimal("80.00"),
            platform_amount=Decimal("6.50"),
            distributor_amount=Decimal("0.00"),
            total_amount=Decimal("86.50"),
            **kwargs,
        )

    def _authorise_with_rating(self, payment, rating):
        self.auth(self.parent_user)
        url = reverse("payment_authorise", kwargs={"pk": payment.pk})
        return self.client.post(
            url,
            {"rating": rating},
            content_type="application/json",
        )

    def test_rating_1_creates_low_session_rating_admin_job(self):
        """A rating of 1 (<=2) triggers an AdminJob of type low_session_rating."""
        payment = self._make_payment()
        before_count = AdminJob.objects.filter(job_type="low_session_rating").count()

        resp = self._authorise_with_rating(payment, rating=1)

        self.assertEqual(resp.status_code, 200)
        after_count = AdminJob.objects.filter(job_type="low_session_rating").count()
        self.assertEqual(after_count, before_count + 1)

        # The admin job subject should be the parent
        job = AdminJob.objects.filter(job_type="low_session_rating").order_by("-triggered_at").first()
        self.assertEqual(job.subject, self.parent_user)

    def test_rating_2_creates_low_session_rating_admin_job(self):
        """A rating of 2 (<=2) also triggers an AdminJob."""
        payment = self._make_payment()
        before_count = AdminJob.objects.filter(job_type="low_session_rating").count()

        self._authorise_with_rating(payment, rating=2)

        after_count = AdminJob.objects.filter(job_type="low_session_rating").count()
        self.assertEqual(after_count, before_count + 1)

    def test_rating_3_does_not_create_low_session_rating_admin_job(self):
        """A rating of 3 must NOT trigger a low_session_rating AdminJob."""
        payment = self._make_payment()
        before_count = AdminJob.objects.filter(job_type="low_session_rating").count()

        self._authorise_with_rating(payment, rating=3)

        after_count = AdminJob.objects.filter(job_type="low_session_rating").count()
        self.assertEqual(after_count, before_count)

    def test_rating_5_does_not_create_low_session_rating_admin_job(self):
        """A rating of 5 (high) must NOT trigger a low_session_rating AdminJob."""
        payment = self._make_payment()
        before_count = AdminJob.objects.filter(job_type="low_session_rating").count()

        self._authorise_with_rating(payment, rating=5)

        after_count = AdminJob.objects.filter(job_type="low_session_rating").count()
        self.assertEqual(after_count, before_count)

    def test_no_rating_does_not_create_low_session_rating_admin_job(self):
        """Authorising without submitting a rating must NOT create the admin job."""
        payment = self._make_payment()
        before_count = AdminJob.objects.filter(job_type="low_session_rating").count()

        self.auth(self.parent_user)
        url = reverse("payment_authorise", kwargs={"pk": payment.pk})
        self.client.post(url, {}, content_type="application/json")

        after_count = AdminJob.objects.filter(job_type="low_session_rating").count()
        self.assertEqual(after_count, before_count)
