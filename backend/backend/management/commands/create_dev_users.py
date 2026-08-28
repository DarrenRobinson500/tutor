from django.core.management.base import BaseCommand

from backend.models import (
    User,
    GlobalSetting,
    TutorProfile,
    StudentProfile,
    TutorStudent,
    ParentChild,
)

DEV_USERS = [
    {"role": "admin", "username_setting": "dev_admin_email", "password_setting": "dev_admin_password",
     "default_username": "Darren", "first_name": "Darren", "last_name": "Admin"},
    {"role": "parent", "username_setting": "dev_parent_email", "password_setting": "dev_parent_password",
     "default_username": "Amanda", "first_name": "Amanda", "last_name": "Parent"},
    {"role": "student", "username_setting": "dev_student_email", "password_setting": "dev_student_password",
     "default_username": "Michael", "first_name": "Michael", "last_name": "Student"},
    {"role": "tutor", "username_setting": "dev_tutor_email", "password_setting": "dev_tutor_password",
     "default_username": "Alex", "first_name": "Alex", "last_name": "Tutor"},
]


class Command(BaseCommand):
    help = "Create the dev quick-login test accounts (admin/parent/student/tutor) used by the login page."

    def handle(self, *args, **options):
        users = {}

        for spec in DEV_USERS:
            username = GlobalSetting.get(spec["username_setting"], spec["default_username"])
            password = GlobalSetting.get(spec["password_setting"], spec["default_username"])

            user, created = User.objects.get_or_create(
                username=username,
                defaults={
                    "email": username if "@" in username else "",
                    "role": spec["role"],
                    "first_name": spec["first_name"],
                    "last_name": spec["last_name"],
                    "is_staff": spec["role"] == "admin",
                    "is_superuser": spec["role"] == "admin",
                },
            )
            user.set_password(password)
            user.role = spec["role"]
            user.save()
            users[spec["role"]] = user

            verb = "Created" if created else "Updated"
            self.stdout.write(self.style.SUCCESS(f"{verb} {spec['role']} user '{username}' (password: {password})"))

        # Link tutor <-> student <-> parent so their dashboards have data to show.
        tutor = users["tutor"]
        student = users["student"]
        parent = users["parent"]

        TutorProfile.objects.get_or_create(
            tutor=tutor,
            defaults={"approved": True, "looking_for_students": True},
        )
        StudentProfile.objects.get_or_create(user=student)
        TutorStudent.objects.get_or_create(tutor=tutor, student=student)
        ParentChild.objects.get_or_create(parent=parent, child=student)

        self.stdout.write(self.style.SUCCESS("Linked dev tutor/student/parent accounts."))
