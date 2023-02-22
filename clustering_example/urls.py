"""clustering_example URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.conf import settings
from django.contrib import admin
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
from django.urls import include, path

from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularRedocView,
    SpectacularSwaggerView,
)

from main.views import (
    VehicleListView,
    VehicleMapLargeCountListView,
    VehicleMapListView,
    VehicleNotPaginatedListView,
)

urlpatterns = [
    path("admin/", admin.site.urls),
    path(
        "api/vehicles/",
        VehicleListView.as_view(),
    ),
    path(
        "api/vehicles/js_clustering/",
        VehicleNotPaginatedListView.as_view(),
    ),
    path(
        "api/vehicles/map/",
        VehicleMapListView.as_view(),
    ),
    path(
        "api/vehicles/map_fast/",
        VehicleMapLargeCountListView.as_view(),
    ),
    path(
        "api/doc/schema/",
        SpectacularAPIView.as_view(),
        name="schema",
    ),
    path(
        "api/doc/swagger/",
        SpectacularSwaggerView.as_view(url_name="schema"),
        name="swagger-ui",
    ),
    path(
        "api/doc/redoc/",
        SpectacularRedocView.as_view(url_name="schema"),
        name="redoc",
    ),
]
urlpatterns += staticfiles_urlpatterns()
if settings.DEBUG:
    urlpatterns += [path("silk/", include("silk.urls", namespace="silk"))]
