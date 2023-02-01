from rest_framework import serializers
from rest_framework_gis.serializers import GeometrySerializerMethodField
from main.models import Vehicle


class VehicleSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        exclude = ["id"]


class VehicleForJSSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vehicle
        fields = [
            "vehicle_make",
            "vehicle_make",
            "vehicle_color",
            "creation_date",
            "completion_date",
            "type_of_service_request",
            "location",
        ]


class MapVehicleSerializer(serializers.Serializer):
    cluster = serializers.IntegerField()
    vehicles_count = serializers.IntegerField()
    vehicle_make = serializers.CharField()
    vehicle_color = serializers.CharField()
    creation_date = serializers.DateField()
    completion_date = serializers.DateField()
    type_of_service_request = serializers.CharField()
    location = GeometrySerializerMethodField()

    def get_location(self, obj):
        return obj["location"]
