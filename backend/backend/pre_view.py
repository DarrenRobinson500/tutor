from .cache import *

def get_combined_calendar(tutor, start_date_iso):
    start_date = date.fromisoformat(start_date_iso)
    today = date.today()

    # These now return fully-normalised dicts with:
    # start_time, end_time, start_date, day_str, duration_minutes, booking_type, student_can_edit
    weekly_bookings = get_weekly_bookings(tutor)      # { weekday: [dict, dict...] }
    adhoc_bookings = get_adhoc_bookings(tutor, start_date_iso)  # { "YYYY-MM-DD": [dict...] }

    result = {}

    for i in range(7):
        day = (start_date + timedelta(days=i))
        day_str = day.isoformat()
        weekday = day.weekday()

        # Determine day status
        if day < today:
            day_status = "past"
        elif day == today:
            day_status = "today"
            # otherwise
        else:
            day_status = "future"

        # Weekly bookings for this weekday
        weekly_for_day = []
        for b in weekly_bookings.get(weekday, []):
            # Weekly bookings already include:
            # - booking_type = "weekly"
            # - start_time, end_time, duration_minutes, start_date, day_str
            # We only need to adjust paused status.
            is_paused = False
            wb_start_date = b.get("start_date")

            if wb_start_date:
                # wb_date_str = wb_start_date.split("T")[0]
                # wb_date = date.fromisoformat(wb_date_str)
                if isinstance(wb_start_date, datetime):
                    wb_start_date = wb_start_date.date()

                # print("Get combined calendar. Types:", type(day), type(wb_start_date))

                if day < wb_start_date :
                    is_paused = True

            b = {
                **b,
                "booking_type": "weekly_paused" if is_paused else "weekly",
            }
            weekly_for_day.append(b)

        # Adhoc bookings for this exact date
        adhoc_for_day = []
        for b in adhoc_bookings.get(day_str, []):
            # Already includes booking_type="adhoc"
            adhoc_for_day.append(b)

        # Merge: adhoc overrides weekly at same start_time
        adhoc_times = {b["start_time"] for b in adhoc_for_day}
        merged = [b for b in weekly_for_day if b["start_time"] not in adhoc_times]
        merged.extend(adhoc_for_day)

        # Sort by start_time (already "HH:MM")
        merged.sort(key=lambda b: b["start_time"])

        result[day_str] = {
            "day_status": day_status,
            "bookings": merged,
        }

    return result