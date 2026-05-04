from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("backend", "0014_skill_detail"),
    ]

    operations = [
        migrations.CreateModel(
            name="Knowledge",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("title", models.CharField(max_length=200)),
                ("text", models.TextField(blank=True)),
                ("diagram", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("skills", models.ManyToManyField(blank=True, related_name="knowledge_items", to="backend.Skill")),
            ],
        ),
    ]
