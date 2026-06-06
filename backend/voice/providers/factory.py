"""Auswahl der Sprach-Bausteine je Souveränitätsstufe – nur über Stufe + ENV.

``plan_for_tier(tier)`` gibt den ``VoicePlan`` (Pipeline oder Realtime) für eine Stufe zurück.
Kein anderer Teil des Codes entscheidet, welcher konkrete Anbieter eine Stufe bedient.
"""
from __future__ import annotations

from django.conf import settings

from . import base, stub

# Stufe → fester Bauplan aus dem Baustein-Katalog (siehe base.py / Unterplan 1D).
_TIER_PLANS = {
    "sov": base.VoicePlan(
        tier="sov", stt=base.STT_VOXTRAL_LOCAL, llm=base.LLM_LOCAL, tts=base.TTS_PIPER_LOCAL,
    ),
    "eu": base.VoicePlan(
        tier="eu", stt=base.STT_VOXTRAL_MISTRAL, llm=base.LLM_MISTRAL, tts=base.TTS_VOXTRAL_MISTRAL,
    ),
    "us": base.VoicePlan(
        tier="us", realtime=base.REALTIME_OPENAI,
    ),
}


def plan_for_tier(tier: str) -> base.VoicePlan:
    """Bauplan für ``tier``. Bei ``VOICE_FORCE_STUB=true`` immer der offline Stub-Plan.

    :raises VoiceError: bei unbekannter Stufe.
    """
    if getattr(settings, "VOICE_FORCE_STUB", False):
        return stub.stub_plan(tier)
    try:
        return _TIER_PLANS[tier]
    except KeyError as exc:
        raise base.VoiceError(
            f"Unbekannte Souveränitätsstufe: {tier!r} (erlaubt: sov, eu, us)."
        ) from exc
