# Generated by Django 3.1.1 on 2021-04-08 10:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alcpt', '0009_user_browser'),
    ]

    operations = [
        migrations.AddField(
            model_name='exam',
            name='is_started',
            field=models.BooleanField(default=False),
        ),
    ]
