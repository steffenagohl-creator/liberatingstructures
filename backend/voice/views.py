"""DRF-Endpunkte der Sprachkanäle (Stufe 1D, Fundament).

Zwei zustandslose Endpunkte (Datensparsamkeit – nichts wird gespeichert):

* ``GET  /api/voice/config/``  – welche Souveränitätsstufen die Installation anbietet.
* ``POST /api/voice/session/`` – startet eine Sprach-Sitzung: löst die Stufe auf
  (datensparsamer Fallback), erzeugt ein LiveKit-Zugangstoken und liefert den Bauplan.

Beide sind über drf-spectacular dokumentiert (sprechende ``operation_id``).
Die *eigentliche* Sprachverarbeitung passiert später im LiveKit-Agent-Worker (Phasen 3–5).
"""
import uuid

from drf_spectacular.utils import extend_schema
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from . import sovereignty, tokens
from .providers import factory
from .providers.base import VoiceError
from .serializers import (
    VoiceConfigResponseSerializer,
    VoiceSessionRequestSerializer,
    VoiceSessionResponseSerializer,
)


class VoiceConfigView(APIView):
    """Liste der verfügbaren Souveränitätsstufen (für den Souveränitäts-Screen der UI)."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="voice_config",
        summary="Verfügbare Sprach-Souveränitätsstufen abrufen",
        description=(
            "Gibt die drei Stufen (sov/eu/us) mit Selbstbeschreibung, Konfigurations-Status "
            "und gewähltem Bauplan zurück, plus die Standardstufe und ob der LiveKit-Transport "
            "bereit ist. Speichert nichts (zustandslos)."
        ),
        responses={200: VoiceConfigResponseSerializer},
    )
    def get(self, request):
        data = {
            "default_tier": sovereignty.DEFAULT_TIER,
            "livekit_ready": sovereignty.livekit_ready(),
            "tiers": sovereignty.available_tiers(),
        }
        return Response(data, status=status.HTTP_200_OK)


class VoiceSessionView(APIView):
    """Startet eine Sprach-Sitzung und liefert die Beitrittsdaten für LiveKit."""

    permission_classes = [AllowAny]

    @extend_schema(
        operation_id="voice_session",
        summary="Sprach-Sitzung starten (LiveKit-Token + Bauplan)",
        description=(
            "Nimmt die gewünschte Souveränitätsstufe entgegen und löst sie gegen die "
            "Konfiguration auf – dabei wird **nur Richtung mehr Souveränität** heruntergestuft "
            "(wer 'eu' wählt, landet nie bei 'us'). Erzeugt ein LiveKit-Zugangstoken (in Phase 1 "
            "ein klar markierter Stub) und gibt den je Stufe gewählten Bauplan zurück. "
            "Speichert nichts (zustandslos)."
        ),
        request=VoiceSessionRequestSerializer,
        responses={200: VoiceSessionResponseSerializer},
    )
    def post(self, request):
        serializer = VoiceSessionRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        resolved = sovereignty.resolve_tier(data.get("sovereignty"))
        room = data.get("room") or f"ls-{uuid.uuid4().hex[:12]}"
        identity = data.get("identity") or f"gast-{uuid.uuid4().hex[:8]}"

        try:
            plan = factory.plan_for_tier(resolved.effective)
            token = tokens.issue_token(room=room, identity=identity, tier=resolved.effective)
        except VoiceError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)

        hinweis = ""
        if not resolved.configured:
            hinweis = (
                "Diese Stufe ist in dieser Installation noch nicht voll einsatzbereit "
                "(Schlüssel/Transport fehlen). Token ist ein Stub."
            )

        payload = {
            "requested_tier": resolved.requested,
            "effective_tier": resolved.effective,
            "fell_back": resolved.fell_back,
            "configured": resolved.configured,
            "livekit_url": token.livekit_url,
            "room": room,
            "identity": identity,
            "token": token.token,
            "token_is_stub": token.is_stub,
            "plan": plan.to_dict(),
            "hinweis": hinweis,
        }
        return Response(payload, status=status.HTTP_200_OK)
