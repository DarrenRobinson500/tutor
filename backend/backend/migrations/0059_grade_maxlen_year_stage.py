from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0058_studentprofile_plain_password"),
    ]

    operations = [
        # Extend grade fields to accommodate S6 course codes like "11std", "12adv"
        migrations.AlterField(
            model_name="template",
            name="grade",
            field=models.CharField(max_length=10, null=True, blank=True),
        ),
        migrations.AlterField(
            model_name="templategroup",
            name="grade",
            field=models.CharField(max_length=10, null=True, blank=True),
        ),
        # Add stage to Year so K-10 and S6 courses can be separated
        migrations.AddField(
            model_name="year",
            name="stage",
            field=models.CharField(max_length=20, default="k10", blank=True),
        ),
    ]
