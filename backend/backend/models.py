import uuid as _uuid
from collections import defaultdict
from django.core.cache import cache

from django.db import models

from django.contrib.auth.models import AbstractUser
from django.conf import settings as django_settings
from datetime import datetime, timedelta, time, date
# from django.utils.timezone import make_aware
from django.utils.timezone import make_aware, now as tz_now
from django.contrib.auth.models import UserManager

from django.db.models import Count
from .utilities import *


from django.utils import timezone
import pytz
tz = pytz.timezone("Australia/Sydney")
local_tz = timezone.get_default_timezone()
now = timezone.localtime(timezone.now(), local_tz)
today = now.date()

weekday_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]

# from django.db.models import Count
# from django_cte import With
# from django.db.models.expressions import RawSQL


class Year(models.Model):
    """A school year level (e.g. Year 7). Acts as the single source of truth for valid year values."""
    code = models.CharField(max_length=10, unique=True)   # stored value: "K", "1", ..., "10", "11std"
    label = models.CharField(max_length=50)               # display name: "Kindergarten", "Year 1", ...
    order = models.PositiveIntegerField()                  # sort order
    active = models.BooleanField(default=True)             # show in dropdowns
    stage = models.CharField(max_length=20, default="k10", blank=True)  # "k10" or "s6"

    class Meta:
        ordering = ["order"]

    def __str__(self):
        return self.label


class User(AbstractUser):
    ROLE_CHOICES = [
        ("student", "Student"),
        ("tutor", "Tutor"),
        ("parent", "Parent"),
        ("admin", "Admin"),
        ("distributor", "Distributor"),
        ("teacher", "Teacher"),
    ]
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    default_session_minutes = models.IntegerField(default=60)
    buffer_minutes = models.IntegerField(default=15)
    objects = UserManager()
    active = models.BooleanField(default=True)
    account_details = models.CharField(max_length=500, blank=True, default="")
    welcome_email_sent = models.BooleanField(default=False)

    def __str__(self):
        full_name = f"{self.first_name} {self.last_name}".strip()
        if full_name:
            return f"{full_name} ({self.username})"
        return self.username

    def get_student_profile(self):
        if self.role == "student":
            profile = StudentProfile.objects.filter(user=self).first()
        if not profile and self.role == "student":
            profile = StudentProfile.objects.create(user=self)
        return profile

    def get_tutor(self):
        if self.role == "tutor": return self
        if self.role == "student":
            link = TutorStudent.objects.filter(student=self).first()
            if link: return link.tutor
        if self.role == "parent":
            child_link = ParentChild.objects.filter(parent=self).first()
            if child_link: tutor_link = TutorStudent.objects.filter(student=child_link.child).first()
            if tutor_link: return TutorProfile.objects.filter(tutor=tutor_link.tutor).first()
        return None

    def get_tutor_profile(user):
        # Tutor: ensure a TutorProfile exists
        if user.role == "tutor":
            profile, _ = TutorProfile.objects.get_or_create(tutor=user)
            return profile

        # Student: follow TutorStudent → TutorProfile
        if user.role == "student":
            link = TutorStudent.objects.filter(student=user).first()
            if not link:
                return None
            profile, _ = TutorProfile.objects.get_or_create(tutor=link.tutor)
            return profile

        # Parent: follow ParentChild → TutorStudent → TutorProfile
        if user.role == "parent":
            child_link = ParentChild.objects.filter(parent=user).first()
            if not child_link:
                return None
            tutor_link = TutorStudent.objects.filter(student=child_link.child).first()
            if not tutor_link:
                return None
            profile, _ = TutorProfile.objects.get_or_create(tutor=tutor_link.tutor)
            return profile

        return None

    def to_dict(self):
        if self.role == "student":
            return self.get_student_profile().to_dict()
        if self.role == "tutor":
            return self.get_tutor_profile().to_dict()


    def next_booking(self):
        weekly = self.next_weekly_booking()
        adhoc = self.next_ad_hoc_booking()
        # print("Next booking", self, weekly, adhoc)

        if not weekly and not adhoc: return None
        if not adhoc: return weekly
        if not weekly: return adhoc

        return weekly if weekly["start_iso"] <= adhoc["start_iso"] else adhoc

    def next_ad_hoc_booking(self):
        # print("Next adhoc start")
        if self.role != "student": return None
        next_booking = (
            BookingAdhoc.objects
            .filter(student=self, start_datetime__gte=timezone.now())
            .order_by("start_datetime")
            .first()
        )
        # print("Next adhoc:", next_booking)

        if not next_booking: return None

        result = next_booking.to_dict()
        return result

    def next_weekly_booking(self):
        weekly_bookings = BookingWeekly.objects.filter(student=self)
        if not weekly_bookings.exists(): return None
        next_booking = sorted(weekly_bookings, key=lambda wb: wb.next_occurrence())[0]

        result = next_booking.to_dict()
        return result

    def booking_mode(self):
        weekly = self.next_weekly_booking()
        adhoc = self.next_ad_hoc_booking()
        mode = "weekly_booking"
        next_booking = weekly

        # print("Booking mode:", weekly, weekly.get("start_iso"))

        if not weekly and not adhoc:
            mode = "no_booking"
        elif weekly and adhoc:
            weekly_start = weekly["start_iso"]
            adhoc_start = adhoc["start_iso"]
            if adhoc_start < weekly_start:
                mode = "weekly_booking_but_adhoc_this_week"
                next_booking = adhoc
        elif weekly and weekly.get("start_date"):
            resume_date = weekly["start_date"]
            today = date.today()
            if resume_date > today:
                mode = "weekly_booking_but_paused"
        elif adhoc and not weekly:
            mode = "adhoc"
            next_booking = adhoc
        data = {
            "mode": mode,
            "next_booking": next_booking,
            "weekly": weekly,
            "adhoc": adhoc,
        }
        # print("Booking mode:", data)
        return data

    def booking_slots_weekly(self):
        if self.role != "tutor":
            return {i: [] for i in range(7)}

        availability = TutorAvailability.objects.filter(tutor=self)
        weekly_bookings = BookingWeekly.objects.filter(tutor=self)
        session_delta = timedelta(minutes=self.default_session_minutes)
        buffer_delta = timedelta(minutes=self.buffer_minutes)
        blocked = defaultdict(set)

        for wb in weekly_bookings:
            start_dt = datetime.combine(date.today(), wb.start_time) - buffer_delta
            end_dt = datetime.combine(date.today(), wb.end_time) + buffer_delta
            cur = start_dt
            while cur < end_dt:
                blocked[wb.weekday].add(cur.time())
                cur += timedelta(minutes=15)

        result = {i: [] for i in range(7)}

        for av in availability:
            weekday = av.weekday
            start = datetime.combine(date.today(), av.start_time)
            end = datetime.combine(date.today(), av.end_time)
            cur = start
            while cur + session_delta <= end:
                slot_time = cur.time()
                conflict = False
                check = cur
                while check < cur + session_delta:
                    if check.time() in blocked[weekday]:
                        conflict = True
                        break
                    check += timedelta(minutes=15)

                if not conflict:
                    result[weekday].append(slot_time.strftime("%H:%M"))

                cur += timedelta(minutes=15)

        return result

    def booking_slots_adhoc(self, weekly_slots, dates):
        # Get all adhoc bookings for the date range
        booking_map = self.booking_list_adhoc(dates)
        result = {}

        for day in dates:
            day_str = day.isoformat()
            weekday = day.weekday()

            # Weekly base slots for this weekday
            base_slots = weekly_slots.get(weekday, [])

            # Convert weekly slot times into datetime objects for this specific date
            slot_dts = []
            for time_str in base_slots:
                hour, minute = map(int, time_str.split(":"))
                slot_dts.append(
                    datetime.combine(day, time(hour, minute))
                )

            # Build a set of blocked increments from adhoc bookings
            blocked = set()

            for b in booking_map.get(day_str, []):
                # b["start_time"] and b["end_time"] are HH:MM strings
                start_h, start_m = map(int, b["start_time"].split(":"))
                end_h, end_m = map(int, b["end_time"].split(":"))

                cur = datetime.combine(day, time(start_h, start_m))
                end = datetime.combine(day, time(end_h, end_m))

                # Mark every 15‑minute increment as blocked
                while cur < end:
                    blocked.add(cur.time().strftime("%H:%M"))
                    cur += timedelta(minutes=15)

            # Filter out blocked slots
            final_slots = [
                dt.time().strftime("%H:%M")
                for dt in slot_dts
                if dt.time().strftime("%H:%M") not in blocked
            ]

            result[day_str] = final_slots

        return result

    def booking_list_weekly(self):
        if self.role != "tutor":
            return {i: [] for i in range(7)}

        qs = (BookingWeekly.objects.filter(tutor=self).select_related("student"))
        booking_map = defaultdict(list)

        for b in qs:
            data = b.to_dict()
            booking_map[data["weekday"]].append(data)

        return {i: booking_map[i] for i in range(7)}

    def booking_list_adhoc(self, dates):
        if not dates:
            return {}

        start_date = min(dates)
        end_date = max(dates)

        qs = (
            BookingAdhoc.objects
            .filter(
                tutor=self,
                start_datetime__date__range=(start_date, end_date),
            )
            .select_related("student")
        )

        booking_map = {}

        for b in qs:
            data = b.to_dict()
            booking_map.setdefault(data["day_str"], []).append(data)

        return booking_map

    def booking_create_weekly(self, weekday: int, start_time: time):
        if self.role != "student": raise ValueError("Only students can create weekly bookings.")
        tutor = self.get_tutor()
        if not tutor: raise ValueError("Student does not have an assigned tutor.")

        start_dt = datetime.combine(datetime.today(), start_time)
        end_dt = start_dt + timedelta(minutes=tutor.default_session_minutes)
        end_time = end_dt.time()

        exists = BookingWeekly.objects.filter(student=self,tutor=tutor,weekday=weekday,start_time=start_time).exists()
        if exists: raise ValueError("A weekly booking already exists for this time.")
        overlapping = BookingWeekly.objects.filter(student=self,tutor=tutor,weekday=weekday,start_time__lt=end_time,end_time__gt=start_time,).exists()
        if overlapping: raise ValueError("This weekly booking overlaps with an existing one.")

        wb = BookingWeekly.objects.create(student=self,tutor=tutor,weekday=weekday,start_time=start_time,end_time=end_time)
        return wb

    def booking_create_adhoc(self, start_dt):
        print("booking_create_adhoc")
        tutor = self.get_tutor()
        if not tutor: return None

        day = start_dt.date()
        dates = [day]

        weekly_slots = tutor.booking_slots_weekly()
        adhoc_slots = tutor.booking_slots_adhoc(weekly_slots, dates)

        day_str = day.isoformat()
        time_str = start_dt.time().strftime("%H:%M")

        if time_str not in adhoc_slots.get(day_str, []):
            print("Couldn't find time_str", time_str, adhoc_slots.get(day_str, []))
            return None

        booking = BookingAdhoc.objects.create(
            tutor=tutor,
            student=self,
            start_datetime=start_dt,
            end_datetime=start_dt + timedelta(minutes=60),
        )
        print("booking_create_adhoc - created")

        return booking

    def replace_this_weeks_adhoc(self, new_start_dt):
        existing = self.next_ad_hoc_booking()
        if existing:
            BookingAdhoc.objects.filter(id=existing["id"]).delete()
        return self.booking_create_adhoc(new_start_dt)

    def generate_weekly_slots(self, week_start, student=None, tutor_view=False):
        tutor_profile = self.get_tutor_profile()
        session_td = timedelta(minutes=self.default_session_minutes)
        week = []

        # Build the week skeletonx`
        for i in range(7):
            day_date = week_start + timedelta(days=i)
            week.append({"date": day_date, "bookable_slots": [], "segments": []})

        # ── 1. Fetch all appointments for the week in one query
        week_start_dt = make_aware(datetime.combine(week_start, time.min))
        week_end_dt = make_aware(datetime.combine(week_start + timedelta(days=7), time.min))

        appointments = list(
            BookingAdhoc.objects.filter(
                tutor=self,
                start_datetime__lt=week_end_dt,
                end_datetime__gt=week_start_dt,
            ).select_related("student")
        )

        # Group appointments by date for fast lookup
        appointments_by_date = defaultdict(list)
        for appt in appointments:
            date_key = appt.start_datetime.date()
            appointments_by_date[date_key].append(appt)

        appt_start_times = defaultdict(set)

        for appt in appointments:
            date_key = appt.start_datetime.date()
            start_time = appt.start_datetime.time().replace(second=0, microsecond=0)
            appt_start_times[date_key].add(start_time)

        # ── 2. Fetch blocked days for the week
        blocked_days = set(
            TutorBlockedDay.objects.filter(
                tutor=self,
                date__gte=week_start,
                date__lt=week_start + timedelta(days=7),
            ).values_list("date", flat=True)
        )

        # ── 3. Fetch availability windows for the tutor
        availability_by_weekday = {}
        for av in TutorAvailability.objects.filter(tutor=self):
            availability_by_weekday.setdefault(av.weekday, []).append(av)

        # ── 4. Build segments and bookable slots in memory
        for day in week:
            d = day["date"]

            for minute in range(0, 24 * 60, 15):
                t = (datetime.min + timedelta(minutes=minute)).time()

                status, appt = tutor_profile.appointment_status_fast(
                    d, t, student,
                    blocked_days,
                    appointments_by_date,
                    availability_by_weekday,
                )

                if tutor_view and status in ("booked_self", "booked_other"):
                    status = "booked_other"

                segment = {"time": t, "type": status}

                if appt:
                    segment["bookingId"] = appt.id

                    # Only label the FIRST slot of the appointment
                    if t in appt_start_times[d]:

                        # Student view → only show THEIR name
                        if student is not None:
                            if appt.student_id == student.id:
                                segment["studentName"] = appt.student.first_name

                        # Tutor view → show ALL names
                        else:
                            segment["studentName"] = appt.student.first_name

                day["segments"].append(segment)

                # Only compute bookable_slots for available segments
                if status != "available":
                    continue

                end_dt = datetime.combine(d, t) + session_td
                end_t = end_dt.time()

                end_status, _ = tutor_profile.appointment_status_fast(
                    d,
                    end_t,
                    student,
                    blocked_days,
                    appointments_by_date,
                    availability_by_weekday,
                )

                if end_status == "available":
                    day["bookable_slots"].append(t)

        # print("Generate Slots (week):")
        # print_segments(week)

        return week

# Booking Outcome
# Date, Time
# Parent Message, Focus Areas, Payment, Next Focus Areas

class BookingWeekly(models.Model):
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="appointment_tutor_weekly")
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="student_weekly")
    weekday = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    start_date = models.DateField(blank=True, null=True)
    confirmed = models.BooleanField(default=False)

    def __str__(self):
        result = f"{self.tutor} and {self.student}: {weekday_names[self.weekday]}, {self.start_time.strftime('%H:%M')}-{self.end_time.strftime('%H:%M')}"
        if not self.confirmed: result += " [unconfirmed]"
        return result

    def skip(self, weeks=1):
        self.start_date = now + timedelta(weeks=weeks)
        self.save(update_fields=["start_date"])

    def remove_skip(self):
        self.start_date = None
        print("Remove skip:", self, self.start_date)
        self.save(update_fields=["start_date"])

    def next_occurrence(self):
        sd = self.start_date
        if isinstance(sd, datetime):
            sd = sd.date()
        start_date = sd if sd and sd > today else today

        days_ahead = (self.weekday - start_date.weekday()) % 7
        # print("Next occurrence:", start_date, self.weekday, start_date.weekday(), days_ahead)
        next_booking_date = today + timedelta(days=days_ahead)
        while next_booking_date <= start_date:
            next_booking_date += timedelta(days=7)
        next_start_time = make_aware(datetime.combine(next_booking_date, self.start_time), local_tz)
        return next_start_time

    def student_can_edit(self):
        notice_hours = get_int('cancellation_notice_hours', 24)
        return self.next_occurrence() > timezone.now() + timedelta(hours=notice_hours)

    def duration(self):
        return (self.end_time.hour * 60 + self.end_time.minute) - (self.start_time.hour * 60 + self.start_time.minute)

    def to_dict(self):
        start = self.next_occurrence()
        duration_minutes = self.duration()
        end = start + timedelta(minutes=duration_minutes)
        day_str = start.date().isoformat()

        return {
            "id": self.id,
            "student_id": self.student.id if self.student else None,
            "student_name": self.student.get_full_name() if self.student else None,
            "weekday": self.weekday,
            "start_time": start.time().isoformat(timespec="minutes"),
            "end_time": end.time().isoformat(timespec="minutes"),
            "day_str": day_str,
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "start_date": self.start_date,
            "confirmed": self.confirmed,
            "duration_minutes": duration_minutes,
            "booking_type": "weekly",
            "student_can_edit": self.student_can_edit(),
            "tutor_name": self.tutor.get_full_name() if self.tutor else None,
            "tutor_id": self.tutor.id if self.tutor else None,
        }

class BookingAdhoc(models.Model):
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="appointment_tutor")
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student")
    start_datetime = models.DateTimeField()
    end_datetime = models.DateTimeField()
    confirmed = models.BooleanField(default=False)
    status = models.CharField(max_length=20)
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name="appointments_created")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self): return f"{self.start_datetime} {self.student} {self.tutor}"

    def student_can_edit(self):
        notice_hours = get_int('cancellation_notice_hours', 24)
        return self.start_datetime > timezone.now() + timedelta(hours=notice_hours)

    def duration(self):
        return (self.end_datetime.hour * 60 + self.end_datetime.minute) - (self.start_datetime.hour * 60 + self.start_datetime.minute)

    def to_dict(self):
        # Localise datetimes
        start = timezone.localtime(self.start_datetime)
        end = timezone.localtime(self.end_datetime)
        duration_minutes = self.duration()
        day_str = start.date().isoformat()

        return {
            "id": self.id,
            "student_id": self.student.id,
            "student_name": self.student.get_full_name(),
            "start_time": start.time().isoformat(timespec="minutes"),
            "end_time": end.time().isoformat(timespec="minutes"),
            "start_date": day_str,
            "day_str": day_str,
            "start_iso": start.isoformat(),
            "end_iso": end.isoformat(),
            "confirmed": self.confirmed,
            "duration_minutes": duration_minutes,
            "booking_type": "adhoc",
            "student_can_edit": self.student_can_edit(),
            "tutor_name": self.tutor.get_full_name() if self.tutor else None,
            "tutor_id": self.tutor.id if self.tutor else None,
        }

class ParentChild(models.Model):
    parent = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="children")
    child = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="parents")
    sessions_paused = models.BooleanField(default=False)

    class Meta:
        unique_together = ("parent", "child")

class TutorStudent(models.Model):
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="students")
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutors")

    class Meta:
        unique_together = ("tutor", "student")

    def __str__(self): return f"Tutor: {self.tutor} Student: {self.student}"

class StudentProfile(models.Model):
    user = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="student_profile")
    year_level = models.CharField(max_length=50, blank=True, null=True)
    area_of_study = models.TextField(blank=True, null=True)
    mobile = models.CharField(max_length = 20, null=True, blank=True, default='0493461541')
    address = models.CharField(max_length=255, blank=True, null=True)
    school_name = models.CharField(max_length=200, blank=True, null=True)
    hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=70)
    plain_password = models.CharField(max_length=50, blank=True, null=True)
    min_questions_per_skill = models.IntegerField(default=0)
    gender = models.CharField(max_length=20, blank=True, null=True)

    def __str__(self): return f"Profile {self.user} {self.id}"

    def next_booking(self):
        return self.user.next_booking()

    def to_dict(self):
        u = self.user
        tutor_user = u.get_tutor()
        tutor_profile = tutor_user.get_tutor_profile() if tutor_user else None
        booking_mode = u.booking_mode()
        # print("Booking mode:", booking_mode)

        grade_key = str(self.year_level).strip().lower().replace("year", "").strip() if self.year_level else None
        syllabus_percent: int | None = None
        if grade_key:
            try:
                from .competency import get_student_score
                syllabus_percent = round(get_student_score(u, grade_key) * 100)
            except Exception:
                pass

        return {
            # User + profile identifiers
            "user_id": u.id,
            "profile_id": self.id,

            # User identity
            "first_name": u.first_name,
            "last_name": u.last_name,
            "name": u.get_full_name() or u.username,
            "email": u.email,
            "active": u.active,

            # Student profile fields
            "year_level": self.year_level,
            "area_of_study": self.area_of_study,
            "syllabus_percent": syllabus_percent,
            "mobile": self.mobile,
            "address": self.address,
            "min_questions_per_skill": self.min_questions_per_skill,
            "gender": self.gender,

            # Tutor details (flattened for convenience)
            "tutor_id": tutor_user.id if tutor_user else None,
            "tutor_name": tutor_user.get_full_name() if tutor_user else None,
            "tutor_mobile": tutor_profile.mobile if tutor_profile else None,
            "tutor_address": tutor_profile.address if tutor_profile else None,

            # Booking info (already unified via booking.to_dict())
            "booking_mode": booking_mode['mode'],
            "next_booking": booking_mode['next_booking'],
            "next_ad_hoc_booking": booking_mode['adhoc'],
            "next_weekly_booking": booking_mode['weekly'],
        }

class UserPreference(models.Model):
    user = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="preferences")
    key = models.CharField(max_length=100)
    value = models.JSONField()
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("user", "key")

    def __str__(self):
        return f"{self.user} – {self.key} = {self.value}"

class TutorProfile(models.Model):
    # Branding
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="tutor")
    logo = models.ImageField(upload_to='branding/', null=True, blank=True)
    color_scheme = models.CharField(max_length=20, null=True, blank=True)
    welcome_message = models.TextField(null=True, blank=True)
    token = models.CharField(max_length=64, unique=True, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    mobile = models.CharField(max_length=20, blank=True, null=True, default='0493461541')
    address = models.CharField(max_length=255, blank=True, null=True)


    # Bookings
    default_session_minutes = models.IntegerField(default=60)
    buffer_minutes = models.IntegerField(default=15)
    default_hourly_rate = models.DecimalField(max_digits=8, decimal_places=2, default=70)

    # Registration / application
    qualification = models.CharField(max_length=255, blank=True, null=True)
    university = models.CharField(max_length=255, blank=True, null=True)
    tutor_year_levels = models.JSONField(default=list)
    bio = models.TextField(blank=True, null=True)
    approved = models.BooleanField(default=False)

    # Availability
    looking_for_students = models.BooleanField(default=True)
    edit_syllabus = models.BooleanField(default=False)

    # Stripe Connect
    stripe_account_id = models.CharField(max_length=200, blank=True, null=True)

    def __str__(self): return f"{self.tutor}"

    def to_dict(self):
        u = self.tutor

        # If you want to show next bookings on TutorHomePage:
        # next_adhoc = u.next_ad_hoc_booking()
        # next_weekly = u.next_weekly_booking()

        return {
            # User identity
            "user_id": u.id,
            "profile_id": self.id,
            "first_name": u.first_name,
            "last_name": u.last_name,
            "name": u.get_full_name() or u.username,
            "email": u.email,
            "active": u.active,

            # Tutor profile fields
            "approved": self.approved,
            "mobile": format_mobile(self.mobile),
            "address": self.address,
            "default_session_minutes": self.default_session_minutes,
            "buffer_minutes": self.buffer_minutes,
            "looking_for_students": self.looking_for_students,
            "default_hourly_rate": str(self.default_hourly_rate),

            # Booking info (mirrors student structure)
            # "next_ad_hoc_booking": next_adhoc,
            # "next_weekly_booking": next_weekly,

            # Optional: combined next booking (same as student home)
            # "next_booking": next_adhoc or next_weekly,
        }


    def appointment_status(self, date_obj, time_obj, student=None):
        dt = make_aware(datetime.combine(date_obj, time_obj))

        if TutorBlockedDay.objects.filter(tutor=self.tutor, date=date_obj).exists(): return "blocked"
        appt = BookingAdhoc.objects.filter(tutor=self.tutor, start_datetime__lte=dt, end_datetime__gt=dt).first()
        if appt:
            print("BookingAdhoc status:", appt.student, student)
            if student and appt.student == student:
                return "booked_self"
            return "booked_other"

        weekday = date_obj.weekday()  # Monday=0 ... Sunday=6
        availability = TutorAvailability.objects.filter(tutor=self.tutor, weekday=weekday)
        if not availability.exists(): return "outside"
        for window in availability:
            if window.start_time <= time_obj < window.end_time:
                return "available"
        return "outside"

    def appointment_status_fast(
        self,
        date_obj,
        time_obj,
        student,
        blocked_days,
        appointments_by_date,
        availability_by_weekday,
    ):
        # 1. Blocked day
        if date_obj in blocked_days:
            return "blocked", None

        dt = make_aware(datetime.combine(date_obj, time_obj))

        # 2. BookingAdhoc check (using pre-fetched appointments for that date)
        for appt in appointments_by_date.get(date_obj, []):
            if appt.start_datetime <= dt < appt.end_datetime:
                if student and appt.student == student:
                    return "booked_self", appt
                return "booked_other", appt

        # 3. Availability windows
        weekday = date_obj.weekday()  # Monday=0 ... Sunday=6
        windows = availability_by_weekday.get(weekday, [])
        for window in windows:
            if window.start_time <= time_obj < window.end_time:
                return "available", None

        # 4. Outside availability
        return "outside", None




    def is_available(self, date, start, end):
        start_available = self.appointment_status(date, start) == "available"
        end_available = self.appointment_status(date, end) == "available"
        print("Is available (start, end):", start_available, self.appointment_status(date, start), end_available,
              self.appointment_status(date, end))
        return start_available and end_available


class Skill(models.Model):
    parent = models.ForeignKey("self", null=True, blank=True, on_delete=models.CASCADE, related_name="children")
    code = models.CharField(max_length=100)
    description = models.TextField()
    grades = models.CharField(max_length=50, null=True, blank=True)
    order_index = models.IntegerField(default=0)
    is_detail = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.code}: {self.description[:40]}"

    def direct_templates(self):
        return Template.objects.filter(skill_detail=self)

    def get_grade_list(self):
        if not self.grades:
            return []
        raw = [g.strip() for g in self.grades.split(",") if g.strip()]
        parsed = []
        for g in raw:
            if g.upper() == "K":
                parsed.append("K")
            else:
                try:
                    parsed.append(int(g))
                except ValueError:
                    parsed.append(g)
        return parsed

    def template_count(self):
        def collect_ids(skill):
            ids = [skill.id]
            for child in skill.children.all():
                ids.extend(collect_ids(child))
            return ids
        skill_ids = collect_ids(self)
        return Template.objects.filter(skill_detail_id__in=skill_ids).count()

    def validated_count(self):
        return Template.objects.filter(skill_detail=self, validated=True).count()

    def unvalidated_count(self):
        return Template.objects.filter(skill_detail=self, validated=False).count()



class StudentSkillMatrix(models.Model):
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    mastery = models.FloatField(default=0.0)  # 0–1 or 0–100
    evidence_count = models.IntegerField(default=0)
    recent_correct_rate = models.FloatField(default=0.0)
    confidence = models.FloatField(default=0.0)

    last_updated = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ("student", "skill")


class StudentTemplateProgress(models.Model):
    """Tracks per-template progress for the competency system."""
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='template_progress')
    template_id = models.IntegerField()
    skill_code = models.CharField(max_length=100)
    difficulty = models.CharField(max_length=10)
    ever_correct = models.BooleanField(default=False)
    # Date of first correct answer in the current robustness attempt (None if broken by incorrect).
    streak_start_date = models.DateField(null=True, blank=True)
    has_robust = models.BooleanField(default=False)
    last_answered_date = models.DateField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'template_id')
        indexes = [
            models.Index(fields=['student', 'skill_code', 'difficulty']),
        ]

    def __str__(self):
        status = 'robust' if self.has_robust else ('started' if self.ever_correct else 'unseen')
        return f"Progress[student={self.student_id} t={self.template_id} {status}]"


class StudentSkillCompetency(models.Model):
    """7-level (0–6) competency per student per skill. Replaces StudentSkillMatrix."""
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='skill_competency')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    level = models.IntegerField(default=0)  # 0–6
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = ('student', 'skill')

    def __str__(self):
        return f"Competency[student={self.student_id} skill={self.skill.code} L{self.level}]"


class StudentFocusArea(models.Model):
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='focus_areas')
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    added_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='focus_areas_added')
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    # Stores the Monday date of the week in which learning/tutoring was last completed.
    # Null means never done. Compare to _this_weeks_monday() to check "this week".
    learning_done_week = models.DateField(null=True, blank=True)
    tutoring_done_week = models.DateField(null=True, blank=True)
    # Competency level snapshotted when this week's learning session starts and ends.
    level_before_learning = models.IntegerField(null=True, blank=True)
    level_after_learning = models.IntegerField(null=True, blank=True)

    class Meta:
        unique_together = ('student', 'skill')
        ordering = ['order', 'id']


class SessionSkillSnapshot(models.Model):
    """Records a student's competence level per skill at the end of each tutoring session."""
    session = models.ForeignKey('TutoringSession', on_delete=models.CASCADE, related_name='skill_snapshots')
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)
    mastery = models.FloatField()
    competence_label = models.CharField(max_length=20)
    recorded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('session', 'skill')
        ordering = ['recorded_at']


class WeeklyProgressSnapshot(models.Model):
    SOURCE_CHOICES = [
        ('post_session', 'Post Session'),
        ('scheduled', 'Scheduled'),
    ]
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='weekly_progress_snapshots',
    )
    score = models.FloatField()  # 0–100+ percentage (same scale as the progress chart)
    recorded_at = models.DateTimeField(auto_now_add=True)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)

    class Meta:
        ordering = ['recorded_at']


class TutorJob(models.Model):
    JOB_TYPES = [
        ('post_tuition_review', 'Post Tuition Review'),
        ('send_progress_message', 'Send Progress Message'),
        ('review_focus_area', 'Review Focus Area'),
        ('review_available_hours', 'Review My Available Hours'),
        ('setup_weekly_session', 'Set Up Weekly Session'),
        ('set_fee', 'Set Your Tutoring Fee'),
        ('payment_failed', 'Payment Failed'),
        ('payment_overdue_7', 'Payment Overdue — 7 Days'),
        ('payment_overdue_14', 'Payment Overdue — 14 Days — Sessions Paused'),
        ('confirm_payment_receipt', 'Confirm Payment Receipt'),
    ]
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='tutor_jobs')
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True, related_name='student_jobs')
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    session = models.ForeignKey('TutoringSession', on_delete=models.SET_NULL, null=True, blank=True, related_name='jobs')
    # Identifies the booking occurrence that triggered this job, e.g.
    # "adhoc_42" or "weekly_7_2026-04-14".  Used to prevent duplicate creation.
    booking_ref = models.CharField(max_length=80, null=True, blank=True)
    booking_outcome = models.OneToOneField(
        'BookingOutcome',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='job',
    )
    triggered_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()
    completed_at = models.DateTimeField(null=True, blank=True)
    show_from = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['triggered_at']


class AdminJob(models.Model):
    JOB_TYPES = [
        ('approve_distributor', 'Approve Distributor'),
        ('approve_tutor', 'Approve Tutor'),
        ('payment_failed', 'Payment Failed'),
        ('payment_overdue_7', 'Payment Overdue — 7 Days'),
        ('payment_overdue_14', 'Payment Overdue — 14 Days'),
        ('low_session_rating', 'Low Session Rating'),
        ('setup_bank_details', 'Setup Bank Details'),
        ('tutor_removed', 'Tutor Removed'),
        ('call_tutor_overdue_review', 'Call Tutor — Overdue Review'),
    ]
    job_type = models.CharField(max_length=50, choices=JOB_TYPES)
    subject = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name='admin_jobs',
    )
    notes = models.TextField(blank=True, null=True)
    triggered_at = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['triggered_at']


class TutorAvailability(models.Model):
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    weekday = models.IntegerField()
    start_time = models.TimeField()
    end_time = models.TimeField()
    def __str__(self): return f"{self.weekday}, {self.start_time}= {self.end_time}"



class TutorBlockedDay(models.Model):
    tutor = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    date = models.DateField()



class Notification(models.Model):
    recipient = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    message = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)

class TemplateGroup(models.Model):
    name = models.CharField(max_length=200, blank=True, null=True)
    skill_detail = models.ForeignKey(Skill, null=True, blank=True, on_delete=models.SET_NULL, related_name="template_groups")
    grade = models.CharField(max_length=10, null=True, blank=True)
    # class Meta:
    #     constraints = [
    #         models.UniqueConstraint(fields=["group", "difficulty"], name="unique_difficulty_per_group")
    #     ]

    def __str__(self):
        return self.name or f"Group {self.id}"

    def create_version(self, difficulty: str):
        """
        Create (or return existing) Template for this group at the given difficulty.
        Copies YAML content from the next-easiest available version.
        """

        # If it already exists, return it
        existing = self.templates.filter(difficulty=difficulty).first()
        if existing:
            return existing, False

        # Determine source template for copying content
        source = None

        if difficulty == "medium":
            source = self.templates.filter(difficulty="easy").first()

        elif difficulty == "hard":
            # Prefer medium, fallback to easy
            source = (
                self.templates.filter(difficulty="medium").first()
                or self.templates.filter(difficulty="easy").first()
            )

        # Copy content if source exists
        copied_content = source.content if source else ""

        # Create new template
        tpl = Template.objects.create(
            group=self,
            difficulty=difficulty,
            grade=self.grade,
            skill_detail=self.skill_detail,
            name=f"{self.name} ({difficulty.capitalize()})",
            content=copied_content,
            status="draft",
        )

        return tpl, True



class Template(models.Model):
    # --- Core content ---
    name = models.CharField(max_length=200, blank=True, null=True)
    description = models.TextField(blank=True)

    # Raw YAML/JSON template content
    content = models.TextField(blank=True, null=True)

    # --- Metadata ---
    topic = models.CharField(max_length=100, blank=True)
    subtopic = models.CharField(max_length=100, blank=True)
    grade = models.CharField(max_length=10, null=True, blank=True)
    difficulty = models.CharField(max_length=50, blank=True)
    tags = models.JSONField(default=list, blank=True)
    group = models.ForeignKey(TemplateGroup, null=True, blank=True, on_delete=models.SET_NULL, related_name="templates")


    curriculum = models.JSONField(default=list, blank=True)
    skill_detail = models.ForeignKey(Skill, null=True, blank=True, on_delete=models.SET_NULL, related_name='templates')
    validated = models.BooleanField(default=False)

    @property
    def skill(self):
        return self.skill_detail.parent if self.skill_detail else None

    # --- Workflow state ---
    STATUS_CHOICES = [
        ("draft", "Draft"),
        ("validated", "Validated"),
        ("published", "Published"),
    ]
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="draft")

    # --- Versioning ---
    version = models.IntegerField(default=1)

    # --- Ownership & audit ---
    created_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="templates_created")
    updated_by = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, related_name="templates_updated")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # --- Flags for quality control ---
    has_preview = models.BooleanField(default=False)  # set true once preview successfully generated
    last_validated_at = models.DateTimeField(null=True, blank=True)
    knowledge_items = models.ManyToManyField('Knowledge', blank=True, related_name='templates')

    # --- Translation ---
    language = models.CharField(max_length=10, default='en')
    parent_template = models.ForeignKey(
        'self', null=True, blank=True, on_delete=models.SET_NULL, related_name='translations'
    )

    def __str__(self):
        detail = self.skill_detail.description if self.skill_detail else "—"
        return f"{detail} (v{self.version})"

class TutoringSession(models.Model):
    """Tracks an active or past online tutoring session between a tutor and student."""
    room_name = models.CharField(max_length=100, unique=True)
    tutor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        related_name="tutoring_sessions_tutor",
        on_delete=models.CASCADE,
    )
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        related_name="tutoring_sessions_student",
        on_delete=models.CASCADE,
    )
    active_template = models.ForeignKey(
        "Template",
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name="+",
    )
    session_mode = models.CharField(max_length=20, null=True, blank=True)  # 'focus_area' | 'assessment'
    session_state = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_called_at = models.DateTimeField(null=True, blank=True)
    student_joined_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Session {self.room_name}"


class Knowledge(models.Model):
    """
    A reusable piece of knowledge (formula, rule, definition) attached to one
    or more Skills.  Shown alongside the solution whenever a question from one
    of those skills is answered, so students always see the same canonical
    explanation for a concept.
    """
    title = models.CharField(max_length=200)
    text = models.TextField(blank=True)
    diagram = models.TextField(blank=True)
    text_2 = models.TextField(blank=True)
    skills = models.ManyToManyField(Skill, blank=True, related_name="knowledge_items")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "text": self.text,
            "diagram": self.diagram,
            "skill_ids": list(self.skills.values_list("id", flat=True)),
        }


class TemplateDiagram(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    svg_spec = models.TextField()

class TemplateSkill(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    skill = models.ForeignKey(Skill, on_delete=models.CASCADE)

    class Meta:
        unique_together = ("template", "skill")

class Question(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="question_instances")
    params = models.JSONField()
    question_text = models.TextField()
    correct_answer = models.TextField()
    help_requested = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    selected_answer = models.TextField(null=True)
    correct = models.BooleanField(default=True)
    time_taken_ms = models.IntegerField(null=True, blank=True)

    def __str__(self):
        return f"Instance {self.id} of {self.template.name}"

class QuestionAttempt(models.Model):
    question = models.ForeignKey(Question, null=True, on_delete=models.CASCADE)
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, on_delete=models.CASCADE)
    template = models.ForeignKey(Template, null=True, on_delete=models.CASCADE)

    skills = models.JSONField(null=True)
    selected_answer = models.TextField(null=True)
    correct = models.BooleanField(default=True)
    time_taken_ms = models.IntegerField(null=True, blank=True)

    attempted_at = models.DateTimeField(auto_now_add=True, null=True)

class Task(models.Model):
    student = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

class TaskItem(models.Model):
    task = models.ForeignKey(Task, on_delete=models.CASCADE)
    question = models.ForeignKey(Question, null=True, on_delete=models.CASCADE)

class SyllabusMapping(models.Model):
    template = models.ForeignKey(Template, on_delete=models.CASCADE)
    region = models.CharField(max_length=50)
    outcome_code = models.CharField(max_length=50)

class Note(models.Model):
    author = models.ForeignKey(django_settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="notes")
    template = models.ForeignKey(Template, null=True, blank=True, on_delete=models.SET_NULL, related_name="notes")
    text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    category = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        if self.template:
            return f"Note by {self.author} on {self.template.name}"
        return f"Note by {self.author} (general)"

# Global

class GlobalSetting(models.Model):
    key = models.CharField(max_length=100, unique=True)
    value = models.CharField(max_length=500)

    def __str__(self):
        return f"{self.key} = {self.value}"

    @staticmethod
    def get(key, default=None):
        try:
            return GlobalSetting.objects.get(key=key).value
        except GlobalSetting.DoesNotExist:
            return default
        except Exception:
            # Table may not exist yet (pre-migration) — return default safely
            return default

    @staticmethod
    def set(key, value):
        obj, _ = GlobalSetting.objects.update_or_create(
            key=key,
            defaults={"value": value},
        )
        return obj

def get_bool(key, default=False):
    cache_key = f"global_setting_{key}"
    val = cache.get(cache_key)
    if val is None:
        val = GlobalSetting.get(key, default)
        # print("Get bool (db):", val)
        global_settings_cache_min = get_int("global_settings_cache_min", 10)
        cache.set(cache_key, val, global_settings_cache_min * 60)
    if isinstance(val, bool):
        return val
    return str(val).lower() in ("1", "true", "yes", "on")

def get_int(key, default=0):
    cache_key = f"global_setting_{key}"
    val = cache.get(cache_key)

    if val is None:
        val = GlobalSetting.get(key, default)
        cache.set(cache_key, val, 2 * 60)

    try:
        return int(val)
    except (TypeError, ValueError):
        return default

def get_decimal(key, default="0"):
    """Return a GlobalSetting value as a Decimal, cached for 2 minutes."""
    import decimal
    cache_key = f"global_setting_{key}"
    val = cache.get(cache_key)

    if val is None:
        val = GlobalSetting.get(key, default)
        cache.set(cache_key, val, 2 * 60)

    try:
        return decimal.Decimal(str(val))
    except (decimal.InvalidOperation, TypeError):
        return decimal.Decimal(str(default))

# Messaging

class SMSConversation(models.Model):
    tutor = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sms_conversations_as_tutor")
    student = models.ForeignKey(User, on_delete=models.CASCADE, related_name="sms_conversations_as_student")
    created_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tutor} {self.student}"

class SMSMessage(models.Model):
    direction = models.CharField(max_length=10, choices=[("outbound", "Outbound"), ("inbound", "Inbound")])
    conversation = models.ForeignKey(SMSConversation, on_delete=models.CASCADE, related_name="messages")
    body = models.TextField()
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    provider_message_id = models.CharField(max_length=100, null=True, blank=True)
    status = models.CharField(max_length=20, default="queued")
    created_at = models.DateTimeField(auto_now_add=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    delivered_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.body} (Sent: {format_sms_datetime_django(self.sent_at)})"

    @property
    def tutor(self):
        return self.conversation.tutor

    @property
    def student(self):
        return self.conversation.student

    def to_dict(self):
        return {
            "id": self.id,
            "direction": self.direction,
            "tutor_id": self.tutor.id,
            "student_id": self.student.id,
            "student_name": f"{self.student.first_name} {self.student.last_name}",
            "body": self.body,
            "created_at": self.created_at.isoformat(),
            "sent_at": self.sent_at.isoformat() if self.sent_at else None,
            "status": self.status,
        }

class SMSSendJob(models.Model):
    conversation = models.ForeignKey(SMSConversation, blank=True, null=True, on_delete=models.CASCADE, related_name="jobs")
    to_number = models.CharField(max_length=20, null=True, blank=True)  # used when no conversation
    message_type = models.CharField(max_length=60, null=True, blank=True)
    body = models.TextField()
    scheduled_for = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)
    cancelled = models.BooleanField(default=False)

    last_error = models.TextField(null=True, blank=True)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    retry_count = models.IntegerField(default=0)

    def __str__(self):
        result = f"{self.conversation}"
        if self.cancelled:
            result += " [Sent]"
        return result

    @property
    def time_until_sent(self):
        return self.scheduled_for - timezone.now()

    def to_dict(self):
        student = self.conversation.student
        tutor = self.conversation.tutor

        return {
            "id": self.id,
            "tutor_id": tutor.id,
            "student_id": student.id,
            "student_name": f"{student.first_name} {student.last_name}",
            "body": self.body,
            "created_at": self.created_at.isoformat(),
            "scheduled_for": self.scheduled_for.isoformat(),
            "time_until_sent_seconds": self.time_until_sent.total_seconds(),
            "cancelled": self.cancelled,
        }


class AdminEmailRecord(models.Model):
    to_email = models.EmailField()
    to_name = models.CharField(max_length=255, blank=True, default='')
    subject = models.CharField(max_length=255)
    body = models.TextField()
    sent_at = models.DateTimeField(auto_now_add=True)
    sent_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name='sent_admin_emails'
    )
    status = models.CharField(max_length=20, default='sent')  # 'sent' | 'failed'
    error = models.TextField(blank=True, default='')

    class Meta:
        ordering = ['-sent_at']

    def __str__(self):
        return f"Email to {self.to_email} — {self.subject}"


class ParentFeedback(models.Model):
    parent = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='feedback_submitted',
    )
    body = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    admin_response = models.TextField(blank=True, null=True)
    responded_at = models.DateTimeField(null=True, blank=True)
    responded_by = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='feedback_responses',
    )

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"Feedback from {self.parent} ({self.created_at.date()})"


def get_or_create_conversation(tutor, student):
    convo, created = SMSConversation.objects.get_or_create(
        tutor=tutor,
        student=student
    )
    return convo


class TestSession(models.Model):
    STATUS_ACTIVE = 'active'
    STATUS_COMPLETED = 'completed'
    STATUS_ABANDONED = 'abandoned'
    STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ABANDONED, 'Abandoned'),
    ]

    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='test_sessions',
    )
    started_at = models.DateTimeField(default=timezone.now)
    completed_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_ACTIVE)
    skill_codes = models.JSONField(default=list)
    current_skill_index = models.IntegerField(default=0)
    current_difficulty = models.CharField(max_length=10, default='easy')
    correct_streak = models.IntegerField(default=0)
    incorrect_count = models.IntegerField(default=0)
    used_template_ids = models.JSONField(default=list)
    test_type = models.CharField(
        max_length=10,
        choices=[('easy', 'Easy'), ('medium', 'Moderate'), ('hard', 'Hard')],
        default='',
        blank=True,   # empty string = legacy adaptive test
    )
    # 'test': 1-correct→harder, 1-incorrect→next skill
    # 'learning': two loops through all templates with difficulty adjustment between loops
    # '': legacy adaptive behaviour
    mode = models.CharField(max_length=20, default='', blank=True)
    # JSON state for learning mode: loop, loop_remaining, loop1_correct, loop1_total, etc.
    mode_state = models.JSONField(default=dict)
    # When set, marks this focus area's learning_done_week on session completion.
    linked_focus_area = models.ForeignKey(
        'StudentFocusArea',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='learning_sessions',
    )
    # Set when the session is started from the tutor chat panel (Focus Area mode).
    # On completion, marks the focus area's tutoring_done_week.
    linked_tutoring_focus_area = models.ForeignKey(
        'StudentFocusArea',
        null=True, blank=True,
        on_delete=models.SET_NULL,
        related_name='tutoring_learning_sessions',
    )

    class Meta:
        ordering = ['-started_at']

    def __str__(self):
        return f"TestSession {self.id} — {self.student} ({self.status})"


class TestSkillResult(models.Model):
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name='skill_results')
    skill_code = models.CharField(max_length=100)
    skill_description = models.CharField(max_length=255, blank=True)
    highest_difficulty_reached = models.CharField(max_length=10, default='none')
    questions_asked = models.IntegerField(default=0)
    questions_correct = models.IntegerField(default=0)
    completed_at = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.skill_code}: {self.highest_difficulty_reached}"


class TestQuestionResult(models.Model):
    """Records every individual question answered in a TestSession."""
    session = models.ForeignKey(TestSession, on_delete=models.CASCADE, related_name='question_results')
    template_id = models.IntegerField()
    skill_code = models.CharField(max_length=100)
    correct = models.BooleanField()
    time_taken_ms = models.IntegerField(null=True, blank=True)
    answered_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['answered_at']

    def __str__(self):
        return f"Q{self.template_id} {'✓' if self.correct else '✗'} ({self.session_id})"


class DistributorProfile(models.Model):
    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='distributor_profile',
    )
    mobile = models.CharField(max_length=20, blank=True, null=True)
    university = models.CharField(max_length=255, blank=True, null=True)
    bio = models.TextField(blank=True, null=True)
    referral_code = models.CharField(max_length=16, unique=True, blank=True)
    approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    stripe_account_id = models.CharField(max_length=200, blank=True, null=True)

    def save(self, *args, **kwargs):
        if not self.referral_code:
            import uuid as _uid
            code = _uid.uuid4().hex[:8]
            while DistributorProfile.objects.filter(referral_code=code).exists():
                code = _uid.uuid4().hex[:8]
            self.referral_code = code
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Distributor: {self.user} ({self.referral_code})"


class DistributorParent(models.Model):
    """Links a parent to the distributor who referred them."""
    distributor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referred_parents',
    )
    parent = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='referred_by',
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ("distributor", "parent")

    def __str__(self):
        return f"{self.distributor} → {self.parent}"


class Payment(models.Model):
    """Records a single tuition payment and its allocation across parties."""

    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payments_as_student",
    )
    tutor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payments_as_tutor",
    )
    distributor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name="payments_as_distributor",
    )

    # Amounts
    amount_paid        = models.DecimalField(max_digits=10, decimal_places=2)
    amount_platform    = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_distributor = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    amount_tutor       = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    # Account references (e.g. bank account IDs, Stripe account IDs)
    account_paid        = models.CharField(max_length=255, blank=True, default="")
    account_platform    = models.CharField(max_length=255, blank=True, default="")
    account_distributor = models.CharField(max_length=255, blank=True, default="")
    account_tutor       = models.CharField(max_length=255, blank=True, default="")

    # Dates
    date_tuition = models.DateField(null=True, blank=True, help_text="Date the tuition session occurred")
    date_debit   = models.DateField(null=True, blank=True, help_text="Date the payment was debited from the payer")
    date_credit  = models.DateField(null=True, blank=True, help_text="Date the payment was credited to recipients")

    # Context
    focus_area = models.TextField(blank=True, default="")
    notes      = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-date_tuition", "-created_at"]

    def __str__(self):
        student_str = str(self.student) if self.student else "unknown student"
        return f"Payment ${self.amount_paid} — {student_str} ({self.date_tuition})"


class BookingOutcome(models.Model):
    """
    Records the outcome of a single tutoring session.
    Created by the tutor during the Post Tuition Review workflow.
    """

    tutor = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_outcomes_as_tutor',
    )
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_outcomes_as_student',
    )

    # When the session took place
    date = models.DateField()
    time = models.TimeField()

    # The message sent/to be sent to the parent after the session
    parent_message = models.TextField(blank=True, default="")

    # Skills that were the focus during this session (snapshot at time of session)
    focus_areas = models.ManyToManyField(
        'Skill',
        blank=True,
        related_name='booking_outcomes_current',
        help_text="Focus areas covered during this session.",
    )

    # Focus areas for the next session.
    # Defaults to the same as focus_areas; tutor may modify these after the session.
    focus_areas_next = models.ManyToManyField(
        'Skill',
        blank=True,
        related_name='booking_outcomes_next',
        help_text="Focus areas for the next session. Same as focus_areas unless the tutor changes them.",
    )

    # Link to the corresponding payment record (if payment has been processed)
    payment = models.ForeignKey(
        'Payment',
        on_delete=models.SET_NULL,
        null=True, blank=True,
        related_name='booking_outcomes',
    )

    # Free-form notes the tutor wants to record about the session
    notes = models.TextField(blank=True, default="")

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-date', '-time']

    def __str__(self):
        student_str = str(self.student) if self.student else "unknown"
        return f"BookingOutcome — {student_str} ({self.date})"


def _generate_class_code():
    import secrets, string as _string
    return ''.join(secrets.choice(_string.ascii_uppercase + _string.digits) for _ in range(6))


class TeacherProfile(models.Model):
    user = models.OneToOneField(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_profile',
    )
    school_name = models.CharField(max_length=200, blank=True, default='')
    approved = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"TeacherProfile({self.user})"

    def to_dict(self):
        u = self.user
        return {
            'user_id': u.id,
            'first_name': u.first_name,
            'last_name': u.last_name,
            'name': u.get_full_name() or u.username,
            'email': u.email,
            'school_name': self.school_name,
            'approved': self.approved,
        }


class TeacherClass(models.Model):
    teacher = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='teacher_classes',
    )
    name = models.CharField(max_length=100)        # e.g. "7M", "Year 10 Advanced"
    year_level = models.CharField(max_length=10)   # e.g. "7", "10"
    code = models.CharField(max_length=8, unique=True, default=_generate_class_code)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} ({self.teacher})"

    def student_count(self):
        return self.memberships.count()

    def to_dict(self):
        return {
            'id': self.id,
            'name': self.name,
            'year_level': self.year_level,
            'code': self.code,
            'student_count': self.student_count(),
            'created_at': self.created_at.isoformat(),
        }


class TeacherClassStudent(models.Model):
    teacher_class = models.ForeignKey(
        TeacherClass,
        on_delete=models.CASCADE,
        related_name='memberships',
    )
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='class_memberships',
    )
    joined_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('teacher_class', 'student')

    def __str__(self):
        return f"{self.student} in {self.teacher_class}"


class ClassAssessment(models.Model):
    STATUS_CHOICES = [('active', 'Active'), ('ended', 'Ended')]
    teacher_class = models.ForeignKey(
        TeacherClass, on_delete=models.CASCADE, related_name='assessments'
    )
    status = models.CharField(max_length=10, choices=STATUS_CHOICES, default='active')
    skill_ids = models.JSONField(default=list)  # ordered list of Skill PKs for this assessment
    started_at = models.DateTimeField(auto_now_add=True)
    ended_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"Assessment for {self.teacher_class} ({self.status})"

    def to_dict(self):
        return {
            'id': self.id,
            'class_id': self.teacher_class_id,
            'class_name': self.teacher_class.name,
            'year_level': self.teacher_class.year_level,
            'status': self.status,
            'started_at': self.started_at.isoformat(),
            'ended_at': self.ended_at.isoformat() if self.ended_at else None,
        }


class AssessmentStudentResult(models.Model):
    assessment = models.ForeignKey(
        ClassAssessment, on_delete=models.CASCADE, related_name='results'
    )
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assessment_results',
    )
    correct = models.IntegerField(default=0)
    incorrect = models.IntegerField(default=0)
    absent = models.BooleanField(default=False)
    joined_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        unique_together = ('assessment', 'student')

    def __str__(self):
        return f"{self.student} in {self.assessment}"


class AssessmentToken(models.Model):
    """Short-lived token allowing a parent to launch a child's assessment
    without requiring the child to enter a password."""
    student = models.ForeignKey(
        django_settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='assessment_tokens',
    )
    token = models.UUIDField(default=_uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_valid(self):
        return timezone.now() < self.expires_at

    def __str__(self):
        return f"AssessmentToken({self.student}, expires {self.expires_at})"


# ── Payment flow ──────────────────────────────────────────────────────────────

class SessionPayment(models.Model):
    """Stripe-integrated payment for a completed tutoring session."""
    STATUS_CHOICES = [
        ('pending',     'Pending'),
        ('authorised',  'Authorised'),
        ('paid',        'Paid'),
        ('confirmed',   'Confirmed'),
        ('failed',      'Failed'),
        ('overdue_7',   'Overdue 7d'),
        ('overdue_14',  'Overdue 14d'),
    ]

    session      = models.OneToOneField('TutoringSession', on_delete=models.CASCADE, related_name='session_payment', null=True, blank=True)
    student      = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_payments_as_student')
    parent       = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_payments_as_parent')
    tutor        = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='session_payments_as_tutor')
    distributor  = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.SET_NULL, null=True, blank=True, related_name='session_payments_as_distributor')

    tutor_amount        = models.DecimalField(max_digits=8, decimal_places=2)
    platform_amount     = models.DecimalField(max_digits=8, decimal_places=2, default=6.50)
    distributor_amount  = models.DecimalField(max_digits=8, decimal_places=2, default=0.00)
    total_amount        = models.DecimalField(max_digits=8, decimal_places=2)

    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')

    stripe_payment_intent_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_customer_id       = models.CharField(max_length=200, blank=True, null=True)

    created_at               = models.DateTimeField(auto_now_add=True)
    authorised_at            = models.DateTimeField(null=True, blank=True)
    paid_at                  = models.DateTimeField(null=True, blank=True)
    confirmed_at             = models.DateTimeField(null=True, blank=True)
    expected_settlement_date = models.DateField(null=True, blank=True)

    rating         = models.IntegerField(null=True, blank=True)
    rating_comment = models.TextField(blank=True, null=True)

    class Meta:
        ordering = ['-created_at']

    def __str__(self):
        return f"SessionPayment #{self.id} — {self.parent} — ${self.total_amount} — {self.status}"

    def _focus_areas(self):
        """Return focus area descriptions from the linked BookingOutcome, if any."""
        try:
            outcome = BookingOutcome.objects.filter(
                tutor=self.tutor,
                student=self.session.student,
            ).order_by('-date').first()
            if outcome:
                return [s.description for s in outcome.focus_areas.all()]
        except Exception:
            pass
        return []

    def _parent_message(self):
        try:
            outcome = BookingOutcome.objects.filter(
                tutor=self.tutor,
                student=self.session.student,
            ).order_by('-date').first()
            return outcome.parent_message if outcome else ""
        except Exception:
            return ""

    def to_dict(self):
        return {
            'id': self.id,
            'status': self.status,
            'tutor_amount': str(self.tutor_amount),
            'platform_amount': str(self.platform_amount),
            'distributor_amount': str(self.distributor_amount),
            'total_amount': str(self.total_amount),
            'tutor_name': self.tutor.get_full_name(),
            'tutor_id': self.tutor.id,
            'parent_id': self.parent.id,
            'session_id': self.session.id if self.session else None,
            'session_date': self.session.created_at.date().isoformat() if self.session else self.created_at.date().isoformat(),
            'child_name': (self.session.student if self.session else self.student).first_name if (self.session or self.student) else '',
            'focus_areas': self._focus_areas(),
            'parent_message': self._parent_message(),
            'rating': self.rating,
            'student_name': (self.session.student if self.session else self.student).get_full_name() if (self.session or self.student) else '',
            'created_at': self.created_at.isoformat(),
            'paid_at': self.paid_at.isoformat() if self.paid_at else None,
            'confirmed_at': self.confirmed_at.isoformat() if self.confirmed_at else None,
            'expected_settlement_date': self.expected_settlement_date.isoformat() if self.expected_settlement_date else None,
        }


class ParentPaymentProfile(models.Model):
    """Stores the parent's Stripe customer ID and saved payment method."""
    parent             = models.OneToOneField(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='payment_profile')
    stripe_customer_id = models.CharField(max_length=200, blank=True, null=True)
    stripe_pm_id       = models.CharField(max_length=200, blank=True, null=True)
    card_last4         = models.CharField(max_length=4, blank=True, null=True)
    card_brand         = models.CharField(max_length=20, blank=True, null=True)
    setup_complete     = models.BooleanField(default=False)
    created_at         = models.DateTimeField(auto_now_add=True)
    updated_at         = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"PaymentProfile — {self.parent} — {'setup' if self.setup_complete else 'not setup'}"


class ParentJob(models.Model):
    JOB_TYPES = [
        ('payment_due',      'Payment Due'),
        ('payment_failed',   'Payment Failed — Update Card'),
        ('payment_overdue_7',  'Payment Overdue — 7 Days'),
        ('payment_overdue_14', 'Payment Overdue — Sessions Paused'),
    ]
    parent       = models.ForeignKey(django_settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='parent_jobs')
    payment      = models.ForeignKey(SessionPayment, on_delete=models.CASCADE, related_name='parent_jobs')
    job_type     = models.CharField(max_length=50, choices=JOB_TYPES)
    created_at   = models.DateTimeField(auto_now_add=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        ordering = ['created_at']
