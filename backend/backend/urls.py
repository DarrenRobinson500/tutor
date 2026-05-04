from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import (
    TokenObtainPairView,
    TokenRefreshView,
)
from .views import *

router = DefaultRouter()
router.register(r"questions", QuestionViewSet, basename="questions")
router.register(r"templates", TemplateViewSet, basename="template")
router.register(r"skills", SkillViewSet, basename="skills")
router.register(r"tutors", TutorViewSet, basename="tutors")
router.register(r"students", StudentViewSet, basename="student")
router.register(r"notes", NoteViewSet, basename="note")
router.register(r"auth", AuthViewSet, basename="auth")
router.register(r'weekly_bookings', BookingWeeklyViewSet, basename='weekly_bookings')
router.register(r'adhoc_bookings', BookingAdhocViewSet, basename='adhoc_bookings')
router.register(r'preferences', PreferenceViewSet, basename='preferences')
router.register(r'knowledge', KnowledgeViewSet, basename='knowledge')
router.register(r'sessions', TutoringSessionViewSet, basename='sessions')
router.register(r'tests', TestViewSet, basename='tests')
router.register(r'years', YearViewSet, basename='years')
router.register(r'focus-areas', FocusAreaViewSet, basename='focus-areas')
router.register(r'jobs', TutorJobViewSet, basename='jobs')
router.register(r'distributors', DistributorViewSet, basename='distributors')
router.register(r'admin-jobs', AdminJobViewSet, basename='admin-jobs')
router.register(r"template_groups", TemplateGroupViewSet)
router.register(r"teachers", TeacherViewSet, basename="teachers")
router.register(r"assessments", AssessmentViewSet, basename="assessments")


urlpatterns = [
    path("auth/jwt/login/", TokenObtainPairView.as_view(), name="token_obtain_pair"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("docs/", editor_docs, name="editor_docs"),
]

urlpatterns += router.urls
