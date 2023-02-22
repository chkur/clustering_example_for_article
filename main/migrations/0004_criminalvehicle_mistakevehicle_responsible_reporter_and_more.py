# Generated by Django 4.1.6 on 2023-02-19 23:01

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("main", "0003_alter_vehicle_completion_date_and_more"),
    ]

    operations = [
        migrations.CreateModel(
            name="CriminalVehicle",
            fields=[
                (
                    "vehicle_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="main.vehicle",
                    ),
                ),
                ("top_secret", models.BooleanField(default=False)),
                ("police_data", models.JSONField(default=dict)),
            ],
            bases=("main.vehicle",),
        ),
        migrations.CreateModel(
            name="MistakeVehicle",
            fields=[
                (
                    "vehicle_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="main.vehicle",
                    ),
                ),
                ("description", models.TextField()),
            ],
            bases=("main.vehicle",),
        ),
        migrations.CreateModel(
            name="Responsible",
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
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(max_length=50)),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="Reporter",
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
                ("name", models.CharField(max_length=255)),
                ("phone", models.CharField(max_length=50)),
                (
                    "reports",
                    models.ManyToManyField(related_name="reporters", to="main.vehicle"),
                ),
            ],
            options={
                "abstract": False,
            },
        ),
        migrations.CreateModel(
            name="RepeatedVehicle",
            fields=[
                (
                    "vehicle_ptr",
                    models.OneToOneField(
                        auto_created=True,
                        on_delete=django.db.models.deletion.CASCADE,
                        parent_link=True,
                        primary_key=True,
                        serialize=False,
                        to="main.vehicle",
                    ),
                ),
                (
                    "previous_event",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="next_event",
                        to="main.vehicle",
                    ),
                ),
            ],
            bases=("main.vehicle",),
        ),
        migrations.CreateModel(
            name="Comment",
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
                ("name", models.CharField(max_length=255)),
                ("text", models.TextField()),
                (
                    "vehicle",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="main.vehicle"
                    ),
                ),
            ],
        ),
        migrations.AddField(
            model_name="vehicle",
            name="responsible",
            field=models.ForeignKey(
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                to="main.responsible",
            ),
        ),
    ]