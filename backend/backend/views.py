from django.http import HttpResponse
from django.contrib.auth.hashers import make_password
from rest_framework.permissions import IsAuthenticated
from rest_framework import viewsets
from rest_framework.decorators import action
from rest_framework.decorators import api_view
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from django.contrib.auth import authenticate, login, logout
# from datetime import datetime, timedelta, time as dtime
from django.db.models import Case, When, Value, IntegerField, Q


from .validation import *
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import status
import yaml
from .import_skills import *
from .ai import *
from .utilities import *
from .serializers import *
from .tutor_calendar import *
from .cache import *
import time
from .template_utilities import *
from django.contrib.auth import get_user_model
User = get_user_model()
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from rest_framework_simplejwt.tokens import RefreshToken
from .pre_view import *
from .message import *
from .booking import *

@method_decorator(csrf_exempt, name='dispatch')
class AuthViewSet(viewsets.ViewSet):
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def me(self, request):
        user = request.user
        if not user or not user.is_authenticated:
            return Response({"error": "Not authenticated"}, status=401)
        return Response({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
            "last_name": user.last_name,
            "email": user.email,
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def dev_login(self, request):
        username = request.data.get("username")

        dev_users = {
            "admin": "admin",
            "alex": "Alex",
            "blair": "Blair",
        }

        if username not in dev_users:
            return Response({"error": "Unknown dev user"}, status=400)

        try:
            user = User.objects.get(username=dev_users[username])
        except User.DoesNotExist:
            return Response({"error": "User not found"}, status=404)

        # Force login (no password)
        login(request, user)

        # Return the same structure as your normal login
        return Response({
            "id": user.id,
            "username": user.username,
            "first_name": user.first_name,
            "role": user.role,
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny])
    def dev_switch_to_parent(self, request):
        """Dev-only: given a student_id, return JWT for their parent (no password required)."""
        from .models import ParentChild
        from rest_framework_simplejwt.tokens import RefreshToken as JWTRefresh
        student_id = request.data.get("student_id")
        try:
            student = User.objects.get(id=student_id, role="student")
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)

        link = ParentChild.objects.filter(child=student).select_related("parent").first()
        if not link:
            return Response({"error": "No parent linked to this student"}, status=404)

        parent = link.parent
        refresh = JWTRefresh.for_user(parent)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "id": parent.id,
            "first_name": parent.first_name,
            "last_name": parent.last_name,
            "email": parent.email,
            "role": parent.role,
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[],)
    def register(self, request):
        email = request.data.get("email")
        password = request.data.get("password")
        role = request.data.get("role")

        if not email or not password or not role:
            return Response({"error": "Missing fields"}, status=400)

        if role not in ["tutor", "parent", "student"]:
            return Response({"error": "Invalid role"}, status=400)

        if User.objects.filter(username=email).exists():
            return Response({"error": "Email already registered"}, status=400)

        user = User.objects.create(
            username=email,
            email=email,
            password=make_password(password),
            role=role,
        )

        if user.role == "tutor":
            profile = TutorProfile.objects.create(tutor=user)

        login(request, user)

        return Response({
            "id": user.id,
            "username": user.username,
            "role": user.role,
            "first_name": user.first_name,
        })

    @method_decorator(csrf_exempt, name='login')
    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[],)
    def login(self, request):
        email = request.data.get("email")
        password = request.data.get("password")

        user = authenticate(request, username=email, password=password)

        if user is None:
            print("Login: invalid credentials")
            return Response({"error": "Invalid credentials"}, status=400)

        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        edit_syllabus = False
        if user.role == "admin":
            edit_syllabus = True
        elif user.role == "tutor":
            profile = user.tutor.first()
            if profile:
                edit_syllabus = profile.edit_syllabus
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role,
                "first_name": user.first_name,
                "edit_syllabus": edit_syllabus,
            }
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def register_parent(self, request):
        """Register a parent and their first child in one step."""
        d = request.data
        parent_email = (d.get("parent_email") or "").strip()
        parent_password = d.get("parent_password", "")
        parent_confirm = d.get("parent_confirm_password", "")
        parent_first = (d.get("parent_first_name") or "").strip()
        parent_last = (d.get("parent_last_name") or "").strip()
        parent_mobile = (d.get("parent_mobile") or "").strip()

        child_first = (d.get("child_first_name") or "").strip()
        child_last = (d.get("child_last_name") or "").strip()
        child_year = (d.get("child_year_level") or "").strip()
        child_school = (d.get("child_school_name") or "").strip()
        child_mobile = (d.get("child_mobile") or "").strip()
        child_password = d.get("child_password", "")
        child_confirm = d.get("child_confirm_password", "")

        required = [parent_email, parent_password, parent_first, parent_last,
                    parent_mobile, child_first, child_last, child_year, child_password]
        if not all(required):
            return Response({"error": "Please fill in all required fields."}, status=400)
        if parent_password != parent_confirm:
            return Response({"error": "Passwords do not match."}, status=400)
        if child_password != child_confirm:
            return Response({"error": "Child's passwords do not match."}, status=400)
        if User.objects.filter(username=parent_email).exists():
            return Response({"error": "An account with this email already exists."}, status=400)

        parent_user = User.objects.create(
            username=parent_email,
            email=parent_email,
            password=make_password(parent_password),
            first_name=parent_first,
            last_name=parent_last,
            role="parent",
        )

        # Build a unique username for the child account
        base = f"student_{parent_user.id}_{child_first.lower()}"
        child_username = base
        counter = 1
        while User.objects.filter(username=child_username).exists():
            child_username = f"{base}_{counter}"
            counter += 1

        child_user = User.objects.create(
            username=child_username,
            email=f"{child_username}@students.subjectmatter.app",
            password=make_password(child_password),
            first_name=child_first,
            last_name=child_last,
            role="student",
        )
        StudentProfile.objects.create(
            user=child_user,
            year_level=child_year,
            school_name=child_school or None,
            mobile=child_mobile or None,
        )
        ParentChild.objects.create(parent=parent_user, child=child_user)

        referral_code = (d.get("referral_code") or "").strip()
        if referral_code:
            from .models import DistributorProfile, DistributorParent
            try:
                dist_profile = DistributorProfile.objects.select_related("user").get(
                    referral_code=referral_code, approved=True
                )
                DistributorParent.objects.get_or_create(
                    distributor=dist_profile.user, parent=parent_user
                )
            except DistributorProfile.DoesNotExist:
                pass  # invalid/expired code — don't block registration

        refresh = RefreshToken.for_user(parent_user)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": parent_user.id,
                "first_name": parent_user.first_name,
                "last_name": parent_user.last_name,
                "email": parent_user.email,
                "role": parent_user.role,
            },
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def register_tutor(self, request):
        """Submit a tutor application (requires manual approval before login)."""
        d = request.data
        email = (d.get("email") or "").strip()
        password = d.get("password", "")
        confirm = d.get("confirm_password", "")
        first_name = (d.get("first_name") or "").strip()
        last_name = (d.get("last_name") or "").strip()
        mobile = (d.get("mobile") or "").strip()
        qualification = (d.get("qualification") or "").strip()
        year_levels = d.get("year_levels", [])
        bio = (d.get("bio") or "").strip()

        if not all([email, password, first_name, last_name, mobile, qualification]):
            return Response({"error": "Please fill in all required fields."}, status=400)
        if password != confirm:
            return Response({"error": "Passwords do not match."}, status=400)

        if User.objects.filter(username=email).exists():
            return Response({"error": "An account with this email already exists."}, status=400)
        if bio and len(bio) > 300:
            return Response({"error": "Bio must be 300 characters or fewer."}, status=400)

        tutor_user = User.objects.create(
            username=email,
            email=email,
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role="tutor",
            active=False,  # not active until approved
        )
        TutorProfile.objects.create(
            tutor=tutor_user,
            mobile=mobile or None,
            qualification=qualification,
            tutor_year_levels=year_levels if isinstance(year_levels, list) else [],
            bio=bio or None,
            approved=False,
        )
        from .models import AdminJob
        AdminJob.objects.create(job_type='approve_tutor', subject=tutor_user)
        TutorJob.objects.create(
            tutor=tutor_user,
            job_type='review_available_hours',
            expires_at=timezone.now() + timedelta(days=365),
        )
        refresh = RefreshToken.for_user(tutor_user)
        return Response({
            "status": "application_received",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": tutor_user.id,
                "first_name": tutor_user.first_name,
                "last_name": tutor_user.last_name,
                "email": tutor_user.email,
                "role": tutor_user.role,
            },
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def register_distributor(self, request):
        """Submit a distributor application (requires manual approval before login)."""
        from .models import DistributorProfile
        d = request.data
        email = (d.get("email") or "").strip()
        password = d.get("password", "")
        confirm = d.get("confirm_password", "")
        first_name = (d.get("first_name") or "").strip()
        last_name = (d.get("last_name") or "").strip()
        mobile = (d.get("mobile") or "").strip()
        bio = (d.get("bio") or "").strip()

        if not all([email, password, first_name, last_name, mobile]):
            return Response({"error": "Please fill in all required fields."}, status=400)
        if password != confirm:
            return Response({"error": "Passwords do not match."}, status=400)

        if User.objects.filter(username=email).exists():
            return Response({"error": "An account with this email already exists."}, status=400)
        if bio and len(bio) > 500:
            return Response({"error": "Bio must be 500 characters or fewer."}, status=400)

        dist_user = User.objects.create(
            username=email,
            email=email,
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role="distributor",
            active=False,
        )
        DistributorProfile.objects.create(
            user=dist_user,
            mobile=mobile or None,
            bio=bio or None,
            approved=False,
        )
        from .models import AdminJob
        AdminJob.objects.create(job_type='approve_distributor', subject=dist_user)
        refresh = RefreshToken.for_user(dist_user)
        return Response({
            "status": "application_received",
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": dist_user.id,
                "first_name": dist_user.first_name,
                "last_name": dist_user.last_name,
                "email": dist_user.email,
                "role": dist_user.role,
            },
        })

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def register_teacher(self, request):
        """Register a teacher account (auto-approved, no manual review needed)."""
        from .models import TeacherProfile
        d = request.data
        email = (d.get("email") or "").strip()
        password = d.get("password", "")
        confirm = d.get("confirm_password", "")
        first_name = (d.get("first_name") or "").strip()
        last_name = (d.get("last_name") or "").strip()
        school_name = (d.get("school_name") or "").strip()

        if not all([email, password, first_name, last_name]):
            return Response({"error": "Please fill in all required fields."}, status=400)
        if password != confirm:
            return Response({"error": "Passwords do not match."}, status=400)
        if User.objects.filter(username=email).exists():
            return Response({"error": "An account with this email already exists."}, status=400)

        teacher = User.objects.create(
            username=email,
            email=email,
            password=make_password(password),
            first_name=first_name,
            last_name=last_name,
            role="teacher",
            active=True,
        )
        TeacherProfile.objects.create(user=teacher, school_name=school_name)

        refresh = RefreshToken.for_user(teacher)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": teacher.id,
                "first_name": teacher.first_name,
                "last_name": teacher.last_name,
                "email": teacher.email,
                "role": teacher.role,
            },
        })

    @action(detail=False, methods=["get"], permission_classes=[AllowAny], authentication_classes=[])
    def resolve_referral(self, request):
        """Return the distributor's first name for a given referral code (for personalising the landing page)."""
        from .models import DistributorProfile
        code = (request.query_params.get("code") or "").strip()
        if not code:
            return Response({"error": "No code provided."}, status=400)
        try:
            profile = DistributorProfile.objects.select_related("user").get(referral_code=code, approved=True)
        except DistributorProfile.DoesNotExist:
            return Response({"error": "Invalid referral code."}, status=404)
        return Response({"first_name": profile.user.first_name})

    @action(detail=False, methods=["post"])
    def add_child(self, request):
        """Add another child to the authenticated parent's account."""
        user = request.user
        if not user.is_authenticated or user.role != "parent":
            return Response({"error": "Not authorised."}, status=403)

        d = request.data
        child_first = (d.get("first_name") or "").strip()
        child_last = (d.get("last_name") or "").strip()
        child_year = (d.get("year_level") or "").strip()
        child_school = (d.get("school_name") or "").strip()
        child_mobile = (d.get("mobile") or "").strip()
        child_password = d.get("password", "")
        child_confirm = d.get("confirm_password", "")

        if not all([child_first, child_last, child_year]):
            return Response({"error": "First name, last name and year level are required."}, status=400)
        if not child_password:
            return Response({"error": "Please provide a password for your child."}, status=400)
        if child_password != child_confirm:
            return Response({"error": "Passwords do not match."}, status=400)

        base = f"student_{user.id}_{child_first.lower()}"
        child_username = base
        counter = 1
        while User.objects.filter(username=child_username).exists():
            child_username = f"{base}_{counter}"
            counter += 1

        child_user = User.objects.create(
            username=child_username,
            email=f"{child_username}@students.subjectmatter.app",
            password=make_password(child_password),
            first_name=child_first,
            last_name=child_last,
            role="student",
        )
        StudentProfile.objects.create(
            user=child_user,
            year_level=child_year,
            school_name=child_school or None,
            mobile=child_mobile or None,
        )
        ParentChild.objects.create(parent=user, child=child_user)

        return Response({
            "id": child_user.id,
            "first_name": child_user.first_name,
            "last_name": child_user.last_name,
            "year_level": child_year,
            "school_name": child_school or None,
        })

    @action(detail=False, methods=["get"], permission_classes=[IsAuthenticated])
    def parent_payments(self, request):
        from .models import Payment, ParentChild
        from django.db.models import Sum
        from datetime import date

        user = request.user
        if user.role != "parent":
            return Response({"error": "Not authorised."}, status=403)

        child_ids = ParentChild.objects.filter(parent=user).values_list("child_id", flat=True)
        today = date.today()
        current_month_start = today.replace(day=1)
        if today.month == 1:
            last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month - 1, day=1)

        qs = (
            Payment.objects
            .filter(student_id__in=child_ids)
            .select_related("student", "tutor")
            .order_by("-date_tuition", "-created_at")
        )

        def _fmt(p):
            return {
                "id": p.id,
                "date_tuition": p.date_tuition.isoformat() if p.date_tuition else None,
                "student_name": p.student.get_full_name() if p.student else "Unknown",
                "tutor_name": p.tutor.get_full_name() if p.tutor else "Unknown",
                "amount_paid": str(p.amount_paid),
                "focus_area": p.focus_area,
            }

        def _total(queryset):
            agg = queryset.aggregate(t=Sum("amount_paid"))
            return str(agg["t"] or "0.00")

        current_qs = qs.filter(date_tuition__gte=current_month_start)
        last_qs    = qs.filter(date_tuition__gte=last_month_start, date_tuition__lt=current_month_start)
        older_qs   = qs.filter(date_tuition__lt=last_month_start)

        return Response({
            "current_month": {
                "label": today.strftime("%B %Y"),
                "payments": [_fmt(p) for p in current_qs],
                "total": _total(current_qs),
            },
            "last_month": {
                "label": last_month_start.strftime("%B %Y"),
                "payments": [_fmt(p) for p in last_qs],
                "total": _total(last_qs),
            },
            "older": {
                "payments": [_fmt(p) for p in older_qs],
                "total": _total(older_qs),
            },
        })

    @action(detail=False, methods=["get"])
    def parent_home(self, request):
        """Return parent + children dashboard data."""
        from .models import AssessmentToken, TestSession, ParentChild
        from django.utils import timezone as tz

        user = request.user
        if not user.is_authenticated or user.role != "parent":
            return Response({"error": "Not authorised."}, status=403)

        children_links = ParentChild.objects.filter(parent=user).select_related("child")
        children_data = []
        for link in children_links:
            child = link.child
            profile = StudentProfile.objects.filter(user=child).first()
            latest_session = TestSession.objects.filter(
                student=child, status="completed"
            ).order_by("-completed_at").first()
            test_count = TestSession.objects.filter(student=child, status="completed").count()

            children_data.append({
                "id": child.id,
                "first_name": child.first_name,
                "last_name": child.last_name,
                "year_level": profile.year_level if profile else None,
                "school_name": profile.school_name if profile else None,
                "test_count": test_count,
                "latest_test_date": latest_session.completed_at.isoformat() if latest_session else None,
            })

        return Response({
            "parent": {
                "id": user.id,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "email": user.email,
            },
            "children": children_data,
        })

    @action(detail=False, methods=["post"])
    def launch_assessment(self, request):
        """Generate a short-lived token to launch a child's assessment."""
        from .models import AssessmentToken
        from django.utils import timezone as tz
        from datetime import timedelta

        user = request.user
        if not user.is_authenticated or user.role != "parent":
            return Response({"error": "Not authorised."}, status=403)

        child_id = request.data.get("child_id")
        if not child_id:
            return Response({"error": "child_id is required."}, status=400)

        try:
            child = User.objects.get(id=child_id, role="student")
        except User.DoesNotExist:
            return Response({"error": "Child not found."}, status=404)

        if not ParentChild.objects.filter(parent=user, child=child).exists():
            return Response({"error": "Not authorised for this child."}, status=403)

        # Invalidate any existing tokens for this child
        AssessmentToken.objects.filter(student=child).delete()

        token = AssessmentToken.objects.create(
            student=child,
            expires_at=tz.now() + timedelta(minutes=30),
        )
        return Response({"token": str(token.token), "student_id": child.id})

    @action(detail=False, methods=["post"], permission_classes=[AllowAny], authentication_classes=[])
    def exchange_token(self, request):
        """Exchange a one-time assessment token for a student JWT."""
        from .models import AssessmentToken
        from django.utils import timezone as tz

        raw_token = request.data.get("token")
        if not raw_token:
            return Response({"error": "Token is required."}, status=400)

        try:
            obj = AssessmentToken.objects.select_related("student").get(token=raw_token)
        except (AssessmentToken.DoesNotExist, Exception):
            return Response({"error": "Invalid or expired token."}, status=400)

        if not obj.is_valid():
            obj.delete()
            return Response({"error": "Token has expired."}, status=400)

        student = obj.student
        obj.delete()  # one-time use

        refresh = RefreshToken.for_user(student)
        return Response({
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "user": {
                "id": student.id,
                "first_name": student.first_name,
                "last_name": student.last_name,
                "email": student.email,
                "role": student.role,
            },
        })


class DistributorViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, pk=None):
        from .models import DistributorProfile, DistributorParent, ParentChild
        try:
            dist_user = User.objects.get(pk=pk, role="distributor")
        except User.DoesNotExist:
            return Response({"error": "Not found."}, status=404)
        if request.user.id != dist_user.id and not request.user.is_staff:
            return Response({"error": "Forbidden."}, status=403)

        profile = DistributorProfile.objects.filter(user=dist_user).first()

        referred = DistributorParent.objects.filter(
            distributor=dist_user
        ).select_related("parent").order_by("-created_at")

        parents_data = []
        for dp in referred:
            parent = dp.parent
            children = ParentChild.objects.filter(
                parent=parent
            ).select_related("child", "child__student_profile")
            children_data = []
            for pc in children:
                child = pc.child
                sp = getattr(child, "student_profile", None)
                children_data.append({
                    "id": child.id,
                    "first_name": child.first_name,
                    "last_name": child.last_name,
                    "year_level": sp.year_level if sp else None,
                })
            parents_data.append({
                "id": parent.id,
                "first_name": parent.first_name,
                "last_name": parent.last_name,
                "email": parent.email,
                "joined": dp.created_at.strftime("%d %b %Y"),
                "children": children_data,
            })

        return Response({
            "id": dist_user.id,
            "first_name": dist_user.first_name,
            "last_name": dist_user.last_name,
            "email": dist_user.email,
            "referral_code": profile.referral_code if profile else None,
            "approved": profile.approved if profile else False,
            "parents": parents_data,
            "parent_count": len(parents_data),
            "student_count": sum(len(p["children"]) for p in parents_data),
        })


class QuestionViewSet(viewsets.ViewSet):
    @action(detail=False, methods=["post"])
    def record(self, request):
        student_id = request.data.get("student_id")
        template_id = request.data.get("template_id")

        if not student_id:
            return Response({"error": "student_id is required"}, 400)

        if not template_id:
            return generate_first_question(request)

        # Validate student
        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            return Response({"error": "Student not found"}, status=404)
        print("Found student")

        # Validate template
        try:
            template = Template.objects.get(id=template_id)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=404)
        print("Found template")

        # Create the Question record
        q = Question.objects.create(
            template=template,
            student=student,
            params=request.data.get("params", {}),
            question_text=request.data.get("question_text", ""),
            correct_answer=request.data.get("correct_answer", ""),
            help_requested=request.data.get("help_requested", False),
            selected_answer=request.data.get("selected_answer"),
            correct=request.data.get("correct", False),
            time_taken_ms=request.data.get("time_taken_ms"),
        )

        # ---------------------------------------------------------
        # UPDATE STUDENT COMPETENCY
        # ---------------------------------------------------------
        from .competency import update_template_progress, recompute_skill_competency, level_to_label, get_student_question_difficulty

        skill = template.skill_detail.parent  # Skill-level node (parent of skill_detail)
        profile = student.get_student_profile()
        grade = profile.year_level if profile else None

        # Snapshot the level before recording the answer so we can prevent
        # an incorrect answer from causing a star increase.
        from .models import StudentSkillCompetency as _SSC
        prev_comp = _SSC.objects.filter(student=student, skill=skill).values_list('level', flat=True).first()
        prev_level = prev_comp if prev_comp is not None else 0

        update_template_progress(
            student=student,
            template_id=template.id,
            skill_code=skill.code,
            difficulty=template.difficulty or 'easy',
            correct=q.correct,
        )

        comp = recompute_skill_competency(student, skill.code, grade or '')

        # Incorrect answers must never increase the star count.
        if not q.correct and comp and comp.level > prev_level:
            comp.level = prev_level
            comp.save(update_fields=['level'])

        # ---------------------------------------------------------
        # DETERMINE NEXT DIFFICULTY
        # ---------------------------------------------------------
        next_difficulty = get_student_question_difficulty(student, skill.code)

        # ---------------------------------------------------------
        # FETCH NEXT QUESTION — exclude already-seen templates so the
        # session loops through each template exactly once, then stops.
        # ---------------------------------------------------------
        seen_ids = request.data.get("seen_template_ids", [])
        session_ids = request.data.get("session_template_ids", [])

        # Remaining = session pool minus already seen
        if session_ids:
            remaining_ids = [tid for tid in session_ids if tid not in seen_ids]
        else:
            remaining_ids = None  # no session pool — fall back to old behaviour

        loop_complete = False
        next_template = None

        if remaining_ids is not None:
            if remaining_ids:
                next_template = (
                    Template.objects.filter(id__in=remaining_ids, validated=True, language='en')
                    .order_by("?")
                    .first()
                )
            if not next_template:
                loop_complete = True
        else:
            # Legacy path (no session_template_ids provided)
            next_template = (
                Template.objects.filter(
                    skill_detail__parent=template.skill,
                    grade=template.grade,
                    difficulty__iexact=next_difficulty,
                    validated=True,
                    language='en',
                )
                .order_by("?")
                .first()
            )
            if not next_template:
                next_template = Template.objects.filter(
                    skill_detail__parent=template.skill, grade=template.grade,
                    validated=True, language='en',
                ).first()

        # Generate question from the template
        next_question = None
        next_template_id = None
        if next_template and not loop_complete:
            next_template_id = next_template.id  # track by English ID
            print(f"Generating question for template: {next_template_id}")

            from .template_utilities import get_translated_template
            render_template = get_translated_template(next_template, student)
            preview = generate_values_and_question(render_template.id)
            if preview["ok"]:
                next_question = preview["preview"]
                next_question["template_id"] = next_template_id  # English ID for session tracking
                print(f"Successfully generated question with template_id: {next_template_id}")
            else:
                print("Failed to generate question from template:", preview.get("error"))
                next_question = None
                next_template_id = None
        elif loop_complete:
            print("Session loop complete — all templates in pool have been shown")

        # ---------------------------------------------------------
        # RETURN RESPONSE
        # ---------------------------------------------------------
        comp_level = comp.level if comp else 0
        response_data = {
            "ok": True,
            "question_id": q.id,
            "mastery": comp_level,
            "competence_label": level_to_label(comp_level),
            "next_difficulty": next_difficulty,
            "next_question": next_question,
            "template_id": next_template.id if next_template else None,
            "correct": request.data.get("correct", False),
            "loop_complete": loop_complete,
        }
        print("Returning response:", response_data)
        return Response(response_data, status=201)

class TemplateGroupViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = TemplateGroup.objects.all()
    serializer_class = TemplateGroupSerializer  # You can create a simple serializer

    @action(detail=True, methods=["GET"])
    def trio(self, request, pk=None):
        """
        Return the easy/medium/hard templates in this group.
        """
        try:
            group = self.get_object()
        except TemplateGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=404)

        templates = group.templates.select_related('skill_detail').all()
        lookup = {t.difficulty.lower(): t for t in templates}

        def serialize(t):
            if not t:
                return None
            return {
                "id": t.id,
                "name": t.name,
                "difficulty": t.difficulty,
                "content": t.content,
                "topic": t.topic,
                "subtopic": t.subtopic,
                "grade": t.grade,
                "skill_detail": t.skill_detail_id,
                "skill_id": t.skill_detail.parent_id if t.skill_detail else None,
                "validated": t.validated,
            }

        return Response({
            "easy": serialize(lookup.get("easy")),
            "medium": serialize(lookup.get("medium")),
            "hard": serialize(lookup.get("hard")),
        })

    @action(detail=True, methods=["POST"])
    def create_easy(self, request, pk=None):
        return self._create_version(pk, "easy")

    @action(detail=True, methods=["POST"])
    def create_medium(self, request, pk=None):
        return self._create_version(pk, "medium")

    @action(detail=True, methods=["POST"])
    def create_hard(self, request, pk=None):
        return self._create_version(pk, "hard")

    def _create_version(self, group_id, difficulty):
        try:
            group = TemplateGroup.objects.get(id=group_id)
        except TemplateGroup.DoesNotExist:
            return Response({"error": "Group not found"}, status=404)

        tpl, created = group.create_version(difficulty)

        return Response({"id": tpl.id, "created": created}, status=201 if created else 200)

class TemplateViewSet(viewsets.ModelViewSet):
    queryset = Template.objects.all().order_by("-id")
    serializer_class = TemplateSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        import yaml, re as _re
        from django.db.models import Q
        from django.core.paginator import Paginator

        qs = Template.objects.prefetch_related('notes').select_related('skill_detail__parent').order_by('-id')

        # Existing toggle filters
        if request.query_params.get('has_notes') == 'true':
            qs = qs.filter(notes__isnull=False).distinct()
        if request.query_params.get('no_skill_detail') == 'true':
            qs = qs.filter(skill_detail__isnull=True)

        # Column filters
        grade_f = request.query_params.get('grade', '')
        skill_f = request.query_params.get('skill', '')
        diff_f  = request.query_params.get('difficulty', '')

        if grade_f == '__none__':
            qs = qs.filter(Q(grade__isnull=True) | Q(grade=''))
        elif grade_f:
            qs = qs.filter(grade=grade_f)

        if skill_f == '__none__':
            qs = qs.filter(skill_detail__isnull=True)
        elif skill_f:
            qs = qs.filter(skill_detail__parent__description=skill_f)

        if diff_f == '__none__':
            qs = qs.filter(Q(difficulty__isnull=True) | Q(difficulty=''))
        elif diff_f:
            qs = qs.filter(difficulty=diff_f)

        # Distinct filter options (from all templates, unaffected by current filters)
        base = Template.objects.select_related('skill_detail__parent')
        grade_options = sorted(set(
            base.exclude(Q(grade__isnull=True) | Q(grade='')).values_list('grade', flat=True)
        ))
        skill_options = sorted(set(
            base.filter(skill_detail__parent__isnull=False)
                .values_list('skill_detail__parent__description', flat=True)
        ))
        diff_options = sorted(set(
            base.exclude(Q(difficulty__isnull=True) | Q(difficulty='')).values_list('difficulty', flat=True)
        ))

        # Pagination
        page_num  = max(1, int(request.query_params.get('page', 1)))
        page_size = max(1, int(request.query_params.get('page_size', 20)))
        paginator = Paginator(qs, page_size)
        page_obj  = paginator.get_page(page_num)

        def _extract_question(content):
            if not content:
                return ''
            from .template_utilities import _fix_unquoted_diagram, _fix_parameters_indentation, _fix_bare_expressions
            try:
                fixed = _fix_bare_expressions(_fix_parameters_indentation(_fix_unquoted_diagram(content)))
                parsed = yaml.safe_load(fixed)
                q = parsed.get('question', '') if isinstance(parsed, dict) else ''
                text = q.get('text', '') if isinstance(q, dict) else (q or '')
                text = _re.sub(r'\{\{.*?\}\}', '…', str(text))
                return text[:120]
            except Exception:
                pass
            m = _re.search(r'^[ \t]*text:\s*["\']?(.*?)["\']?\s*$', content, _re.MULTILINE)
            if not m:
                m = _re.search(r'^question:\s*["\']?(.*?)["\']?\s*$', content, _re.MULTILINE)
            text = _re.sub(r'\{\{.*?\}\}', '…', m.group(1)) if m else ''
            return text[:120]

        results = []
        for t in page_obj.object_list:
            notes = list(t.notes.order_by('-created_at').values_list('text', flat=True))
            results.append({
                'id': t.id,
                'grade': t.grade or '',
                'skill': t.skill.description if t.skill else '',
                'skill_detail': t.skill_detail.description if t.skill_detail else '',
                'difficulty': t.difficulty or '',
                'status': t.status or '',
                'updated_at': t.updated_at.isoformat() if t.updated_at else '',
                'note_count': len(notes),
                'notes': notes,
                'question_text': _extract_question(t.content),
            })

        return Response({
            'count': paginator.count,
            'results': results,
            'grade_options': grade_options,
            'skill_options': skill_options,
            'diff_options': diff_options,
        })


    @action(detail=True, methods=["POST"])
    def create_group(self, request, pk=None):
        """
        Create a TemplateGroup and attach this template to it.
        """
        try:
            tpl = self.get_object()
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=404)

        # If already in a group, return it
        if tpl.group:
            return Response({"group_id": tpl.group.id}, status=200)

        # Create new group using template metadata
        group = TemplateGroup.objects.create(
            skill_detail=tpl.skill_detail,
            grade=tpl.grade,
            name=f"Group for {tpl.name or tpl.id}"
        )

        tpl.group = group
        tpl.save()

        return Response({"group_id": group.id}, status=201)


    @action(detail=False, methods=["get"])
    def subjects(self, request):
        """Return distinct skill_detail descriptions (and IDs) for templates matching filters."""
        qs = Template.objects.filter(skill_detail__isnull=False)
        skill = request.query_params.get("skill")
        grade = request.query_params.get("grade")
        difficulty = request.query_params.get("difficulty")
        validated = request.query_params.get("validated")
        if skill:
            qs = qs.filter(skill_detail__parent_id=skill)
        if grade:
            qs = qs.filter(grade=grade)
        if difficulty:
            qs = qs.filter(difficulty__iexact=difficulty.strip())
        if validated == "validated":
            qs = qs.filter(validated=True)
        elif validated == "unvalidated":
            qs = qs.filter(validated=False)
        descriptions = (
            qs.values_list("skill_detail__description", flat=True)
            .distinct()
            .order_by("skill_detail__order_index")
        )
        return Response([d for d in descriptions if d])

    def _skill_level_id(self, template):
        """Return the Skill-level node ID for matrix cache updates."""
        if template.skill_detail_id and template.skill_detail:
            return template.skill_detail.parent_id
        return None

    def perform_update(self, serializer):
        old_skill_level_id = self._skill_level_id(serializer.instance)
        instance = serializer.save()
        new_skill_level_id = self._skill_level_id(instance)
        if old_skill_level_id:
            update_matrix_cache_for_count(old_skill_level_id)
        if new_skill_level_id and new_skill_level_id != old_skill_level_id:
            update_matrix_cache_for_count(new_skill_level_id)

    def perform_destroy(self, instance):
        skill_level_id = self._skill_level_id(instance)
        instance.delete()
        if skill_level_id:
            update_matrix_cache_for_count(skill_level_id)

    @action(detail=True, methods=['post'])
    def toggle_validated(self, request, pk=None):
        template = self.get_object()
        template.validated = not template.validated
        template.save()
        skill_level_id = self._skill_level_id(template)
        if skill_level_id:
            update_matrix_cache_for_count(skill_level_id)
        return Response({"validated": template.validated})

    @action(detail=True, methods=['post'])
    def duplicate(self, request, pk=None):
        original = self.get_object()
        copy = Template.objects.create(
            skill_detail=original.skill_detail,
            grade=original.grade,
            name=original.name,
            difficulty=original.difficulty,
            content=original.content,
        )
        skill_level_id = self._skill_level_id(copy)
        if skill_level_id:
            update_matrix_cache_for_count(skill_level_id)
        return Response({"id": copy.id})

    @action(detail=True, methods=['post'])
    def duplicate_harder(self, request, pk=None):
        """Duplicate this template with difficulty incremented one step (easy→medium→hard)."""
        original = self.get_object()
        next_difficulty = {'easy': 'medium', 'medium': 'hard'}.get(original.difficulty, original.difficulty)
        copy = Template.objects.create(
            skill_detail=original.skill_detail,
            grade=original.grade,
            name=original.name,
            difficulty=next_difficulty,
            content=original.content,
        )
        skill_level_id = self._skill_level_id(copy)
        if skill_level_id:
            update_matrix_cache_for_count(skill_level_id)
        return Response({"id": copy.id, "difficulty": next_difficulty})

    @action(detail=True, methods=["post"])
    def get_translation(self, request, pk=None):
        """Return (or create) a translated version of this template for the given language."""
        from .models import Template as _Template
        language = (request.data.get("language") or "").strip()
        SUPPORTED = {"zh", "ar", "vi", "ko", "hi", "es", "fr", "it", "pt"}
        if language not in SUPPORTED:
            return Response({"error": f"Unsupported language: {language}"}, status=400)

        template = self.get_object()
        source = template if template.language == "en" else (template.parent_template or template)
        translated = _get_or_create_translation(source, language)
        if not translated:
            return Response({"error": "Translation failed"}, status=500)

        return Response({
            "id": translated.id,
            "language": translated.language,
            "content": translated.content,
        })

    @action(detail=True, methods=["get"])
    def language_info(self, request, pk=None):
        """Return the English source and all existing translations for this template."""
        template = self.get_object()
        source = template if template.language == "en" else (template.parent_template or template)
        translations = list(source.translations.values("id", "language"))
        return Response({
            "source_id": source.id,
            "source_content": source.content,
            "translations": translations,
        })

    @action(detail=False, methods=["get"])
    def export_all(self, request):
        import yaml as _yaml
        templates = Template.objects.select_related("skill_detail__parent").all()
        records = []
        for t in templates:
            parsed = {}
            if t.content:
                try:
                    parsed = yaml.safe_load(t.content) or {}
                except Exception:
                    pass
            record = {
                "skill_detail_code": t.skill_detail.code if t.skill_detail else None,
                "grade":            t.grade or "",
                "difficulty":       t.difficulty or "",
                "validated":        t.validated,
                "status":           t.status,
                "topic":            t.topic,
                "subtopic":         t.subtopic,
                "tags":             t.tags,
                "curriculum":       t.curriculum,
                "content":          t.content,
            }
            records.append(record)
        yaml_str = _yaml.dump(records, allow_unicode=True, default_flow_style=False, sort_keys=False)
        d = __import__("datetime").date.today().strftime("%Y_%m_%d")
        response = HttpResponse(yaml_str, content_type="text/yaml; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="templates_{d}.yaml"'
        return response

    @action(detail=False, methods=["post"])
    def import_bulk(self, request):
        import json as _json
        import yaml as _yaml
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file uploaded"}, status=400)
        raw = uploaded.read().decode("utf-8")
        name = uploaded.name or ""
        try:
            if name.endswith(".yaml") or name.endswith(".yml"):
                records = _yaml.safe_load(raw)
            else:
                records = _json.loads(raw)
        except Exception as e:
            return Response({"error": f"Invalid file: {e}"}, status=400)

        # Duplicate detection: compare stripped content strings
        existing = set(
            (t or "").strip()
            for t in Template.objects.values_list("content", flat=True)
        )

        created = skipped = errors = 0
        first_error = None
        for record in records:
            content = record.get("content") or ""
            if content.strip() in existing:
                skipped += 1
                continue

            parsed = {}
            if content:
                try:
                    parsed = yaml.safe_load(content) or {}
                except Exception:
                    pass  # Metadata extraction failed; still import the content

            name       = str(parsed.get("title") or "")
            years_raw  = parsed.get("years") or record.get("grade") or ""
            if isinstance(years_raw, list):
                years_raw = years_raw[0] if years_raw else ""
            grade      = str(years_raw).strip()[:2] or None
            difficulty = str(parsed.get("difficulty") or record.get("difficulty") or "")

            skill_detail = None
            skill_detail_code = record.get("skill_detail_code")
            if skill_detail_code:
                skill_detail = Skill.objects.filter(code=skill_detail_code, is_detail=True).first()
            if skill_detail is None:
                skill_detail_id = record.get("skill_detail_id")
                if skill_detail_id is not None:
                    skill_detail = Skill.objects.filter(pk=skill_detail_id, is_detail=True).first()

            try:
                Template.objects.create(
                    name=name,
                    content=content,
                    topic=record.get("topic") or "",
                    subtopic=record.get("subtopic") or "",
                    grade=grade,
                    difficulty=difficulty,
                    tags=record.get("tags") or [],
                    curriculum=record.get("curriculum") or [],
                    skill_detail=skill_detail,
                    validated=record.get("validated", False),
                    status=record.get("status", "draft"),
                )
                existing.add(content.strip())
                created += 1
            except Exception as e:
                if first_error is None:
                    first_error = f"DB error: {e}"
                errors += 1

        result = {"created": created, "skipped": skipped, "errors": errors}
        if first_error:
            result["first_error"] = first_error
        return Response(result)

    @action(detail=False, methods=["post"])
    def delete_all(self, request):
        """Delete every template. Admin / edit_syllabus only."""
        user = request.user
        allowed = user.role == "admin" or (
            user.role == "tutor" and
            hasattr(user, "tutor") and
            user.tutor.filter(edit_syllabus=True).exists()
        )
        if not allowed:
            return Response({"error": "Not authorised"}, status=403)
        count, _ = Template.objects.all().delete()
        return Response({"deleted": count})

    @action(detail=True, methods=["get"], url_path="preview")
    def preview_by_id(self, request, pk=None):
        """GET /api/templates/:id/preview/ — render a fresh preview for a stored template."""
        try:
            template = Template.objects.get(pk=pk)
        except Template.DoesNotExist:
            return Response({"error": "Template not found"}, status=404)
        result = generate_preview_from_content(template.content or "")
        if not result.get("ok"):
            return Response({"error": result.get("error", "Preview failed")}, status=400)
        return Response(result.get("preview"))

    @action(detail=False, methods=["post"])
    def preview(self, request):

        # 1. Content-based preview (TemplateEditorPage)
        content = request.data.get("content")
        if content:
            result = generate_preview_from_content(content)
            # Inject knowledge items when the template ID is also known
            template_id = request.data.get("templateId")
            if result["ok"] and template_id and result.get("preview") is not None:
                try:
                    tpl = Template.objects.get(pk=template_id)
                    from .diagram.engine import render_diagram_from_code
                    knowledge_items = []
                    for k in tpl.knowledge_items.all():
                        svg = ""
                        if k.diagram and k.diagram.strip() and k.diagram.strip().lower() != "none":
                            try:
                                svg = render_diagram_from_code(k.diagram)
                            except Exception:
                                pass
                        knowledge_items.append({
                            "id": k.id,
                            "title": k.title,
                            "text": k.text,
                            "text_2": k.text_2,
                            "diagram_svg": svg,
                        })
                    result["preview"]["knowledge_items"] = knowledge_items
                except Exception:
                    pass
            return Response(
                {"ok": result["ok"], "preview": result["preview"], "error": result["error"]},
                status=200 if result["ok"] else 400
            )

        # 2. Skill + grade lookup (SkillsMatrix) — skill_id is the Skill-level node
        skill_id = request.data.get("skill")
        grade = request.data.get("grade")
        difficulty = request.data.get("difficulty")
        if skill_id and grade:
            qs = Template.objects.filter(skill_detail__parent_id=skill_id, grade=grade)
            # print("Query set:", skill_id, grade, qs)
            if difficulty:
                qs = qs.filter(difficulty=difficulty)
            else:
                qs = qs.order_by(
                    Case(
                        When(difficulty="easy", then=0),
                        When(difficulty="medium", then=1),
                        When(difficulty="hard", then=2),
                        default=3,
                        output_field=IntegerField(),
                    ),
                    "id"
                )

            qs = qs.order_by("id")
            first = qs.first()
            if not first:
                return Response({
                    "ok": False,
                    "template_id": None,
                    "error": "No templates exist for this skill and grade."
                }, status=404)

            result = generate_values_and_question(first.id)
            print(qs)
            print(result)
            return Response({
                "ok": result["ok"],
                "template_id": first.id,
                "preview": result["preview"],
                "error": result["error"]
            }, status=200 if result["ok"] else 400)

        # 3. Template ID preview (Editor navigation)
        template_id = request.data.get("templateId") or request.data.get("id")
        if template_id:
            result = generate_values_and_question(template_id)
            return Response(
                {"ok": result["ok"], "preview": result["preview"], "error": result["error"]},
                status=200 if result["ok"] else 400
            )

        # 4. Fallback
        return Response(
            {"ok": False, "error": "No valid preview parameters provided"},
            status=400
        )

    @action(detail=False, methods=["post"])
    def generate(self, request):
        skill_id = request.data.get("skill_id")
        grade = request.data.get("grade")
        if not skill_id:
            return Response({"error": "skill_id missing"}, status=400)
        try:
            skill = Skill.objects.get(id=skill_id)
        except Skill.DoesNotExist:
            return Response({"error": "Skill not found"}, status=404)

        print(f"Generating Questions. Skill: {skill.description}, Grade: {grade}")
        try:
            data = generate_template_content(skill, grade)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"AI generation failed: {e}"}, status=500)

        print(f"AI returned {len(data) if isinstance(data, list) else type(data).__name__} items")

        if not isinstance(data, list):
            return Response({"error": f"AI returned unexpected type {type(data).__name__}, expected list"}, status=500)

        created_templates = []

        for i, item in enumerate(data):
            try:
                # Match the AI's subject text to a skill_detail child of the chosen skill
                skill_detail = None
                subject_text = item.get("subject") or item.get("title", "")
                if subject_text and skill:
                    skill_detail = skill.children.filter(
                        is_detail=True, description=subject_text
                    ).first()
                template = Template.objects.create(
                    skill_detail=skill_detail,
                    grade=grade,
                    name=item["title"],
                    difficulty=item["difficulty"],
                    content=format_for_editor(item),
                )
                created_templates.append(template)
            except Exception as e:
                import traceback
                print(f"Failed to create template {i}: {e}")
                traceback.print_exc()

        if not created_templates:
            return Response({"error": "No templates could be created from AI output"}, status=500)

        first = created_templates[0]
        update_matrix_cache_for_count(skill_id)

        return Response({
            "id": first.id,
            "skill_detail": first.skill_detail_id,
            "content": first.content,
            "skill": skill.id,
        })

    @action(detail=False, methods=["post"])
    def invalidate_all(self, request):
        skill_id = request.data.get("skill_id")
        if not skill_id:
            return Response({"error": "skill_id required"}, status=400)
        count = Template.objects.filter(skill_detail__parent_id=skill_id).update(validated=False)
        return Response({"invalidated": count})

    @action(detail=False, methods=["post"])
    def generate_for_subject(self, request):
        """Generate a single template for a specific skill_detail/grade/difficulty."""
        from .ai import generate_single_template
        skill_detail_id = request.data.get("skill_detail_id")
        grade = request.data.get("grade")
        difficulty = request.data.get("difficulty")
        if not all([skill_detail_id, grade, difficulty]):
            return Response({"error": "skill_detail_id, grade and difficulty are required"}, status=400)
        try:
            skill_detail = Skill.objects.get(pk=skill_detail_id, is_detail=True)
        except Skill.DoesNotExist:
            return Response({"error": "Skill Detail not found"}, status=404)
        try:
            item = generate_single_template(skill_detail.parent, str(grade), difficulty, skill_detail.description)
        except Exception as e:
            import traceback; traceback.print_exc()
            return Response({"error": f"AI generation failed: {e}"}, status=500)
        try:
            template = Template.objects.create(
                skill_detail=skill_detail,
                grade=grade,
                name=item.get("title", skill_detail.description),
                difficulty=difficulty,
                content=format_for_editor(item),
            )
            update_matrix_cache_for_count(skill_detail.parent_id)
            return Response({"id": template.id})
        except Exception as e:
            return Response({"error": f"Failed to save template: {e}"}, status=500)

    @action(detail=False, methods=["post"])
    def create_empty_for_subject(self, request):
        """Create a blank template stub for a specific skill_detail/grade/difficulty."""
        skill_detail_id = request.data.get("skill_detail_id")
        grade = request.data.get("grade")
        difficulty = request.data.get("difficulty")
        if not all([skill_detail_id, grade, difficulty]):
            return Response({"error": "skill_detail_id, grade and difficulty are required"}, status=400)
        try:
            skill_detail = Skill.objects.get(pk=skill_detail_id, is_detail=True)
        except Skill.DoesNotExist:
            return Response({"error": "Skill Detail not found"}, status=404)
        template = Template.objects.create(
            skill_detail=skill_detail,
            grade=grade,
            name=skill_detail.description,
            difficulty=difficulty,
            content="",
        )
        update_matrix_cache_for_count(skill_detail.parent_id)
        return Response({"id": template.id})

    @action(detail=False, methods=["post"])
    def shift_grade(self, request):
        """Shift the grade of all templates for a given skill + grade by +1 or -1."""
        skill_id = request.data.get("skill_id")
        grade = request.data.get("grade")
        delta = request.data.get("delta")
        if not skill_id or grade is None or delta is None:
            return Response({"error": "skill_id, grade and delta are required"}, status=400)
        try:
            delta = int(delta)
            if str(grade).strip().upper() == "K":
                if delta == 1:
                    new_grade = "1"
                else:
                    return Response({"error": "No year below Year K"}, status=400)
            else:
                new_grade = str(int(grade) + delta)
        except (ValueError, TypeError):
            return Response({"error": "grade and delta must be integers"}, status=400)
        updated = Template.objects.filter(
            skill_detail__parent_id=skill_id,
            grade=str(grade),
        ).update(grade=new_grade)
        _reset_year_caches()
        return Response({"updated": updated, "new_grade": new_grade})

    @action(detail=False, methods=["post"])
    def generate_from_image(self, request):
        image_b64 = request.data.get("image")
        mime_type = request.data.get("mime_type", "image/png")
        grade = request.data.get("grade", "")
        additional_prompt = request.data.get("additional_prompt", "")
        override_skill_detail_id = request.data.get("skill_detail_id")
        override_difficulty = request.data.get("difficulty")

        if not grade:
            return Response({"error": "grade required"}, status=400)

        # Build skill list (Skill-level nodes) filtered to the selected grade
        matrix = get_matrix_cache()
        grade_str = str(grade)
        skills_list = [
            {"id": row["id"], "code": row["code"], "description": row["description"]}
            for row in matrix["skills"]
            if row["children_count"] == 0
            and row["cells"].get(grade_str, {}).get("colour") == "covered"
        ]

        if not skills_list:
            return Response({"error": f"No skills found for Year {grade}"}, status=400)

        try:
            item = generate_template_from_image(image_b64, mime_type, skills_list, grade_str, additional_prompt)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"AI generation failed: {e}"}, status=500)

        # Resolve skill_detail: use override if supplied, otherwise leave unassigned
        skill_detail = None
        if override_skill_detail_id:
            try:
                skill_detail = Skill.objects.get(id=int(override_skill_detail_id), is_detail=True)
            except Exception:
                pass

        difficulty = override_difficulty if override_difficulty is not None else item.get("difficulty", "")

        template = Template.objects.create(
            skill_detail=skill_detail,
            grade=grade_str,
            name=item.get("title", ""),
            difficulty=difficulty,
            content=format_for_editor(item),
        )

        if skill_detail:
            update_matrix_cache_for_count(skill_detail.parent_id)

        return Response({
            "id": template.id,
            "skill_detail": template.skill_detail_id,
            "content": template.content,
            "skill": template.skill.id if template.skill else None,
        })

    @action(detail=True, methods=["post"])
    def diagram(self, request, pk=None):
        template = self.get_object()
        svg = request.data.get("svg")

        if not svg:
            return Response({"error": "SVG missing"}, status=400)

        diagram, _ = TemplateDiagram.objects.update_or_create(
            template=template,
            defaults={"svg_spec": svg}
        )

        return Response({"ok": True})

    @action(detail=False, methods=["post"])
    def update_with_ai(self, request):
        existing_yaml = request.data.get("content", "")
        instruction = request.data.get("instruction", "")
        use_pro = request.data.get("pro", False)
        model = "gpt-4o" if use_pro else "gpt-4o-mini"

        if not instruction.strip():
            return Response({"error": "instruction required"}, status=400)

        try:
            from .ai import update_template
            from .utilities import format_for_editor
            item = update_template(existing_yaml, instruction, model=model)
            content = format_for_editor(item)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"AI update failed: {e}"}, status=500)

        return Response({"content": content})

    @action(detail=False, methods=["get"])
    def filtered(self, request):
        skill = request.query_params.get("skill")
        grade = request.query_params.get("grade")
        difficulty = request.query_params.get("difficulty")
        validated = request.query_params.get("validated")
        language = request.query_params.get("language")

        qs = Template.objects.select_related("skill_detail__parent").all()
        if skill: qs = qs.filter(skill_detail__parent_id=skill)
        if grade: qs = qs.filter(grade=grade)
        if difficulty: qs = qs.filter(difficulty__iexact=difficulty.strip())
        if validated == "validated": qs = qs.filter(validated=True)
        elif validated == "unvalidated": qs = qs.filter(validated=False)
        if language and language != "all": qs = qs.filter(language=language)

        qs = qs.order_by("-id")

        import yaml as _yaml
        def _question_text(t):
            try:
                parsed = _yaml.safe_load(t.content or "")
                q = (parsed or {}).get("question", "")
                if isinstance(q, dict):
                    return q.get("text", "") or ""
                return str(q) if q else ""
            except Exception:
                return ""

        return Response([
            {
                "id": t.id,
                "name": t.name or "",
                "description": t.description or "",
                "skill_detail": t.skill_detail.description if t.skill_detail else "",
                "skill": t.skill.id if t.skill else None,
                "grade": t.grade,
                "difficulty": t.difficulty,
                "validated": t.validated,
                "question_text": _question_text(t),
            }
            for t in qs
        ])

    @action(detail=False, methods=["post"])
    def autosave(self, request):
        content = request.data.get("content", "")
        template_id = request.data.get("templateId") or request.data.get("id")
        # Reject missing / sentinel IDs — never create a template from autosave
        invalid_ids = [None, "", "undefined", "new"]
        if template_id in invalid_ids or not template_id:
            return Response({"ok": True})

        # If template_id exists, update the template
        try:
            template = Template.objects.get(pk=template_id)
            template.content = content
            template.save()
            # print(f"AUTOSAVED TEMPLATE {template_id}")
            return Response({"ok": True})
        except Template.DoesNotExist:
            template = Template.objects.create(content=content)
            return Response({"ok": True})



class SkillViewSet(viewsets.ModelViewSet):
    queryset = Skill.objects.all().order_by("order_index")
    serializer_class = SkillSerializer
    permission_classes = [AllowAny]

    @action(detail=False, methods=["get"])
    def leaf(self, request):
        grade = request.query_params.get("grade")
        matrix = get_matrix_cache()  # uses cached tree
        rows = matrix["skills"]
        leaf_skills = []
        for row in rows:
            if row["children_count"] != 0:
                continue
            if grade:
                g = str(grade)
                if row["cells"][g]["colour"] != "covered":
                    continue

            leaf_skills.append({
                "id": row["id"],
                "description": row["description"],
            })

        return Response(leaf_skills)

    @action(detail=True, methods=["get"])
    def children(self, request, pk=None):
        parent = self.get_object()
        children = parent.children.order_by("order_index")
        serializer = SkillSerializer(children, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def direct_templates(self, request, pk=None):
        skill = self.get_object()
        templates = skill.direct_templates()
        serializer = TemplateSerializer(templates, many=True)
        return Response(serializer.data)

    def list(self, request, *args, **kwargs):
        parent_id = request.query_params.get("parent")
        if parent_id:
            skills = Skill.objects.filter(parent_id=parent_id).order_by("order_index")
        else:
            skills = Skill.objects.filter(parent__isnull=True).order_by("order_index")

        serializer = SkillSerializer(skills, many=True)
        return Response(serializer.data)

    @action(detail=True, methods=["get"])
    def parents(self, request, pk=None):
        skill = self.get_object()
        chain = []
        current = skill.parent

        while current:
            chain.append(current)
            current = current.parent

        # reverse so it goes root → child → current
        chain.reverse()

        serializer = SkillSerializer(chain, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def load_syllabus(self, request):
        import_syllabus()
        _reset_year_caches()
        return Response({"status": "Syllabus loaded successfully"})

    @action(detail=False, methods=["get"])
    def export_all(self, request):
        """Export the full skill tree as YAML."""
        import yaml as _yaml

        def build_node(skill):
            details = list(
                Skill.objects.filter(parent=skill, is_detail=True).order_by("order_index")
            )
            children = list(
                Skill.objects.filter(parent=skill, is_detail=False).order_by("order_index")
            )
            grades_list = [g.strip() for g in (skill.grades or "").split(",") if g.strip()]
            node = {
                "code": skill.code,
                "description": skill.description,
                "years_practised": grades_list,
                "detail": [d.description for d in details],
            }
            if children:
                node["children"] = [build_node(c) for c in children]
            return node

        roots = Skill.objects.filter(parent__isnull=True, is_detail=False).order_by("order_index")
        data = [build_node(r) for r in roots]
        yaml_str = _yaml.dump(data, allow_unicode=True, default_flow_style=False, sort_keys=False)
        d = __import__("datetime").date.today().strftime("%Y_%m_%d")
        response = HttpResponse(yaml_str, content_type="text/yaml; charset=utf-8")
        response["Content-Disposition"] = f'attachment; filename="skills_{d}.yaml"'
        return response

    @action(detail=False, methods=["post"])
    def import_bulk(self, request):
        """Import a skills YAML or JSON file (same format as export_all)."""
        import json as _json
        import yaml as _yaml
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file uploaded"}, status=400)
        raw = uploaded.read().decode("utf-8")
        name = uploaded.name or ""
        try:
            if name.endswith(".yaml") or name.endswith(".yml"):
                data = _yaml.safe_load(raw)
            else:
                data = _json.loads(raw)
        except Exception as e:
            return Response({"error": f"Invalid file: {e}"}, status=400)

        from .import_skills import import_skill_tree
        existing_by_code = {s.code: s for s in Skill.objects.all()}
        seen_codes = set()
        try:
            for top in data:
                import_skill_tree(top, parent=None, existing_by_code=existing_by_code, seen_codes=seen_codes)
        except Exception as e:
            return Response({"error": f"Import failed: {e}"}, status=400)

        _reset_year_caches()
        return Response({"status": "Skills imported successfully", "seen": len(seen_codes)})

    @action(detail=True, methods=["post"])
    def add_detail(self, request, pk=None):
        """Add a new is_detail=True child to this skill node."""
        skill = self.get_object()
        if skill.is_detail:
            return Response({"error": "Cannot add a detail to a detail node."}, status=400)
        description = (request.data.get("description") or "").strip()
        if not description:
            return Response({"error": "Description is required."}, status=400)

        next_index = Skill.objects.filter(parent=skill, is_detail=True).count()
        code = f"{skill.code}-D{next_index + 1}"
        # Ensure code uniqueness
        while Skill.objects.filter(code=code).exists():
            next_index += 1
            code = f"{skill.code}-D{next_index + 1}"

        detail = Skill.objects.create(
            parent=skill,
            code=code,
            description=description,
            grades=skill.grades,
            order_index=next_index,
            is_detail=True,
        )
        _reset_year_caches()
        return Response(SkillSerializer(detail).data, status=201)

    def update(self, request, *args, **kwargs):
        skill = self.get_object()
        if not skill.is_detail:
            return Response({"error": "Only skill detail nodes can be edited."}, status=400)
        return super().update(request, *args, **kwargs)

    def partial_update(self, request, *args, **kwargs):
        skill = self.get_object()
        if not skill.is_detail:
            # Allow patching grades/description on parent (non-detail) skills.
            allowed_fields = {"grades", "description"}
            if not set(request.data.keys()).issubset(allowed_fields):
                return Response({"error": "Only skill detail nodes can be edited."}, status=400)
            # Bypass the custom update() guard by calling the serializer directly.
            serializer = self.get_serializer(skill, data=request.data, partial=True)
            serializer.is_valid(raise_exception=True)
            serializer.save()
            _reset_year_caches()
            return Response(serializer.data)
        result = super().partial_update(request, *args, **kwargs)
        _reset_year_caches()
        return result

    def destroy(self, request, *args, **kwargs):
        skill = self.get_object()

        if not skill.is_detail:
            return Response(
                {"error": "Only skill detail nodes can be deleted from this interface."},
                status=400
            )

        if skill.children.exists():
            return Response(
                {"error": "Cannot delete a skill that has sub-skills."},
                status=400
            )

        result = super().destroy(request, *args, **kwargs)
        _reset_year_caches()
        return result

    @action(detail=True, methods=["post"])
    def diagram(self, request, pk=None):
        template = self.get_object()
        svg = request.data.get("svg")

        if not svg:
            return Response({"error": "SVG missing"}, status=400)

        diagram, _ = TemplateDiagram.objects.update_or_create(
            template=template,
            defaults={"svg_spec": svg}
        )

        return Response({"ok": True})

    @action(detail=False, methods=["get"], permission_classes=[AllowAny])
    def matrix(self, request):
        matrix = get_matrix_cache()  # fast, full matrix
        grade = request.query_params.get("grade")
        # Normalise "Year 7" → "7" so it matches matrix cell keys; treat "all" as no filter
        if grade:
            grade = grade.strip().lower().replace("year", "").strip()
            if grade == "all":
                grade = None
        student_id = request.query_params.get("student_id")
        course_set = request.query_params.get("course_set")  # "k10" or "s6"

        # ----------------------------------------
        # Restrict grades/skills to a course set
        # ----------------------------------------
        if course_set:
            from .models import Year as _Year
            cs_grade_set = set(
                _Year.objects.filter(stage=course_set, active=True)
                .values_list("code", flat=True)
            )
            available_grades = [g for g in matrix["grades"] if g in cs_grade_set]

            # Keep only skill rows that are in-syllabus for at least one course_set grade
            id_to_skill = {s["id"]: s for s in matrix["skills"]}
            relevant_ids: set = set()
            for s in matrix["skills"]:
                if s["children_count"] == 0:  # leaf
                    if any(s["cells"].get(g, {}).get("colour") == "covered" for g in available_grades):
                        relevant_ids.add(s["id"])
                        pid = s["parent_id"]
                        while pid is not None:
                            relevant_ids.add(pid)
                            pid = id_to_skill[pid]["parent_id"] if pid in id_to_skill else None
            # If no S6 skills imported yet, fall through with all skills (empty matrix)
            cs_skills = [s for s in matrix["skills"] if s["id"] in relevant_ids] if relevant_ids else matrix["skills"]
        else:
            available_grades = matrix["grades"]
            cs_skills = matrix["skills"]

        # ----------------------------------------
        # Build mastery map if student_id provided
        # ----------------------------------------
        mastery_map = {}

        if student_id:
            from .competency import level_to_label as _ltl
            rows = StudentSkillCompetency.objects.filter(student_id=student_id)
            for row in rows:
                mastery_map[row.skill_id] = {
                    "mastery": row.level,
                    "competence_label": _ltl(row.level),
                    "updated_at": row.updated_at.isoformat() if row.updated_at else None,
                }

        # ----------------------------------------
        # Apply grade filtering if needed
        # ----------------------------------------
        if grade:
            filtered = filter_matrix_by_grade({"grades": available_grades, "skills": cs_skills}, grade)

            # ── Per-difficulty skill-detail coverage ──────────────────────────
            # For each Skill-level node: how many Skill Detail children have a
            # validated template at each difficulty level?
            from .models import Skill as _Skill, Template as _Tmpl

            leaf_ids = [s['id'] for s in filtered if s['children_count'] == 0]

            # Count of detail children per Skill
            detail_total_map: dict = {
                row['parent_id']: row['cnt']
                for row in _Skill.objects
                    .filter(parent_id__in=leaf_ids, is_detail=True)
                    .values('parent_id')
                    .annotate(cnt=Count('id'))
            }

            # Which detail skill IDs have at least one validated template per difficulty?
            covered_rows = (
                _Tmpl.objects
                .filter(skill_detail__parent_id__in=leaf_ids, grade=grade, validated=True)
                .values('skill_detail__parent_id', 'difficulty', 'skill_detail_id')
                .distinct()
            )
            coverage_map: dict = {}
            for row in covered_rows:
                sid = row['skill_detail__parent_id']
                diff = (row['difficulty'] or '').lower()
                coverage_map.setdefault(sid, {}).setdefault(diff, set()).add(row['skill_detail_id'])

            for skill in filtered:
                if skill['children_count'] > 0:
                    skill['detail_coverage'] = None
                    continue
                sid = skill['id']
                total = detail_total_map.get(sid, 0)
                dc = {}
                for diff in ('easy', 'medium', 'hard'):
                    covered = len(coverage_map.get(sid, {}).get(diff, set()))
                    dc[diff] = {'covered': covered, 'total': total}
                skill['detail_coverage'] = dc
            # ─────────────────────────────────────────────────────────────────

            return Response({
                "grades": available_grades,
                "skills": filtered,
                "mastery": mastery_map,
            })

        return Response({
            "grades": available_grades,
            "skills": cs_skills,
            "mastery": mastery_map,
        })

# -------------- TUTOR ---------------- #

class TutorViewSet(viewsets.ModelViewSet):

    queryset = User.objects.filter(role="tutor").order_by("username")
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]

    @action(detail=True, methods=["get"])
    def home(self, request, pk=None):
        tutor = self.get_object()
        profile = tutor.get_tutor_profile()
        return Response(profile.to_dict())

    @action(detail=True, methods=["get"])
    def payments(self, request, pk=None):
        from .models import Payment
        from django.db.models import Sum
        from datetime import date

        tutor = self.get_object()

        today = date.today()
        current_month_start = today.replace(day=1)
        if today.month == 1:
            last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month - 1, day=1)

        qs = (
            Payment.objects
            .filter(tutor=tutor)
            .select_related('student')
            .order_by('-date_tuition', '-created_at')
        )

        def _fmt(p):
            return {
                'id': p.id,
                'date_tuition': p.date_tuition.isoformat() if p.date_tuition else None,
                'student_name': p.student.get_full_name() if p.student else 'Unknown',
                'amount_paid': str(p.amount_paid),
                'amount_tutor': str(p.amount_tutor),
                'focus_area': p.focus_area,
                'notes': p.notes,
            }

        current_qs = qs.filter(date_tuition__gte=current_month_start)
        last_qs    = qs.filter(date_tuition__gte=last_month_start, date_tuition__lt=current_month_start)
        older_qs   = qs.filter(date_tuition__lt=last_month_start)

        def _total(queryset):
            agg = queryset.aggregate(t=Sum('amount_tutor'))
            return str(agg['t'] or '0.00')

        return Response({
            'current_month': {
                'label': today.strftime('%B %Y'),
                'payments': [_fmt(p) for p in current_qs],
                'total_tutor': _total(current_qs),
            },
            'last_month': {
                'label': last_month_start.strftime('%B %Y'),
                'payments': [_fmt(p) for p in last_qs],
                'total_tutor': _total(last_qs),
            },
            'older': {
                'payments': [_fmt(p) for p in older_qs],
                'total_tutor': _total(older_qs),
            },
        })

    @action(detail=True, methods=["post"])
    def toggle_looking(self, request, pk=None):
        tutor = self.get_object()
        profile = tutor.get_tutor_profile()
        profile.looking_for_students = not profile.looking_for_students
        profile.save()
        return Response({"looking_for_students": profile.looking_for_students})

    @action(detail=True, methods=["post"], url_path="visited_schedule")
    def visited_schedule(self, request, pk=None):
        """Called when the tutor visits the schedule/available-hours page.
        Completes any open review_available_hours jobs and schedules a new one
        to reappear in 3 weeks."""
        tutor = self.get_object()
        now = timezone.now()
        # Complete existing open jobs of this type
        TutorJob.objects.filter(
            tutor=tutor,
            job_type='review_available_hours',
            completed_at__isnull=True,
        ).update(completed_at=now)
        # Create a new job visible 3 weeks from now
        TutorJob.objects.create(
            tutor=tutor,
            job_type='review_available_hours',
            expires_at=now + timedelta(days=365),
            show_from=now + timedelta(weeks=3),
        )
        return Response({'ok': True})

    @action(detail=True, methods=["get"])
    def students(self, request, pk=None):
        # print("Getting students:")
        tutor_user = self.get_object()
        data = get_cached_students_for_tutor(tutor_user)
        # print("Received students:", now)
        # print(data)
        return Response(data)

    @action(detail=True, methods=["get"], url_path="booking")
    def booking(self, request, pk=None):

        tutor = self.get_object()
        students = get_cached_students_for_tutor(tutor)

        today = date.today()
        weekday = today.weekday()
        last_monday = today - timedelta(days=weekday)
        next_monday = last_monday + timedelta(days=7)
        last_monday = last_monday.isoformat()
        next_monday = next_monday.isoformat()

        # Build two weeks using cached data
        week1 = get_combined_calendar(tutor, last_monday)
        week2 = get_combined_calendar(tutor, next_monday)
        # print("Week 1:", week1)

        return Response({
            "students": students,
            "week1": week1,
            "week2": week2,
        })

    @action(detail=True, methods=["post"])
    def edit(self, request, pk=None):
        print("Tutor edit")
        user = self.get_object()
        profile = user.get_tutor_profile()

        fields = request.data.get("fields", {})
        print("Tutor edit (fields)", fields)

        # Update User fields
        for key, value in fields.items():
            if hasattr(user, key):
                setattr(user, key, value)

        user.save()

        fields_to_update = ["mobile", "address", "default_session_minutes", "buffer_minutes", "default_hourly_rate"]
        changed = False
        for key, value in fields.items():
            if key in fields_to_update:
                print("Tutor edit:", key)
                setattr(profile, key, value)
                changed = True

        if changed:
            profile.save()

        return Response(profile.to_dict(), status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def sms(self, request, pk=None):
        tutor = self.get_object()
        conversations = SMSConversation.objects.filter(tutor=tutor).select_related("student").order_by("-last_message_at")

        data = []
        for convo in conversations:
            last_msg = convo.messages.order_by("-created_at").first()
            student = convo.student

            data.append({
                "conversation_id": convo.id,
                "student_id": student.id,
                "student_name": student.get_full_name() or student.username,
                "last_message": last_msg.body if last_msg else "",
                "last_message_at": last_msg.created_at if last_msg else convo.created_at,
            })

        return Response(data, status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"], url_path="sms/conversation/(?P<conversation_id>[^/.]+)")
    def sms_conversation(self, request, pk=None, conversation_id=None):
        tutor = self.get_object()

        try:
            convo = SMSConversation.objects.get(id=conversation_id, tutor=tutor)
        except SMSConversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=404)

        messages = convo.messages.order_by("created_at")

        return Response({
            "conversation_id": convo.id,
            "tutor_id": tutor.id,
            "student_id": convo.student.id,
            "student_name": convo.student.get_full_name(),
            "messages": [
                {
                    "id": m.id,
                    "direction": m.direction,
                    "body": m.body,
                    "created_at": m.created_at,
                    "sent_at": m.sent_at,
                    "delivered_at": m.delivered_at,
                    "status": m.status,
                    "phone_number": m.phone_number,
                }
                for m in messages
            ]
        })

    @action(detail=False, methods=["get"], url_path="admin_sms")
    def admin_sms(self, request):
        if getattr(request.user, 'role', None) != 'admin':
            return Response({'error': 'Forbidden'}, status=403)
        conversations = SMSConversation.objects.select_related("tutor", "student").order_by("-last_message_at")
        data = []
        for convo in conversations:
            last_msg = convo.messages.order_by("-created_at").first()
            data.append({
                "conversation_id": convo.id,
                "tutor_id": convo.tutor.id,
                "tutor_name": convo.tutor.get_full_name() or convo.tutor.username,
                "student_id": convo.student.id,
                "student_name": convo.student.get_full_name() or convo.student.username,
                "last_message": last_msg.body if last_msg else "",
                "last_message_at": last_msg.created_at if last_msg else convo.created_at,
            })
        return Response(data)

    @action(detail=False, methods=["get"], url_path=r"admin_sms/conversation/(?P<conversation_id>[^/.]+)")
    def admin_sms_conversation(self, request, conversation_id=None):
        if getattr(request.user, 'role', None) != 'admin':
            return Response({'error': 'Forbidden'}, status=403)
        try:
            convo = SMSConversation.objects.select_related("tutor", "student").get(id=conversation_id)
        except SMSConversation.DoesNotExist:
            return Response({"error": "Conversation not found"}, status=404)
        messages = convo.messages.order_by("created_at")
        return Response({
            "conversation_id": convo.id,
            "tutor_id": convo.tutor.id,
            "tutor_name": convo.tutor.get_full_name() or convo.tutor.username,
            "student_id": convo.student.id,
            "student_name": convo.student.get_full_name() or convo.student.username,
            "messages": [
                {
                    "id": m.id,
                    "direction": m.direction,
                    "body": m.body,
                    "created_at": m.created_at,
                    "sent_at": m.sent_at,
                    "delivered_at": m.delivered_at,
                    "status": m.status,
                    "phone_number": m.phone_number,
                }
                for m in messages
            ]
        })

    @action(detail=True, methods=["get"], url_path="sms/activity")
    def sms_activity(self, request, pk=None):
        tutor = self.get_object()

        today = timezone.localdate()
        start_of_day = timezone.make_aware(datetime.combine(today, time.min))

        jobs = (SMSSendJob.objects.filter(conversation__tutor_id=tutor.id, cancelled=False, retry_count__lt=3).order_by("-created_at"))
        messages = (SMSMessage.objects.filter(conversation__tutor_id=tutor.id, created_at__gte=start_of_day,).select_related("conversation", "conversation__student").order_by("-created_at"))
        active = get_bool("sms_send", default=False)
        # print("active's type:", type(active))


        return Response({
            "jobs": [job.to_dict() for job in jobs],
            "messages": [msg.to_dict() for msg in messages],
            "active": active
        })

    @action(detail=True, methods=["get"])
    def templates(self, request, pk=None):
        tutor = self.get_object()
        templates = Template.objects.filter(created_by=tutor)
        serializer = TemplateSerializer(templates, many=True)
        return Response(serializer.data)

    @action(detail=False, methods=["post"])
    def create_tutor(self, request):
        name = request.data.get("name")
        email = request.data.get("email")
        password = request.data.get("password") or User.objects.make_random_password()

        if not name or not email:
            return Response({"error": "Name and email are required"}, status=400)

        new_tutor = User.objects.create(
            username=email,
            email=email,
            first_name=name,
            role="tutor",
            password=make_password(password),
        )

        TutorProfile.objects.create(tutor=new_tutor)

        return Response({
            "id": new_tutor.id,
            "name": new_tutor.first_name,
            "email": new_tutor.email,
            "password": password
        })

    @action(detail=True, methods=["get"])
    def availability(self, request, pk=None):
        tutor = self.get_object()
        availability = list(
            TutorAvailability.objects.filter(tutor=tutor).values(
                "id", "weekday", "start_time", "end_time"
            )
        )
        # Convert time fields to strings for JSON serialisation
        for a in availability:
            a["start_time"] = str(a["start_time"])
            a["end_time"] = str(a["end_time"])
            # Return JS weekday (Mon=1..Sun=7 → stored as Mon=0..Sun=6, so +1 mod 7)
            a["weekday"] = (a["weekday"] + 1) % 7
        blocked_days = list(
            TutorBlockedDay.objects.filter(tutor=tutor).values("id", "date")
        )
        for b in blocked_days:
            b["date"] = str(b["date"])
        return Response({"availability": availability, "blocked_days": blocked_days})

    @action(detail=True, methods=["post"])
    def add_availability(self, request, pk=None):
        tutor = self.get_object()
        js_weekday = int(request.data["weekday"])
        weekday = (js_weekday - 1) % 7
        start = request.data.get("start_time")
        end = request.data.get("end_time")

        a = TutorAvailability.objects.create(
            tutor=tutor,
            weekday=weekday,
            start_time=start,
            end_time=end,
        )
        invalidate_availability_adhoc(tutor.id)
        invalidate_weekly_slots(tutor.id)

        return Response({"id": a.id})

    @action(detail=True, methods=["post"])
    def remove_availability(self, request, pk=None):

        TutorAvailability.objects.filter(id=request.data.get("id")).delete()
        invalidate_availability_adhoc(request.data.get("id"))

        return Response({"status": "ok"})

    @action(detail=True, methods=["post"])
    def block_day(self, request, pk=None):
        tutor = self.get_object()
        date = request.data.get("date")
        b = TutorBlockedDay.objects.create(tutor=tutor, date=date)
        invalidate_availability_adhoc(tutor.id)

        return Response({"id": b.id})


    @action(detail=True, methods=["post"])
    def unblock_day(self, request, pk=None):
        TutorBlockedDay.objects.filter(id=request.data.get("id")).delete()
        invalidate_availability_adhoc(tutor.id)

        return Response({"status": "ok"})

    @action(detail=True, methods=["get"])
    def session_settings(self, request, pk=None):
        user = self.get_object()
        tutor = TutorProfile.objects.get(tutor=user)
        serializer = TutorSerializer(tutor)
        return Response(serializer.data)


    # --------------- UNIFIED FUNCTION ----------------------

    @action(detail=True, methods=["POST"], url_path="booking_action")
    def booking_action(self, request, pk=None):
        tutor = self.get_object()
        data = request.data
        print("Booking action (data):", data)
        user_role = request.user.role

        command = data.get("command") or data.get("action")
        booking_type = data.get("booking_type") or data.get("type")
        booking_id = request.data.get("id")

        if not command or not booking_type:
            return Response({"ok": False, "error": "Missing command or booking_type"}, status=400)
        model = BookingAdhoc if booking_type == "adhoc" else BookingWeekly

        # CREATE
        if command == "create":
            # print("→ start create")
            # Delay the weekly and create adhoc (for a one-off change to a weekly schedule)
            if data.get("pause_weekly"):
                student_id = request.data.get("student_id")
                student = User.objects.get(id=student_id)
                weekly = BookingWeekly.objects.filter(tutor=tutor, student=student).first()
                if weekly:
                    weekly.skip()
                    update_booking_caches(weekly, "skip")
            return create_booking(tutor, data, booking_type, user_role)

        # ADJUST EXISTING BOOKING
        try:
            booking = model.objects.get(id=booking_id)
        except model.DoesNotExist:
            print("Couldn't find booking. model, Booking id:", model, booking_id)
            return Response({"ok": False, "error": "Booking not found"}, status=404)

        if command == "confirm":return confirm_booking(booking, user_role)
        if command == "edit": return edit_booking(booking, data, booking_type, user_role)
        if command == "skip": return skip_booking(booking, user_role)
        if command == "remove_skip": return remove_skip_booking(booking, user_role)
        if command == "delete":return delete_booking(booking, booking_type, user_role)

        return Response({"ok": False, "error": "Unknown command"}, status=400)

# -------------- TUTOR JOBS ---------------- #

def _get_parent_mobile(student):
    """Return a mobile number to contact the parent/guardian for a student.

    Priority: parent User linked via ParentChild → StudentProfile.mobile fallback.
    Parents don't have a dedicated profile model, so we fall back to the student's
    contact mobile (which for minors is typically the parent's number).
    """
    from .models import ParentChild, StudentProfile
    parent_link = ParentChild.objects.filter(child=student).select_related('parent').first()
    if parent_link:
        # Check if parent has a student profile (unlikely) or use student's mobile
        # Parents don't have a ParentProfile, so fall through to student mobile
        pass

    try:
        sp = StudentProfile.objects.get(user=student)
        return sp.mobile or None
    except StudentProfile.DoesNotExist:
        return None


class TutorJobViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        now = timezone.now()
        jobs = TutorJob.objects.filter(
            tutor=request.user,
            completed_at__isnull=True,
            expires_at__gt=now,
        ).filter(
            Q(show_from__isnull=True) | Q(show_from__lte=now)
        ).select_related('student', 'booking_outcome')
        data = []
        for job in jobs:
            outcome = job.booking_outcome
            data.append({
                'id': job.id,
                'job_type': job.job_type,
                'student_id': job.student_id,
                'student_first_name': job.student.first_name if job.student else None,
                'student_last_name': job.student.last_name if job.student else None,
                'tutor_id': job.tutor_id,
                'triggered_at': job.triggered_at,
                'booking_date': outcome.date if outcome else None,
                'booking_time': outcome.time.strftime('%H:%M') if outcome and outcome.time else None,
            })
        return Response(data)

    @action(detail=True, methods=['get'])
    def progress_message(self, request, pk=None):
        from .models import (
            StudentProfile, StudentFocusArea, StudentSkillCompetency, Skill, ParentChild
        )
        import datetime

        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related(
            'student', 'booking_outcome'
        ).first()
        if not job:
            return Response({'error': 'Not found'}, status=404)

        student = job.student
        outcome = job.booking_outcome

        # If a message is already saved, return it
        if outcome and outcome.parent_message:
            parent_mobile = _get_parent_mobile(student)
            return Response({
                'message': outcome.parent_message,
                'parent_mobile': parent_mobile,
            })

        # --- Build the message ---
        student_name = student.first_name or "Your child"

        # Year level
        try:
            sp = StudentProfile.objects.get(user=student)
            year_level = sp.year_level or "?"
        except StudentProfile.DoesNotExist:
            year_level = "?"

        # Session date (Monday of that week for tutoring_done_week lookup)
        session_date = outcome.date if outcome else None
        if session_date:
            # Monday of the session week
            session_monday = session_date - datetime.timedelta(days=session_date.weekday())
        else:
            session_monday = None

        # Focus areas covered this session
        if session_monday:
            session_focus = StudentFocusArea.objects.filter(
                student=student,
                tutoring_done_week=session_monday,
            ).select_related('skill')
        else:
            session_focus = StudentFocusArea.objects.none()

        focus_names = [fa.skill.description for fa in session_focus if fa.skill]
        if not focus_names:
            focus_text = "various topics"
        elif len(focus_names) == 1:
            focus_text = focus_names[0]
        elif len(focus_names) == 2:
            focus_text = f"{focus_names[0]} and {focus_names[1]}"
        else:
            focus_text = ", ".join(focus_names[:-1]) + f", and {focus_names[-1]}"

        # Syllabus completion
        year_skills = Skill.objects.filter(is_detail=True)
        if year_level and year_level != "?":
            # Filter to skills that include this year level
            year_skills = [s for s in year_skills if year_level in [str(g) for g in s.get_grade_list()]]
        else:
            year_skills = list(year_skills)

        total_skills = len(year_skills)
        if total_skills > 0:
            year_skill_ids = [s.id for s in year_skills]
            completed_ids = set(
                StudentSkillCompetency.objects.filter(
                    student=student, skill_id__in=year_skill_ids, level__gt=0
                ).values_list('skill_id', flat=True)
            )
            current_pct = round(len(completed_ids) / total_skills * 100)

            # Estimate previous %: skills newly mastered this session
            # = focus areas done this session where level_before_learning was 0 and now level > 0
            newly_mastered = session_focus.filter(
                level_before_learning=0,
                skill_id__in=completed_ids,
            ).count()
            prev_completed = max(len(completed_ids) - newly_mastered, 0)
            prev_pct = round(prev_completed / total_skills * 100)
        else:
            current_pct = 0
            prev_pct = 0

        # Parent mobile
        parent_mobile = _get_parent_mobile(student)

        # Build message
        if current_pct != prev_pct:
            pct_line = (
                f"has now completed {current_pct}% of the Year {year_level} Maths syllabus"
                f" — up from {prev_pct}% last week"
            )
        else:
            pct_line = f"has now completed {current_pct}% of the Year {year_level} Maths syllabus"

        message = (
            f"Great news! {student_name} had a productive session today. "
            f"They worked through {focus_text}, and {pct_line}. "
            f"Keep up the encouragement at home! 🎉"
        )

        return Response({
            'message': message,
            'parent_mobile': parent_mobile,
        })

    @action(detail=True, methods=['post'])
    def save_progress_message(self, request, pk=None):
        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related('booking_outcome').first()
        if not job:
            return Response({'error': 'Not found'}, status=404)
        outcome = job.booking_outcome
        if not outcome:
            return Response({'error': 'No outcome record'}, status=400)
        msg = request.data.get('message', '')
        outcome.parent_message = msg
        outcome.save(update_fields=['parent_message'])
        return Response({'ok': True})

    @action(detail=True, methods=['post'])
    def send_progress_message(self, request, pk=None):
        from .models import SMSSendJob, SMSConversation, StudentProfile, get_or_create_conversation
        from .message import process_sms_jobs

        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related(
            'student', 'booking_outcome'
        ).first()
        if not job:
            return Response({'error': 'Not found'}, status=404)

        outcome = job.booking_outcome
        if not outcome or not outcome.parent_message:
            return Response({'error': 'No message to send'}, status=400)

        student = job.student
        tutor = request.user

        # Use to_number so the SMS goes to the parent's mobile.
        # Link to the tutor-student conversation so the message appears in the inbox.
        parent_mobile = _get_parent_mobile(student)
        if not parent_mobile:
            return Response({'error': 'No parent mobile number found'}, status=400)

        conversation = get_or_create_conversation(tutor, student)

        SMSSendJob.objects.create(
            conversation=conversation,
            to_number=parent_mobile,
            body=outcome.parent_message,
            scheduled_for=timezone.now(),
        )
        process_sms_jobs()

        return Response({'ok': True})

    @action(detail=True, methods=['get'])
    def payment_summary(self, request, pk=None):
        from .models import (
            StudentProfile, TutorProfile, DistributorParent, ParentChild, Payment
        )
        import decimal

        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related(
            'student', 'booking_outcome'
        ).first()
        if not job:
            return Response({'error': 'Not found'}, status=404)

        student = job.student
        tutor = request.user
        outcome = job.booking_outcome

        # Student hourly rate and session duration
        try:
            sp = StudentProfile.objects.get(user=student)
            hourly_rate = sp.hourly_rate
        except StudentProfile.DoesNotExist:
            hourly_rate = decimal.Decimal('70.00')

        tutor_profile = TutorProfile.objects.filter(tutor=tutor).first()
        session_minutes = tutor_profile.default_session_minutes if tutor_profile else 60
        amount_paid = (hourly_rate * decimal.Decimal(session_minutes) / decimal.Decimal(60)).quantize(decimal.Decimal('0.01'))

        # Distributor: student → parent → DistributorParent
        distributor = None
        parent_link = ParentChild.objects.filter(child=student).select_related('parent').first()
        if parent_link:
            dist_link = DistributorParent.objects.filter(parent=parent_link.parent).select_related('distributor').first()
            if dist_link:
                distributor = dist_link.distributor

        # Account details
        account_tutor = tutor.account_details or ""
        account_distributor = distributor.account_details if distributor else ""

        # Split: tutor share = hourly_rate prorated; platform and (if distributor exists) distributor fees from GlobalSettings
        from .models import get_decimal
        platform_fee_per_hour = get_decimal('platform_fee_per_hour', '5')
        distributor_fee_per_hour = get_decimal('distributor_fee_per_hour', '5')
        mins = decimal.Decimal(session_minutes)
        amount_tutor       = (hourly_rate          * mins / 60).quantize(decimal.Decimal('0.01'))
        amount_platform    = (platform_fee_per_hour * mins / 60).quantize(decimal.Decimal('0.01'))
        amount_distributor = (distributor_fee_per_hour * mins / 60).quantize(decimal.Decimal('0.01')) if distributor else decimal.Decimal('0.00')
        amount_paid = (amount_tutor + amount_platform + amount_distributor).quantize(decimal.Decimal('0.01'))

        # Check if payment already applied
        payment_id = outcome.payment_id if outcome else None
        already_applied = payment_id is not None
        has_outcome = outcome is not None

        return Response({
            'student_name': f"{student.first_name} {student.last_name}".strip() if student else "",
            'tutor_name': tutor.get_full_name(),
            'distributor_name': distributor.get_full_name() if distributor else None,
            'hourly_rate': str(hourly_rate),
            'session_minutes': session_minutes,
            'amount_paid': str(amount_paid),
            'amount_tutor': str(amount_tutor),
            'amount_platform': str(amount_platform),
            'amount_distributor': str(amount_distributor),
            'platform_fee_per_hour': str(platform_fee_per_hour),
            'distributor_fee_per_hour': str(distributor_fee_per_hour),
            'account_tutor': account_tutor,
            'account_distributor': account_distributor,
            'date_tuition': outcome.date.isoformat() if outcome and outcome.date else None,
            'already_applied': already_applied,
            'payment_id': payment_id,
            'has_outcome': has_outcome,
        })

    @action(detail=True, methods=['post'])
    def apply_payment(self, request, pk=None):
        from .models import (
            StudentProfile, TutorProfile, DistributorParent, ParentChild, Payment
        )
        import decimal

        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related(
            'student', 'booking_outcome'
        ).first()
        if not job:
            return Response({'error': 'Not found'}, status=404)

        outcome = job.booking_outcome
        if not outcome:
            return Response({'error': 'No outcome record'}, status=400)

        if outcome.payment_id:
            return Response({'error': 'Payment already applied', 'payment_id': outcome.payment_id}, status=400)

        student = job.student
        tutor = request.user

        # Student hourly rate and session duration
        try:
            sp = StudentProfile.objects.get(user=student)
            hourly_rate = sp.hourly_rate
        except StudentProfile.DoesNotExist:
            hourly_rate = decimal.Decimal('70.00')

        tutor_profile = TutorProfile.objects.filter(tutor=tutor).first()
        session_minutes = tutor_profile.default_session_minutes if tutor_profile else 60

        # Distributor
        distributor = None
        parent_link = ParentChild.objects.filter(child=student).select_related('parent').first()
        if parent_link:
            dist_link = DistributorParent.objects.filter(parent=parent_link.parent).select_related('distributor').first()
            if dist_link:
                distributor = dist_link.distributor

        # Focus areas as text
        focus_text = ", ".join(
            fa.skill.description for fa in outcome.focus_areas.select_related('skill').all() if fa
        ) if outcome.focus_areas.exists() else ""

        # Split: tutor share = hourly_rate prorated; platform and (if distributor exists) distributor fees from GlobalSettings
        from .models import get_decimal
        platform_fee_per_hour    = get_decimal('platform_fee_per_hour', '5')
        distributor_fee_per_hour = get_decimal('distributor_fee_per_hour', '5')
        mins = decimal.Decimal(session_minutes)
        amount_tutor       = (hourly_rate               * mins / 60).quantize(decimal.Decimal('0.01'))
        amount_platform    = (platform_fee_per_hour    * mins / 60).quantize(decimal.Decimal('0.01'))
        amount_distributor = (distributor_fee_per_hour * mins / 60).quantize(decimal.Decimal('0.01')) if distributor else decimal.Decimal('0.00')
        amount_paid = (amount_tutor + amount_platform + amount_distributor).quantize(decimal.Decimal('0.01'))

        payment = Payment.objects.create(
            student=student,
            tutor=tutor,
            distributor=distributor,
            amount_paid=amount_paid,
            amount_tutor=amount_tutor,
            amount_platform=amount_platform,
            amount_distributor=amount_distributor,
            account_tutor=tutor.account_details or "",
            account_distributor=distributor.account_details if distributor else "",
            date_tuition=outcome.date,
            focus_area=focus_text,
            notes=outcome.notes or "",
        )

        outcome.payment = payment
        outcome.save(update_fields=['payment'])

        return Response({'ok': True, 'payment_id': payment.id})

    @action(detail=True, methods=['post'])
    def complete(self, request, pk=None):
        job = TutorJob.objects.filter(pk=pk, tutor=request.user).select_related('booking_outcome').first()
        if not job:
            return Response({'error': 'Not found'}, status=404)
        job.completed_at = timezone.now()
        job.save()

        # For post_tuition_review, persist any outcome data submitted with the request.
        # If the BookingOutcome is missing (e.g. legacy job) and focus_area_next_ids are
        # being submitted, create the record now so data is never silently dropped.
        if job.job_type == 'post_tuition_review' and not job.booking_outcome and 'focus_area_next_ids' in request.data:
            from .models import BookingOutcome as _BO
            import datetime as _dt
            outcome = _BO.objects.create(
                tutor=job.tutor,
                student=job.student,
                date=_dt.date.today(),
                time=_dt.time(0, 0),
            )
            job.booking_outcome = outcome
            job.save(update_fields=['booking_outcome'])

        if job.job_type == 'post_tuition_review' and job.booking_outcome:
            outcome = job.booking_outcome
            scalar_fields = []
            if 'parent_message' in request.data:
                outcome.parent_message = request.data['parent_message']
                scalar_fields.append('parent_message')
            if 'notes' in request.data:
                outcome.notes = request.data['notes']
                scalar_fields.append('notes')
            if 'payment_id' in request.data:
                outcome.payment_id = request.data['payment_id'] or None
                scalar_fields.append('payment_id')
            if scalar_fields:
                outcome.save(update_fields=scalar_fields)
            if 'focus_area_ids' in request.data:
                from .models import Skill
                ids = request.data['focus_area_ids']
                if not isinstance(ids, list):
                    ids = [ids]
                outcome.focus_areas.set(Skill.objects.filter(id__in=ids))
            if 'focus_area_next_ids' in request.data:
                from .models import Skill
                ids = request.data['focus_area_next_ids']
                if not isinstance(ids, list):
                    ids = [ids]
                outcome.focus_areas_next.set(Skill.objects.filter(id__in=ids))

        return Response({'ok': True})


# -------------- ADMIN JOBS ---------------- #

class AdminJobViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _check_admin(self, request):
        if getattr(request.user, 'role', None) != 'admin':
            return Response({'error': 'Forbidden'}, status=403)
        return None

    def list(self, request):
        err = self._check_admin(request)
        if err: return err
        from .models import AdminJob, TutorProfile, DistributorProfile

        # Ensure every unapproved applicant has a pending AdminJob,
        # regardless of when they registered.
        for profile in TutorProfile.objects.filter(approved=False).select_related('tutor'):
            if not AdminJob.objects.filter(
                job_type='approve_tutor', subject=profile.tutor, completed_at__isnull=True
            ).exists():
                AdminJob.objects.create(job_type='approve_tutor', subject=profile.tutor)

        for profile in DistributorProfile.objects.filter(approved=False).select_related('user'):
            if not AdminJob.objects.filter(
                job_type='approve_distributor', subject=profile.user, completed_at__isnull=True
            ).exists():
                AdminJob.objects.create(job_type='approve_distributor', subject=profile.user)

        jobs = AdminJob.objects.filter(completed_at__isnull=True).select_related('subject')
        data = []
        for job in jobs:
            entry = {
                'id': job.id,
                'job_type': job.job_type,
                'subject_id': job.subject_id,
                'first_name': job.subject.first_name,
                'last_name': job.subject.last_name,
                'email': job.subject.email,
                'triggered_at': job.triggered_at,
            }
            if job.job_type == 'approve_tutor':
                profile = TutorProfile.objects.filter(tutor=job.subject).first()
                if profile:
                    entry['qualification'] = profile.qualification
                    entry['bio'] = profile.bio
                    entry['year_levels'] = profile.tutor_year_levels
            elif job.job_type == 'approve_distributor':
                profile = DistributorProfile.objects.filter(user=job.subject).first()
                if profile:
                    entry['bio'] = profile.bio
                    entry['mobile'] = profile.mobile
            data.append(entry)
        return Response(data)

    @action(detail=True, methods=['post'])
    def approve(self, request, pk=None):
        err = self._check_admin(request)
        if err: return err
        from .models import AdminJob, TutorProfile, DistributorProfile
        job = AdminJob.objects.filter(pk=pk).select_related('subject').first()
        if not job:
            return Response({'error': 'Not found'}, status=404)
        subject = job.subject
        subject.active = True
        subject.save()
        from .message import send_approval_sms
        if job.job_type == 'approve_tutor':
            TutorProfile.objects.filter(tutor=subject).update(approved=True)
            profile = TutorProfile.objects.filter(tutor=subject).first()
            mobile = profile.mobile if profile else None
            send_approval_sms(mobile, subject.first_name, "tutor", subject, request.user)
        elif job.job_type == 'approve_distributor':
            DistributorProfile.objects.filter(user=subject).update(approved=True)
            profile = DistributorProfile.objects.filter(user=subject).first()
            mobile = profile.mobile if profile else None
            send_approval_sms(mobile, subject.first_name, "distributor", subject, request.user)
        job.completed_at = timezone.now()
        job.save()
        return Response({'ok': True})

    @action(detail=True, methods=['post'])
    def dismiss(self, request, pk=None):
        err = self._check_admin(request)
        if err: return err
        from .models import AdminJob
        job = AdminJob.objects.filter(pk=pk).first()
        if not job:
            return Response({'error': 'Not found'}, status=404)
        job.completed_at = timezone.now()
        job.save()
        return Response({'ok': True})

    @action(detail=False, methods=["get"])
    def payments(self, request):
        err = self._check_admin(request)
        if err: return err

        from .models import Payment
        from django.db.models import Sum
        from datetime import date

        today = date.today()
        current_month_start = today.replace(day=1)
        if today.month == 1:
            last_month_start = today.replace(year=today.year - 1, month=12, day=1)
        else:
            last_month_start = today.replace(month=today.month - 1, day=1)

        qs = (
            Payment.objects
            .select_related("student", "tutor")
            .order_by("-date_tuition", "-created_at")
        )

        def _fmt(p):
            return {
                "id": p.id,
                "date_tuition": p.date_tuition.isoformat() if p.date_tuition else None,
                "student_name": p.student.get_full_name() if p.student else "Unknown",
                "tutor_name": p.tutor.get_full_name() if p.tutor else "Unknown",
                "amount_paid": str(p.amount_paid),
                "amount_tutor": str(p.amount_tutor),
                "amount_platform": str(p.amount_platform),
                "amount_distributor": str(p.amount_distributor),
                "focus_area": p.focus_area,
            }

        def _totals(queryset):
            agg = queryset.aggregate(
                paid=Sum("amount_paid"),
                tutor=Sum("amount_tutor"),
                platform=Sum("amount_platform"),
                distributor=Sum("amount_distributor"),
            )
            return {
                "total_paid": str(agg["paid"] or "0.00"),
                "total_tutor": str(agg["tutor"] or "0.00"),
                "total_platform": str(agg["platform"] or "0.00"),
                "total_distributor": str(agg["distributor"] or "0.00"),
            }

        current_qs = qs.filter(date_tuition__gte=current_month_start)
        last_qs    = qs.filter(date_tuition__gte=last_month_start, date_tuition__lt=current_month_start)
        older_qs   = qs.filter(date_tuition__lt=last_month_start)

        return Response({
            "current_month": {"label": today.strftime("%B %Y"), "payments": [_fmt(p) for p in current_qs], **_totals(current_qs)},
            "last_month":    {"label": last_month_start.strftime("%B %Y"), "payments": [_fmt(p) for p in last_qs], **_totals(last_qs)},
            "older":         {"payments": [_fmt(p) for p in older_qs], **_totals(older_qs)},
        })


# -------------- FOCUS AREAS ---------------- #

class FocusAreaViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def list(self, request):
        student_id = request.query_params.get("student_id")
        if not student_id:
            return Response({"error": "student_id required"}, status=400)

        from .competency import level_to_label as _ltl
        from django.utils import timezone as _tz
        from datetime import timedelta as _td
        focus_areas = StudentFocusArea.objects.filter(student_id=student_id).select_related("skill")
        comp_map = {
            row.skill_id: row
            for row in StudentSkillCompetency.objects.filter(student_id=student_id)
        }

        now = _tz.now()
        this_monday = _this_weeks_monday()
        data = []
        for fa in focus_areas.order_by("order", "id"):
            comp = comp_map.get(fa.skill_id)
            lvl = comp.level if comp else 0
            learning_done = fa.learning_done_week == this_monday

            # 6-day cooldown: if the student has earned at least 1 star, they must
            # wait 6 days before they can earn the next one.
            next_star_available = None
            if comp and lvl >= 1 and comp.updated_at:
                unlock = comp.updated_at + _td(days=6)
                if unlock > now:
                    next_star_available = unlock.isoformat()

            data.append({
                "id": fa.id,
                "skill_id": fa.skill_id,
                "skill_code": fa.skill.code,
                "skill_description": fa.skill.description,
                "order": fa.order,
                "mastery": lvl,
                "competence_label": _ltl(lvl),
                "learning_done_this_week": learning_done,
                "tutoring_done_this_week": fa.tutoring_done_week == this_monday,
                "next_star_available": next_star_available,
                # Level snapshots for learning-status display (only meaningful when learning_done)
                "level_before_learning": fa.level_before_learning if learning_done else None,
                "level_after_learning": fa.level_after_learning if learning_done else None,
                "label_before_learning": _ltl(fa.level_before_learning) if learning_done and fa.level_before_learning is not None else None,
                "label_after_learning": _ltl(fa.level_after_learning) if learning_done and fa.level_after_learning is not None else None,
            })
        return Response(data)

    def create(self, request):
        student_id = request.data.get("student_id")
        skill_id = request.data.get("skill_id")
        if not student_id or not skill_id:
            return Response({"error": "student_id and skill_id required"}, status=400)
        max_order = StudentFocusArea.objects.filter(student_id=student_id).aggregate(
            m=models.Max("order")
        )["m"] or 0
        fa, created = StudentFocusArea.objects.get_or_create(
            student_id=student_id,
            skill_id=skill_id,
            defaults={"added_by": request.user, "order": max_order + 1},
        )
        return Response({"id": fa.id, "created": created})

    def destroy(self, request, pk=None):
        StudentFocusArea.objects.filter(pk=pk).delete()
        return Response({"deleted": True})

    @action(detail=True, methods=["post"], url_path="move_up")
    def move_up(self, request, pk=None):
        fa = StudentFocusArea.objects.filter(pk=pk).first()
        if not fa:
            return Response({"error": "Not found"}, status=404)
        prev = (
            StudentFocusArea.objects
            .filter(student=fa.student, order__lt=fa.order)
            .order_by("-order", "-id")
            .first()
        )
        if prev:
            fa.order, prev.order = prev.order, fa.order
            fa.save()
            prev.save()
        return Response({"ok": True})

    @action(detail=True, methods=["post"], url_path="move_down")
    def move_down(self, request, pk=None):
        fa = StudentFocusArea.objects.filter(pk=pk).first()
        if not fa:
            return Response({"error": "Not found"}, status=404)
        nxt = (
            StudentFocusArea.objects
            .filter(student=fa.student, order__gt=fa.order)
            .order_by("order", "id")
            .first()
        )
        if nxt:
            fa.order, nxt.order = nxt.order, fa.order
            fa.save()
            nxt.save()
        return Response({"ok": True})


# -------------- STUDENT ---------------- #

class StudentViewSet(viewsets.ModelViewSet):
    queryset = User.objects.filter(role="student").select_related("student_profile")
    serializer_class = StudentSerializer
    permission_classes = [AllowAny]

    def list(self, request, *args, **kwargs):
        users = self.get_queryset().prefetch_related("tutors__tutor")
        data = []
        for u in users:
            profile = getattr(u, "student_profile", None)
            tutor_link = u.tutors.first()
            tutor = tutor_link.tutor if tutor_link else None
            data.append({
                "user_id": u.id,
                "profile_id": profile.id if profile else None,
                "first_name": u.first_name,
                "last_name": u.last_name,
                "email": u.email,
                "mobile": profile.mobile if profile else None,
                "active": u.active,
                "year_level": profile.year_level if profile else None,
                "area_of_study": profile.area_of_study if profile else None,
                "tutor_name": tutor.get_full_name() if tutor else None,
                "tutor_id": tutor.id if tutor else None,
            })
        data.sort(key=lambda s: (s["tutor_name"] or "", s["first_name"].lower()))
        return Response(data)

    def get_object(self):
        user = super().get_object()
        profile = user.get_student_profile()
        return profile

    def retrieve(self, request, *args, **kwargs):
        student_profile = self.get_object()
        data = student_profile.to_dict()
        lang_pref = UserPreference.objects.filter(user=student_profile.user, key='language').first()
        data['language'] = lang_pref.value if lang_pref else 'en'
        return Response(data)

    @action(detail=True, methods=["post"])
    def edit(self, request, pk=None):
        student_profile = self.get_object()
        student = student_profile.user
        fields = request.data.get("fields", {})
        print("Student edit (fields)", fields)
        for key, value in fields.items():
            if hasattr(student, key):
                print("Saved (to user): ", key, value)
                setattr(student, key, value)

        student.save()

        profile_fields = ["year_level", "area_of_study", "mobile", "address"]
        changed = False

        for key, value in fields.items():
            if key in profile_fields:
                print("Student edit:", key)
                setattr(student_profile, key, value)
                changed = True
        if changed:
            student_profile.save()

        if 'language' in fields:
            UserPreference.objects.update_or_create(
                user=student,
                key='language',
                defaults={'value': fields['language']},
            )

        update_student_cache(student)
        return Response(student_profile.to_dict(), status=status.HTTP_200_OK)

    @action(detail=True, methods=["get"])
    def home(self, request, pk=None):
        student_profile = self.get_object()
        result = student_profile.to_dict()
        student = student_profile.user
        lang_pref = UserPreference.objects.filter(user=student, key='language').first()
        result['language'] = lang_pref.value if lang_pref else 'en'
        return Response(result)

    @action(detail=True, methods=["post"])
    def set_language(self, request, pk=None):
        """Set the question language preference for this student."""
        student_profile = self.get_object()
        student = student_profile.user
        language = request.data.get('language', 'en')
        UserPreference.objects.update_or_create(
            user=student,
            key='language',
            defaults={'value': language},
        )
        return Response({'ok': True, 'language': language})

    @action(detail=True, methods=["get"])
    def progress(self, request, pk=None):
        """Return weekly overall progress snapshots for the student."""
        from .models import WeeklyProgressSnapshot
        student_profile = self.get_object()
        student = student_profile.user

        snapshots = WeeklyProgressSnapshot.objects.filter(student=student).order_by('recorded_at')
        return Response({
            "snapshots": [
                {
                    "date": s.recorded_at.strftime("%d %b %Y"),
                    "score": s.score,
                }
                for s in snapshots
            ]
        })

    @action(detail=True, methods=["get"])
    def booking(self, request, pk=None):
        student_profile = self.get_object()
        student = student_profile.user

        tutor = student.get_tutor()
        if not tutor:
            return Response({"error": "Student has no tutor assigned"}, status=400)

        start_date = (date.today() + timedelta(days=1)).isoformat()

        weekly_slots = get_weekly_slots(tutor)
        weekly_bookings = get_weekly_bookings(tutor)
        weekly_bookings = mask_weekly_bookings(weekly_bookings, student.id)

        adhoc_slots = get_availability_adhoc(tutor, start_date)
        adhoc_bookings = get_adhoc_bookings(tutor, start_date)
        adhoc_bookings = mask_adhoc_bookings(adhoc_bookings, student.id)

        return Response({
            "weekly_slots": weekly_slots,
            "weekly_bookings": weekly_bookings,
            "adhoc_slots": adhoc_slots,
            "adhoc_bookings": adhoc_bookings,
        })

    @action(detail=False, methods=["post"])
    def create_student(self, request):
        name = request.data.get("name")
        email = request.data.get("email")
        password = request.data.get("password") or User.objects.make_random_password()
        tutor_id = request.data.get("tutor_id")
        year_level = (request.data.get("year_level") or "").strip() or None
        print("Create student: Tutor id:", tutor_id)

        # Pre-creation checks
        if not name or not email: return Response({"error": "Name and email are required"}, status=400)
        user = User.objects.filter(email=email).first()
        if user: return Response({"error": "A user with this email already exists."}, status=400)

        # Create the user, student profile, link student to tutor and update cache
        user = User.objects.create(username=email, email=email, first_name=name, role="student", password=make_password(password),)
        profile, _ = StudentProfile.objects.get_or_create(user=user)
        profile_fields = []
        if year_level:
            profile.year_level = year_level
            profile_fields.append("year_level")
        if tutor_id:
            TutorStudent.objects.get_or_create(tutor_id=tutor_id, student=user)
            tutor_profile = TutorProfile.objects.filter(tutor_id=tutor_id).first()
            if tutor_profile:
                profile.hourly_rate = tutor_profile.default_hourly_rate
                profile_fields.append("hourly_rate")
        if profile_fields:
            profile.save(update_fields=profile_fields)
        update_student_cache(user)

        return Response(user.to_dict())

class NoteViewSet(viewsets.ModelViewSet):
    queryset = Note.objects.all().order_by("-created_at")
    serializer_class = NoteSerializer

    def get_queryset(self):
        qs = super().get_queryset()
        template_id = self.request.query_params.get("template")
        if template_id:
            qs = qs.filter(template_id=template_id)
        return qs

    def perform_create(self, serializer):
        user = self.request.user if self.request.user.is_authenticated else None
        serializer.save(author=user)

class BookingWeeklyViewSet(viewsets.ModelViewSet):
    queryset = BookingWeekly.objects.all()
    serializer_class = BookingWeeklySerializer

    @action(detail=True, methods=["post"])
    def skip(self, request, pk=None):
        booking = self.get_object()
        booking.skip()
        invalidate_weekly_slots(booking.tutor.id)
        return Response({
            "ok": True,
            "id": booking.id,
        })

    @action(detail=True, methods=["post"])
    def remove_skip(self, request, pk=None):
        booking = self.get_object()
        booking.remove_skip()
        invalidate_weekly_slots(booking.tutor.id)
        return Response({
            "ok": True,
            "id": booking.id,
        })


class BookingAdhocViewSet(viewsets.ModelViewSet):
    queryset = BookingAdhoc.objects.all()
    serializer_class = BookingAdhocSerializer

    def create(self, request, *args, **kwargs):
        print("BookingAdhoc api - create")
        student_id = request.data.get("student_id")
        start_str = request.data.get("start")
        if start_str.endswith("Z"): start_str = start_str.replace("Z", "+00:00")

        if not student_id or not start_str:
            print("Adhoc create", student_id, start_str)
            return Response({"error": "student_id and start are required"}, status=400)

        try:
            start_dt = datetime.fromisoformat(start_str)
            start_dt = timezone.localtime(start_dt, local_tz)

        except ValueError:
            print("Adhoc create - datestring:", start_str)
            return Response({"error": "Invalid datetime format"}, status=400)

        student = User.objects.get(id=student_id)

        try:
            booking = student.replace_this_weeks_adhoc(start_dt)

        except ValueError as e:
            print("Adhoc create - Booking error", str(e))
            return Response({"error": str(e)}, status=400)

        serializer = self.get_serializer(booking)
        return Response(serializer.data, status=201)

    def destroy(self, request, *args, **kwargs):
        booking = self.get_object()
        booking.delete()
        return Response(status=204)

    from rest_framework.decorators import action
    from rest_framework.response import Response
    from rest_framework import status

class BookingAdhocViewSet(viewsets.ModelViewSet):
    queryset = BookingAdhoc.objects.all()
    serializer_class = BookingAdhocSerializer

    @action(detail=False, methods=["post"], url_path="delete_override")
    def delete_override(self, request):
        print("Delete override")
        student_id = request.data.get("student_id")
        if not student_id:
            return Response({"error": "student_id required"}, status=400)

        student = User.objects.filter(id=student_id).first()
        if not student:
            return Response({"error": "Student not found"}, status=404)

        # Get the next ad-hoc booking (the override)
        override = student.next_ad_hoc_booking()
        if not override:
            return Response({"ok": True, "message": "No override to delete"})

        BookingAdhoc.objects.filter(id=override["id"]).delete()
        print("Deleted")

        # Invalidate caches
        tutor_id = student.get_tutor().id
        invalidate_availability_adhoc(tutor_id)
        invalidate_adhoc_bookings(tutor_id)

        return Response({"ok": True})

    @action(detail=False, methods=["post"], url_path="modify_one_week")
    def modify_one_week(self, request):
        print("Modify one week")
        student_id = request.data.get("student_id")
        start_str = request.data.get("start")

        if not student_id or not start_str:
            print("No student id or start str")
            return Response({"error": "student_id and start required"}, status=400)

        student = User.objects.filter(id=student_id).first()
        if not student:
            print("Student not found")
            return Response({"error": "Student not found"}, status=404)

        try:
            start_str = start_str.replace("Z", "+00:00")
            start_dt = datetime.fromisoformat(start_str)
            start_dt = timezone.localtime(start_dt, local_tz)

        except Exception:
            print("Invalid start datetime:", start_str)
            return Response({"error": "Invalid start datetime"}, status=400)

        # 1. Delete existing override (if any)
        override = student.next_ad_hoc_booking()
        if override:
            BookingAdhoc.objects.filter(id=override["id"]).delete()

        # 2. Create new override
        new_booking = student.booking_create_adhoc(start_dt)

        # 3. Pause weekly booking if needed
        weekly = student.next_weekly_booking()

        if weekly:
            weekly_id = weekly["id"]
            weekly = BookingWeekly.objects.get(id=weekly_id)
            weekly.skip()

        tutor_id = student.get_tutor().id
        invalidate_weekly_bookings(tutor_id)
        invalidate_adhoc_bookings(tutor_id)

        return Response({
            "ok": True,
        })

class SMSConversationViewSet(viewsets.ViewSet):

    def retrieve(self, request, pk=None):
        convo = SMSConversation.objects.get(pk=pk)
        messages = convo.messages.order_by("created_at")

        data = []
        for msg in messages:
            data.append({
                "id": msg.id,
                "direction": msg.direction,
                "body": msg.body,
                "created_at": msg.created_at,
                "sent_at": msg.sent_at,
                "delivered_at": msg.delivered_at,
                "status": msg.status,
                "phone_number": msg.phone_number,
            })

        return Response({
            "conversation_id": convo.id,
            "tutor_id": convo.tutor.id,
            "student_id": convo.student.id,
            "student_name": convo.student.get_full_name(),
            "messages": data,
        })

class PreferenceViewSet(viewsets.ModelViewSet):
    serializer_class = UserPreferenceSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return UserPreference.objects.filter(user=self.request.user)

    @action(detail=False, methods=["post"])
    def set(self, request):
        key = request.data.get("key")
        value = request.data.get("value")

        if not key:
            return Response({"error": "Missing key"}, status=400)

        pref, _ = UserPreference.objects.update_or_create(
            user=request.user,
            key=key,
            defaults={"value": value}
        )

        return Response({"ok": True})

    @action(detail=False, methods=["get"])
    def flat(self, request):
        prefs = self.get_queryset()
        return Response({p.key: p.value for p in prefs})


def _pick_template(skill_id, grade, difficulty, used_ids):
    """Return a validated template for a skill/grade, trying target difficulty then any, avoiding used ids."""
    qs_base = Template.objects.filter(skill_detail__parent_id=skill_id, grade=grade, validated=True)
    for diff_filter in [{"difficulty__iexact": difficulty}, {}]:
        t = qs_base.filter(**diff_filter).exclude(id__in=used_ids).order_by("?").first()
        if t:
            return t
    # All templates used — allow repeats
    return qs_base.filter(difficulty__iexact=difficulty).order_by("?").first() or qs_base.order_by("?").first()


def _update_skill_mastery(student, skill_id, correct):
    """Kept for compatibility — no longer updates a mastery float; competency is updated via QuestionViewSet."""
    pass


def _session_focus_area_question(session, student, grade, state, result):
    focus_areas = list(
        StudentFocusArea.objects.filter(student=student).select_related("skill").order_by("order", "id")
    )
    if not focus_areas:
        return Response({"template_id": None, "error": "No focus areas set for this student"})

    # Update mastery for the skill just answered
    if result in ("correct", "wrong") and state.get("current_skill_id"):
        _update_skill_mastery(student, state["current_skill_id"], result == "correct")

    focus_index = state.get("focus_index", 0)
    correct_streak = state.get("correct_streak", 0)
    used_ids = state.get("used_template_ids", [])

    if result == "correct":
        correct_streak += 1
        if correct_streak >= 3:
            focus_index = (focus_index + 1) % len(focus_areas)
            correct_streak = 0
    elif result == "wrong":
        correct_streak = 0

    fa = focus_areas[min(focus_index, len(focus_areas) - 1)]

    # Difficulty from competency level
    from .competency import get_student_question_difficulty
    difficulty = get_student_question_difficulty(student, fa.skill.code)

    template = _pick_template(fa.skill_id, grade, difficulty, used_ids)
    if template:
        used_ids = (used_ids + [template.id])[-100:]

    state.update({
        "focus_index": focus_index,
        "correct_streak": correct_streak,
        "used_template_ids": used_ids,
        "current_skill_id": fa.skill_id,
    })
    session.session_state = state
    session.save(update_fields=["session_state"])

    return Response({
        "template_id": template.id if template else None,
        "focus_area": fa.skill.description,
        "focus_index": focus_index,
        "focus_total": len(focus_areas),
        "correct_streak": correct_streak,
        "difficulty": difficulty,
    })


def _session_assessment_question(session, student, grade, state, result):
    from .cache import get_matrix_cache, filter_matrix_by_grade
    matrix = get_matrix_cache()
    leaf_skills = [s for s in filter_matrix_by_grade(matrix, grade) if s["children_count"] == 0]
    if not leaf_skills:
        return Response({"template_id": None, "error": "No skills available for this grade"})

    DIFFICULTIES = ["easy", "medium", "hard"]
    skill_index = state.get("skill_index", 0)
    difficulty = state.get("difficulty", "easy")
    used_ids = state.get("used_template_ids", [])

    # Update mastery for the skill just answered
    if result in ("correct", "wrong") and state.get("current_skill_id"):
        _update_skill_mastery(student, state["current_skill_id"], result == "correct")

    if result == "correct":
        diff_idx = DIFFICULTIES.index(difficulty) if difficulty in DIFFICULTIES else 0
        if diff_idx < len(DIFFICULTIES) - 1:
            difficulty = DIFFICULTIES[diff_idx + 1]
        else:
            skill_index += 1
            difficulty = "easy"
    elif result == "wrong":
        skill_index += 1
        difficulty = "easy"

    # Skip skills with no templates
    attempts = 0
    template = None
    while skill_index < len(leaf_skills) and attempts < len(leaf_skills):
        template = _pick_template(leaf_skills[skill_index]["id"], grade, difficulty, used_ids)
        if template:
            break
        skill_index += 1
        difficulty = "easy"
        attempts += 1

    if skill_index >= len(leaf_skills) or template is None:
        session.session_state = state
        session.save(update_fields=["session_state"])
        return Response({"template_id": None, "complete": True, "total_skills": len(leaf_skills)})

    current_skill_id = leaf_skills[skill_index]["id"]
    used_ids = (used_ids + [template.id])[-100:]
    state.update({
        "skill_index": skill_index,
        "difficulty": difficulty,
        "used_template_ids": used_ids,
        "current_skill_id": current_skill_id,
    })
    session.session_state = state
    session.save(update_fields=["session_state"])

    return Response({
        "template_id": template.id,
        "skill": leaf_skills[skill_index]["description"],
        "skill_index": skill_index,
        "total_skills": len(leaf_skills),
        "difficulty": difficulty,
    })


class TutoringSessionViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=["post"])
    def token(self, request):
        """
        Generate a Livekit room token for the requesting user.
        Room name format: t{tutor_id}-s{student_id}
        Creates a TutoringSession record on first join.
        """
        import re, os
        room_name = (request.data.get("room_name") or "").strip()
        if not room_name:
            return Response({"error": "room_name required"}, status=400)

        m = re.match(r"^t(\d+)-s(\d+)$", room_name)
        if not m:
            return Response({"error": "Invalid room name. Expected t{tutor_id}-s{student_id}"}, status=400)

        tutor_id, student_id = int(m.group(1)), int(m.group(2))
        user = request.user

        if user.id not in (tutor_id, student_id):
            return Response({"error": "Not authorised for this room"}, status=403)

        try:
            tutor  = User.objects.get(pk=tutor_id)
            student = User.objects.get(pk=student_id)
        except User.DoesNotExist:
            return Response({"error": "Invalid participant IDs"}, status=400)

        session, _ = TutoringSession.objects.get_or_create(
            room_name=room_name,
            defaults={"tutor": tutor, "student": student},
        )

        # Mark when the tutor initiates the call so the student can be notified.
        # Mark when the student joins so the incoming-call banner clears.
        if user.id == tutor_id:
            session.last_called_at = timezone.now()
            session.save(update_fields=["last_called_at"])
        elif user.id == student_id:
            session.student_joined_at = timezone.now()
            session.save(update_fields=["student_joined_at"])

        api_key    = os.environ.get("LIVEKIT_API_KEY", "")
        api_secret = os.environ.get("LIVEKIT_API_SECRET", "")
        livekit_url = os.environ.get("LIVEKIT_URL", "")

        if not api_key or not api_secret or not livekit_url:
            return Response({"error": "Livekit not configured on server"}, status=500)

        try:
            from livekit.api import AccessToken, VideoGrants
            token = (
                AccessToken(api_key, api_secret)
                .with_identity(str(user.id))
                .with_name(user.get_full_name() or user.username)
                .with_grants(VideoGrants(room_join=True, room=room_name))
                .to_jwt()
            )
        except Exception as e:
            return Response({"error": f"Token generation failed: {e}"}, status=500)

        return Response({
            "token": token,
            "livekit_url": livekit_url,
            "room_name": room_name,
            "active_template_id": session.active_template_id,
        })

    @action(detail=False, methods=["post"])
    def set_template(self, request):
        """Tutor sets the active question for the session."""
        from django.shortcuts import get_object_or_404
        room_name   = (request.data.get("room_name") or "").strip()
        template_id = request.data.get("template_id")
        learn_mode  = request.data.get("learn_mode", False)
        session_id  = request.data.get("session_id")

        session = get_object_or_404(TutoringSession, room_name=room_name)

        if request.user.id not in (session.tutor_id, session.student_id):
            return Response({"error": "Not authorised"}, status=403)

        if template_id:
            try:
                session.active_template = Template.objects.get(pk=template_id)
            except Template.DoesNotExist:
                return Response({"error": "Template not found"}, status=400)
        else:
            session.active_template = None

        # Persist learn mode context so the student can restore it on reconnect
        preview = request.data.get("preview")
        state = dict(session.session_state or {})
        state["learn_mode"] = bool(learn_mode)
        state["learn_session_id"] = session_id if learn_mode else None
        state["preview"] = preview if learn_mode else None
        session.session_state = state
        session.save(update_fields=["active_template", "session_state"])
        return Response({"ok": True, "active_template_id": session.active_template_id})

    @action(detail=False, methods=["get"])
    def state(self, request):
        """Return current session state (active template + learn mode) for reconnects."""
        room_name = (request.query_params.get("room_name") or "").strip()
        if not room_name:
            return Response({"error": "room_name required"}, status=400)

        try:
            session = TutoringSession.objects.get(room_name=room_name)
        except TutoringSession.DoesNotExist:
            return Response({"active_template_id": None})

        if request.user.id not in (session.tutor_id, session.student_id):
            return Response({"error": "Not authorised"}, status=403)

        state = session.session_state or {}
        return Response({
            "active_template_id": session.active_template_id,
            "learn_mode": bool(state.get("learn_mode", False)),
            "learn_session_id": state.get("learn_session_id"),
            "preview": state.get("preview"),
        })

    @action(detail=False, methods=["post"])
    def next_question(self, request):
        """Return the next template for the active session mode (focus_area or assessment)."""
        room_name = request.data.get("room_name")
        mode = request.data.get("mode")          # 'focus_area' | 'assessment'
        result = request.data.get("result")       # 'correct' | 'wrong' | None (first question)

        session = TutoringSession.objects.filter(room_name=room_name).first()
        if not session:
            return Response({"error": "Session not found"}, status=404)

        try:
            grade = session.student.student_profile.year_level
        except Exception:
            grade = None
        if not grade:
            return Response({"template_id": None, "error": "Student has no grade set"})

        # Reset state whenever mode changes
        if session.session_mode != mode:
            session.session_mode = mode
            session.session_state = {}
            session.save(update_fields=["session_mode", "session_state"])

        state = dict(session.session_state or {})

        if mode == "focus_area":
            return _session_focus_area_question(session, student=session.student, grade=grade, state=state, result=result)
        elif mode == "assessment":
            return _session_assessment_question(session, student=session.student, grade=grade, state=state, result=result)
        else:
            return Response({"error": "Invalid mode"}, status=400)

    @action(detail=False, methods=["post"])
    def end_session(self, request):
        """Called when a tutor leaves a session. Snapshots skill competency."""
        room_name = request.data.get("room_name")
        session = TutoringSession.objects.filter(room_name=room_name).first()
        if not session:
            return Response({"error": "Session not found"}, status=404)

        # Snapshot competence for focus area skills + any skill with level > 0
        from .competency import level_to_label as _ltl
        focus_skill_ids = set(
            StudentFocusArea.objects.filter(student=session.student).values_list('skill_id', flat=True)
        )
        comp_entries = StudentSkillCompetency.objects.filter(
            student=session.student
        ).filter(
            models.Q(skill_id__in=focus_skill_ids) | models.Q(level__gt=0)
        ).select_related('skill')

        for entry in comp_entries:
            SessionSkillSnapshot.objects.get_or_create(
                session=session,
                skill=entry.skill,
                defaults={
                    'student': session.student,
                    'mastery': entry.level,
                    'competence_label': _ltl(entry.level),
                }
            )

        return Response({"ok": True})

    @action(detail=False, methods=["post"])
    def learn_mode(self, request):
        """
        Start (or restart) a learning TestSession for the student in this room.
        Targets the highest-priority focus area where tutoring hasn't been done this week.
        Returns the first question payload so the tutor can show it in the QuestionPanel.
        """
        from .models import StudentFocusArea, TestSession
        from .competency import get_student_question_difficulty

        room_name = (request.data.get("room_name") or "").strip()
        session = TutoringSession.objects.filter(room_name=room_name).first()
        if not session:
            return Response({"error": "Session not found"}, status=404)

        monday = _this_weeks_monday()
        focus_area_id = request.data.get("focus_area_id")

        if focus_area_id:
            # Caller selected a specific focus area to start
            fa = (
                StudentFocusArea.objects
                .filter(id=focus_area_id, student=session.student)
                .select_related("skill")
                .first()
            )
            if not fa:
                return Response({"error": "Focus area not found"}, status=404)
        else:
            # Auto-select: highest-priority FA not yet done this week
            fa = (
                StudentFocusArea.objects
                .filter(student=session.student)
                .exclude(tutoring_done_week=monday)
                .select_related("skill")
                .order_by("order", "id")
                .first()
            )
            if not fa:
                return Response({"error": "No pending focus areas this week"}, status=200)

        student = session.student
        skill_code = fa.skill.code

        # Snapshot level before learning
        comp_now = StudentSkillCompetency.objects.filter(
            student=student, skill=fa.skill
        ).values_list('level', flat=True).first()
        fa.level_before_learning = comp_now if comp_now is not None else 0
        fa.level_after_learning = None
        fa.save(update_fields=['level_before_learning', 'level_after_learning'])

        # Abandon any existing active learning session for this student
        TestSession.objects.filter(student=student, status='active', mode='learning').update(
            status='abandoned'
        )

        difficulty = get_student_question_difficulty(student, skill_code)
        test_session = TestSession.objects.create(
            student=student,
            skill_codes=[skill_code],
            mode='learning',
            current_difficulty=difficulty,
            linked_tutoring_focus_area=fa,
        )

        question = _advance_to_question_learning_mode(test_session)
        if question is None:
            test_session.status = 'completed'
            test_session.save()
            return Response({"error": "No templates available for this focus area"}, status=200)

        return Response({
            "session_id": test_session.id,
            "skill_description": fa.skill.description,
            "focus_area_name": fa.skill.description,
            "question": question,
        })

    @action(detail=False, methods=["get"])
    def incoming_call(self, request):
        """Poll endpoint for students: returns active call if tutor called in last 5 minutes
        and the student has not yet joined since that call."""
        user = request.user
        cutoff = timezone.now() - timedelta(minutes=5)
        session = (
            TutoringSession.objects
            .filter(student=user, last_called_at__gte=cutoff)
            .select_related("tutor")
            .order_by("-last_called_at")
            .first()
        )
        if not session:
            return Response({"room_name": None})
        # Hide the banner if the student joined after the most recent call
        if session.student_joined_at and session.student_joined_at >= session.last_called_at:
            return Response({"room_name": None})
        return Response({
            "room_name": session.room_name,
            "tutor_name": session.tutor.get_full_name() or session.tutor.username,
        })


def _reset_year_caches():
    import backend.cache as _cache
    _cache.MATRIX_CACHE = None


class YearViewSet(viewsets.ModelViewSet):
    """CRUD for year levels. Adding/removing years automatically rebuilds the skills matrix."""
    permission_classes = [AllowAny]
    serializer_class = YearSerializer
    queryset = Year.objects.filter(active=True).order_by("order")

    def perform_create(self, serializer):
        serializer.save()
        _reset_year_caches()

    def perform_update(self, serializer):
        serializer.save()
        _reset_year_caches()

    def perform_destroy(self, instance):
        instance.delete()
        _reset_year_caches()

    @action(detail=False, methods=["post"])
    def import_years(self, request):
        """Import a years YAML file (same format as backend/Files/years.yaml)."""
        import yaml as _yaml
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file uploaded"}, status=400)
        raw = uploaded.read().decode("utf-8")
        try:
            data = _yaml.safe_load(raw)
        except Exception as e:
            return Response({"error": f"Invalid file: {e}"}, status=400)
        if not isinstance(data, list):
            return Response({"error": "Expected a list of year entries"}, status=400)
        count = 0
        try:
            for entry in data:
                code = str(entry.get("code", "")).strip()
                if not code:
                    continue
                Year.objects.update_or_create(
                    code=code,
                    defaults={
                        "label": entry.get("label", code),
                        "order": int(entry.get("order", 0)),
                        "active": bool(entry.get("active", True)),
                        "stage": str(entry.get("stage", "k10")),
                    },
                )
                count += 1
        except Exception as e:
            return Response({"error": f"Import failed: {e}"}, status=400)
        _reset_year_caches()
        return Response({"status": "Years imported successfully", "count": count})


class KnowledgeViewSet(viewsets.ModelViewSet):
    serializer_class = KnowledgeSerializer

    def get_queryset(self):
        qs = Knowledge.objects.prefetch_related("skills").order_by("title")
        skill_id = self.request.query_params.get("skill_id")
        if skill_id:
            qs = qs.filter(skills__id=skill_id)
        return qs

    @action(detail=False, methods=["post"])
    def import_bulk(self, request):
        """Import a knowledge YAML file (same format as backend/Files/knowledge.yaml)."""
        import yaml as _yaml
        uploaded = request.FILES.get("file")
        if not uploaded:
            return Response({"error": "No file uploaded"}, status=400)
        raw = uploaded.read().decode("utf-8")
        try:
            data = _yaml.safe_load(raw)
        except Exception as e:
            return Response({"error": f"Invalid file: {e}"}, status=400)
        if not isinstance(data, list):
            return Response({"error": "Expected a list of knowledge entries"}, status=400)
        skill_map = {s.code: s for s in Skill.objects.all()}
        count = 0
        try:
            for entry in data:
                title = str(entry.get("title", "")).strip()
                if not title:
                    continue
                obj, _ = Knowledge.objects.update_or_create(
                    title=title,
                    defaults={
                        "text": entry.get("text", "") or "",
                        "diagram": entry.get("diagram", "") or "",
                        "text_2": entry.get("text_2", "") or "",
                    },
                )
                codes = entry.get("skill_codes") or []
                skills = [skill_map[c] for c in codes if c in skill_map]
                obj.skills.set(skills)
                count += 1
        except Exception as e:
            return Response({"error": f"Import failed: {e}"}, status=400)
        return Response({"status": "Knowledge imported successfully", "count": count})

    @action(detail=False, methods=["post"])
    def preview(self, request):
        diagram_code = request.data.get("diagram", "")
        svg = ""
        error = None
        if diagram_code.strip() and diagram_code.strip().lower() != "none":
            try:
                from .diagram.engine import render_diagram_from_code
                svg = render_diagram_from_code(diagram_code)
            except Exception as e:
                error = str(e)
        return Response({"diagram_svg": svg, "error": error})

    @action(detail=False, methods=["post"])
    def generate_from_image(self, request):
        image_b64 = request.data.get("image")
        mime_type = request.data.get("mime_type", "image/png")
        additional_prompt = request.data.get("additional_prompt", "")

        if not image_b64:
            return Response({"error": "image required"}, status=400)

        try:
            from .ai import generate_knowledge_from_image
            item = generate_knowledge_from_image(image_b64, mime_type, additional_prompt)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({"error": f"AI generation failed: {e}"}, status=500)

        return Response({
            "title": item.get("title", ""),
            "text": item.get("text", ""),
            "diagram": item.get("diagram", ""),
            "text_2": item.get("text_2", ""),
        })


@api_view(["GET"])
def editor_docs(request):
    print("Editor docs")
    import os
    doc_path = os.path.join(os.path.dirname(__file__), "Editor Documentation.txt")
    with open(doc_path, encoding="utf-8") as f:
        content = f.read()
    return Response({"content": content})


from django.shortcuts import render as django_render


def tutor_payments_page(request):
    return django_render(request, "tutor_payments.html")


from django.http import HttpResponse

# ─────────────────────────────────────────────────────────────────────────────
# TEST SYSTEM
# ─────────────────────────────────────────────────────────────────────────────

def _skill_matches_year(skill, year_level: str) -> bool:
    """Check if a skill's grades CharField contains the given year level.
    Handles both bare numbers ('7') and 'Year 7' style values."""
    if not skill.grades or not year_level:
        return False
    # Normalise to bare number: 'Year 7' → '7'
    normalised = year_level.strip().lower().replace('year', '').strip()
    grades = [g.strip() for g in skill.grades.split(',')]
    return normalised in grades


def _get_next_template(session, skill_code: str, difficulty: str, exclude_skill_detail_ids=None):
    """Find a validated template for the given Skill and difficulty, avoiding repeats.
    skill_code identifies a Skill-level node (parent of skill_detail nodes)."""
    from .models import Template
    qs = Template.objects.filter(
        skill_detail__parent__code=skill_code,
        difficulty__iexact=difficulty,
        validated=True,
    ).exclude(id__in=session.used_template_ids)
    if exclude_skill_detail_ids:
        qs = qs.exclude(skill_detail_id__in=exclude_skill_detail_ids)
    return qs.order_by('?').first()


def _get_or_create_translation(template, language: str):
    """Return a translated sister Template for the given language.
    Delegates to the shared get_translated_template helper in template_utilities.
    """
    from .template_utilities import get_translated_template
    from .models import User as _User

    # Build a minimal stand-in object that has a .value attribute
    class _FakePref:
        value = language

    class _FakeStudent:
        pass

    fake_student = _FakeStudent()
    # Monkey-patch UserPreference lookup by calling get_translated_template directly
    # with the language already known — bypass the student lookup entirely.
    if language == 'en' or not language:
        return template

    from .models import Template as _Template
    from .ai import translate_template_content

    existing = _Template.objects.filter(
        parent_template=template, language=language, validated=True
    ).first()
    if existing:
        return existing

    try:
        translated_content = translate_template_content(template.content, language)
    except Exception:
        return template

    # Restore any Knowledge/Skill function arguments that the AI may have translated.
    # These are database references and must match exactly what is stored in English.
    import re as _re
    def _restore_func_args(src: str, translated: str) -> str:
        pattern = r"""(Knowledge|Skill)\((['"])(.*?)\2\)"""
        source_calls = _re.findall(pattern, src)
        for func_name, quote, original_arg in source_calls:
            translated = _re.sub(
                r"""(?<!\w)""" + func_name + r"""\((['"])(.*?)\1\)""",
                lambda m, fn=func_name, q=quote, arg=original_arg: f"{fn}({q}{arg}{q})",
                translated,
                count=1,
            )
        return translated

    translated_content = _restore_func_args(template.content, translated_content)

    return _Template.objects.create(
        name=template.name,
        description=template.description,
        content=translated_content,
        topic=template.topic,
        subtopic=template.subtopic,
        grade=template.grade,
        difficulty=template.difficulty,
        tags=template.tags,
        group=template.group,
        curriculum=template.curriculum,
        skill_detail=template.skill_detail,
        validated=True,
        status=template.status,
        version=template.version,
        language=language,
        parent_template=template,
    )


def _build_question_payload(session, template, skill_code: str, skill_description: str):
    """Generate a preview for the template and return the question payload dict."""
    from .template_utilities import generate_values_and_question
    preview_result = generate_values_and_question(template.id)
    if not preview_result.get('ok'):
        return None
    preview = preview_result['preview']
    preview['template_id'] = template.id
    return {
        'template_id': template.id,
        'preview': preview,
        'skill_code': skill_code,
        'skill_description': skill_description,
        'difficulty': session.current_difficulty,
        'current_skill_index': session.current_skill_index,
        'total_skills': len(session.skill_codes),
        'correct_streak': session.correct_streak,
        'incorrect_count': session.incorrect_count,
    }


DIFFICULTIES = ['easy', 'medium', 'hard']


def _this_weeks_monday():
    """Return the date of the most recent Monday (start of this ISO week)."""
    from django.utils import timezone as _tz
    today = _tz.localdate()
    return today - timedelta(days=today.weekday())


def _advance_to_question_test_mode(session):
    """
    Mode 'test': one question per skill per difficulty level.
    Correct → harder difficulty (handled in answer view, this just fetches the question).
    Incorrect → next skill (handled in answer view).
    This function finds the next un-asked question for the current skill/difficulty.
    """
    from .models import Template, Skill, TestSkillResult

    while session.current_skill_index < len(session.skill_codes):
        skill_code = session.skill_codes[session.current_skill_index]
        skill = Skill.objects.filter(code=skill_code).first()
        skill_description = skill.description if skill else skill_code

        # Try current difficulty first, then scan all difficulties for a fallback
        for d in ([session.current_difficulty] +
                  [x for x in DIFFICULTIES if x != session.current_difficulty]):
            template = _get_next_template(session, skill_code, d)
            if template:
                if d != session.current_difficulty:
                    session.current_difficulty = d
                    session.save()
                payload = _build_question_payload(session, template, skill_code, skill_description)
                if payload:
                    payload['mode'] = 'test'
                    return payload

        # No templates at any difficulty — skip skill
        TestSkillResult.objects.get_or_create(
            session=session, skill_code=skill_code,
            defaults={
                'skill_description': skill_description,
                'highest_difficulty_reached': 'none',
                'questions_asked': 0,
                'questions_correct': 0,
            },
        )
        session.current_skill_index += 1
        session.current_difficulty = 'easy'
        session.save()

    return None


def _advance_to_question_learning_mode(session):
    """
    Mode 'learning': two full loops through all templates for the current skill/difficulty.
    Loop 1 → if all correct: promote difficulty; if <50% correct: demote difficulty.
    Loop 2 → uses (possibly adjusted) difficulty.
    mode_state keys: loop, loop_remaining (template IDs), loop1_correct, loop1_total, skill_code.
    """
    import random as _random
    from .models import Template, Skill, TestSkillResult

    while session.current_skill_index < len(session.skill_codes):
        skill_code = session.skill_codes[session.current_skill_index]
        skill = Skill.objects.filter(code=skill_code).first()
        skill_description = skill.description if skill else skill_code

        state = session.mode_state or {}

        # Initialise state for this skill (new skill or fresh start)
        if state.get('skill_code') != skill_code:
            template_ids = list(Template.objects.filter(
                skill_detail__parent__code=skill_code,
                difficulty__iexact=session.current_difficulty,
                validated=True,
            ).values_list('id', flat=True))

            if not template_ids:
                # No templates — skip skill
                TestSkillResult.objects.get_or_create(
                    session=session, skill_code=skill_code,
                    defaults={
                        'skill_description': skill_description,
                        'highest_difficulty_reached': 'none',
                        'questions_asked': 0, 'questions_correct': 0,
                    },
                )
                session.current_skill_index += 1
                session.mode_state = {}
                session.save()
                continue

            _random.shuffle(template_ids)
            state = {
                'skill_code': skill_code,
                'loop': 1,
                'loop_remaining': template_ids,
                'loop1_correct': 0,
                'loop1_total': 0,
            }
            session.mode_state = state
            session.save()

        loop_remaining = state.get('loop_remaining', [])
        if not loop_remaining:
            # Exhausted with no answer call — shouldn't happen, but guard
            session.current_skill_index += 1
            session.mode_state = {}
            session.save()
            continue

        template_id = loop_remaining[0]
        template = Template.objects.filter(id=template_id, validated=True).first()
        if not template:
            # Template disappeared — remove and retry
            state['loop_remaining'] = loop_remaining[1:]
            session.mode_state = state
            session.save()
            continue

        # Translate template for the student's preferred language
        try:
            from .models import UserPreference
            lang_pref = UserPreference.objects.filter(user=session.student, key='language').first()
            student_language = lang_pref.value if lang_pref else 'en'
            if student_language and student_language != 'en':
                template = _get_or_create_translation(template, student_language)
        except Exception:
            pass  # Never block the session due to translation failure

        payload = _build_question_payload(session, template, skill_code, skill_description)
        if not payload:
            state['loop_remaining'] = loop_remaining[1:]
            session.mode_state = state
            session.save()
            continue

        payload['mode'] = 'learning'
        payload['loop'] = state['loop']
        payload['loop_remaining'] = len(loop_remaining)
        payload['loop1_correct'] = state.get('loop1_correct', 0)
        payload['loop1_total'] = state.get('loop1_total', 0)
        return payload

    return None


def _handle_learning_answer(session, skill_code, skill_description, correct):
    """Update learning-mode state after an answer. Returns True if skill is now complete."""
    import random as _random
    from .models import Template, TestSkillResult

    state = session.mode_state or {}
    loop = state.get('loop', 1)
    loop_remaining = list(state.get('loop_remaining', []))

    # Consume the current template (index 0)
    if loop_remaining:
        loop_remaining = loop_remaining[1:]

    if loop == 1:
        state['loop1_total'] = state.get('loop1_total', 0) + 1
        if correct:
            state['loop1_correct'] = state.get('loop1_correct', 0) + 1

    result_obj, _ = TestSkillResult.objects.get_or_create(
        session=session, skill_code=skill_code,
        defaults={'skill_description': skill_description},
    )
    result_obj.questions_asked += 1
    if correct:
        result_obj.questions_correct += 1

    if not loop_remaining:
        if loop == 1:
            from django.utils import timezone
            from datetime import timedelta
            from .models import StudentTemplateProgress
            from .competency import recompute_skill_competency, get_student_question_difficulty

            today = timezone.localdate()

            # Gate: only run loop 2 if some templates are ready to earn robustness
            # (ever correct, not yet robust, and first correct answer was 6+ days ago)
            eligible_for_loop2 = StudentTemplateProgress.objects.filter(
                student=session.student,
                skill_code=skill_code,
                difficulty__iexact=session.current_difficulty,
                ever_correct=True,
                has_robust=False,
                streak_start_date__lte=today - timedelta(days=6),
            ).exists()

            if not eligible_for_loop2:
                # Nothing to gain from loop 2 today — end here
                result_obj.highest_difficulty_reached = session.current_difficulty
                result_obj.save()
                session.current_skill_index += 1
                session.current_difficulty = 'easy'
                session.mode_state = {}
                session.save()
                return True

            # Recompute competency from the updated template progress, then use
            # the single difficulty calculator to determine what loop 2 should serve
            recompute_skill_competency(session.student, skill_code, '')
            original_diff = session.current_difficulty
            new_diff = get_student_question_difficulty(session.student, skill_code)

            session.current_difficulty = new_diff
            result_obj.highest_difficulty_reached = new_diff

            template_ids = list(Template.objects.filter(
                skill_detail__parent__code=skill_code,
                difficulty__iexact=new_diff,
                validated=True,
            ).values_list('id', flat=True))

            # Fallback: if no templates at adjusted difficulty, use original difficulty
            if not template_ids and new_diff != original_diff:
                template_ids = list(Template.objects.filter(
                    skill_detail__parent__code=skill_code,
                    difficulty__iexact=original_diff,
                    validated=True,
                ).values_list('id', flat=True))
                session.current_difficulty = original_diff
                result_obj.highest_difficulty_reached = original_diff

            _random.shuffle(template_ids)

            state['loop'] = 2
            state['loop_remaining'] = template_ids
            session.mode_state = state
            result_obj.save()
            session.save()
            return False  # skill not yet complete
        else:
            # Loop 2 done — skill complete
            result_obj.highest_difficulty_reached = session.current_difficulty
            result_obj.save()
            session.current_skill_index += 1
            session.current_difficulty = 'easy'
            session.mode_state = {}
            session.save()
            return True  # skill complete
    else:
        state['loop_remaining'] = loop_remaining
        session.mode_state = state
        result_obj.save()
        session.save()
        return False


def _get_starting_difficulty(student, skill_code, exclude_session_id=None):
    """Return the starting difficulty for a skill based on the student's competency level."""
    from .competency import get_student_question_difficulty
    return get_student_question_difficulty(student, skill_code)


def _learning_complete_payload(session):
    """
    Build the extra fields included in the 'complete' response for a learning session.
    Must be called AFTER _complete_learning_focus_area so level_after_learning is saved.
    """
    stars_before = stars_after = skill_description = None

    if session.skill_codes:
        from .models import Skill
        skill = Skill.objects.filter(code=session.skill_codes[0]).first()
        skill_description = skill.description if skill else None

    if session.linked_focus_area_id:
        fa = StudentFocusArea.objects.filter(id=session.linked_focus_area_id).first()
        if fa:
            stars_before = fa.level_before_learning
            stars_after = fa.level_after_learning

    stars_gained = (
        max(0, stars_after - stars_before)
        if stars_before is not None and stars_after is not None
        else None
    )

    return {
        'complete': True,
        'session_id': session.id,
        'mode': 'learning',
        'stars_before': stars_before,
        'stars_after': stars_after,
        'stars_gained': stars_gained,
        'skill_description': skill_description,
    }


def _complete_learning_focus_area(session):
    """
    Mark learning/tutoring done for the week and snapshot level-after.
    Called after _recompute_session_competency so the new level is already saved.
    """
    monday = _this_weeks_monday()

    if session.linked_focus_area_id:
        fa = session.linked_focus_area
        fa.learning_done_week = monday
        comp = StudentSkillCompetency.objects.filter(
            student=session.student, skill=fa.skill
        ).values_list('level', flat=True).first()
        fa.level_after_learning = comp if comp is not None else 0
        fa.save(update_fields=['learning_done_week', 'level_after_learning'])

    if session.linked_tutoring_focus_area_id:
        tfa = session.linked_tutoring_focus_area
        tfa.tutoring_done_week = monday
        tfa.save(update_fields=['tutoring_done_week'])


def _recompute_session_competency(session):
    """
    Called at TestSession completion. For each skill in the session, compute
    per-skill correct/total from TestQuestionResult and call recompute_skill_competency
    (which applies regression if < 50 % correct).
    """
    from .competency import recompute_skill_competency
    from .models import TestQuestionResult
    from django.db.models import Count as _Count
    from django.db.models import Q as _Q

    student = session.student
    profile = student.get_student_profile()
    grade = profile.year_level if profile else None
    if not grade:
        return

    skill_stats = (
        TestQuestionResult.objects
        .filter(session=session)
        .values('skill_code')
        .annotate(
            total=_Count('id'),
            correct_count=_Count('id', filter=_Q(correct=True)),
        )
    )
    for stat in skill_stats:
        recompute_skill_competency(
            student,
            stat['skill_code'],
            grade,
            session_correct=stat['correct_count'],
            session_total=stat['total'],
        )


def _advance_to_question(session):
    """
    Find the next question for the current session state.
    Skips difficulties/skills if no templates exist.
    Returns question payload dict, or None if test is complete.
    Mutates and saves session if skipping.
    """
    from .models import Skill, TestSkillResult, Template

    # ── Fixed-difficulty tests: 1 question per skill detail, no streak logic ──
    if session.test_type in ('easy', 'medium', 'hard'):
        fixed = session.test_type
        while session.current_skill_index < len(session.skill_codes):
            skill_code = session.skill_codes[session.current_skill_index]
            skill = Skill.objects.filter(code=skill_code).first()
            skill_description = skill.description if skill else skill_code

            # Skill Detail IDs already asked for this skill in this session
            used_skill_detail_ids = list(
                Template.objects.filter(
                    id__in=session.used_template_ids,
                    skill_detail__parent__code=skill_code,
                ).values_list('skill_detail_id', flat=True).distinct()
            )

            template = _get_next_template(session, skill_code, fixed, exclude_skill_detail_ids=used_skill_detail_ids)
            if template:
                payload = _build_question_payload(session, template, skill_code, skill_description)
                if payload:
                    return payload

            # No more un-asked subjects (or no templates at this difficulty) — finish this skill
            result, created = TestSkillResult.objects.get_or_create(
                session=session,
                skill_code=skill_code,
                defaults={
                    'skill_description': skill_description,
                    'highest_difficulty_reached': 'none',
                    'questions_asked': 0,
                    'questions_correct': 0,
                },
            )
            if not created and used_subjects:
                # At least one question was asked → record that they were assessed at this level
                result.highest_difficulty_reached = fixed
                result.save()

            session.current_skill_index += 1
            session.correct_streak = 0
            session.incorrect_count = 0
            session.save()
        return None  # all skills done

    # ── Dynamic test: per-skill difficulty based on past correct answers ─────
    if session.test_type == 'dynamic':
        while session.current_skill_index < len(session.skill_codes):
            skill_code = session.skill_codes[session.current_skill_index]
            skill = Skill.objects.filter(code=skill_code).first()
            skill_description = skill.description if skill else skill_code

            target_difficulty = _get_starting_difficulty(
                session.student, skill_code, exclude_session_id=session.id
            )
            if session.current_difficulty != target_difficulty:
                session.current_difficulty = target_difficulty
                session.save()

            used_skill_detail_ids = list(
                Template.objects.filter(
                    id__in=session.used_template_ids,
                    skill_detail__parent__code=skill_code,
                ).values_list('skill_detail_id', flat=True).distinct()
            )

            template = _get_next_template(session, skill_code, target_difficulty, exclude_skill_detail_ids=used_skill_detail_ids)
            if template:
                payload = _build_question_payload(session, template, skill_code, skill_description)
                if payload:
                    return payload

            # No templates at target difficulty — finish this skill
            result, created = TestSkillResult.objects.get_or_create(
                session=session,
                skill_code=skill_code,
                defaults={
                    'skill_description': skill_description,
                    'highest_difficulty_reached': 'none',
                    'questions_asked': 0,
                    'questions_correct': 0,
                },
            )
            if not created and result.questions_correct > 0:
                result.highest_difficulty_reached = target_difficulty
                result.save()

            session.current_skill_index += 1
            session.correct_streak = 0
            session.incorrect_count = 0
            session.save()
        return None

    # ── Adaptive test (original logic) ───────────────────────────────────────
    while session.current_skill_index < len(session.skill_codes):
        skill_code = session.skill_codes[session.current_skill_index]
        skill = Skill.objects.filter(code=skill_code).first()
        skill_description = skill.description if skill else skill_code

        # Try current difficulty and up (skipping those with no templates)
        diff_index = DIFFICULTIES.index(session.current_difficulty)
        found = False
        for d in DIFFICULTIES[diff_index:]:
            template = _get_next_template(session, skill_code, d)
            if template:
                # Jump to this difficulty if we had to skip
                if d != session.current_difficulty:
                    session.current_difficulty = d
                    session.correct_streak = 0
                    session.incorrect_count = 0
                    session.save()
                payload = _build_question_payload(session, template, skill_code, skill_description)
                if payload:
                    return payload
            # No template at this difficulty — try next

        # No templates found at any difficulty for this skill — skip it
        TestSkillResult.objects.get_or_create(
            session=session,
            skill_code=skill_code,
            defaults={
                'skill_description': skill_description,
                'highest_difficulty_reached': 'none',
                'questions_asked': 0,
                'questions_correct': 0,
            },
        )
        session.current_skill_index += 1
        session.current_difficulty = 'easy'
        session.correct_streak = 0
        session.incorrect_count = 0
        session.save()

    return None  # All skills exhausted


class TestViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['post'])
    def start(self, request):
        from .models import Skill, StudentProfile, TestSession, StudentFocusArea

        student_id = request.data.get('student_id')
        if not student_id:
            return Response({'error': 'student_id required'}, status=400)

        mode = request.data.get('mode', '')  # 'test' | 'learning' | ''
        if mode not in ('test', 'learning', ''):
            return Response({'error': 'Invalid mode'}, status=400)

        focus_area_id = request.data.get('focus_area_id')
        skill_codes_override = request.data.get('skill_codes')  # optional list

        test_type = request.data.get('test_type', 'dynamic')
        if test_type not in ('easy', 'medium', 'hard', 'dynamic', ''):
            return Response({'error': 'Invalid test_type'}, status=400)

        try:
            student = User.objects.get(id=student_id)
        except User.DoesNotExist:
            return Response({'error': 'Student not found'}, status=404)

        # ── Resolve skill codes ───────────────────────────────────────────────
        if skill_codes_override:
            skill_codes = list(skill_codes_override) if isinstance(skill_codes_override, list) else [skill_codes_override]
        else:
            profile = StudentProfile.objects.filter(user=student).first()
            year_level = (profile.year_level or '').strip() if profile else ''
            from django.db.models import Count as _Count, Q as _Q
            all_leaf = (
                Skill.objects
                .filter(is_detail=False)
                .annotate(non_detail_children=_Count('children', filter=_Q(children__is_detail=False)))
                .filter(non_detail_children=0)
                .order_by('code')
            )
            if year_level:
                skill_codes = [s.code for s in all_leaf if _skill_matches_year(s, year_level)]
            else:
                skill_codes = list(all_leaf.values_list('code', flat=True))

        if not skill_codes:
            return Response({'error': 'No skills found'}, status=400)

        # ── Resolve linked focus area ─────────────────────────────────────────
        linked_fa = None
        if focus_area_id:
            linked_fa = StudentFocusArea.objects.filter(id=focus_area_id, student=student).first()

        # Snapshot the current competency level before a learning session starts
        if mode == 'learning' and linked_fa:
            comp_now = StudentSkillCompetency.objects.filter(
                student=student, skill=linked_fa.skill
            ).values_list('level', flat=True).first()
            linked_fa.level_before_learning = comp_now if comp_now is not None else 0
            linked_fa.level_after_learning = None  # clear previous week's result
            linked_fa.save(update_fields=['level_before_learning', 'level_after_learning'])

        # ── For new modes, always create a fresh session ──────────────────────
        if mode in ('test', 'learning'):
            # Abandon any existing active session of the same mode/type to avoid confusion
            TestSession.objects.filter(student=student, status='active', mode=mode).update(
                status='abandoned'
            )
            session = TestSession.objects.create(
                student=student,
                skill_codes=skill_codes,
                test_type=test_type if mode == '' else '',
                current_difficulty='easy',
                mode=mode,
                linked_focus_area=linked_fa,
            )
            if mode == 'test':
                question = _advance_to_question_test_mode(session)
            else:
                question = _advance_to_question_learning_mode(session)
            if question is None:
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                return Response({'complete': True, 'session_id': session.id, 'mode': mode})
            return Response({
                'session_id': session.id,
                'question': question,
                'total_skills': len(skill_codes),
                'mode': mode,
            })

        # ── Legacy modes: resume or create ───────────────────────────────────
        existing_session = TestSession.objects.filter(
            student=student, status='active', test_type=test_type, mode='',
        ).order_by('-started_at').first()

        if existing_session:
            session = existing_session
            question = _advance_to_question(session)
            if question is None:
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                return Response({'complete': True, 'session_id': session.id})

            skill_progress = [
                {
                    'code': r.skill_code,
                    'description': r.skill_description,
                    'result': r.highest_difficulty_reached,
                }
                for r in session.skill_results.all()
            ]
            return Response({
                'session_id': session.id,
                'question': question,
                'total_skills': len(session.skill_codes),
                'skill_progress': skill_progress,
                'test_type': session.test_type,
                'resumed': True,
            })

        session = TestSession.objects.create(
            student=student,
            skill_codes=skill_codes,
            test_type=test_type,
            current_difficulty=test_type if test_type in ('easy', 'medium', 'hard') else 'easy',
        )

        question = _advance_to_question(session)
        if question is None:
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            return Response({'complete': True, 'session_id': session.id})

        return Response({
            'session_id': session.id,
            'question': question,
            'total_skills': len(skill_codes),
            'test_type': session.test_type,
        })

    @action(detail=True, methods=['post'])
    def answer(self, request, pk=None):
        from .models import TestSession, TestSkillResult

        try:
            session = TestSession.objects.get(id=pk)
        except TestSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        if session.status != 'active':
            return Response({'error': 'Session is not active'}, status=400)

        template_id = request.data.get('template_id')
        correct = bool(request.data.get('correct', False))
        time_taken_ms = request.data.get('time_taken_ms')

        # Track used template (skip for learning mode — we want repeats between loops)
        if template_id and session.mode != 'learning' and template_id not in session.used_template_ids:
            session.used_template_ids = session.used_template_ids + [template_id]

        skill_code = session.skill_codes[session.current_skill_index]
        from .models import Skill, TestQuestionResult
        skill = Skill.objects.filter(code=skill_code).first()
        skill_description = skill.description if skill else skill_code

        # ── Per-question result record + competency update ───────────────────
        if template_id:
            TestQuestionResult.objects.create(
                session=session,
                template_id=template_id,
                skill_code=skill_code,
                correct=correct,
                time_taken_ms=int(time_taken_ms) if time_taken_ms is not None else None,
            )
            # Update per-template progress for the competency system
            from .models import Template as _Tmpl
            from .competency import update_template_progress as _utp
            _tmpl = _Tmpl.objects.filter(id=template_id).values('difficulty').first()
            if _tmpl:
                _utp(
                    student=session.student,
                    template_id=int(template_id),
                    skill_code=skill_code,
                    difficulty=_tmpl['difficulty'] or 'easy',
                    correct=correct,
                )

        # ── Route to mode-specific state machine ──────────────────────────────
        if session.mode == 'learning':
            skill_complete = _handle_learning_answer(session, skill_code, skill_description, correct)
            # session already saved by _handle_learning_answer
            if session.current_skill_index >= len(session.skill_codes):
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                _recompute_session_competency(session)
                _complete_learning_focus_area(session)
                return Response(_learning_complete_payload(session))
            question = _advance_to_question_learning_mode(session)
            if question is None:
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                _recompute_session_competency(session)
                _complete_learning_focus_area(session)
                return Response(_learning_complete_payload(session))
            return Response({'question': question, 'mode': 'learning'})

        if session.mode == 'test':
            from .models import TestSkillResult
            result_obj, _ = TestSkillResult.objects.get_or_create(
                session=session, skill_code=skill_code,
                defaults={'skill_description': skill_description},
            )
            result_obj.questions_asked += 1
            if correct:
                result_obj.questions_correct += 1
                # Promote difficulty or advance skill if already at hard
                idx = DIFFICULTIES.index(session.current_difficulty)
                if idx < len(DIFFICULTIES) - 1:
                    session.current_difficulty = DIFFICULTIES[idx + 1]
                    result_obj.highest_difficulty_reached = session.current_difficulty
                else:
                    result_obj.highest_difficulty_reached = 'hard'
                    session.current_skill_index += 1
                    session.current_difficulty = 'easy'
            else:
                # Wrong — move to next skill
                result_obj.highest_difficulty_reached = session.current_difficulty
                session.current_skill_index += 1
                session.current_difficulty = 'easy'
            result_obj.save()
            session.save()

            if session.current_skill_index >= len(session.skill_codes):
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                _recompute_session_competency(session)
                skill_progress = [
                    {'code': r.skill_code, 'description': r.skill_description, 'result': r.highest_difficulty_reached}
                    for r in session.skill_results.all()
                ]
                return Response({'complete': True, 'session_id': session.id, 'skill_progress': skill_progress, 'mode': 'test'})

            question = _advance_to_question_test_mode(session)
            if question is None:
                session.status = 'completed'
                session.completed_at = timezone.now()
                session.save()
                _recompute_session_competency(session)
                skill_progress = [
                    {'code': r.skill_code, 'description': r.skill_description, 'result': r.highest_difficulty_reached}
                    for r in session.skill_results.all()
                ]
                return Response({'complete': True, 'session_id': session.id, 'skill_progress': skill_progress, 'mode': 'test'})

            skill_progress = [
                {'code': r.skill_code, 'description': r.skill_description, 'result': r.highest_difficulty_reached}
                for r in session.skill_results.all()
            ]
            return Response({'question': question, 'skill_progress': skill_progress, 'mode': 'test'})

        # Legacy path — skill/skill_description already resolved above

        result_obj, _ = TestSkillResult.objects.get_or_create(
            session=session,
            skill_code=skill_code,
            defaults={'skill_description': skill_description},
        )
        result_obj.questions_asked += 1
        if correct:
            result_obj.questions_correct += 1

        if session.test_type in ('easy', 'medium', 'hard', 'dynamic'):
            # Fixed/dynamic test: just record the answer.
            # Skill advancement is handled by _advance_to_question.
            result_obj.save()
            session.save()
        else:
            # Adaptive test: update streak/difficulty state
            if correct:
                session.correct_streak += 1
            else:
                session.correct_streak = 0
                session.incorrect_count += 1

            advance_skill = False
            advance_difficulty = False
            mastered = False

            if session.correct_streak >= 3:
                if session.current_difficulty == 'hard':
                    mastered = True
                    advance_skill = True
                else:
                    advance_difficulty = True
            elif session.incorrect_count >= 2:
                advance_skill = True

            if advance_skill or advance_difficulty:
                if mastered:
                    result_obj.highest_difficulty_reached = 'mastered'
                else:
                    result_obj.highest_difficulty_reached = session.current_difficulty
            result_obj.save()

            if advance_skill:
                session.current_skill_index += 1
                session.current_difficulty = 'easy'
                session.correct_streak = 0
                session.incorrect_count = 0
            elif advance_difficulty:
                idx = DIFFICULTIES.index(session.current_difficulty)
                session.current_difficulty = DIFFICULTIES[idx + 1]
                session.correct_streak = 0
                session.incorrect_count = 0

            session.save()

        # Check completion
        if session.current_skill_index >= len(session.skill_codes):
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            return Response({'complete': True, 'session_id': session.id})

        # Get next question
        question = _advance_to_question(session)
        if question is None:
            session.status = 'completed'
            session.completed_at = timezone.now()
            session.save()
            return Response({'complete': True, 'session_id': session.id})

        # Build skill progress summary
        completed_results = list(session.skill_results.all())
        skill_progress = [
            {
                'code': r.skill_code,
                'description': r.skill_description,
                'result': r.highest_difficulty_reached,
            }
            for r in completed_results
        ]

        return Response({
            'question': question,
            'skill_progress': skill_progress,
        })

    @action(detail=True, methods=['get'])
    def report(self, request, pk=None):
        from .models import TestSession
        from .test_report import generate_test_report

        try:
            session = TestSession.objects.get(id=pk)
        except TestSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)

        try:
            pdf_bytes = generate_test_report(session)
        except Exception as e:
            import traceback
            traceback.print_exc()
            return Response({'error': str(e)}, status=500)
        student_name = (session.student.get_full_name() or session.student.username).replace(' ', '_')
        date_str = session.started_at.strftime('%Y-%m-%d')
        filename = f"progress_report_{student_name}_{date_str}.pdf"
        response = HttpResponse(pdf_bytes, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="{filename}"'
        return response

    @action(detail=True, methods=['post'])
    def abandon(self, request, pk=None):
        from .models import TestSession
        try:
            session = TestSession.objects.get(id=pk)
        except TestSession.DoesNotExist:
            return Response({'error': 'Session not found'}, status=404)
        session.status = 'abandoned'
        session.completed_at = timezone.now()
        session.save()
        return Response({'ok': True})

    @action(detail=False, methods=['get'])
    def past(self, request):
        from .models import TestSession, TestSkillResult
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'error': 'student_id required'}, status=400)
        sessions = TestSession.objects.filter(
            student_id=student_id,
            status__in=['completed', 'abandoned'],
        ).prefetch_related('skill_results').order_by('-started_at')
        data = []
        for s in sessions:
            skill_results = [
                {
                    'skill_description': r.skill_description,
                    'highest_difficulty_reached': r.highest_difficulty_reached,
                    'questions_asked': r.questions_asked,
                    'questions_correct': r.questions_correct,
                }
                for r in s.skill_results.all()
            ]
            data.append({
                'id': s.id,
                'started_at': s.started_at,
                'completed_at': s.completed_at,
                'status': s.status,
                'test_type': s.test_type,
                'skill_results': skill_results,
            })
        return Response(data)


# ─────────────────────────────────────────────────────────────────────────────
# TEACHER
# ─────────────────────────────────────────────────────────────────────────────

def _send_student_welcome_email(student, plaintext_password, teacher_class, teacher):
    """Send a welcome email to a newly-created student with their login credentials."""
    from django.core.mail import send_mail
    from django.conf import settings as _settings

    login_url = getattr(_settings, 'FRONTEND_URL', 'https://greenlearning.vercel.app') + '/login'
    subject = f"Your SubjectMatter login for {teacher_class.name}"
    body = (
        f"Hi {student.first_name},\n\n"
        f"Your teacher {teacher.get_full_name()} has set up a SubjectMatter account for you.\n\n"
        f"Log in at: {login_url}\n"
        f"Email:     {student.email}\n"
        f"Password:  {plaintext_password}\n\n"
        f"Class: {teacher_class.name} (Year {teacher_class.year_level})\n\n"
        f"You can change your password after you log in.\n\n"
        f"SubjectMatter"
    )
    try:
        send_mail(
            subject=subject,
            message=body,
            from_email=getattr(_settings, 'DEFAULT_FROM_EMAIL', 'noreply@subjectmatter.app'),
            recipient_list=[student.email],
            fail_silently=True,
        )
    except Exception:
        pass  # Don't let email failure block the import response

class TeacherViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    def _get_teacher(self, request, pk):
        try:
            user = User.objects.get(pk=pk, role='teacher')
        except User.DoesNotExist:
            return None, Response({'error': 'Teacher not found.'}, status=404)
        if request.user.pk != user.pk and request.user.role != 'admin':
            return None, Response({'error': 'Forbidden.'}, status=403)
        return user, None

    @action(detail=True, methods=['get'])
    def home(self, request, pk=None):
        """Return teacher profile + class list with student counts and focus area summaries."""
        from .models import TeacherProfile, TeacherClass, TeacherClassStudent, StudentFocusArea
        teacher, err = self._get_teacher(request, pk)
        if err:
            return err
        profile = TeacherProfile.objects.filter(user=teacher).first()
        classes = list(TeacherClass.objects.filter(teacher=teacher).order_by('name'))

        # Build class_id → [student_id] map in one query
        memberships = TeacherClassStudent.objects.filter(
            teacher_class__in=classes
        ).values('teacher_class_id', 'student_id')
        class_students: dict = {}
        for m in memberships:
            class_students.setdefault(m['teacher_class_id'], []).append(m['student_id'])

        # Fetch all focus areas for all students across all classes in one query
        all_student_ids = [sid for ids in class_students.values() for sid in ids]
        focus_rows = (
            StudentFocusArea.objects
            .filter(student_id__in=all_student_ids)
            .select_related('skill')
            .values('student_id', 'skill__description')
        ) if all_student_ids else []

        # student_id → [skill_description]
        student_focus: dict = {}
        for row in focus_rows:
            student_focus.setdefault(row['student_id'], []).append(row['skill__description'])

        def class_focus_areas(class_id):
            counts: dict = {}
            for sid in class_students.get(class_id, []):
                for desc in student_focus.get(sid, []):
                    counts[desc] = counts.get(desc, 0) + 1
            # Return sorted by frequency desc, then alpha
            return [d for d, _ in sorted(counts.items(), key=lambda x: (-x[1], x[0]))]

        class_dicts = []
        for c in classes:
            d = c.to_dict()
            d['focus_areas'] = class_focus_areas(c.id)
            class_dicts.append(d)

        return Response({
            'profile': profile.to_dict() if profile else {},
            'classes': class_dicts,
        })

    @action(detail=True, methods=['post'])
    def create_class(self, request, pk=None):
        """Create a new class for this teacher."""
        from .models import TeacherClass
        teacher, err = self._get_teacher(request, pk)
        if err:
            return err
        name = (request.data.get('name') or '').strip()
        year_level = (request.data.get('year_level') or '').strip()
        if not name or not year_level:
            return Response({'error': 'name and year_level are required.'}, status=400)
        tc = TeacherClass.objects.create(teacher=teacher, name=name, year_level=year_level)
        return Response(tc.to_dict(), status=201)

    @action(detail=True, methods=['post'])
    def import_students(self, request, pk=None):
        """
        Bulk-import students into a class.

        Expected body:
          {
            "class_id": 42,
            "students": [
              {"first_name": "...", "last_name": "...", "email": "..."},
              ...
            ]
          }

        Email is required for every student. For each row:
          - Email matches existing account → link them (no new password).
          - New email → create account with a 4-character alphanumeric password,
            send a welcome email to the student with their login credentials.

        Returns a list with plaintext passwords for new accounts so the teacher
        can also print/distribute them.
        """
        from .models import TeacherClass, TeacherClassStudent, StudentProfile
        import secrets, string as _string

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.data.get('class_id')
        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        students_data = request.data.get('students', [])
        if not isinstance(students_data, list) or not students_data:
            return Response({'error': 'Provide a non-empty "students" list.'}, status=400)

        results = []
        year_level = tc.year_level

        for s in students_data:
            first = (s.get('first_name') or '').strip()
            last = (s.get('last_name') or '').strip()
            email = (s.get('email') or '').strip().lower()

            if not first or not last:
                results.append({'error': 'first_name and last_name required', 'raw': s})
                continue
            if not email:
                results.append({'error': f'Email required for {first} {last}', 'raw': s})
                continue

            plaintext_pin = None

            existing = User.objects.filter(email__iexact=email).first()
            if existing:
                student_user = existing
            else:
                # New account — 4-char alphanumeric password
                chars = _string.ascii_letters + _string.digits
                plaintext_pin = ''.join(secrets.choice(chars) for _ in range(4))
                username = email
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{email}_{counter}"
                    counter += 1
                student_user = User.objects.create(
                    username=username,
                    email=email,
                    password=make_password(plaintext_pin),
                    first_name=first,
                    last_name=last,
                    role='student',
                    active=True,
                )
                StudentProfile.objects.create(
                    user=student_user, year_level=year_level, plain_password=plaintext_pin
                )
                _send_student_welcome_email(student_user, plaintext_pin, tc, teacher)

            # Link to class (idempotent)
            TeacherClassStudent.objects.get_or_create(teacher_class=tc, student=student_user)

            entry = {
                'id': student_user.id,
                'name': student_user.get_full_name(),
                'username': student_user.username,
                'email': student_user.email,
                'new_account': plaintext_pin is not None,
            }
            if plaintext_pin is not None:
                entry['pin'] = plaintext_pin
            results.append(entry)

        return Response({'imported': results})

    @action(detail=True, methods=['post'])
    def email_credentials(self, request, pk=None):
        """Re-send welcome emails for a list of student IDs (new accounts only)."""
        from .models import TeacherClass, TeacherClassStudent

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.data.get('class_id')
        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        credentials = request.data.get('credentials', [])
        # Each entry: {id, email, pin}
        sent = 0
        for cred in credentials:
            try:
                student = User.objects.get(pk=cred['id'])
            except (User.DoesNotExist, KeyError):
                continue
            pin = cred.get('pin', '')
            if pin:
                _send_student_welcome_email(student, pin, tc, teacher)
                sent += 1

        return Response({'sent': sent})

    @action(detail=True, methods=['post'])
    def reset_student_password(self, request, pk=None):
        """Generate a new 4-char password for a student and store it in plain text."""
        from .models import TeacherClass, TeacherClassStudent, StudentProfile
        import secrets, string as _string

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        student_id = request.data.get('student_id')
        class_id = request.data.get('class_id')

        # Verify the student is in one of this teacher's classes
        if not TeacherClassStudent.objects.filter(
            teacher_class__teacher=teacher,
            teacher_class_id=class_id,
            student_id=student_id,
        ).exists():
            return Response({'error': 'Student not found in class.'}, status=404)

        try:
            student = User.objects.get(pk=student_id)
        except User.DoesNotExist:
            return Response({'error': 'Student not found.'}, status=404)

        chars = _string.ascii_letters + _string.digits
        new_password = ''.join(secrets.choice(chars) for _ in range(4))

        student.set_password(new_password)
        student.save(update_fields=['password'])

        StudentProfile.objects.filter(user=student).update(plain_password=new_password)

        return Response({'password': new_password})

    @action(detail=True, methods=['get'])
    def class_detail(self, request, pk=None):
        """Return a single class with its full student list and per-student scores."""
        from .models import TeacherClass, TeacherClassStudent, StudentProfile
        from .competency import get_student_score

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.query_params.get('class_id')
        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        memberships = (
            TeacherClassStudent.objects
            .filter(teacher_class=tc)
            .select_related('student', 'student__student_profile')
            .order_by('student__last_name', 'student__first_name')
        )

        students = []
        for m in memberships:
            u = m.student
            profile = getattr(u, 'student_profile', None)
            yl = (profile.year_level or tc.year_level) if profile else tc.year_level
            score_ratio = get_student_score(u, yl)
            students.append({
                'id': u.id,
                'name': u.get_full_name(),
                'username': u.username,
                'email': u.email,
                'year_level': yl,
                'score_pct': round(score_ratio * 100, 1),
            })

        return Response({**tc.to_dict(), 'students': students})

    @action(detail=True, methods=['get'])
    def gap_report(self, request, pk=None):
        """
        Return a class-level gap report: for each leaf skill in the year level,
        show how many students have each star level (0–4).
        """
        from .models import TeacherClass, TeacherClassStudent, StudentSkillCompetency
        from .cache import get_matrix_cache, filter_matrix_by_grade

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.query_params.get('class_id')
        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        student_ids = list(
            TeacherClassStudent.objects.filter(teacher_class=tc).values_list('student_id', flat=True)
        )
        if not student_ids:
            return Response({'class': tc.to_dict(), 'skills': []})

        grade = tc.year_level.strip().lower().replace('year', '').strip()
        matrix = get_matrix_cache()
        leaf_skills = [s for s in filter_matrix_by_grade(matrix, grade) if s['children_count'] == 0]

        skill_ids = [s['id'] for s in leaf_skills]
        competencies = StudentSkillCompetency.objects.filter(
            student_id__in=student_ids,
            skill_id__in=skill_ids,
        ).values('skill_id', 'student_id', 'level')

        # Build skill_id → {student_id: level}
        comp_map: dict = {}
        for c in competencies:
            comp_map.setdefault(c['skill_id'], {})[c['student_id']] = c['level']

        n = len(student_ids)
        skills_report = []
        for skill in leaf_skills:
            sid = skill['id']
            levels = [comp_map.get(sid, {}).get(uid, 0) for uid in student_ids]
            avg = sum(levels) / n if n else 0
            below = sum(1 for lv in levels if lv == 0)
            skills_report.append({
                'skill_id': sid,
                'description': skill['description'],
                'avg_level': round(avg, 2),
                'students_at_zero': below,
                'student_count': n,
                'distribution': {str(i): levels.count(i) for i in range(5)},
            })

        # Sort by avg_level ascending so biggest gaps come first
        skills_report.sort(key=lambda x: x['avg_level'])

        return Response({'class': tc.to_dict(), 'skills': skills_report})

    @action(detail=True, methods=['post'])
    def class_add_focus(self, request, pk=None):
        """Add a skill as a focus area for every student in a class."""
        from .models import TeacherClass, TeacherClassStudent, StudentFocusArea

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.data.get('class_id')
        skill_id = request.data.get('skill_id')
        if not class_id or not skill_id:
            return Response({'error': 'class_id and skill_id required.'}, status=400)

        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        student_ids = list(
            TeacherClassStudent.objects.filter(teacher_class=tc).values_list('student_id', flat=True)
        )

        added = 0
        for student_id in student_ids:
            max_order = StudentFocusArea.objects.filter(student_id=student_id).aggregate(
                m=models.Max('order')
            )['m'] or 0
            _, created = StudentFocusArea.objects.get_or_create(
                student_id=student_id,
                skill_id=skill_id,
                defaults={'added_by': request.user, 'order': max_order + 1},
            )
            if created:
                added += 1

        return Response({'added': added, 'total_students': len(student_ids)})

    @action(detail=True, methods=['post'])
    def class_remove_focus(self, request, pk=None):
        """Remove a skill focus area from every student in a class who has it."""
        from .models import TeacherClass, TeacherClassStudent, StudentFocusArea

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.data.get('class_id')
        skill_id = request.data.get('skill_id')
        if not class_id or not skill_id:
            return Response({'error': 'class_id and skill_id required.'}, status=400)

        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        student_ids = list(
            TeacherClassStudent.objects.filter(teacher_class=tc).values_list('student_id', flat=True)
        )

        deleted, _ = StudentFocusArea.objects.filter(
            student_id__in=student_ids,
            skill_id=skill_id,
        ).delete()

        return Response({'removed': deleted})

    @action(detail=True, methods=['post'])
    def start_assessment(self, request, pk=None):
        """Start a new in-class assessment for a class."""
        from .models import TeacherClass, ClassAssessment, TeacherClassStudent, AssessmentStudentResult

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        class_id = request.data.get('class_id')
        try:
            tc = TeacherClass.objects.get(pk=class_id, teacher=teacher)
        except TeacherClass.DoesNotExist:
            return Response({'error': 'Class not found.'}, status=404)

        skill_ids = request.data.get('skill_ids', [])

        # End any existing active assessment for this class first
        ClassAssessment.objects.filter(teacher_class=tc, status='active').update(status='ended')

        assessment = ClassAssessment.objects.create(teacher_class=tc, skill_ids=skill_ids)

        student_ids = list(
            TeacherClassStudent.objects.filter(teacher_class=tc).values_list('student_id', flat=True)
        )
        for sid in student_ids:
            AssessmentStudentResult.objects.get_or_create(assessment=assessment, student_id=sid)

        return Response({'assessment_id': assessment.id})

    @action(detail=True, methods=['post'])
    def end_assessment(self, request, pk=None):
        """End an active assessment."""
        from .models import ClassAssessment
        from django.utils import timezone

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        assessment_id = request.data.get('assessment_id')
        updated = ClassAssessment.objects.filter(
            pk=assessment_id,
            teacher_class__teacher=teacher,
            status='active',
        ).update(status='ended', ended_at=timezone.now())

        if not updated:
            return Response({'error': 'Assessment not found.'}, status=404)

        return Response({'ok': True})

    @action(detail=True, methods=['get'])
    def assessment_dashboard(self, request, pk=None):
        """Return live student results for an assessment, sorted for teacher view."""
        from .models import ClassAssessment, AssessmentStudentResult

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        assessment_id = request.query_params.get('assessment_id')
        try:
            assessment = ClassAssessment.objects.get(
                pk=assessment_id, teacher_class__teacher=teacher
            )
        except ClassAssessment.DoesNotExist:
            return Response({'error': 'Assessment not found.'}, status=404)

        results = AssessmentStudentResult.objects.filter(
            assessment=assessment
        ).select_related('student', 'student__student_profile')

        students = []
        for r in results:
            if r.absent:
                continue
            profile = getattr(r.student, 'student_profile', None)
            entry = {
                'student_id': r.student_id,
                'name': r.student.get_full_name() or r.student.username,
                'correct': r.correct,
                'incorrect': r.incorrect,
                'joined': r.joined_at is not None,
                'username': r.student.email or r.student.username,
                'plain_password': profile.plain_password if profile else None,
            }
            students.append(entry)

        # Sort: not-joined first, then most incorrect, then least correct
        students.sort(key=lambda s: (
            0 if not s['joined'] else 1,
            -s['incorrect'],
            s['correct'],
        ))

        return Response({'assessment': assessment.to_dict(), 'students': students})

    @action(detail=True, methods=['post'])
    def mark_absent(self, request, pk=None):
        """Mark a student as not attending today's assessment."""
        from .models import ClassAssessment, AssessmentStudentResult

        teacher, err = self._get_teacher(request, pk)
        if err:
            return err

        assessment_id = request.data.get('assessment_id')
        student_id = request.data.get('student_id')

        try:
            assessment = ClassAssessment.objects.get(
                pk=assessment_id, teacher_class__teacher=teacher
            )
        except ClassAssessment.DoesNotExist:
            return Response({'error': 'Assessment not found.'}, status=404)

        AssessmentStudentResult.objects.filter(
            assessment=assessment, student_id=student_id
        ).update(absent=True)

        return Response({'ok': True})


class AssessmentViewSet(viewsets.ViewSet):
    permission_classes = [IsAuthenticated]

    @action(detail=False, methods=['get'])
    def active(self, request):
        """Return any active assessment for a student's enrolled classes."""
        student_id = request.query_params.get('student_id')
        if not student_id:
            return Response({'assessment': None})

        from .models import ClassAssessment, TeacherClassStudent

        class_ids = TeacherClassStudent.objects.filter(
            student_id=student_id
        ).values_list('teacher_class_id', flat=True)

        assessment = ClassAssessment.objects.filter(
            teacher_class_id__in=class_ids, status='active'
        ).select_related('teacher_class').first()

        if not assessment:
            return Response({'assessment': None})

        return Response({'assessment': assessment.to_dict()})

    @action(detail=True, methods=['post'])
    def join(self, request, pk=None):
        """Student joins the assessment — records joined_at and returns the assessment's skill list."""
        from .models import ClassAssessment, AssessmentStudentResult, Skill
        from django.utils import timezone

        assessment = ClassAssessment.objects.filter(pk=pk, status='active').first()
        if not assessment:
            return Response({'error': 'Assessment not found or not active.'}, status=404)

        student_id = request.data.get('student_id') or request.user.pk

        result, _ = AssessmentStudentResult.objects.get_or_create(
            assessment=assessment, student_id=student_id,
        )
        if not result.joined_at:
            result.joined_at = timezone.now()
            result.save(update_fields=['joined_at'])

        # Return the assessment's selected skills (in order)
        skill_id_list = assessment.skill_ids or []
        skill_map = {
            s.id: s.description
            for s in Skill.objects.filter(id__in=skill_id_list)
        }
        skills = [
            {'id': sid, 'description': skill_map[sid]}
            for sid in skill_id_list
            if sid in skill_map
        ]

        return Response({'ok': True, 'focus_areas': skills})

    @action(detail=True, methods=['post'])
    def record_answer(self, request, pk=None):
        """Record a correct/incorrect answer for assessment result tracking."""
        from .models import ClassAssessment, AssessmentStudentResult

        assessment = ClassAssessment.objects.filter(pk=pk).first()
        if not assessment:
            return Response({'error': 'Assessment not found.'}, status=404)

        student_id = request.data.get('student_id')
        correct = request.data.get('correct', False)

        result, _ = AssessmentStudentResult.objects.get_or_create(
            assessment_id=pk, student_id=student_id,
        )
        if correct:
            AssessmentStudentResult.objects.filter(pk=result.pk).update(
                correct=models.F('correct') + 1
            )
        else:
            AssessmentStudentResult.objects.filter(pk=result.pk).update(
                incorrect=models.F('incorrect') + 1
            )

        return Response({'ok': True})
