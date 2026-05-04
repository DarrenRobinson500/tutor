from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0015_knowledge"),
    ]

    operations = [
        migrations.AddField(
            model_name="knowledge",
            name="text_2",
            field=models.TextField(blank=True, default=""),
            preserve_default=False,
        ),
    ]
