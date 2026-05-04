from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0048_tutorjob_post_tuition_review'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='BookingOutcome',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date', models.DateField()),
                ('time', models.TimeField()),
                ('parent_message', models.TextField(blank=True, default='')),
                ('notes', models.TextField(blank=True, default='')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('tutor', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='booking_outcomes_as_tutor',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('student', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='booking_outcomes_as_student',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('payment', models.ForeignKey(
                    blank=True, null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    related_name='booking_outcomes',
                    to='backend.payment',
                )),
                ('focus_areas', models.ManyToManyField(
                    blank=True,
                    related_name='booking_outcomes_current',
                    to='backend.skill',
                )),
                ('focus_areas_next', models.ManyToManyField(
                    blank=True,
                    related_name='booking_outcomes_next',
                    to='backend.skill',
                )),
            ],
            options={
                'ordering': ['-date', '-time'],
            },
        ),
    ]
