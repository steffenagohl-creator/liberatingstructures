"""URL-Routen der Katalog-App (read-only Struktur-Endpunkte, eingebunden unter ``/api/``)."""
from django.urls import path

from .views import StructureDetailView, StructureListView

urlpatterns = [
    path("structures/", StructureListView.as_view(), name="structures-list"),
    path("structures/<slug:slug>/", StructureDetailView.as_view(), name="structures-detail"),
]
