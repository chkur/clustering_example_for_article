from django.contrib.gis.db.models import PointField
from django.db import models

# from psqlextra.types import PostgresPartitioningMethod
# from psqlextra.models import PostgresPartitionedModel
from model_utils.managers import InheritanceManager


class Vehicle(models.Model):
    custom_partitioned = {
        "column": "id",
        "size": 100000,
    }

    creation_date = models.DateField(
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        null=True,
        blank=True,
    )
    completion_date = models.DateField(
        null=True,
        blank=True,
        db_index=True,
    )
    service_request_number = models.CharField(
        max_length=50,
        db_index=True,
    )
    type_of_service_request = models.CharField(max_length=255)
    license_plate = models.CharField(
        max_length=1000,
        null=True,
        blank=True,
    )
    vehicle_make = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        db_index=True,
    )
    vehicle_color = models.CharField(
        max_length=250,
        null=True,
        blank=True,
        db_index=True,
    )
    current_activity = models.CharField(
        max_length=250,
        null=True,
        blank=True,
    )
    most_recent_action = models.CharField(
        max_length=250,
        null=True,
        blank=True,
    )
    days_parked = models.BigIntegerField(
        null=True,
        blank=True,
    )
    street_address = models.CharField(
        max_length=250,
        null=True,
        blank=True,
    )
    zip_code = models.CharField(
        max_length=10,
        null=True,
        blank=True,
    )
    x_coordinate = models.FloatField(
        null=True,
        blank=True,
    )
    y_coordinate = models.FloatField(
        null=True,
        blank=True,
    )
    ward = models.IntegerField(
        null=True,
        blank=True,
    )
    police_district = models.IntegerField(
        null=True,
        blank=True,
    )
    community_area = models.IntegerField(
        null=True,
        blank=True,
    )
    ssa = models.IntegerField(
        null=True,
        blank=True,
    )
    latitude = models.FloatField(
        null=True,
        blank=True,
    )
    longitude = models.FloatField(
        null=True,
        blank=True,
    )
    location = PointField(
        null=True,
        blank=True,
    )
    responsible = models.ForeignKey(
        "Responsible",
        null=True,
        on_delete=models.SET_NULL,
    )
    objects = InheritanceManager()


class CriminalVehicle(Vehicle):
    custom_partitioned = {
        "column": "vehicle_ptr_id",
        "size": 100000,
    }
    top_secret = models.BooleanField(default=False)
    police_data = models.JSONField(default=dict)


class MistakeVehicle(Vehicle):
    custom_partitioned = False

    description = models.TextField()


class RepeatedVehicle(Vehicle):
    custom_partitioned = False

    previous_event = models.OneToOneField(
        "Vehicle",
        related_name="next_event",
        on_delete=models.PROTECT,
    )


class Person(models.Model):
    name = models.CharField(max_length=255)
    phone = models.CharField(max_length=50)

    class Meta:
        abstract = True


class Responsible(Person):
    ...


class Reporter(Person):
    reports = models.ManyToManyField(
        "Vehicle",
        related_name="reporters",
    )


class Comment(models.Model):
    custom_partitioned = {
        "column": "vehicle_id",
        "size": 100000,
    }
    vehicle = models.ForeignKey(
        "Vehicle",
        on_delete=models.CASCADE,
    )
    name = models.CharField(max_length=255)
    text = models.TextField()
