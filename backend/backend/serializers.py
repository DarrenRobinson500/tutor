from rest_framework import serializers
from .models import *


class YearSerializer(serializers.ModelSerializer):
    class Meta:
        model = Year
        fields = ["id", "code", "label", "order", "stage"]

class TemplateGroupSerializer(serializers.ModelSerializer):
    class Meta:
        model = TemplateGroup
        fields = ["id", "name", "skill_detail", "grade", "topic", "subtopic",]

class TemplateTranslationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Template
        fields = ['id', 'language']

class TemplateSerializer(serializers.ModelSerializer):
    knowledge_ids = serializers.PrimaryKeyRelatedField(
        source="knowledge_items", many=True, queryset=Knowledge.objects.all(), required=False
    )
    skill_id = serializers.SerializerMethodField()
    skill_detail_description = serializers.SerializerMethodField()
    translations = TemplateTranslationSerializer(many=True, read_only=True)

    def get_skill_id(self, obj):
        s = obj.skill
        return s.id if s else None

    def get_skill_detail_description(self, obj):
        return obj.skill_detail.description if obj.skill_detail else None

    class Meta:
        model = Template
        fields = "__all__"
        read_only_fields = ['id']

class SkillSerializer(serializers.ModelSerializer):
    children_count = serializers.IntegerField(source="children.count", read_only=True)
    template_count = serializers.IntegerField(read_only=True)
    parent_id = serializers.IntegerField(source="parent.id", allow_null=True, read_only=True)
    detail_covered = serializers.SerializerMethodField()
    detail_total = serializers.SerializerMethodField()

    def get_detail_total(self, obj):
        return obj.children.filter(is_detail=True).count()

    def get_detail_covered(self, obj):
        return obj.children.filter(is_detail=True, templates__validated=True).distinct().count()

    class Meta:
        model = Skill
        fields = ["id", "parent_id", "code", "description", "grades", "order_index", "is_detail", "children_count", "template_count", "validated_count", "unvalidated_count", "detail_covered", "detail_total"]

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "first_name", "last_name", "email", "role"]

class StudentSerializer(serializers.ModelSerializer):
    next_booking = serializers.SerializerMethodField()

    class Meta:
        model = StudentProfile
        fields = ["id", "user", "year_level", "area_of_study", "next_booking", "mobile", "address"]
        read_only_fields = ["id", "user"]
        depth = 1

    def get_next_booking(self, obj):
        return obj.next_booking()

class TutorSerializer(serializers.ModelSerializer):
    class Meta:
        model = TutorProfile
        fields = ["id", "tutor", "logo", "color_scheme", "welcome_message", "default_session_minutes", "buffer_minutes", "token", "created_at"]
        depth = 1  # includes user details

class NoteSerializer(serializers.ModelSerializer):
    class Meta:
        model = Note
        fields = "__all__"
        read_only_fields = ["id", "author", "created_at"]

class BookingWeeklySerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingWeekly
        fields = "__all__"

class BookingAdhocSerializer(serializers.ModelSerializer):
    class Meta:
        model = BookingAdhoc
        fields = ["id", "student", "tutor", "start_datetime", "end_datetime", "confirmed"]
        read_only_fields = ["id", "tutor", "end", "confirmed"]

class UserPreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserPreference
        fields = ["id", "key", "value", "updated_at"]

class KnowledgeSerializer(serializers.ModelSerializer):
    skill_ids = serializers.PrimaryKeyRelatedField(
        source="skills", many=True, queryset=Skill.objects.all()
    )

    class Meta:
        model = Knowledge
        fields = ["id", "title", "text", "diagram", "text_2", "skill_ids", "created_at", "updated_at"]
        read_only_fields = ["id", "created_at", "updated_at"]
