"""
Migration 0025: Remove deprecated fields now that skill_detail is populated.
- Template.skill  (old FK, replaced by skill_detail + @property)
- Template.subject (replaced by skill_detail.description)
- Skill.detail    (replaced by is_detail child Skill nodes)
"""
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0024_data_create_skill_details'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='template',
            name='skill',
        ),
        migrations.RemoveField(
            model_name='template',
            name='subject',
        ),
        migrations.RemoveField(
            model_name='skill',
            name='detail',
        ),
    ]
