"""
Management command: reload_skills
----------------------------------
1. Snapshots Template → skill code and Knowledge → skill codes before deletion
2. Deletes ALL Skill objects (cascades: TemplateSkill, StudentSkillMatrix)
3. Re-imports the skill tree from nsw_math_k10_years.json
4. Relinks Template.skill and TemplateSkill rows by code
5. Relinks Knowledge.skills M2M by code

Usage:
    python manage.py reload_skills
    python manage.py reload_skills --dry-run   # shows counts, makes no changes
"""

from django.core.management.base import BaseCommand
from django.db import transaction

from backend.models import Skill, Template, TemplateSkill, Knowledge
from backend.import_skills import import_syllabus


class Command(BaseCommand):
    help = "Delete all skills, reload from JSON, relink templates and knowledge items"

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Print what would happen without making any changes",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]

        # ── Step 1: Snapshot existing links ───────────────────────────────────

        self.stdout.write("Snapshotting template -> skill links...")
        template_skill_map = {}   # template.id → skill.code
        for t in Template.objects.select_related("skill").filter(skill__isnull=False):
            template_skill_map[t.id] = t.skill.code

        self.stdout.write(f"  {len(template_skill_map)} templates have a skill link")

        self.stdout.write("Snapshotting TemplateSkill rows...")
        template_skill_rows = {}  # template.id -> [skill.code, ...]
        for ts in TemplateSkill.objects.select_related("skill"):
            template_skill_rows.setdefault(ts.template_id, []).append(ts.skill.code)

        total_ts_rows = sum(len(v) for v in template_skill_rows.values())
        self.stdout.write(f"  {total_ts_rows} TemplateSkill rows across {len(template_skill_rows)} templates")

        self.stdout.write("Snapshotting Knowledge -> skill links...")
        knowledge_skill_map = {}  # knowledge.id → [skill.code, ...]
        for k in Knowledge.objects.prefetch_related("skills"):
            codes = list(k.skills.values_list("code", flat=True))
            if codes:
                knowledge_skill_map[k.id] = codes

        self.stdout.write(f"  {len(knowledge_skill_map)} knowledge items have skill links")

        skill_count = Skill.objects.count()
        self.stdout.write(f"\nTotal skills currently in DB: {skill_count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n--dry-run: no changes made."))
            return

        # ── Step 2: Delete all skills ──────────────────────────────────────────

        with transaction.atomic():
            self.stdout.write("\nDeleting all skills (cascades TemplateSkill + StudentSkillMatrix)...")
            deleted, breakdown = Skill.objects.all().delete()
            self.stdout.write(f"  Deleted {deleted} rows: {breakdown}")

            # Step 3: Re-import from JSON

            self.stdout.write("\nImporting skill tree from nsw_math_k10_years.json...")
            import_syllabus()
            new_count = Skill.objects.count()
            self.stdout.write(f"  Imported {new_count} skill nodes")

            # Build code -> Skill lookup
            skill_by_code = {s.code: s for s in Skill.objects.all()}

            # Step 4a: Relink Template.skill

            self.stdout.write("\nRelinking Template.skill...")
            relinked = 0
            missing_codes = []
            templates_to_update = []
            for template_id, code in template_skill_map.items():
                skill = skill_by_code.get(code)
                if skill:
                    templates_to_update.append(
                        Template(id=template_id, skill=skill)
                    )
                    relinked += 1
                else:
                    missing_codes.append((template_id, code))

            Template.objects.bulk_update(templates_to_update, ["skill"])
            self.stdout.write(f"  Relinked: {relinked}")
            if missing_codes:
                self.stdout.write(
                    self.style.WARNING(
                        f"  WARNING: {len(missing_codes)} template(s) had unresolvable skill codes:"
                    )
                )
                for tid, code in missing_codes:
                    self.stdout.write(f"    Template #{tid} -> code '{code}' not found in new tree")

            # Step 4b: Recreate TemplateSkill rows

            self.stdout.write("\nRecreating TemplateSkill rows...")
            ts_created = 0
            ts_missing = []
            new_ts_rows = []
            for template_id, codes in template_skill_rows.items():
                for code in codes:
                    skill = skill_by_code.get(code)
                    if skill:
                        new_ts_rows.append(TemplateSkill(template_id=template_id, skill=skill))
                        ts_created += 1
                    else:
                        ts_missing.append((template_id, code))

            TemplateSkill.objects.bulk_create(new_ts_rows, ignore_conflicts=True)
            self.stdout.write(f"  Created: {ts_created} TemplateSkill rows")
            if ts_missing:
                self.stdout.write(
                    self.style.WARNING(f"  WARNING: {len(ts_missing)} TemplateSkill code(s) not found")
                )

            # Step 4c: Relink Knowledge.skills M2M

            self.stdout.write("\nRelinking Knowledge.skills...")
            k_relinked = 0
            k_missing = []
            for knowledge_id, codes in knowledge_skill_map.items():
                skills = []
                for code in codes:
                    skill = skill_by_code.get(code)
                    if skill:
                        skills.append(skill)
                    else:
                        k_missing.append((knowledge_id, code))
                if skills:
                    try:
                        k = Knowledge.objects.get(pk=knowledge_id)
                        k.skills.set(skills)
                        k_relinked += 1
                    except Knowledge.DoesNotExist:
                        pass

            self.stdout.write(f"  Relinked: {k_relinked} knowledge items")
            if k_missing:
                self.stdout.write(
                    self.style.WARNING(f"  WARNING: {len(k_missing)} Knowledge skill code(s) not found")
                )

        self.stdout.write(self.style.SUCCESS("\nDone. Skill tree reloaded and all links restored."))
