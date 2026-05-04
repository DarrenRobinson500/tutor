from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0017_template_knowledge_items'),
    ]

    operations = [
        migrations.CreateModel(
            name='TestSession',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('started_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('completed_at', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(choices=[('active', 'Active'), ('completed', 'Completed'), ('abandoned', 'Abandoned')], default='active', max_length=20)),
                ('skill_codes', models.JSONField(default=list)),
                ('current_skill_index', models.IntegerField(default=0)),
                ('current_difficulty', models.CharField(default='easy', max_length=10)),
                ('correct_streak', models.IntegerField(default=0)),
                ('incorrect_count', models.IntegerField(default=0)),
                ('used_template_ids', models.JSONField(default=list)),
                ('student', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='test_sessions', to='backend.user')),
            ],
            options={'ordering': ['-started_at']},
        ),
        migrations.CreateModel(
            name='TestSkillResult',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('skill_code', models.CharField(max_length=100)),
                ('skill_description', models.CharField(blank=True, max_length=255)),
                ('highest_difficulty_reached', models.CharField(default='none', max_length=10)),
                ('questions_asked', models.IntegerField(default=0)),
                ('questions_correct', models.IntegerField(default=0)),
                ('completed_at', models.DateTimeField(default=django.utils.timezone.now)),
                ('session', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='skill_results', to='backend.testsession')),
            ],
        ),
    ]
