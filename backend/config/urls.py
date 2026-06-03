"""URL-Konfiguration des LS-Matchmaker-Backends.

In AP2 nur Admin + OpenAPI-Gerüst. Die fachlichen Endpunkte (Interview, Matchmaking)
folgen in AP3 und werden dann hier eingebunden.
"""
from django.contrib import admin
from django.urls import path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI-Schema + interaktive Doku (für AP3-Endpunkte vorbereitet)
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
]
