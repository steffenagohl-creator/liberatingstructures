"""Das „Gehirn" des Sprach-Agenten — bewusst LiveKit-unabhängig & testbar.

Hier steckt die LS-Logik des Gesprächs, **getrennt** vom LiveKit-Framework: Der Agent
(``agent.py``) kümmert sich nur um Ohren/Stimme/Transport; diese Klasse hält den Gesprächs-
zustand und spricht mit unserem deterministischen Backend (``/api/interview/`` + ``/api/match/``).

Konversationell, **kein** Intent-Dispatch: Das Backend bleibt die Wahrheit darüber, *welche
Diagnose-Dimension noch fehlt* und *wann genug Information da ist* — der Agent formuliert nur
natürlich aus.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import httpx


@dataclass
class InterviewState:
    """Ergebnis eines Interview-Schritts (gespiegelt ans Frontend = „Spinnennetz")."""

    diagnose: dict = field(default_factory=dict)
    open_questions: list = field(default_factory=list)
    ready: bool = False

    @property
    def next_question(self) -> str | None:
        """Der Text der nächsten offenen Rückfrage (für die Gesprächsführung), falls vorhanden."""
        if self.open_questions:
            return self.open_questions[0].get("label") or self.open_questions[0].get("key")
        return None


class LSInterviewBrain:
    """Hält Transkript + Diagnose und ruft das LS-Backend.

    :param backend_url: Basis-URL des Django-Backends (z. B. ``http://web:8000``).
    :param timeout: HTTP-Timeout in Sekunden.
    """

    def __init__(self, backend_url: str, timeout: float = 30.0):
        self.backend_url = backend_url.rstrip("/")
        self.timeout = timeout
        self._utterances: list[str] = []
        self.state = InterviewState()

    @property
    def situation_text(self) -> str:
        """Das bisher Gesagte als ein Freitext (so erwartet es ``/api/interview/``)."""
        return " ".join(self._utterances).strip()

    async def observe(self, user_text: str) -> InterviewState:
        """Verarbeitet eine Nutzer-Äußerung: anhängen → ``/api/interview/`` → neuen Zustand.

        Gibt den aktualisierten ``InterviewState`` zurück (Aufrufer spiegelt ihn ans Frontend).
        """
        text = (user_text or "").strip()
        if text:
            self._utterances.append(text)
        payload = {"situation": self.situation_text, "answers": self.state.diagnose or {}}
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(f"{self.backend_url}/api/interview/", json=payload)
            resp.raise_for_status()
            data = resp.json()
        self.state = InterviewState(
            diagnose=data.get("diagnose", {}),
            open_questions=data.get("open_questions", []),
            ready=bool(data.get("ready", False)),
        )
        return self.state

    async def match(self) -> dict:
        """Ruft ``/api/match/`` mit der erhobenen Diagnose → der begründete LS-String."""
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            resp = await client.post(
                f"{self.backend_url}/api/match/", json={"diagnose": self.state.diagnose}
            )
            resp.raise_for_status()
            return resp.json()

    @staticmethod
    def spoken_summary(match_result: dict) -> str:
        """Formuliert aus dem Match-Ergebnis einen kurzen, vorlesbaren deutschen Text."""
        steps = match_result.get("string", [])
        summary = match_result.get("summary", "")
        names = ", ".join(s.get("slug", "") for s in steps)
        total = match_result.get("total_duration")
        teil = f" Dauer insgesamt etwa {total} Minuten." if total else ""
        return (
            f"Mein Vorschlag: {names}.{teil} {summary}".strip()
        )
