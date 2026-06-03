"""Auswahl des LLM-Anbieters – ausschließlich über die ENV/Konfiguration.

``get_llm_client()`` liest ``LLM_PROVIDER`` (Default ``mistral``) und gibt den
passenden Client zurück. Kein anderer Teil des Codes entscheidet über den Anbieter.
"""
from __future__ import annotations

from django.conf import settings

from .base import LLMClient, LLMError
from .mistral import MistralClient
from .stub import StubClient


def get_llm_client(provider: str | None = None) -> LLMClient:
    """Erzeugt den konfigurierten LLM-Client.

    :param provider: optionaler Override (sonst ``settings.LLM_PROVIDER``).
    """
    provider = (provider or getattr(settings, "LLM_PROVIDER", "mistral")).lower()

    if provider == "stub":
        return StubClient()
    if provider == "mistral":
        return MistralClient(
            api_key=getattr(settings, "LLM_API_KEY", ""),
            model=getattr(settings, "LLM_MODEL", "mistral-medium-latest"),
            timeout=getattr(settings, "LLM_TIMEOUT", 60.0),
        )
    raise LLMError(f"Unbekannter LLM_PROVIDER: {provider!r} (erlaubt: mistral, stub).")
