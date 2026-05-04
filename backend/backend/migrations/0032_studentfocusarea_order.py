from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('backend', '0031_student_focus_area'),
    ]

    operations = [
        migrations.AddField(
            model_name='studentfocusarea',
            name='order',
            field=models.PositiveIntegerField(default=0),
        ),
        migrations.AlterModelOptions(
            name='studentfocusarea',
            options={'ordering': ['order', 'id']},
        ),
    ]
