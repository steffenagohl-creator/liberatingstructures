"""Öffentliche, read-only Katalog-Endpunkte (für AP4-App, KIs/MCP und Crawler).

* ``GET /api/structures/``        – Liste aller Strukturen (Filter optional).
* ``GET /api/structures/<slug>/`` – eine einzelne Struktur per Slug.

Die Sprache wird über ``?lang=de|en`` gesteuert (Default Deutsch). Alle Endpunkte
sind über drf-spectacular mit sprechender ``operation_id`` dokumentiert, damit sie
für Maschinen eindeutig identifizierbar und konsumierbar sind (Leitprinzip).
"""
from drf_spectacular.utils import OpenApiParameter, OpenApiResponse, extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import constants
from .i18n import SUPPORTED_LANGS, normalize_lang
from .models import Structure
from .serializers import StructureSerializer

_LANG_PARAM = OpenApiParameter(
    name="lang", type=str, location=OpenApiParameter.QUERY, enum=list(SUPPORTED_LANGS),
    description="Antwortsprache (de | en). Default: de. Unbekannte Werte fallen auf de zurück.",
)
_EDITION_PARAM = OpenApiParameter(
    name="edition", type=str, location=OpenApiParameter.QUERY, enum=constants.EDITIONS,
    description="Optionaler Filter: original (die 33 Kern-LS) oder extended (alle 43).",
)
_PURPOSE_PARAM = OpenApiParameter(
    name="purpose_tag", type=str, location=OpenApiParameter.QUERY, enum=constants.PURPOSE_TAGS,
    description="Optionaler Filter auf eine Zweck-Kategorie (offenlegen, teilen, …).",
)


class StructureListView(APIView):
    """Liste aller Liberating Structures, sprachaufgelöst und filterbar."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="catalog_structures_list",
        summary="Alle Liberating Structures auflisten",
        description=(
            "Liefert den vollständigen Katalog der Liberating Structures in der gewählten "
            "Sprache (?lang=de|en). Optional filterbar nach edition und purpose_tag. "
            "Read-only, speichert nichts. Sortiert nach structure_id."
        ),
        parameters=[_LANG_PARAM, _EDITION_PARAM, _PURPOSE_PARAM],
        responses={200: StructureSerializer(many=True)},
    )
    def get(self, request):
        lang = normalize_lang(request.query_params.get("lang"))
        qs = Structure.objects.all()
        edition = request.query_params.get("edition")
        if edition in constants.EDITIONS:
            qs = qs.filter(edition=edition)
        purpose_tag = request.query_params.get("purpose_tag")
        if purpose_tag in constants.PURPOSE_TAGS:
            qs = qs.filter(purpose_tags__contains=[purpose_tag])
        data = StructureSerializer(qs, many=True, context={"lang": lang}).data
        return Response(data, status=status.HTTP_200_OK)


class StructureDetailView(APIView):
    """Eine einzelne Liberating Structure per Slug, sprachaufgelöst."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="catalog_structure_detail",
        summary="Eine Liberating Structure per Slug abrufen",
        description=(
            "Liefert eine einzelne Struktur (inkl. vollem Guide) in der gewählten Sprache "
            "(?lang=de|en). Read-only. 404, wenn der Slug nicht existiert."
        ),
        parameters=[_LANG_PARAM],
        responses={
            200: StructureSerializer,
            404: OpenApiResponse(description="Keine Struktur mit diesem Slug."),
        },
    )
    def get(self, request, slug):
        lang = normalize_lang(request.query_params.get("lang"))
        structure = Structure.objects.filter(slug=slug).first()
        if structure is None:
            return Response(
                {"detail": f"Keine Struktur mit Slug „{slug}“."},
                status=status.HTTP_404_NOT_FOUND,
            )
        data = StructureSerializer(structure, context={"lang": lang}).data
        return Response(data, status=status.HTTP_200_OK)
