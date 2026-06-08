from django.db import migrations


def remove_confirm_appointment_jobs(apps, schema_editor):
    TutorJob = apps.get_model('backend', 'TutorJob')
    TutorJob.objects.filter(job_type='confirm_appointment').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0076_bookingadhoc_is_assisted_assessment'),
    ]

    operations = [
        migrations.RunPython(remove_confirm_appointment_jobs, migrations.RunPython.noop),
    ]
