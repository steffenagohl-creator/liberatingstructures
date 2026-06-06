"""Provider-agnostisches Sprach-Abstraktions-Layer (siehe ``base.py``).

Das Backend nutzt nur ``plan_for_tier`` + die selbstbeschreibenden Provider-Objekte;
der konkrete Anbieter je Stufe ergibt sich allein aus Stufe + ENV.
"""
from .base import (
    VoiceError,
    VoicePlan,
    VoiceProvider,
    SttProvider,
    TtsProvider,
    LlmProvider,
    RealtimeProvider,
)
from .factory import plan_for_tier

__all__ = [
    "VoiceError",
    "VoicePlan",
    "VoiceProvider",
    "SttProvider",
    "TtsProvider",
    "LlmProvider",
    "RealtimeProvider",
    "plan_for_tier",
]
