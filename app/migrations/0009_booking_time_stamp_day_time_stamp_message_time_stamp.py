# Generated by Django 4.0.4 on 2022-05-05 10:49

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('app', '0008_remove_booking_day'),
    ]

    operations = [
        migrations.AddField(
            model_name='booking',
            name='time_stamp',
            field=models.DateField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='day',
            name='time_stamp',
            field=models.DateField(auto_now_add=True, null=True),
        ),
        migrations.AddField(
            model_name='message',
            name='time_stamp',
            field=models.DateField(auto_now_add=True, null=True),
        ),
    ]
