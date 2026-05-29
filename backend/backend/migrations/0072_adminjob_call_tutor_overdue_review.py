from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0071_add_smssendjob_message_type'),
    ]

    operations = [
        migrations.AlterField(
            model_name='adminjob',
            name='job_type',
            field=models.CharField(
                max_length=50,
                choices=[
                    ('approve_distributor', 'Approve Distributor'),
                    ('approve_tutor', 'Approve Tutor'),
                    ('payment_failed', 'Payment Failed'),
                    ('payment_overdue_7', 'Payment Overdue — 7 Days'),
                    ('payment_overdue_14', 'Payment Overdue — 14 Days'),
                    ('low_session_rating', 'Low Session Rating'),
                    ('setup_bank_details', 'Setup Bank Details'),
                    ('tutor_removed', 'Tutor Removed'),
                    ('call_tutor_overdue_review', 'Call Tutor — Overdue Review'),
                ],
            ),
        ),
    ]
