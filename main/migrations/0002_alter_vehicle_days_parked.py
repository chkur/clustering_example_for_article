# Generated by Django 4.1.5 on 2023-01-19 19:06

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("main", "0001_initial"),
    ]

    operations = [
        migrations.AlterField(
            model_name="vehicle",
            name="days_parked",
            field=models.BigIntegerField(blank=True, null=True),
        ),
    ]