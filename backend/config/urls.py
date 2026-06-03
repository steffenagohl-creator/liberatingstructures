"""URL-Konfiguration des LS-Matchmaker-Backends.

Admin + OpenAPI-Doku + die fachlichen AP3-Endpunkte (Interview, Matchmaking)
unter ``/api/``.
"""
from django.contrib import admin
from django.urls import include, path
from drf_spectacular.views import SpectacularAPIView, SpectacularSwaggerView

urlpatterns = [
    path("admin/", admin.site.urls),
    # OpenAPI-Schema + interaktive Doku
    path("api/schema/", SpectacularAPIView.as_view(), name="schema"),
    path("api/docs/", SpectacularSwaggerView.as_view(url_name="schema"), name="docs"),
    # Fachliche Endpunkte (AP3): /api/interview/, /api/match/
    path("api/", include("matchmaker.urls")),
]
