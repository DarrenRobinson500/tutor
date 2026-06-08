from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0075_add_parentprofile'),
    ]

    operations = [
        migrations.AddField(
            model_name='bookingadhoc',
            name='is_assisted_assessment',
            field=models.BooleanField(default=False),
        ),
    ]
