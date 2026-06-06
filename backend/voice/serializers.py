"""DRF-Serializer der Sprachkanäle.

Validieren die Eingaben **und** beschreiben Request/Response für die OpenAPI-Doku
(`/api/docs/`) – damit die Endpunkte für Menschen, KIs/MCP und Crawler selbsterklärend
sind (Barrierefreiheits-/Selbstbeschreibungs-Leitprinzip).
"""
from rest_framework import serializers


# -- Provider/Plan (Selbstbeschreibung der gewählten Sprach-Bausteine) ------- #
class VoiceProviderSerializer(serializers.Serializer):
    """Ein selbstbeschreibender Sprach-Baustein (STT/TTS/LLM/Realtime)."""

    id = serializers.CharField(help_text="Stabiler Bezeichner, z. B. voxtral-mistral.")
    label = serializers.CharField(help_text="Lesbarer Name (UI/Screenreader).")
    region = serializers.CharField(help_text="Wohin Daten gehen: lokal | eu | us.")
    kind = serializers.CharField(help_text="stt | tts | llm | realtime.")
    open_weights = serializers.BooleanField(help_text="Offene Gewichte (selbst hostbar)?")
    notes = serializers.CharField(required=False, allow_blank=True, help_text="Kurzbeschreibung.")
    configured = serializers.BooleanField(
        required=False, help_text="Sind die nötigen Schlüssel/ENV gesetzt?",
    )


class VoicePlanSerializer(serializers.Serializer):
    """Der je Stufe aufgelöste Bauplan: Pipeline (stt+llm+tts) **oder** ein realtime-Anbieter."""

    tier = serializers.CharField(help_text="Souveränitätsstufe: sov | eu | us.")
    mode = serializers.CharField(help_text="pipeline | realtime.")
    stt = VoiceProviderSerializer(allow_null=True, required=False)
    llm = VoiceProviderSerializer(allow_null=True, required=False)
    tts = VoiceProviderSerializer(allow_null=True, required=False)
    realtime = VoiceProviderSerializer(allow_null=True, required=False)


# -- /api/voice/config/ ----------------------------------------------------- #
class VoiceTierSerializer(serializers.Serializer):
    """Eine Souveränitätsstufe inkl. Status und Bauplan."""

    id = serializers.CharField(help_text="sov | eu | us.")
    flag = serializers.CharField(help_text="Flaggen-Emoji der Stufe.")
    label = serializers.CharField(help_text="Kurzname der Stufe.")
    region = serializers.CharField(help_text="lokal | eu | us.")
    description = serializers.CharField(help_text="Was die Wahl bedeutet (für die UI).")
    configured = serializers.BooleanField(help_text="In dieser Installation tatsächlich nutzbar?")
    plan = VoicePlanSerializer()


class VoiceConfigResponseSerializer(serializers.Serializer):
    """Antwort von ``/api/voice/config/``: welche Stufen die Installation anbietet."""

    default_tier = serializers.CharField(help_text="Vorausgewählte Stufe (Standard: eu).")
    livekit_ready = serializers.BooleanField(help_text="Ist der LiveKit-Transport konfiguriert?")
    tiers = VoiceTierSerializer(many=True)


# -- /api/voice/session/ ---------------------------------------------------- #
class VoiceSessionRequestSerializer(serializers.Serializer):
    """Eingabe für den Sitzungs-Start: gewünschte Stufe (+ optionaler Raum/Identität)."""

    sovereignty = serializers.CharField(
        required=False, allow_blank=True, default="eu",
        help_text="Gewünschte Souveränitätsstufe: sov | eu | us. Unbekanntes → eu.",
    )
    room = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Optionaler Raumname. Leer → Server vergibt einen.",
    )
    identity = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Optionale Teilnehmer-Identität. Leer → Server vergibt eine.",
    )


class VoiceSessionResponseSerializer(serializers.Serializer):
    """Antwort des Sitzungs-Starts: Beitrittsdaten + aufgelöste Stufe + Bauplan."""

    requested_tier = serializers.CharField(help_text="Die angefragte Stufe (normalisiert).")
    effective_tier = serializers.CharField(help_text="Die tatsächlich genutzte Stufe.")
    fell_back = serializers.BooleanField(
        help_text="True, wenn datensparsam auf eine souveränere Stufe heruntergestuft wurde.",
    )
    configured = serializers.BooleanField(
        help_text="Ist die effektive Stufe wirklich einsatzbereit (Schlüssel/Stack vorhanden)?",
    )
    livekit_url = serializers.CharField(
        allow_blank=True, help_text="WebSocket-URL des LiveKit-Servers (leer bis Phase 2).",
    )
    room = serializers.CharField(help_text="Der Raumname.")
    identity = serializers.CharField(help_text="Die Teilnehmer-Identität.")
    token = serializers.CharField(help_text="Zugangstoken (in Phase 1 ein Stub).")
    token_is_stub = serializers.BooleanField(
        help_text="True, solange nur der Stub-Signer aktiv ist (kein echtes LiveKit-Token).",
    )
    plan = VoicePlanSerializer()
    hinweis = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Klartext-Hinweis, falls die Stufe nicht voll einsatzbereit ist.",
    )
