from rest_framework.routers import DefaultRouter
from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
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
router.register(r'admin-emails', AdminEmailViewSet, basename='admin-emails')
router.register(r"template_groups", TemplateGroupViewSet)
router.register(r"teachers", TeacherViewSet, basename="teachers")
router.register(r"assessments", AssessmentViewSet, basename="assessments")

urlpatterns = [
    path("auth/jwt/login/", SuperuserRoleTokenView.as_view(), name="token_obtain_pair"),
    path("auth/jwt/refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("docs/", editor_docs, name="editor_docs"),
    path("docs/messages/", messages_docs, name="messages_docs"),

    # Payment flow
    path("payments/setup-intent/",        payment_setup_intent,    name="payment_setup_intent"),
    path("payments/save-payment-method/", payment_save_method,     name="payment_save_method"),
    path("payments/pending/",             payment_pending,         name="payment_pending"),
    path("payments/tutor-billing/",       tutor_billing,           name="tutor_billing"),
    path("payments/admin-feedback/",      admin_feedback,          name="admin_feedback"),
    path("payments/<int:pk>/",            payment_detail,          name="payment_detail"),
    path("payments/<int:pk>/authorise/",  payment_authorise,       name="payment_authorise"),
    path("payments/<int:pk>/confirm/",    payment_confirm_receipt, name="payment_confirm_receipt"),
    path("payments/<int:pk>/retry/",      payment_retry,           name="payment_retry"),
    path("parents/<int:pk>/payments/",    parent_payment_history,  name="parent_payment_history"),
    path("admin/activity/",               admin_activity,          name="admin_activity"),
    path("settings/",                     system_settings,         name="system_settings"),
    path("admin/variables/",              admin_variables,         name="admin_variables"),
]

urlpatterns += router.urls
