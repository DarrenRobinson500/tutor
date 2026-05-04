import uuid
import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0020_testsession_test_type'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='school_name',
            field=models.CharField(blank=True, max_length=200, null=True),
        ),
        migrations.AddField(
            model_name='tutorprofile',
            name='qualification',
            field=models.CharField(blank=True, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='tutorprofile',
            name='tutor_year_levels',
            field=models.JSONField(default=list),
        ),
        migrations.AddField(
            model_name='tutorprofile',
            name='bio',
            field=models.TextField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name='tutorprofile',
            name='approved',
            field=models.BooleanField(default=False),
        ),
        migrations.CreateModel(
            name='AssessmentToken',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('token', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('expires_at', models.DateTimeField()),
                ('student', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='assessment_tokens',
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
        ),
    ]
