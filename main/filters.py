from django.contrib.gis.geos import Polygon

from django_filters import rest_framework as filters

from main.models import Vehicle


class VehicleFilter(filters.FilterSet):
    class Meta:
        model = Vehicle
        fields = {
            "creation_date": ["lt", "gt", "exact"],
            "completion_date": ["lt", "gt", "exact"],
            "vehicle_make": ["icontains"],
            "vehicle_color": ["exact"],
            "status": ["exact"],
        }
