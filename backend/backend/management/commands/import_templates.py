import json
import yaml
from django.core.management.base import BaseCommand, CommandError
from backend.models import Template, Skill


class Command(BaseCommand):
    help = "Import Templates from a JSON file produced by export_templates"

    def add_arguments(self, parser):
        parser.add_argument("input", help="Path to the JSON file to import")
        parser.add_argument(
            "--overwrite",
            action="store_true",
            help="If a matching template already exists, overwrite it",
        )

    def handle(self, *args, **options):
        input_path = options["input"]
        overwrite = options["overwrite"]

        try:
            with open(input_path, "r", encoding="utf-8") as f:
                records = json.load(f)
        except FileNotFoundError:
            raise CommandError(f"File not found: {input_path}")
        except json.JSONDecodeError as e:
            raise CommandError(f"Invalid JSON: {e}")

        created = updated = skipped = 0

        for record in records:
            # Derive name/grade/difficulty from the YAML content (source of truth)
            content = record.get("content") or ""
            parsed = {}
            if content:
                try:
                    parsed = yaml.safe_load(content) or {}
                except Exception as e:
                    self.stderr.write(f"  Skipping record — invalid YAML content: {e}")
                    skipped += 1
                    continue

            name = str(parsed.get("title") or "")
            grade = str(parsed.get("years") or record.get("grade") or "")
            difficulty = str(parsed.get("difficulty") or "")

            # Resolve skill
            skill_id = record.get("skill_id")
            skill = None
            if skill_id is not None:
                try:
                    skill = Skill.objects.get(pk=skill_id)
                except Skill.DoesNotExist:
                    self.stderr.write(
                        f"  Skill id={skill_id} not found — importing '{name}' without skill link"
                    )

            # Duplicate detection: same name + skill
            existing = None
            if name:
                existing = Template.objects.filter(name=name, skill=skill).first()

            if existing and not overwrite:
                skipped += 1
                continue

            fields = dict(
                name=name,
                description="",
                content=content,
                subject=record.get("subject") or "",
                topic=record.get("topic") or "",
                subtopic=record.get("subtopic") or "",
                grade=grade or None,
                difficulty=difficulty,
                tags=record.get("tags") or [],
                curriculum=record.get("curriculum") or [],
                skill=skill,
                validated=record.get("validated", False),
                status=record.get("status", "draft"),
            )

            if existing:
                for attr, value in fields.items():
                    setattr(existing, attr, value)
                existing.save()
                updated += 1
            else:
                Template.objects.create(**fields)
                created += 1

        self.stdout.write(self.style.SUCCESS(
            f"Import complete — created: {created}, updated: {updated}, skipped: {skipped}"
        ))
