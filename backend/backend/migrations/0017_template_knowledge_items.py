from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0016_knowledge_text_2"),
    ]

    operations = [
        migrations.AddField(
            model_name="template",
            name="knowledge_items",
            field=models.ManyToManyField(
                blank=True,
                related_name="templates",
                to="backend.knowledge",
            ),
        ),
    ]
