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

    def __init__(self, backend_url: str, timeout: float = 30.0, match_timeout: float = 180.0,
                 tier: str = "eu"):
        self.backend_url = backend_url.rstrip("/")
        # Souveränitäts-/Modellpfad: wird an /api/interview/ mitgesendet, damit das Backend den
        # pfad-getrennten Erhebungs-Prompt wählt (EU = vorsichtig, US = eingefroren).
        self.tier = tier
        self.timeout = timeout
        # Der Match (LLM-Verdichtung) braucht real bis ~60 s; eigener, großzügiger Timeout,
        # damit der Agent nicht vorzeitig aufgibt (sonst: „Matchmaking fehlgeschlagen", kein
        # String). Das Interview (observe) bleibt beim kurzen Timeout — es muss flott sein.
        self.match_timeout = match_timeout
        self._utterances: list[str] = []
        self.state = InterviewState()

    @property
    def situation_text(self) -> str:
        """Das bisher Gesagte als ein Freitext (so erwartet es ``/api/interview/``)."""
        return " ".join(self._utterances).strip()

    # Reine Grußfloskeln taugen NICHT als Situations-Beschriftung (Test 2026-06-06: der Mittelpunkt
    # zeigte „Hallo."). Wir überspringen sie und nehmen die erste inhaltliche Äußerung.
    _GREETINGS = {"hallo", "hi", "hey", "hallöchen", "moin", "servus", "guten tag", "guten morgen",
                  "guten abend", "grüß dich", "grüß gott", "na", "jo", "ja"}

    @property
    def opening(self) -> str:
        """Die erste INHALTLICHE Nutzeräußerung (gekürzt) — dient dem Frontend als kurze
        Situations-Beschriftung des Spinnen-Mittelpunkts, falls das Backend keinen
        ``scrum_kontext`` erkennt. Reine Grüße werden übersprungen."""
        for u in self._utterances:
            clean = u.strip().rstrip(".!?,").lower()
            if clean and clean not in self._GREETINGS:
                return u[:80].strip()
        return ""

    async def observe(self, user_text: str) -> InterviewState:
        """Verarbeitet eine Nutzer-Äußerung: anhängen → ``/api/interview/`` → neuen Zustand.

        Gibt den aktualisierten ``InterviewState`` zurück (Aufrufer spiegelt ihn ans Frontend).
        """
        text = (user_text or "").strip()
        if text:
            self._utterances.append(text)
        payload = {"situation": self.situation_text, "answers": self.state.diagnose or {},
                   "tier": self.tier}
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

    @staticmethod
    def _to_int(value):
        """Robust nach int: akzeptiert Zahlen und zieht Ziffern aus Text („60 Minuten" → 60).
        Gibt None zurück, wenn nichts Sinnvolles drinsteckt."""
        if isinstance(value, bool):
            return None
        if isinstance(value, int):
            return value
        if isinstance(value, float):
            return int(value)
        if isinstance(value, str):
            digits = "".join(ch for ch in value if ch.isdigit())
            return int(digits) if digits else None
        return None

    @classmethod
    def _sanitize_diagnose(cls, raw: dict | None) -> dict:
        """Bringt die Diagnose in die vom ``/api/match/``-Serializer erwarteten TYPEN. Das
        Interview-LLM liefert gelegentlich falsche Typen (z. B. ``zweck`` als String,
        ``zeitbudget`` als „60 Minuten") — ohne diese Härtung antwortet der Match-Endpunkt mit
        400 (Test 2026-06-06, nach einem Realtime-Verbindungsabriss). Werte werden nur
        umgeformt, nie erfunden."""
        d = dict(raw or {})
        # Listenfelder: String → einelementige Liste, None → leere Liste.
        for key in ("zweck", "phase_bogen"):
            val = d.get(key)
            if isinstance(val, str):
                d[key] = [val] if val.strip() else []
            elif isinstance(val, list):
                d[key] = [str(x) for x in val if str(x).strip()]
            elif val is None:
                d.pop(key, None)
            else:
                d[key] = []
        # Zahlenfelder: robust zu int — sonst Feld weglassen (Serializer erlaubt das Fehlen).
        for key in ("gruppengroesse", "zeitbudget"):
            if key in d:
                num = cls._to_int(d.get(key))
                if num is None:
                    d.pop(key, None)
                else:
                    d[key] = num
        return d

    async def match(self) -> dict:
        """Ruft ``/api/match/`` mit der erhobenen Diagnose → der begründete LS-String.
        Die Diagnose wird vorher typsicher gemacht (s. ``_sanitize_diagnose``)."""
        diagnose = self._sanitize_diagnose(self.state.diagnose)
        async with httpx.AsyncClient(timeout=self.match_timeout) as client:
            resp = await client.post(
                f"{self.backend_url}/api/match/", json={"diagnose": diagnose}
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
