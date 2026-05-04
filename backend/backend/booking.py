from rest_framework.response import Response

from .cache import *
from .utilities import *
from .message import *

def create_booking(tutor, data, booking_type, user_role):
    student_id = data.get("student_id")
    student = User.objects.filter(id=student_id).first()
    if not student:
        return Response({"ok": False, "error": "Student not found"}, status=404)

    confirmed = True
    if user_role == "student": confirmed = False


    if booking_type == "weekly":
        weekday = data.get("weekday")
        time_str = data.get("time")
        if weekday is None or not time_str:
            return Response({"ok": False, "error": "weekday and time required"}, status=400)

        start_time, end_time = get_times(time_str, tutor.default_session_minutes)

        booking = BookingWeekly.objects.create(
            tutor=tutor,
            student=student,
            weekday=weekday,
            start_time=start_time,
            end_time=end_time,
            confirmed=confirmed,
        )
        sms_enqueue(booking, "create_weekly", user_role)

    else:  # adhoc
        print("Create ad hoc")
        dt_str = data.get("start_time")
        start_dt, end_dt = get_datetimes(dt_str, tutor.default_session_minutes)
        print("Create ad hoc", start_dt, end_dt)

        booking = BookingAdhoc.objects.create(
            tutor=tutor,
            student=student,
            start_datetime=start_dt,
            end_datetime=end_dt,
            confirmed=confirmed,
        )
        sms_enqueue(booking, "create_adhoc", user_role)

    update_booking_caches(booking, "create")
    return Response({"ok": True, "id": booking.id})

def confirm_booking(booking, user_role):
    booking.confirmed = not booking.confirmed
    if user_role == "student": booking.confirmed = False
    booking.save()

    update_booking_caches(booking, "confirm")
    if booking.confirmed:
        sms_enqueue(booking, "confirmed", user_role)
    else:
        sms_enqueue(booking, "unconfirmed", user_role)

    return Response({"ok": True, "confirmed": booking.confirmed})

def edit_booking(booking, data, booking_type, user_role):
    duration = int(data.get("duration", 60))
    changed_date_or_starttime = False

    if booking_type in ["weekly", "weekly_paused"]:
        weekday = data.get("weekday")
        start_time_str = data.get("start_time")
        start_time, end_time = get_times(start_time_str, duration)

        if booking.weekday != weekday or booking.start_time != start_time: changed_date_or_starttime = True

        booking.weekday = weekday
        booking.start_time = start_time
        booking.end_time = end_time

    else:  # adhoc
        start_datetime_str = data.get("start_time")
        start_dt, end_dt = get_datetimes(start_datetime_str, duration)
        if booking.start_datetime != start_dt : changed_date_or_starttime = True

        booking.start_datetime = start_dt
        booking.end_datetime = end_dt

    if user_role == "student": booking.confirmed = False
    booking.save()
    update_booking_caches(booking, "edit")
    if changed_date_or_starttime:
        sms_enqueue(booking, "updated", user_role)

    return Response({"ok": True, "edit": booking.id})

def skip_booking(booking, user_role):
    booking.skip()
    update_booking_caches(booking, "skip")
    sms_enqueue(booking, "skipped", user_role)

    return Response({"ok": True, "skip": booking.id})

def remove_skip_booking(booking, user_role):
    booking.remove_skip()
    update_booking_caches(booking, "remove_skip")
    sms_enqueue(booking, "unskipped", user_role)

    return Response({"ok": True, "remove_skip": booking.id})

def delete_booking(booking, booking_type, user_role):
    if booking_type in ["adhoc"]:
        sms_enqueue(booking, "cancelled_adhoc", user_role)
    else:
        sms_enqueue(booking, "cancelled_weekly", user_role)
    update_booking_caches(booking, "delete")
    booking.delete()

    return Response({"ok": True, "deleted": True})