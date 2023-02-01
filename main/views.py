from django.conf import settings
from django.contrib.gis.geos import Point, Polygon
from django.db import connection

from rest_framework.generics import ListAPIView
from rest_framework.response import Response

from django_filters import rest_framework as filters
from drf_spectacular.utils import (
    OpenApiExample,
    OpenApiParameter,
    extend_schema,
    extend_schema_view,
)
from silk.profiling.profiler import silk_profile

from main.filters import VehicleFilter
from main.models import Vehicle
from main.serializers import (
    MapVehicleSerializer,
    VehicleForJSSerializer,
    VehicleSerializer,
)

map_schema = extend_schema(
    parameters=[
        OpenApiParameter(
            "min_lat",
            float,
            location=OpenApiParameter.QUERY,
            description="Southern map border",
        ),
        OpenApiParameter(
            "min_lon",
            float,
            location=OpenApiParameter.QUERY,
            description="Western map border",
        ),
        OpenApiParameter(
            "max_lat",
            float,
            location=OpenApiParameter.QUERY,
            description="Northern map border",
        ),
        OpenApiParameter(
            "max_lon",
            float,
            location=OpenApiParameter.QUERY,
            description="Eastern map border",
        ),
    ],
)

map_example = OpenApiExample(
    "200",
    value=[
        {
            "cluster": 0,
            "count": 1,
            "vehicle_color": "Blue",
            "vehicle_make": "Bmw",
            "creation_date": "2020-10-10",
            "completion_date": "2020-10-20",
            "type_of_service_request": "",
            "location": {
                "type": "Point",
                "coordinates": [-87.6201462045411, 41.76176131522946],
            },
        },
        {
            "cluster": 1,
            "ads_count": 3203,
            "location": {
                "type": "Point",
                "coordinates": [-87.5201462045411, 41.86176131522946],
            },
        },
    ],
    response_only=True,
    status_codes=["200"],
)


class VehicleListView(ListAPIView):
    """Paginated list view for showing all."""

    serializer_class = VehicleSerializer
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = VehicleFilter
    queryset = Vehicle.objects.all()


class BaseMapListView(ListAPIView):
    queryset = Vehicle.objects.all()
    filter_backends = [filters.DjangoFilterBackend]
    filterset_class = VehicleFilter

    # Map options for filtering and clustering
    polygon = None
    max_distance_between_objects = None
    grid_cell_size = None

    def set_map_options(self, request):
        # Here we assume that all points will be in one western hemisphere
        # In real project here we should also check 180 degrees
        # to avoid problems when borders are in different hemispheres
        max_lat = float(request.query_params.get("max_lat", 180))
        min_lat = float(request.query_params.get("min_lat", -180))
        max_lon = float(request.query_params.get("max_lon", 90))
        min_lon = float(request.query_params.get("min_lon", -90))
        self.polygon = Polygon(
            [
                (min_lon, min_lat),
                (min_lon, max_lat),
                (max_lon, max_lat),
                (max_lon, min_lat),
                (min_lon, min_lat),
            ],
            srid=4326,
        )
        self.max_distance_between_objects = (
            Point(max_lon, max_lat).distance(Point(min_lon, min_lat))
            / settings.MAP_MAX_OBJECTS_IN_LINE
        )
        self.grid_cell_size = (
            Point(max_lon, max_lat).distance(Point(min_lon, min_lat))
            / settings.MAP_GRID_CELL_COUNT
        )

    def get_queryset(self):
        self.set_map_options(self.request)
        queryset = super().get_queryset()
        queryset = self.filter_queryset(queryset)
        queryset = queryset.filter(
            location__isnull=False,
            location__coveredby=self.polygon,
        )
        return queryset


@extend_schema_view(
    list=extend_schema(
        examples=[map_example],
    ),
    get=map_schema,
)
class VehicleNotPaginatedListView(BaseMapListView):
    """Not paginated list view for js clustering"""

    serializer_class = VehicleForJSSerializer
    pagination_class = None

    @silk_profile(name="Not paginated list")
    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)


@extend_schema_view(
    list=extend_schema(
        examples=[map_example],
    ),
    get=map_schema,
)
class VehicleMapListView(BaseMapListView):
    """List for map, good for small items count.

    For example,
    http://localhost:8000/api/vehicles/map/?max_lat=41.85&max_lon=-87.6&min_lat=41.8491660012213&min_lon=-87.70814559957574&vehicle_make__icontains=Bmw
    """

    serializer_class = MapVehicleSerializer
    pagination_class = None
    queryset = Vehicle.objects.all()

    def get_map_query(self):
        return """
            -- Assign clusters for every record in the queryset according to its location and calculated distance
            WITH clustered_locations AS
            (SELECT ST_ClusterDBScan(location, {self.max_distance_between_objects}, 1) over() AS cluster,
                    vehicle_color,
                    vehicle_make,
                    creation_date,
                    completion_date,
                    type_of_service_request,
                    location
            FROM ({sql}) q1 ),
            -- Subquery count items count for every cluster in first subquery and calculate its center
                t1 AS
            (SELECT cluster,
                    avg(ST_X(location)) as lon,
                    avg(ST_Y(location)) as lat,
                    count(*) AS vehicles_count
            FROM clustered_locations
            GROUP BY cluster),
            -- Subquery selects 1st row for every cluster to add this data for rows with count=1
                t2 AS
            (SELECT DISTINCT ON (cluster) vehicle_color,
                                vehicle_make,
                                creation_date,
                                completion_date,
                                type_of_service_request,
                                location,
                                cluster
            FROM clustered_locations)
            -- Main query merge cluster data (location + items count) with additional information for clusters with one item only
            SELECT t1.*,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.vehicle_make
                    ELSE NULL
                END AS vehicle_make,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.vehicle_color
                    ELSE NULL
                END AS vehicle_color,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.creation_date
                    ELSE NULL
                END AS creation_date,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.completion_date
                    ELSE NULL
                END AS completion_date,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.type_of_service_request
                    ELSE NULL
                END AS type_of_service_request
            FROM t1
            INNER JOIN t2 ON t1.cluster=t2.cluster
        """

    def clusterize(self, queryset):
        query = queryset.values(
            "location",
            "vehicle_color",
            "vehicle_make",
            "creation_date",
            "completion_date",
            "type_of_service_request",
        ).query
        sql, params = query.sql_with_params()

        map_query = self.get_map_query().format(
            sql=sql,
            self=self,
        )
        with connection.cursor() as cursor:
            cursor.execute(map_query, params)
            columns = [col[0] for col in cursor.description]
            data = []
            for row in cursor.fetchall():
                data_item = dict(zip(columns, row))
                data_item["location"] = Point(
                    data_item.pop("lon"),
                    data_item.pop("lat"),
                )
                data.append(data_item)
        return data

    def list(self, request, *args, **kwargs):
        queryset = self.get_queryset()
        result_data = self.clusterize(queryset)
        serializer = self.serializer_class(result_data, many=True)
        return Response(serializer.data)


class VehicleMapLargeCountListView(VehicleMapListView):
    def get_map_query(self):
        return """
            -- Snap to grid every location in the database
            WITH rounded_locations AS
            (SELECT ST_SnapToGrid(location, {self.grid_cell_size}) AS grid_location,
                    vehicle_color,
                    vehicle_make,
                    creation_date,
                    completion_date,
                    type_of_service_request,
                    location
            FROM ({sql}) q1 ),
            -- Calculate clusters for every grid location in new subquery
                clusters_tmp AS
            (SELECT grid_location,
                    ST_ClusterDBScan(grid_location, {self.max_distance_between_objects}, 1) over() AS cluster
            FROM
                (SELECT DISTINCT grid_location
                FROM rounded_locations) grid_points ),
            -- Add clusters to snapped to grid items
                clustered_locations AS
            (SELECT rounded_locations.*,
                    clusters_tmp.cluster
            FROM rounded_locations
            INNER JOIN clusters_tmp ON clusters_tmp.grid_location = rounded_locations.grid_location),
                t1 AS
            (SELECT cluster,
                    avg(ST_X(location)) as lon,
                    avg(ST_Y(location)) as lat,
                    count(*) AS vehicles_count
            FROM clustered_locations
            GROUP BY cluster),
                t2 AS
            (SELECT DISTINCT ON (cluster) vehicle_color,
                                vehicle_make,
                                creation_date,
                                completion_date,
                                type_of_service_request,
                                location,
                                cluster
            FROM clustered_locations)
            -- Main query merges cluster data (location + items count) with additional information for clusters with one item only
            SELECT t1.*,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.vehicle_make
                    ELSE NULL
                END AS vehicle_make,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.vehicle_color
                    ELSE NULL
                END AS vehicle_color,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.creation_date
                    ELSE NULL
                END AS creation_date,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.completion_date
                    ELSE NULL
                END AS completion_date,
                CASE
                    WHEN t1.vehicles_count = 1 THEN t2.type_of_service_request
                    ELSE NULL
                END AS type_of_service_request
            FROM t1
            INNER JOIN t2 ON t1.cluster=t2.cluster
            """
