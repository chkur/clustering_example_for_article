# Generated by Django 4.1.5 on 2023-01-19 18:54

import django.contrib.gis.db.models.fields
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="Vehicle",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("creation_date", models.DateField()),
                ("status", models.CharField(blank=True, max_length=20, null=True)),
                ("completion_date", models.DateField(blank=True, null=True)),
                ("service_request_number", models.CharField(max_length=50)),
                ("type_of_service_request", models.CharField(max_length=255)),
                (
                    "license_plate",
                    models.CharField(blank=True, max_length=1000, null=True),
                ),
                (
                    "vehicle_make",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                (
                    "vehicle_color",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                (
                    "current_activity",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                (
                    "most_recent_action",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                ("days_parked", models.IntegerField(blank=True, null=True)),
                (
                    "street_address",
                    models.CharField(blank=True, max_length=250, null=True),
                ),
                ("zip_code", models.CharField(blank=True, max_length=10, null=True)),
                ("x_coordinate", models.FloatField(blank=True, null=True)),
                ("y_coordinate", models.FloatField(blank=True, null=True)),
                ("ward", models.IntegerField(blank=True, null=True)),
                ("police_district", models.IntegerField(blank=True, null=True)),
                ("community_area", models.IntegerField(blank=True, null=True)),
                ("ssa", models.IntegerField(blank=True, null=True)),
                ("latitude", models.FloatField(blank=True, null=True)),
                ("longitude", models.FloatField(blank=True, null=True)),
                (
                    "location",
                    django.contrib.gis.db.models.fields.PointField(
                        blank=True, null=True, srid=4326
                    ),
                ),
            ],
        ),
    ]
