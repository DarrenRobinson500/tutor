from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0047_user_account_details'),
    ]

    operations = [
        migrations.AlterField(
            model_name='tutorjob',
            name='job_type',
            field=models.CharField(
                choices=[
                    ('post_tuition_review', 'Post Tuition Review'),
                    ('send_progress_message', 'Send Progress Message'),
                    ('review_focus_area', 'Review Focus Area'),
                    ('review_available_hours', 'Review My Available Hours'),
                ],
                max_length=50,
            ),
        ),
    ]
