import random

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from faker import Faker

from main.models import CriminalVehicle, Vehicle

fake = Faker()


class Command(BaseCommand):
    def handle(self, *args, **options):
        # Randomly create criminal vehicles
        criminal_vehicles = Vehicle.objects.order_by("?")[:5000]
        for global_num, vehicle in enumerate(criminal_vehicles, 1):
            vehicle.__class__ = CriminalVehicle
            vehicle.police_data = {"event": fake.text()}
            vehicle.top_secret = random.choice([True, False])
            vehicle.vehicle_ptr_id = vehicle

            try:
                vehicle.save()
            except IntegrityError:
                # if already exist
                pass
            print(f"Create criminal vehicle {global_num} of {len(criminal_vehicles)}")
