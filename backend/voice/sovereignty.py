"""Souveränitäts-Routing (Master-Plan 1C) — gemeinsame Politik für Voice **und** LLM.

Der Nutzer/Coach wählt am Souveränitäts-Screen, **wohin seine Daten gehen dürfen**. Diese
Wahl steuert, welcher Anbieter eine Anfrage bedient. Drei Stufen (identisch zu den Keys im
Frontend ``frontend/src/App.jsx``):

* ``sov`` 🔒 **Souverän** – nichts verlässt den eigenen Server (lokale/offene Modelle).
* ``eu``  🇪🇺 **EU** (Standard) – EU-Dienstleister (Mistral, Paris; DSGVO/AVV).
* ``us``  🇺🇸 **Komfort** – außerhalb der EU erlaubt (OpenAI Realtime).

**Datensparsamer Fallback (wichtig):** Ist eine Stufe nicht konfiguriert, wird auf eine
**souveränere** Stufe heruntergestuft – **nie** auf eine weniger souveräne. Wer ``eu`` wählt,
landet im Zweifel bei ``sov``, **niemals** bei ``us``. So gehen Daten nie weiter nach außen,
als die Nutzerin erlaubt hat.
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

from .providers import factory

# -- Die drei Stufen -------------------------------------------------------- #
TIER_SOV = "sov"
TIER_EU = "eu"
TIER_US = "us"
TIERS = (TIER_SOV, TIER_EU, TIER_US)
DEFAULT_TIER = TIER_EU

# Menschlich lesbare Selbstbeschreibung je Stufe (UI/Screenreader/Doku).
TIER_META = {
    TIER_SOV: {
        "flag": "🔒", "label": "Souverän",
        "region": "lokal",
        "description": "Nur euer eigener Server. Nichts verlässt die Maschine.",
    },
    TIER_EU: {
        "flag": "🇪🇺", "label": "EU",
        "region": "eu",
        "description": "EU-Dienstleister (Mistral). Volle Qualität, DSGVO-konform. Empfohlen.",
    },
    TIER_US: {
        "flag": "🇺🇸", "label": "Komfort",
        "region": "us",
        "description": "USA erlaubt (OpenAI). Bestes Sprachgespräch. Daten gehen in die USA.",
    },
}

# Fallback-Ketten: von der gewählten Stufe nur Richtung **mehr** Souveränität.
FALLBACK_CHAINS = {
    TIER_US: [TIER_US, TIER_EU, TIER_SOV],
    TIER_EU: [TIER_EU, TIER_SOV],
    TIER_SOV: [TIER_SOV],
}

# Stufe → Provider-Name der Matchmaker-LLM-Schicht (für späteren per-Request-Einsatz, 1C.1).
_LLM_PROVIDER_BY_TIER = {
    TIER_SOV: "stub",      # bis ein lokales LLM steht (Phase 4); kein Cloud-Versand
    TIER_EU: "mistral",
    TIER_US: "openai",     # OpenAI-Client wird in Phase 5 ergänzt
}


@dataclass(frozen=True)
class ResolvedTier:
    """Ergebnis der Auflösung: was gewünscht war und was tatsächlich genutzt wird."""

    requested: str
    effective: str
    configured: bool
    fell_back: bool


def normalize_tier(value: str | None) -> str:
    """Bringt eine Eingabe auf eine gültige Stufe; Unbekanntes → Standard (``eu``)."""
    if not value:
        return DEFAULT_TIER
    candidate = str(value).strip().lower()
    return candidate if candidate in TIERS else DEFAULT_TIER


def tier_is_configured(tier: str) -> bool:
    """True, wenn die Stufe in dieser Installation tatsächlich bedient werden kann.

    * ``VOICE_FORCE_STUB`` → alles nutzbar (offline-Dev/Tests).
    * ``sov`` → erst nutzbar, wenn der lokale Stack aktiviert ist (``VOICE_SELFHOSTED_ENABLED``).
    * ``eu``/``us`` → nutzbar, sobald die nötigen Schlüssel (ENV) gesetzt sind.
    """
    if getattr(settings, "VOICE_FORCE_STUB", False):
        return True
    plan = factory.plan_for_tier(tier)
    bausteine = [p for p in (plan.stt, plan.llm, plan.tts, plan.realtime) if p is not None]
    env_ok = all(p.is_configured(settings) for p in bausteine)
    if tier == TIER_SOV:
        return env_ok and bool(getattr(settings, "VOICE_SELFHOSTED_ENABLED", False))
    return env_ok


def resolve_tier(requested: str | None) -> ResolvedTier:
    """Löst die gewünschte Stufe gegen die Konfiguration auf (datensparsamer Fallback)."""
    norm = normalize_tier(requested)
    chain = FALLBACK_CHAINS[norm]
    for tier in chain:
        if tier_is_configured(tier):
            return ResolvedTier(
                requested=norm, effective=tier, configured=True, fell_back=(tier != norm),
            )
    # Keine Stufe der Kette konfiguriert → die souveränste (letzte) als sicherer Default.
    fallback = chain[-1]
    return ResolvedTier(
        requested=norm, effective=fallback, configured=False, fell_back=(fallback != norm),
    )


def llm_provider_for_tier(tier: str) -> str:
    """Welcher Matchmaker-LLM-Provider zu einer Stufe gehört (für 1C-Wiring später)."""
    return _LLM_PROVIDER_BY_TIER.get(normalize_tier(tier), "mistral")


def livekit_ready() -> bool:
    """True, wenn der LiveKit-Transport konfiguriert ist (URL + Schlüssel)."""
    return bool(
        getattr(settings, "LIVEKIT_URL", "")
        and getattr(settings, "LIVEKIT_API_KEY", "")
        and getattr(settings, "LIVEKIT_API_SECRET", "")
    )


def describe_tier(tier: str) -> dict:
    """Selbstbeschreibung einer Stufe inkl. Konfigurations-Status und Bauplan (für /config)."""
    meta = TIER_META[tier]
    return {
        "id": tier,
        "flag": meta["flag"],
        "label": meta["label"],
        "region": meta["region"],
        "description": meta["description"],
        "configured": tier_is_configured(tier),
        "plan": factory.plan_for_tier(tier).to_dict(settings),
    }


def available_tiers() -> list[dict]:
    """Alle drei Stufen als Selbstbeschreibung (Reihenfolge sov → eu → us)."""
    return [describe_tier(t) for t in TIERS]
