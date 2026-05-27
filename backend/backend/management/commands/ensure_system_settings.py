from django.core.management.base import BaseCommand
from backend.models import GlobalSetting

DEFAULTS = {
    # Pricing / booking rules
    'platform_fee': '6.50',
    'cancellation_notice_hours': '24',
    'booking_notice_hours': '24',
    # Quick-login test accounts
    'dev_admin_email': 'Darren',
    'dev_admin_password': 'Darren',
    'dev_parent_email': 'Amanda',
    'dev_parent_password': 'Amanda',
    'dev_student_email': 'Michael',
    'dev_student_password': 'Michael',
    'dev_tutor_email': 'Alex',
    'dev_tutor_password': 'Alex',
}


class Command(BaseCommand):
    help = "Seed required GlobalSetting entries if they do not already exist."

    def handle(self, *args, **options):
        for key, value in DEFAULTS.items():
            _, created = GlobalSetting.objects.get_or_create(
                key=key,
                defaults={'value': value},
            )
            if created:
                self.stdout.write(self.style.SUCCESS(f"Created GlobalSetting '{key}' = {value}"))
            else:
                self.stdout.write(f"GlobalSetting '{key}' already exists (value: {GlobalSetting.get(key)})")
