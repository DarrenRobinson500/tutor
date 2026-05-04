"""
Migration 0023: Schema changes
- Add Skill.is_detail boolean field
- Add Template.skill_detail FK (nullable, to Skill)
Both old fields (Template.skill, Template.subject, Skill.detail) are kept here
so the data migration (0024) can read them.
"""
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0022_tutorprofile_looking_for_students'),
    ]

    operations = [
        # Add is_detail to Skill
        migrations.AddField(
            model_name='skill',
            name='is_detail',
            field=models.BooleanField(default=False),
        ),
        # Add skill_detail FK to Template (nullable — filled by data migration)
        migrations.AddField(
            model_name='template',
            name='skill_detail',
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name='templates',
                to='backend.skill',
            ),
        ),
    ]
