from django.contrib import admin

from main.models import Vehicle


@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = [
        "service_request_number",
        "creation_date",
        "completion_date",
        "status",
        "type_of_service_request",
        "vehicle_make",
        "vehicle_color",
        "current_activity",
    ]
    list_filter = [
        "status",
        "vehicle_make",
    ]
