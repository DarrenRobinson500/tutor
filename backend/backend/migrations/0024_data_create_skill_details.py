"""
Migration 0024: Data migration
1. For each leaf Skill with a non-empty 'detail' text field:
   - Create a child Skill node (is_detail=True) for each detail line.
2. For each Template with a 'skill' FK and a 'subject' value:
   - Find the matching detail child whose description == template.subject
   - Set template.skill_detail to that child.
   Templates whose subject doesn't match any detail line get skill_detail=None.
"""
from django.db import migrations


def create_skill_details(apps, schema_editor):
    Skill = apps.get_model('backend', 'Skill')
    Template = apps.get_model('backend', 'Template')

    # Process every skill that still has detail text (leaf skills before migration)
    for skill in Skill.objects.exclude(detail='').exclude(detail__isnull=True):
        lines = [l.strip() for l in skill.detail.splitlines() if l.strip()]
        if not lines:
            continue

        # Build map of existing detail children by description
        existing = {
            s.description: s
            for s in Skill.objects.filter(parent=skill, is_detail=True)
        }

        detail_skills = {}
        for i, line in enumerate(lines):
            code = f"{skill.code}-D{i + 1}"
            if line in existing:
                ds = existing[line]
                ds.order_index = i
                ds.code = code
                ds.grades = skill.grades or ''
                ds.save()
            else:
                ds = Skill.objects.create(
                    parent=skill,
                    code=code,
                    description=line,
                    grades=skill.grades or '',
                    order_index=i,
                    is_detail=True,
                )
            detail_skills[line] = ds

        # Link templates to their matching detail skill
        for template in Template.objects.filter(skill=skill):
            subject = (template.subject or '').strip()
            if subject in detail_skills:
                template.skill_detail = detail_skills[subject]
                template.save(update_fields=['skill_detail'])
            # else: skill_detail stays None — template needs manual assignment


def reverse_skill_details(apps, schema_editor):
    Skill = apps.get_model('backend', 'Skill')
    Template = apps.get_model('backend', 'Template')
    # Clear skill_detail on templates
    Template.objects.update(skill_detail=None)
    # Delete all is_detail skill nodes
    Skill.objects.filter(is_detail=True).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0023_skill_is_detail_template_skill_detail'),
    ]

    operations = [
        migrations.RunPython(create_skill_details, reverse_skill_details),
    ]
