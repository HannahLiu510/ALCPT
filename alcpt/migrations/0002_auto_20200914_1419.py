# Generated by Django 3.1.1 on 2020-09-14 14:19

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('alcpt', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='question',
            name='q_correct_time',
            field=models.IntegerField(default=0),
        ),
        migrations.AddField(
            model_name='question',
            name='q_time',
            field=models.IntegerField(default=0),
        ),
    ]