from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0062_admin_email_record'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='min_questions_per_skill',
            field=models.IntegerField(default=0),
        ),
    ]
