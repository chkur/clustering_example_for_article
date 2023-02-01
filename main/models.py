from django.contrib.gis.db.models import PointField
from django.db import models


class Vehicle(models.Model):
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
