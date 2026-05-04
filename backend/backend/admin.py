from django.contrib import admin
from .models import *

admin.site.register([User, ])
admin.site.register([BookingWeekly, WeeklyProgressSnapshot, Payment])
admin.site.register([TutorAvailability, TutorProfile, TutorStudent, StudentProfile, DistributorProfile])
admin.site.register([TeacherProfile, TeacherClass, TeacherClassStudent])
admin.site.register([ClassAssessment, AssessmentStudentResult])
admin.site.register([Skill, Template, Note, Year])

@admin.register(Knowledge)
class KnowledgeAdmin(admin.ModelAdmin):
    list_display = ("title", "created_at", "updated_at")
    search_fields = ("title", "text")
    filter_horizontal = ("skills",)
admin.site.register([SMSConversation, SMSMessage, SMSSendJob])

@admin.register(GlobalSetting)
class GlobalSettingAdmin(admin.ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)

@admin.register(UserPreference)
class UserPreference(admin.ModelAdmin):
    list_display = ("key", "value")
    search_fields = ("key",)

@admin.register(BookingAdhoc)
class BookingAdhocAdmin(admin.ModelAdmin):
    list_display = (
        "tutor",
        "student",
        "start_datetime",
        "end_datetime",
        "status",
        "created_at",
        "created_by",
    )

    readonly_fields = ("created_at", "created_by")
