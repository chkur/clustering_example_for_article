import os
from datetime import datetime

from django.contrib.gis.geos import Point
from django.core.management import BaseCommand

import httpx
import numpy as np
import pandas as pd

from main.models import Vehicle


EXAMPLE_FILE_PATH = "files/example.csv"
EXAMPLE_FILE_URL = (
    "https://data.cityofchicago.org/api/views/3c9v-pnva/rows.csv?accessType=DOWNLOAD"
)


class Command(BaseCommand):
    def parse_date(self, dt):
        if dt:
            return datetime.strptime(dt, "%m/%d/%Y")

    def handle(self, *args, **options):
        if not os.path.exists(EXAMPLE_FILE_PATH):
            print("We have to download example csv file from Chicago City Data Portal.")
            print(
                f"Later you can find it at path {EXAMPLE_FILE_PATH} inside project folder."
            )
            print(f"URL: {EXAMPLE_FILE_URL}\n")
            with open(EXAMPLE_FILE_PATH + ".part", "wb") as download_file:
                with httpx.stream("GET", EXAMPLE_FILE_URL) as response:
                    num_bytes_downloaded = response.num_bytes_downloaded
                    for chunk in response.iter_bytes():
                        download_file.write(chunk)
                        num_bytes_downloaded = response.num_bytes_downloaded
                        print(f"\rDownloaded {num_bytes_downloaded} bytes", end="")
            os.rename(EXAMPLE_FILE_PATH + ".part", EXAMPLE_FILE_PATH)

        df = pd.read_csv(EXAMPLE_FILE_PATH)
        df_correct = df.replace({np.nan: None})
        for index, row in df_correct.iterrows():
            print(row)
            Vehicle.objects.get_or_create(
                creation_date=self.parse_date(row["Creation Date"]),
                status=row["Status"],
                completion_date=self.parse_date(row["Completion Date"]),
                service_request_number=row["Service Request Number"],
                type_of_service_request=row["Type of Service Request"],
                license_plate=row["License Plate"],
                vehicle_make=row["Vehicle Make/Model"],
                vehicle_color=row["Vehicle Color"],
                current_activity=row["Current Activity"],
                most_recent_action=row["Most Recent Action"],
                days_parked=row[
                    "How Many Days Has the Vehicle Been Reported as Parked?"
                ],
                street_address=row["Street Address"],
                zip_code=row["ZIP Code"],
                x_coordinate=row["X Coordinate"],
                y_coordinate=row["Y Coordinate"],
                ward=row["Ward"],
                police_district=row["Police District"],
                community_area=row["Community Area"],
                ssa=row["SSA"],
                latitude=row["Latitude"],
                longitude=row["Longitude"],
                location=Point(row["Longitude"], row["Latitude"])
                if row["Location"]
                else None,
            )
