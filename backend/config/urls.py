from django.conf import settings
from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView
from rest_framework.permissions import AllowAny

from .health import health

urlpatterns = [
    path(settings.ADMIN_URL, admin.site.urls),
    path("api/v1/health/", health, name="health"),
]

if settings.DEBUG:
    urlpatterns += [
        path(
            "api/v1/schema/",
            SpectacularAPIView.as_view(permission_classes=[AllowAny], authentication_classes=[]),
            name="schema",
        )
    ]
