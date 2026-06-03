"""DRF-Endpunkte des LS-Matchmaker (AP3).

Zwei zustandslose Endpunkte (keine Persistenz der Situationsdaten – Datensparsamkeit):

* ``POST /api/interview/`` – Freitext → strukturierte Diagnose + Rückfragen.
* ``POST /api/match/``     – Diagnose → validierter, begründeter String.

Beide sind über drf-spectacular dokumentiert (sprechende ``operation_id``).
"""
from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import services
from .llm import LLMError
from .serializers import (
    InterviewRequestSerializer,
    InterviewResponseSerializer,
    MatchRequestSerializer,
    MatchResponseSerializer,
)


class InterviewView(APIView):
    """Adaptiver Interview-Schritt: erhebt aus Freitext die strukturierte Diagnose."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="matchmaker_interview",
        summary="Diagnose aus Situationsbeschreibung erheben",
        description=(
            "Nimmt eine in Alltagssprache geschilderte Situation (plus bereits gegebene "
            "Antworten) entgegen und liefert die strukturierte Diagnose, offene Rückfragen "
            "und ein ready-Flag. Speichert nichts (zustandslos)."
        ),
        request=InterviewRequestSerializer,
        responses={200: InterviewResponseSerializer},
    )
    def post(self, request):
        serializer = InterviewRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data
        try:
            result = services.run_interview(data["situation"], data.get("answers"))
        except LLMError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result, status=status.HTTP_200_OK)


class MatchView(APIView):
    """Matchmaking: erzeugt aus der Diagnose einen validierten, begründeten String."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="matchmaker_match",
        summary="Validierten LS-String vorschlagen",
        description=(
            "Nimmt eine Diagnose entgegen und liefert einen begründeten String aus "
            "Liberating Structures. Ablauf: deterministische Vorfilterung → "
            "LLM-Sequenzierung → Quality Gate (Korrekturschleife). Der Qualitäts-Status "
            "ist transparent im Feld quality enthalten. Speichert nichts (zustandslos)."
        ),
        request=MatchRequestSerializer,
        responses={200: MatchResponseSerializer},
    )
    def post(self, request):
        serializer = MatchRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        diagnose = serializer.validated_data["diagnose"]
        try:
            result = services.match(diagnose)
        except LLMError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_502_BAD_GATEWAY)
        return Response(result, status=status.HTTP_200_OK)
