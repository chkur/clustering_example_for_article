import random

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from faker import Faker

from main.models import MistakeVehicle, Vehicle

fake = Faker()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Randomly create mistake vehicles
        mistake_vehicles = Vehicle.objects.exclude(
            criminalvehicle__isnull=False
        ).order_by("?")[:500]
        for global_num, vehicle in enumerate(mistake_vehicles, 1):
            vehicle.__class__ = MistakeVehicle
            vehicle.description = fake.text()
            vehicle.vehicle_ptr_id = vehicle

            try:
                vehicle.save()
            except IntegrityError:
                # if already exist
                pass
            print(f"Create mistake vehicle {global_num} of {len(mistake_vehicles)}")
