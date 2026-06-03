"""Provider-agnostische LLM-Schicht.

Das übrige Backend spricht **nur** über das Interface ``LLMClient`` (siehe
``base.py``) mit einem Sprachmodell. Welcher Anbieter/welches Modell tatsächlich
antwortet, entscheidet ausschließlich die ENV-Konfiguration über ``factory.get_llm_client``
(``LLM_PROVIDER``, ``LLM_MODEL``, ``MISTRAL_API_KEY``).

So ist das Modell ohne Codeänderung austauschbar und A/B-testbar, und Tests
laufen über den ``StubClient`` komplett ohne Netz und ohne Kosten.
"""
from .base import LLMClient, LLMError
from .factory import get_llm_client

__all__ = ["LLMClient", "LLMError", "get_llm_client"]
