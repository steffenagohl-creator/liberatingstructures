"""Provider-agnostisches Abstraktions-Layer für die Sprachkanäle.

Analog zu ``matchmaker/llm/base.py``: Das übrige Backend spricht **nur** über diese
selbstbeschreibenden Bausteine, nie über einen konkreten Anbieter. Welcher Provider je
Souveränitätsstufe gewählt wird, entscheidet ``factory.plan_for_tier`` (gespeist aus
``voice/sovereignty.py``) – ausschließlich über die Stufe + ENV.

**Wichtig:** Die *eigentlichen* Sprach-Engines (Voxtral-STT, Mistral-LLM, Voxtral-/Piper-TTS,
OpenAI-Realtime) laufen später im **LiveKit-Agent-Worker** (eigener Container, Phasen 3–5).
Hier im Django-Backend stehen nur die **Metadaten**, die Session-Endpunkt und UI brauchen:
welcher Baustein, in welcher Region, mit welchen offenen Gewichten, und ob er konfiguriert ist.
"""
from __future__ import annotations

from dataclasses import dataclass, field


class VoiceError(RuntimeError):
    """Fehler in der Sprachkanal-Schicht (Konfiguration, Token, Provider-Auswahl)."""


# Region eines Bausteins – wohin die Daten zur Verarbeitung gehen (Souveränität).
REGION_LOKAL = "lokal"   # eigener Server/VPS, nichts verlässt die Maschine
REGION_EU = "eu"         # EU-Dienstleister (z. B. Mistral, Paris)
REGION_US = "us"         # außerhalb der EU erlaubt (z. B. OpenAI)


@dataclass(frozen=True)
class VoiceProvider:
    """Selbstbeschreibender Sprach-Baustein (Metadaten, kein Live-Code).

    :param id: stabiler, sprechender Bezeichner (z. B. ``voxtral-mistral``).
    :param label: für Menschen lesbarer Name (UI/Screenreader).
    :param region: ``lokal`` | ``eu`` | ``us`` – wohin die Daten gehen.
    :param kind: ``stt`` | ``tts`` | ``llm`` | ``realtime``.
    :param requires_env: ENV-Variablen, die gesetzt sein müssen, damit der Baustein
        tatsächlich nutzbar ist (z. B. ``("LLM_API_KEY",)`` für Mistral). Leer = immer nutzbar.
    :param open_weights: ob das Modell offene Gewichte hat (für die ``sov``-Stufe selbst hostbar).
    :param notes: kurze, dokumentierende Beschreibung (Selbstbeschreibungs-Leitprinzip).
    """

    id: str
    label: str
    region: str
    kind: str = "generic"
    requires_env: tuple[str, ...] = ()
    open_weights: bool = False
    notes: str = ""

    def is_configured(self, settings) -> bool:
        """True, wenn alle benötigten ENV-Variablen in ``settings`` gesetzt (truthy) sind."""
        return all(getattr(settings, key, "") for key in self.requires_env)

    def to_dict(self, settings=None) -> dict:
        """Serialisierbare Selbstbeschreibung (für API/OpenAPI)."""
        data = {
            "id": self.id,
            "label": self.label,
            "region": self.region,
            "kind": self.kind,
            "open_weights": self.open_weights,
            "notes": self.notes,
        }
        if settings is not None:
            data["configured"] = self.is_configured(settings)
        return data


# -- Typ-spezifische Marker-Unterklassen (fixieren ``kind``, reine Selbstbeschreibung) ------ #
@dataclass(frozen=True)
class SttProvider(VoiceProvider):
    """Sprache → Text (Speech-to-Text)."""

    kind: str = "stt"


@dataclass(frozen=True)
class TtsProvider(VoiceProvider):
    """Text → Sprache (Text-to-Speech)."""

    kind: str = "tts"


@dataclass(frozen=True)
class LlmProvider(VoiceProvider):
    """Das Sprachmodell, das im Gespräch antwortet (das „Hirn" bleibt unser /api/interview/)."""

    kind: str = "llm"


@dataclass(frozen=True)
class RealtimeProvider(VoiceProvider):
    """Ein Sprache↔Sprache-Realtime-Anbieter, der STT+LLM+TTS in einem ersetzt (z. B. OpenAI)."""

    kind: str = "realtime"


@dataclass(frozen=True)
class VoicePlan:
    """Der je Souveränitätsstufe aufgelöste Bauplan für den Agent-Worker.

    Entweder eine klassische Pipeline (``stt`` + ``llm`` + ``tts``) **oder** ein einzelner
    ``realtime``-Anbieter (Sprache↔Sprache), der die drei ersetzt. Diese Struktur wird dem
    LiveKit-Agent-Worker (Phasen 3–5) als Konfiguration übergeben (= „RealtimeAgentConfig").
    """

    tier: str
    stt: SttProvider | None = None
    llm: LlmProvider | None = None
    tts: TtsProvider | None = None
    realtime: RealtimeProvider | None = None

    def to_dict(self, settings=None) -> dict:
        def one(p):
            return p.to_dict(settings) if p is not None else None

        return {
            "tier": self.tier,
            "mode": "realtime" if self.realtime is not None else "pipeline",
            "stt": one(self.stt),
            "llm": one(self.llm),
            "tts": one(self.tts),
            "realtime": one(self.realtime),
        }


# --------------------------------------------------------------------------- #
# Katalog der bekannten Bausteine (verifizierte Recherche 2026-06-05, s. Unterplan 1D).
# Modellnamen/Details werden bei Baubeginn der jeweiligen Phase kurz neu verifiziert.
# --------------------------------------------------------------------------- #

# 🔒 sov — selbst gehostet (offene Gewichte / lokale Engines)
STT_VOXTRAL_LOCAL = SttProvider(
    id="voxtral-local", label="Voxtral STT (lokal, offene Gewichte)", region=REGION_LOKAL,
    open_weights=True, notes="Voxtral Realtime (Apache-2.0) selbst gehostet; nichts verlässt den Server.",
)
LLM_LOCAL = LlmProvider(
    id="local-llm", label="Lokales LLM (Ollama o. ä.)", region=REGION_LOKAL,
    notes="Lokales Sprachmodell auf dem VPS; das Interview-Gehirn bleibt /api/interview/.",
)
TTS_PIPER_LOCAL = TtsProvider(
    id="piper-local", label="Piper TTS (lokal, Deutsch)", region=REGION_LOKAL,
    open_weights=True, notes="Piper-Stimme lokal (Muster aus Klaras module_voice, nur Engine).",
)

# 🇪🇺 eu — Mistral/Voxtral über EU-API (DSGVO: Paris + AVV, Pay-per-Use)
STT_VOXTRAL_MISTRAL = SttProvider(
    id="voxtral-mistral", label="Voxtral Realtime STT (Mistral, EU)", region=REGION_EU,
    requires_env=("LLM_API_KEY",), notes="WebSocket-STT <200 ms, Deutsch; Silero-VAD = offenes Mikro.",
)
LLM_MISTRAL = LlmProvider(
    id="mistral", label="Mistral (EU)", region=REGION_EU, requires_env=("LLM_API_KEY",),
    notes="Mistral-Chat (Paris); identisch zum bereits genutzten Text-Pfad des Matchmaker.",
)
TTS_VOXTRAL_MISTRAL = TtsProvider(
    id="voxtral-mistral-tts", label="Voxtral TTS (Mistral, EU)", region=REGION_EU,
    requires_env=("LLM_API_KEY",), notes="Streamende deutsche Stimme, ~70 ms.",
)

# 🇺🇸 us — OpenAI Realtime (Sprache↔Sprache)
REALTIME_OPENAI = RealtimeProvider(
    id="openai-realtime", label="OpenAI Realtime (US)", region=REGION_US,
    requires_env=("OPENAI_API_KEY",), notes="Sprache↔Sprache, glattestes Unterbrechen; Daten in die USA.",
)
