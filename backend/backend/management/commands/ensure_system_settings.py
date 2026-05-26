from django.core.management.base import BaseCommand
from backend.models import GlobalSetting

DEFAULTS = {
    'platform_fee': '6.50',
    'cancellation_notice_hours': '24',
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
