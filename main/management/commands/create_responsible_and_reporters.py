import random

from django.core.management import BaseCommand
from django.db.utils import IntegrityError

from faker import Faker

from main.models import Reporter, Responsible, Vehicle

fake = Faker()


class Command(BaseCommand):
    def handle(self, *args, **options):
        reporters = []
        responsibles = []
        for i in range(1000):
            reporters.append(
                Reporter(
                    name=fake.name(),
                    phone=fake.phone_number(),
                )
            )
            responsibles.append(
                Responsible(
                    name=fake.name(),
                    phone=fake.phone_number(),
                )
            )
        Reporter.objects.bulk_create(reporters)
        Responsible.objects.bulk_create(responsibles)

        while Vehicle.objects.filter(responsible__isnull=True).exists():
            vehicles_to_update = (
                Vehicle.objects.filter(responsible__isnull=True)
                .order_by("?")
                .values("id")[:1000]
            )
            Vehicle.objects.filter(id__in=vehicles_to_update).update(
                responsible=random.choice(responsibles)
            )
        vehicles = Vehicle.objects.order_by("?").only("id")[:1000]
        vehicle_reporters = [
            Reporter.reports.through(reporter=reporter, vehicle=vehicle)
            for reporter in reporters
            for vehicle in vehicles
        ]
        try:
            Reporter.reports.through.objects.bulk_create(
                vehicle_reporters,
                batch_size=1000,
            )
        except IntegrityError as e:
            print(e)
