"""Gemeinsames Interface aller LLM-Anbieter.

Jeder konkrete Client (Mistral, Stub, später ggf. andere) erbt von ``LLMClient``
und implementiert genau eine Methode: ``chat(messages, json=True) -> str``.
Das übrige Backend kennt nur dieses Interface – nie einen konkreten Anbieter.
"""
from __future__ import annotations

from abc import ABC, abstractmethod


class LLMError(RuntimeError):
    """Fehler beim Aufruf des Sprachmodells (Netz, Authentifizierung, ungültige Antwort)."""


class LLMClient(ABC):
    """Abstrakte Basis für alle Sprachmodell-Anbieter.

    Eine bewusst minimale Schnittstelle: Wir schicken eine Liste von Nachrichten
    (jeweils ``{"role": "system"|"user"|"assistant", "content": "..."}``) und
    erhalten den Text der Antwort zurück.
    """

    #: sprechender Name des Anbieters (für Logging/Doku)
    name: str = "base"

    @abstractmethod
    def chat(self, messages: list[dict], json: bool = True) -> str:
        """Schickt ``messages`` an das Modell und gibt den Antworttext zurück.

        :param messages: Liste von ``{"role", "content"}``-Nachrichten.
        :param json: Wenn ``True``, wird das Modell angewiesen, **ausschließlich**
            ein JSON-Objekt zu liefern (JSON-Modus). Der Aufrufer parst es selbst.
        :returns: Der reine Antworttext (bei ``json=True`` ein JSON-String).
        :raises LLMError: bei Netz-/Auth-/Formatfehlern.
        """
        raise NotImplementedError
