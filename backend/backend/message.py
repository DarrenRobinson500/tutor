from .models import *
from .clicksend import *
SMS_PAUSE = timedelta(minutes=get_int("sms_pause", default=10))

def format_weekday(day_str):
    d = datetime.strptime(day_str, "%Y-%m-%d").date()
    return d.strftime("%A")

def format_time(t_str):
    t = datetime.strptime(t_str, "%H:%M").time()
    return t.strftime("%-I:%M%p").lower()

SMS_TEMPLATES = {
    # Student → Tutor
    "student_create_adhoc": ("Hi {tutor_name}, {student_name} has created a booking: {date_and_time}\n"),
    "student_create_weekly": ("Hi {tutor_name}, a weekly booking has been created by {student_name}. The first booking is {date_and_time}\n"),
    "student_updated": ("Hi {tutor_name}, your booking has been updated by {student_name}. They will see you {date_and_time}\n"),
    "student_confirmed": ("Hi {tutor_name}, your booking has been confirmed by {student_name}. They will see you {date_and_time}\n"),
    "student_unconfirmed": ("Hi {tutor_name}, your booking has been unconfirmed by {student_name}. They will not see you {date_and_time} Please call {student_name} if this is unexpected.\n"),
    "student_skipped": ("Hi {tutor_name}, your weekly booking will be skipped this week. They will see you next week {date_and_time}\n"),
    "student_unskipped": ("Hi {tutor_name}, your booking has been updated by {student_name}. They will see you {date_and_time}\n"),
    "student_cancelled_weekly": ("Hi {tutor_name}, your weekly booking with {student_name} has been cancelled."),
    "student_cancelled_adhoc": ("Hi {tutor_name}, your booking with {student_name} has been cancelled."),

    # Parent → Tutor (parent acting on behalf of student)
    "parent_create_adhoc": ("Hi {tutor_name}, a booking has been created for {student_name} by their parent. We will see you {date_and_time}\n"),
    "parent_create_weekly": ("Hi {tutor_name}, a weekly booking has been created for {student_name} by their parent. The first booking is {date_and_time}\n"),
    "parent_updated": ("Hi {tutor_name}, the booking for {student_name} has been updated by their parent. We will see you {date_and_time}\n"),
    "parent_confirmed": ("Hi {tutor_name}, the booking for {student_name} has been confirmed by their parent. We will see you {date_and_time}\n"),
    "parent_unconfirmed": ("Hi {tutor_name}, the booking for {student_name} has been unconfirmed by their parent. Please call them if this is unexpected.\n"),
    "parent_skipped": ("Hi {tutor_name}, the weekly booking for {student_name} will be skipped. Their parent has paused it.\n"),
    "parent_unskipped": ("Hi {tutor_name}, the booking pause for {student_name} has been removed by their parent. We will see you {date_and_time}\n"),
    "parent_cancelled_weekly": ("Hi {tutor_name}, the weekly booking for {student_name} has been cancelled by their parent."),
    "parent_cancelled_adhoc": ("Hi {tutor_name}, the booking for {student_name} has been cancelled by their parent."),

    # Tutor → Student
    "tutor_create_adhoc": ("Hi {student_name}, your booking has been created by {tutor_name}. We will see you {date_and_time}\n"),
    "tutor_create_weekly": ("Hi {student_name}, your weekly booking has been created by {tutor_name}. We will see you each week and the first booking is {date_and_time}\n"),
    "tutor_updated": ("Hi {student_name}, your booking has been updated by {tutor_name}. We will see you {date_and_time}\n"),
    "tutor_confirmed": ("Hi {student_name}, your booking has been confirmed by {tutor_name}. We will see you {date_and_time}\n"),
    "tutor_unconfirmed": ("Hi {student_name}, your booking has been unconfirmed by {tutor_name}. We will not see you {date_and_time} Please call {tutor_name} if this is unexpected.\n"),
    "tutor_skipped": ("Hi {student_name}, your weekly booking will be skipped this week. We will see you next week {date_and_time}\n"),
    "tutor_unskipped": ("Hi {student_name}, your booking has been updated by {tutor_name}. We will see you {date_and_time}\n"),
    "tutor_cancelled_weekly": ("Hi {student_name}, your weekly booking with {tutor_name} has been cancelled."),
    "tutor_cancelled_adhoc": ("Hi {student_name}, your booking with {tutor_name} has been cancelled."),
}

DEBOUNCE_TYPES = set(SMS_TEMPLATES.keys())

def create_sms_body(booking, message_type, user_role):
    combined_type = f"{user_role}_{message_type}"
    if combined_type not in SMS_TEMPLATES:
        print("Unknown message type:", combined_type)
        raise ValueError(f"Unknown SMS message type: {combined_type}")

    # print("Create sms body:", booking)

    weekday = booking["day_str"]
    date_and_time = format_sms_datetime(booking["start_iso"])
    start = booking["start_time"]
    end = booking["end_time"]

    context = {
        "date_and_time": date_and_time,
        "weekday": weekday,
        "start": start,
        "end": end,
        "student_name": booking.get("student_name"),
        "tutor_name": (booking.get("tutor_name") or "").split()[0] or booking.get("tutor_name"),
    }

    template = SMS_TEMPLATES[combined_type]
    return template.format(**context)

def send_approval_sms(mobile: str, first_name: str, role: str, approved_user, admin_user):
    """Create a conversation-linked SMSSendJob for an approval notification and send immediately."""
    if not mobile:
        return
    body = (
        f"Hi {first_name}, your SubjectMatter {role} account has been approved. Welcome aboard."
        f"You can now log in at subject-matter.com.au"
    )
    conversation = get_or_create_conversation(tutor=approved_user, student=admin_user)
    SMSSendJob.objects.create(
        conversation=conversation,
        to_number=mobile,
        body=body,
        scheduled_for=timezone.now(),
    )
    process_sms_jobs()


def sms_enqueue(booking, message_type, user_role):
    booking=booking.to_dict()
    tutor_id = booking["tutor_id"]
    student_id = booking["student_id"]
    conversation = get_or_create_conversation(User.objects.get(id=tutor_id), User.objects.get(id=student_id))
    combined_type = f"{user_role}_{message_type}"
    body = create_sms_body(booking, message_type, user_role)
    now = timezone.now()
    scheduled_for = now + SMS_PAUSE

    job = SMSSendJob.objects.filter(
        conversation=conversation,
        message_type=combined_type,
        cancelled=False
    ).first()

    if job:
        job.body = body
        job.scheduled_for = scheduled_for
        job.retry_count = 0
        job.save(update_fields=["body", "scheduled_for", "retry_count"])
        return job

    return SMSSendJob.objects.create(
        conversation=conversation,
        message_type=combined_type,
        body=body,
        scheduled_for=scheduled_for
    )


def process_sms_jobs():
    now = timezone.now()
    jobs = SMSSendJob.objects.filter(
        scheduled_for__lte=now,
        cancelled=False,
        retry_count__lt=3
    )

    for job in jobs:
        conversation = job.conversation

        # Resolve the destination number.
        # to_number takes priority (e.g. approval messages sent to tutor, not admin).
        # Fall back to the conversation student's mobile for regular booking SMS.
        if job.to_number:
            phone = job.to_number
        elif conversation:
            msg_type = job.message_type or ""
            if msg_type.startswith("student_") or msg_type.startswith("parent_"):
                # Message is addressed to the tutor
                try:
                    phone = conversation.tutor.tutor.mobile
                except Exception:
                    phone = None
            else:
                phone = conversation.student.student_profile.mobile
        else:
            phone = None

        if not phone:
            job.cancelled = True
            job.last_error = "No phone number"
            job.save(update_fields=["cancelled", "last_error"])
            continue

        try:
            # Attempt to send
            sms_send = get_bool("sms_send", default=False)
            print("SMS Send:", sms_send)

            if sms_send == True:
                provider_id = clicksend_send_sms(phone, job.body)
            else:
                print("SMS Fake Send:", job.body)
                provider_id = "FAKE-SEND"

            # Record the message in the conversation
            if conversation:
                SMSMessage.objects.create(
                    direction="outbound",
                    conversation=conversation,
                    body=job.body,
                    phone_number=phone,
                    provider_message_id=provider_id,
                    status="sent",
                    sent_at=now,
                )

            # Cancel the job
            job.cancelled = True
            job.last_error = None
            job.last_attempt_at = now
            job.save(update_fields=["cancelled", "last_error", "last_attempt_at"])

        except Exception as e:
            # Record failure on the job
            job.last_error = str(e)
            job.last_attempt_at = now
            job.retry_count += 1
            job.save(update_fields=["last_error", "last_attempt_at", "retry_count"])

            print("SMS sending failed:", e)