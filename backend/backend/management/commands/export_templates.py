import json
import yaml
from django.core.management.base import BaseCommand
from backend.models import Template


class Command(BaseCommand):
    help = "Export all Templates to a JSON file"

    def add_arguments(self, parser):
        parser.add_argument("output", help="Path to the output JSON file")

    def handle(self, *args, **options):
        templates = Template.objects.select_related("skill").all()

        records = []
        for t in templates:
            # Parse the YAML content to extract embedded fields
            parsed = {}
            if t.content:
                try:
                    parsed = yaml.safe_load(t.content) or {}
                except Exception:
                    pass

            records.append({
                # Primary: the raw YAML content (source of truth)
                "content": t.content,

                # Fields not present in the YAML — needed for DB restore
                "subject": t.subject,
                "topic": t.topic,
                "subtopic": t.subtopic,
                "skill_id": t.skill_id,
                "tags": t.tags,
                "curriculum": t.curriculum,
                "validated": t.validated,
                "status": t.status,

                # Mirrors of YAML fields — included for readability/reference only.
                # On import, these are derived from `content` and these values are ignored.
                "_title": parsed.get("title", ""),
                "_years": parsed.get("years", ""),
                "_difficulty": parsed.get("difficulty", ""),
            })

        output_path = options["output"]
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(records, f, indent=2, ensure_ascii=False)

        self.stdout.write(self.style.SUCCESS(
            f"Exported {len(records)} templates to {output_path}"
        ))
