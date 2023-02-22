from django.db.utils import IntegrityError
from django.contrib.postgres import aggregates
from django.core.management import BaseCommand
from django.db.models import Count

from main.models import Vehicle, RepeatedVehicle


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Assume that vehicles with the same color and manufacturer
        # which are repeated from 2 to 5 times are "RepeatedVehicle"
        repeated_vehicles = (
            Vehicle.objects.values("vehicle_make", "vehicle_color")
            .annotate(
                count=Count("id"),
                ids=aggregates.ArrayAgg("id"),
            )
            .filter(count__range=[2, 5])
        )
        for global_num, item in enumerate(repeated_vehicles, 1):
            for num, item_id in enumerate(item["ids"][1:], 1):
                vehicle = Vehicle.objects.get(id=item_id)
                vehicle.__class__ = RepeatedVehicle
                vehicle.vehicle_ptr_id = item_id
                vehicle.previous_event_id = item["ids"][num - 1]

                try:
                    vehicle.save()
                except IntegrityError:
                    # if already exist
                    pass
                print(
                    f"Create repeated vehicle {global_num} of {len(repeated_vehicles)}"
                )
