"""Das „Gehirn" des Sprach-Agenten — bewusst LiveKit-unabhängig & testbar.

Hier steckt die LS-Logik des Gesprächs, **getrennt** vom LiveKit-Framework: Der Agent
(``agent.py``) kümmert sich nur um Ohren/Stimme/Transport; diese Klasse hält den Gesprächs-
zustand und spricht mit unserem deterministischen Backend (``/api/interview/`` + ``/api/match/``).

Konversationell, **kein** Intent-Dispatch: Das Backend bleibt die Wahrheit darüber, *welche
Diagnose-Dimension noch fehlt* und *wann genug Information da ist* — der Agent formuliert nur
natürlich aus.
"""
from __future__ import annotations

import re
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
        self._names_cache: dict | None = None  # slug→Anzeigename (einmal vom Katalog geholt, dann gecacht)

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

    # Die 10 LS-Prinzipien (IDs → deutsche Namen, Quelle: data/ls_principles.json im Backend).
    # Bewusst HIER fest hinterlegt (stabil, ändert sich praktisch nie) statt per Extra-Endpunkt —
    # so bleibt die Vorlese-Logik unabhängig und der empfindliche Matchmaker unangetastet.
    PRINCIPLE_NAMES = {
        "P1": "Alle einbeziehen und entfalten",
        "P2": "Tiefen Respekt für Menschen und lokale Lösungen üben",
        "P3": "Schritt für Schritt Vertrauen aufbauen",
        "P4": "Durch Vorwärts-Scheitern lernen",
        "P5": "Selbstentdeckung in der Gruppe ermöglichen",
        "P6": "Freiheit und Verantwortung verstärken",
        "P7": "Möglichkeiten betonen – erst glauben, dann sehen",
        "P8": "Kreative Zerstörung einladen, um Innovation zu ermöglichen",
        "P9": "Ernsthaft verspielte Neugier leben",
        "P10": "Nie ohne klaren Zweck starten",
    }

    async def structure_names(self) -> dict:
        """Lädt EINMALIG (gecacht) die Anzeigenamen aller Strukturen als ``slug→Name`` vom Katalog
        (``/api/structures/``) — fürs Vorlesen echter Namen statt der Slugs. Die LS-Namen sind auch
        auf Deutsch englisch (so von den Autoren gewollt). Wirft nie: bei Fehler leere Tabelle
        (dann Fallback auf den Slug)."""
        if self._names_cache is not None:
            return self._names_cache
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.get(f"{self.backend_url}/api/structures/", params={"lang": "en"})
                resp.raise_for_status()
                data = resp.json()
            items = data if isinstance(data, list) else (data.get("results") or data.get("structures") or [])
            self._names_cache = {it.get("slug"): it.get("name") for it in items if it.get("slug")}
        except Exception:
            self._names_cache = {}
        return self._names_cache

    @staticmethod
    def spoken_summary(match_result: dict) -> str:
        """Formuliert aus dem Match-Ergebnis einen kurzen, vorlesbaren deutschen Text — die
        SCHRITT-/ABLAUF-basierte Fassung (nennt Slugs + ``summary``).

        BEWUSST ERHALTEN (Steffen 2026-06-11): Aktuell vorgelesen wird stattdessen ``spoken_string``
        (Variante 2: Namen + wirkende Prinzipien, ohne operative Schritte). Diese Methode hier bleibt
        als Baustein für eine spätere, ausführliche Schritt-Durchsprache im Code — NICHT löschen."""
        steps = match_result.get("string", [])
        summary = match_result.get("summary", "")
        names = ", ".join(s.get("slug", "") for s in steps)
        total = match_result.get("total_duration")
        teil = f" Dauer insgesamt etwa {total} Minuten." if total else ""
        return (
            f"Mein Vorschlag: {names}.{teil} {summary}".strip()
        )

    @staticmethod
    def _strip_principle_ids(text: str) -> str:
        """Entfernt rohe LS-Prinzip-IDs (P1–P10) aus Prosa — für den Nutzer bedeutungslos, also nicht
        vorlesen (Steffen 2026-06-11). Räumt zurückbleibende leere Klammern / lose Trenner sauber auf,
        damit kein Stolpern in der Sprachausgabe entsteht."""
        text = re.sub(r"\bP(?:10|[1-9])\b", "", text)        # die IDs selbst
        text = re.sub(r"\(\s*[,;]*\s*\)", "", text)           # zurückbleibende leere Klammern ()
        text = re.sub(r"\(\s*[,;]\s*", "(", text)              # „( , …" → „(…"
        text = re.sub(r"\s*[,;]\s*\)", ")", text)              # „…, )" → „…)"
        text = re.sub(r"\s+([.,;:])", r"\1", text)             # Leerzeichen vor Satzzeichen
        text = re.sub(r"[ \t]{2,}", " ", text)                 # doppelte Leerzeichen
        return text.strip()

    @classmethod
    def spoken_string(cls, match_result: dict, names: dict | None = None) -> str:
        """Variante 2 (Steffen 2026-06-11) — das, was AKTUELL vorgelesen wird.

        Nennt die Strukturen beim (englischen) Anzeigenamen, sagt je Element die WIRKENDEN
        LS-Prinzipien (beim Namen) und gibt die ausführliche Gesamt-Begründung von Auswahl UND
        Reihenfolge wieder (``principle_rationale``). BEWUSST OHNE operative Detail-Schritte
        (Gruppengröße/Minuten je Mikroschritt) — die liest die TTS schief/denglisch vor und sind
        hier nicht erwünscht; der ``summary`` (Ablaufbeschreibung) wird daher NICHT verwendet.

        :param names: ``slug→Anzeigename`` (aus :meth:`structure_names`); fehlt ein Name, Fallback Slug.
        """
        names = names or {}
        steps = match_result.get("string", []) or []
        # Anzeigename je Schritt; ein angehängtes Kürzel in Klammern (z. B. „(W³)") fürs Vorlesen
        # entfernen — die TTS spricht es sonst schief aus (Steffens Kern-Anliegen: saubere Aussprache).
        namen = [re.sub(r"\s*\([^)]*\)\s*$", "", names.get(s.get("slug", ""), s.get("slug", ""))).strip()
                 or s.get("slug", "") for s in steps]
        # Abfolge sprachlich: „zuerst X, dann Y, …, und zum Abschluss Z".
        if len(namen) >= 2:
            folge = "zuerst " + ", dann ".join(namen[:-1]) + f", und zum Abschluss {namen[-1]}"
        elif namen:
            folge = namen[0]
        else:
            folge = ""
        total = match_result.get("total_duration")
        dauer = f" — insgesamt etwa {total} Minuten" if total else ""
        # Pro Element die wirkenden Prinzipien (beim Namen) — KEINE Ablauf-/Schritt-Beschreibung.
        prinzip_saetze = []
        for step, name in zip(steps, namen):
            pnamen = [cls.PRINCIPLE_NAMES[p] for p in (step.get("principles") or []) if p in cls.PRINCIPLE_NAMES]
            if pnamen:
                prinzip_saetze.append(f"Bei {name} wirken vor allem: {', '.join(pnamen)}.")
        # principle_rationale ist Prosa, die rohe IDs („(P1, P3)") zitieren KANN. Die sind für den
        # Nutzer bedeutungslos (Steffen 2026-06-11: „P1–P10 sind Garbage") → rausfiltern, nur der
        # semantische Gehalt bleibt. Die Prinzip-Namen oben kommen ohnehin ausgeschrieben.
        warum = cls._strip_principle_ids((match_result.get("principle_rationale") or "").strip())
        teile = [f"Ich schlage euch diese Abfolge vor: {folge}{dauer}."]
        if prinzip_saetze:
            teile.append("Dahinter wirken klare Prinzipien. " + " ".join(prinzip_saetze))
        if warum:
            teile.append(warum)
        return " ".join(teile).strip()
