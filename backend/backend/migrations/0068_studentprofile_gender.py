from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0067_add_welcome_email_sent'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentprofile',
            name='gender',
            field=models.CharField(blank=True, max_length=20, null=True),
        ),
    ]
