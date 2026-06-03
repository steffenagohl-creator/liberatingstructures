"""Mistral-Client (EU, DSGVO-freundlich) über die Chat-Completions-API.

Schlüssel und Modell kommen ausschließlich aus der ENV/Konfiguration; nichts
ist hartkodiert. Wird über ``get_llm_client()`` erzeugt, nie direkt importiert.
"""
from __future__ import annotations

import httpx

from .base import LLMClient, LLMError

MISTRAL_CHAT_URL = "https://api.mistral.ai/v1/chat/completions"


class MistralClient(LLMClient):
    """Spricht die Mistral-Chat-API; gibt den Text der Antwort zurück."""

    name = "mistral"

    def __init__(self, api_key: str, model: str, timeout: float = 60.0):
        if not api_key:
            raise LLMError(
                "Kein Mistral-Schlüssel gesetzt (MISTRAL_API_KEY/LLM_API_KEY). "
                "Für Tests/Offline LLM_PROVIDER=stub verwenden."
            )
        self.api_key = api_key
        self.model = model
        self.timeout = timeout

    def chat(self, messages: list[dict], json: bool = True) -> str:
        payload: dict = {"model": self.model, "messages": messages}
        if json:
            # JSON-Modus: das Modell liefert garantiert ein JSON-Objekt zurück.
            payload["response_format"] = {"type": "json_object"}
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
        try:
            response = httpx.post(
                MISTRAL_CHAT_URL, headers=headers, json=payload, timeout=self.timeout
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except httpx.HTTPStatusError as exc:
            raise LLMError(
                f"Mistral antwortete mit Status {exc.response.status_code}: "
                f"{exc.response.text[:300]}"
            ) from exc
        except (httpx.HTTPError, KeyError, IndexError, ValueError) as exc:
            raise LLMError(f"Mistral-Aufruf fehlgeschlagen: {exc}") from exc
