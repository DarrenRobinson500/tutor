from datetime import datetime, date, time, timedelta
from django.utils.timezone import make_aware

from .models import TutorProfile, TutorAvailability, TutorBlockedDay, BookingAdhoc


# ---------------------------------------------------------
# Helper: convert HH:MM string to datetime for a given date
# ---------------------------------------------------------
def dt(day_date, t):
    return make_aware(datetime.combine(day_date, t))


# ---------------------------------------------------------
# Helper: generate time range in increments
# ---------------------------------------------------------
def time_range(start_dt, end_dt, step_minutes):
    current = start_dt
    while current + timedelta(minutes=step_minutes) <= end_dt:
        yield current
        current += timedelta(minutes=step_minutes)


# ---------------------------------------------------------
# Main weekly slot generator
# ---------------------------------------------------------
def generate_weekly_slots(tutor_profile, week_start):

    default_session = timedelta(minutes=tutor_profile.default_session_minutes)
    buffer = timedelta(minutes=tutor_profile.buffer_minutes)

    # Build the 7-day scaffold
    week = []
    for i in range(7):
        day_date = week_start + timedelta(days=i)
        week.append({
            "date": day_date,
            "availability": [],
            "blocked": False,
            "bookings": [],
            "bookable_slots": [],
            "segments": []
        })

    # ---------------------------------------------------------
    # Load availability (weekly pattern)
    # ---------------------------------------------------------
    availability = TutorAvailability.objects.filter(tutor=tutor_profile)
    availability_by_weekday = {i: [] for i in range(7)}
    for a in availability:
        availability_by_weekday[a.weekday].append(a)

    # ---------------------------------------------------------
    # Load blocked days
    # ---------------------------------------------------------

    blocked_days = set(
        TutorBlockedDay.objects.filter(tutor=tutor_profile)
        .values_list("date", flat=True)
    )

    # ---------------------------------------------------------
    # Load bookings for the week
    # ---------------------------------------------------------
    week_end = week_start + timedelta(days=7)
    bookings = BookingAdhoc.objects.filter(
        tutor=tutor_profile,
        start_datetime__date__gte=week_start,
        start_datetime__date__lt=week_end
    )

    bookings_by_date = {}
    for b in bookings:
        bookings_by_date.setdefault(b.start.date(), []).append(b)

    # ---------------------------------------------------------
    # Fill in availability, blocked, bookings
    # ---------------------------------------------------------
    for day in week:
        d = day["date"]

        # Blocked?
        if d in blocked_days:
            day["blocked"] = True

        # Availability windows
        for a in availability_by_weekday[d.weekday()]:
            day["availability"].append({
                "start": a.start_time,
                "end": a.end_time
            })

        # Bookings
        if d in bookings_by_date:
            for b in bookings_by_date[d]:
                day["bookings"].append({
                    "start": b.start,
                    "end": b.end,
                    "student": b.student_id
                })

    # ---------------------------------------------------------
    # Generate bookable slots
    # ---------------------------------------------------------

    for day in week:
        if day["blocked"]:
            continue

        d = day["date"]

        # Convert bookings to aware datetimes
        booking_intervals = [
            (b["start"], b["end"])
            for b in day["bookings"]
        ]

        for window in day["availability"]:
            start_dt = dt(d, window["start"])
            end_dt = dt(d, window["end"])

            # Candidate start times every 15 minutes
            for candidate in time_range(start_dt, end_dt, 15):

                session_end = candidate + default_session

                # Must fit inside availability
                if session_end > end_dt:
                    continue

                # Check against bookings + buffer
                valid = True
                for b_start, b_end in booking_intervals:
                    if not (
                        session_end + buffer <= b_start or
                        candidate >= b_end + buffer
                    ):
                        valid = False
                        break

                if valid:
                    day["bookable_slots"].append(candidate.time())

    # ---------------------------------------------------------
    # Build graphical segments (for student weekly view)
    # ---------------------------------------------------------
    for day in week:
        segments = []
        d = day["date"]

        # Build a 5-minute timeline
        t = time(0, 0)
        end_of_day = time(23, 59)

        for minute in range(0, 24 * 60, 5):
            t = (datetime.min + timedelta(minutes=minute)).time()

            # Determine segment type
            if day["blocked"]:
                seg_type = "blocked"

            else:
                # Check if inside availability
                in_avail = False
                for a in day["availability"]:
                    if a["start"] <= t < a["end"]:
                        in_avail = True
                        break

                # Check if inside booking
                in_booking = False
                for b in day["bookings"]:
                    if b["start"].time() <= t < b["end"].time():
                        in_booking = True
                        break

                if in_booking:
                    seg_type = "booked_other"
                elif in_avail:
                    seg_type = "available"
                else:
                    seg_type = "outside"

            segments.append({
                "time": t,
                "type": seg_type
            })

            # Increment 5 minutes
            dt_obj = datetime.combine(d, t) + timedelta(minutes=5)
            t = dt_obj.time()

        day["segments"] = segments



    return week