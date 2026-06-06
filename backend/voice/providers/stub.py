"""Netzfreie Stub-Bausteine.

Damit Entwicklung und Tests **ohne Netz, ohne Schlüssel und ohne Kosten** laufen (wie der
``StubClient`` der LLM-Schicht). Wird genutzt, wenn ``VOICE_FORCE_STUB=true`` gesetzt ist –
dann liefert jede Stufe denselben offline nutzbaren Plan.
"""
from __future__ import annotations

from .base import (
    REGION_LOKAL,
    LlmProvider,
    RealtimeProvider,
    SttProvider,
    TtsProvider,
    VoicePlan,
)

STUB_STT = SttProvider(
    id="stub-stt", label="Stub-STT (offline)", region=REGION_LOKAL,
    notes="Tut nichts echtes; nur für Tests/Dev ohne Netz.",
)
STUB_LLM = LlmProvider(
    id="stub-llm", label="Stub-LLM (offline)", region=REGION_LOKAL,
    notes="Tut nichts echtes; nur für Tests/Dev ohne Netz.",
)
STUB_TTS = TtsProvider(
    id="stub-tts", label="Stub-TTS (offline)", region=REGION_LOKAL,
    notes="Tut nichts echtes; nur für Tests/Dev ohne Netz.",
)
STUB_REALTIME = RealtimeProvider(
    id="stub-realtime", label="Stub-Realtime (offline)", region=REGION_LOKAL,
    notes="Tut nichts echtes; nur für Tests/Dev ohne Netz.",
)


def stub_plan(tier: str) -> VoicePlan:
    """Ein offline nutzbarer Pipeline-Plan für eine beliebige Stufe."""
    return VoicePlan(tier=tier, stt=STUB_STT, llm=STUB_LLM, tts=STUB_TTS)
