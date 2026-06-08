import uuid
from datetime import date, time, datetime, timedelta
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.hashers import make_password
from backend.models import (
    User, TutorProfile, StudentProfile, ParentPaymentProfile,
    TutorStudent, ParentChild, BookingWeekly, BookingAdhoc,
    TutoringSession, SessionPayment, Skill, Template,
    StudentSkillCompetency, StudentTemplateProgress, GlobalSetting,
)


def make_user(role='student', password='testpass123', **kwargs):
    uid = uuid.uuid4().hex[:8]
    defaults = dict(
        username=f'user_{uid}',
        email=f'user_{uid}@test.com',
        password=make_password(password),
        role=role,
    )
    defaults.update(kwargs)
    return User.objects.create(**defaults)


def make_tutor_profile(user=None, approved=True, **kwargs):
    if user is None:
        user = make_user(role='tutor')
    defaults = dict(tutor=user, approved=approved)
    defaults.update(kwargs)
    return TutorProfile.objects.create(**defaults)


def make_student_profile(user=None, **kwargs):
    if user is None:
        user = make_user(role='student')
    defaults = dict(user=user)
    defaults.update(kwargs)
    return StudentProfile.objects.create(**defaults)


def make_parent_payment_profile(user=None, setup_complete=True, stripe_customer_id='cus_test123', **kwargs):
    if user is None:
        user = make_user(role='parent')
    defaults = dict(parent=user, setup_complete=setup_complete, stripe_customer_id=stripe_customer_id)
    defaults.update(kwargs)
    return ParentPaymentProfile.objects.create(**defaults)


def make_tutor_student(tutor=None, student=None, **kwargs):
    if tutor is None:
        tutor = make_user(role='tutor')
    if student is None:
        student = make_user(role='student')
    defaults = dict(tutor=tutor, student=student)
    defaults.update(kwargs)
    return TutorStudent.objects.create(**defaults)


def make_parent_child(parent=None, student=None, **kwargs):
    # ParentChild uses 'child' not 'student'
    if parent is None:
        parent = make_user(role='parent')
    if student is None:
        student = make_user(role='student')
    defaults = dict(parent=parent, child=student)
    defaults.update(kwargs)
    return ParentChild.objects.create(**defaults)


def make_booking_weekly(tutor=None, student=None, weekday=0, start_time=None, end_time=None, **kwargs):
    # BookingWeekly has start_time + end_time (no duration_minutes field)
    if tutor is None:
        tutor = make_user(role='tutor')
    if student is None:
        student = make_user(role='student')
    if start_time is None:
        start_time = time(10, 0)
    if end_time is None:
        end_time = time(11, 0)
    defaults = dict(tutor=tutor, student=student, weekday=weekday, start_time=start_time, end_time=end_time)
    defaults.update(kwargs)
    return BookingWeekly.objects.create(**defaults)


def make_booking_adhoc(tutor=None, student=None, start_datetime=None, end_datetime=None, status='confirmed', **kwargs):
    # BookingAdhoc has start_datetime + end_datetime (no duration_minutes field) and requires status
    if tutor is None:
        tutor = make_user(role='tutor')
    if student is None:
        student = make_user(role='student')
    if start_datetime is None:
        start_datetime = timezone.now() + timedelta(days=1)
    if end_datetime is None:
        end_datetime = start_datetime + timedelta(hours=1)
    defaults = dict(tutor=tutor, student=student, start_datetime=start_datetime, end_datetime=end_datetime, status=status)
    defaults.update(kwargs)
    return BookingAdhoc.objects.create(**defaults)


def make_tutoring_session(tutor=None, student=None, **kwargs):
    # TutoringSession requires a unique room_name
    if tutor is None:
        tutor = make_user(role='tutor')
    if student is None:
        student = make_user(role='student')
    defaults = dict(
        tutor=tutor,
        student=student,
        room_name=f'room_{uuid.uuid4().hex[:12]}',
    )
    defaults.update(kwargs)
    return TutoringSession.objects.create(**defaults)


def make_session_payment(session=None, tutor=None, student=None, parent=None, status='pending', total_amount=None, tutor_amount=None, **kwargs):
    # SessionPayment has no 'booking' field; requires tutor_amount and total_amount
    if tutor is None:
        tutor = make_user(role='tutor')
    if student is None:
        student = make_user(role='student')
    if parent is None:
        parent = make_user(role='parent')
    if total_amount is None:
        total_amount = Decimal('86.50')
    if tutor_amount is None:
        tutor_amount = Decimal('80.00')
    defaults = dict(
        tutor=tutor,
        student=student,
        parent=parent,
        status=status,
        total_amount=total_amount,
        tutor_amount=tutor_amount,
    )
    if session is not None:
        defaults['session'] = session
    defaults.update(kwargs)
    return SessionPayment.objects.create(**defaults)


def make_skill(code=None, description=None, parent_skill=None, **kwargs):
    # Skill has 'code' and 'description' (required), not 'name'; no 'is_leaf' field
    if code is None:
        code = f'SK{uuid.uuid4().hex[:6].upper()}'
    if description is None:
        description = f'Skill {code}'
    defaults = dict(code=code, description=description)
    if parent_skill is not None:
        defaults['parent'] = parent_skill
    defaults.update(kwargs)
    return Skill.objects.create(**defaults)


def make_template(skill_detail=None, difficulty='easy', validated=True, **kwargs):
    # Template uses 'skill_detail' FK (not 'skill'); no 'answer' field
    if skill_detail is None:
        skill_detail = make_skill()
    defaults = dict(
        skill_detail=skill_detail,
        difficulty=difficulty,
        validated=validated,
        content='What is 2+2?',
    )
    defaults.update(kwargs)
    return Template.objects.create(**defaults)


def make_student_skill_competency(student=None, skill=None, level=0, **kwargs):
    if student is None:
        student = make_user(role='student')
    if skill is None:
        skill = make_skill()
    defaults = dict(student=student, skill=skill, level=level)
    defaults.update(kwargs)
    return StudentSkillCompetency.objects.get_or_create(student=student, skill=skill, defaults=defaults)[0]


def make_student_template_progress(student=None, template=None, skill_code=None, difficulty='easy', **kwargs):
    # StudentTemplateProgress uses template_id (IntegerField) and skill_code (CharField), not a FK
    if student is None:
        student = make_user(role='student')
    if template is None:
        template = make_template()
    if skill_code is None:
        skill_code = template.skill_detail.code if template.skill_detail else 'TEST'
    defaults = dict(
        student=student,
        template_id=template.id,
        skill_code=skill_code,
        difficulty=difficulty,
    )
    defaults.update(kwargs)
    return StudentTemplateProgress.objects.get_or_create(
        student=student,
        template_id=template.id,
        defaults=defaults,
    )[0]


def make_global_setting(key, value, **kwargs):
    obj, _ = GlobalSetting.objects.get_or_create(key=key, defaults={'value': value})
    if obj.value != value:
        obj.value = value
        obj.save()
    return obj
