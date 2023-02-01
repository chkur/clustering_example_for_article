from datetime import date
from random import uniform

from django.contrib.gis.geos import Point

from rest_framework.test import APITestCase

from ddf import G

from .models import Vehicle


class GeoTestCase(APITestCase):
    def setUp(self) -> None:
        def new_vehicles(
            min_lon,
            min_lat,
            vehicle_make="audi",
            dt=None,
            count=10,
        ):
            for i in range(count):
                G(
                    Vehicle,
                    location=Point(
                        uniform(min_lon, min_lon + 0.1),
                        uniform(min_lat, min_lat + 0.1),
                    ),
                    vehicle_make=vehicle_make,
                    completion_date=dt,
                )

        new_vehicles(39, 39, dt=date(2020, 1, 1))
        new_vehicles(40, 40, dt=date(2020, 1, 1))
        new_vehicles(40, 40, dt=date(2022, 1, 1))
        new_vehicles(40, 40, "bmw", dt=date(2022, 1, 1))
        new_vehicles(41, 41, dt=date(2020, 1, 1))

    def test_map_all(self):
        """Test all map without filtering.

        Here will be just 1 cluster with all vehicles"""

        result = self.client.get("/api/vehicles/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(result.json()["count"], 50)

        result = self.client.get("/api/vehicles/js_clustering/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()), 50)

        result = self.client.get("/api/vehicles/map/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()), 1)
        self.assertEqual(result.json()[0]["vehicles_count"], 50)

        result = self.client.get("/api/vehicles/map_fast/")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()), 1)
        self.assertEqual(result.json()[0]["vehicles_count"], 50)

    def test_map_filter1(self):
        """Test map with filtering #1

        As we take random values for map - it's not known how many clusters will be created
        But in common case clusters count in slow endpoint must match clusters count in faster endpoint"""

        filter_condition = "?vehicle_make__icontains=audi&min_lat=40&max_lat=40.1&min_lon=40&max_lon=40.1"
        result = self.client.get(f"/api/vehicles/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        # This endpoint doesn't use map filtering
        self.assertEqual(result.json()["count"], 40)

        result = self.client.get(f"/api/vehicles/js_clustering/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()), 20)

        result = self.client.get(f"/api/vehicles/map/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(sum(i["vehicles_count"] for i in result.json()), 20)

        clusters_count1 = len(result.json())

        result = self.client.get(f"/api/vehicles/map_fast/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(sum(i["vehicles_count"] for i in result.json()), 20)

        clusters_count2 = len(result.json())

        self.assertAlmostEqual(clusters_count1, clusters_count2, delta=1)

    def test_map_filter2(self):
        """Test map with filtering #2"""

        filter_condition = "?vehicle_make__icontains=audi&min_lat=40&max_lat=40.1&min_lon=40&max_lon=40.1&completion_date__lt=2021-01-01"
        result = self.client.get(f"/api/vehicles/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        # This endpoint doesn't use map filtering
        self.assertEqual(result.json()["count"], 30)

        result = self.client.get(f"/api/vehicles/js_clustering/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(len(result.json()), 10)

        result = self.client.get(f"/api/vehicles/map/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(sum(i["vehicles_count"] for i in result.json()), 10)

        clusters_count1 = len(result.json())

        result = self.client.get(f"/api/vehicles/map_fast/{filter_condition}")
        self.assertEqual(result.status_code, 200)
        self.assertEqual(sum(i["vehicles_count"] for i in result.json()), 10)

        clusters_count2 = len(result.json())

        self.assertAlmostEqual(clusters_count1, clusters_count2, delta=1)
