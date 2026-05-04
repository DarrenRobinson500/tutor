from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0033_tutor_job'),
    ]

    operations = [
        migrations.AddField(
            model_name='tutoringsession',
            name='session_mode',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
        migrations.AddField(
            model_name='tutoringsession',
            name='session_state',
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
