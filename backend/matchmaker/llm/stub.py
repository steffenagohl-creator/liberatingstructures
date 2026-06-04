"""Deterministischer Stub-Client – ersetzt das echte Modell in Tests/Offline.

Der Stub liest den maschinenlesbaren Kontext-Block aus den Nachrichten (siehe
``prompts.py``) und rechnet daraus eine **gültige, reproduzierbare** Antwort:

* Interview: übernimmt die bereits bekannten Antworten als Diagnose und meldet
  fehlende Pflichtfelder als Rückfragen.
* Sequenzierung: baut greedy einen String mit vollständigem Bogen (eine öffnende
  und eine schließende Struktur) innerhalb des Zeitbudgets.

So bleibt das Quality Gate auch ohne Netz prüfbar – kein Schlüssel, keine Kosten.
"""
from __future__ import annotations

import json

from ..prompts import extract_context
from .base import LLMClient

# Knappe, rollenbasierte Begründungen (deterministisch, deutsch).
_ROLE_RATIONALE = {
    "öffnen": "Öffnet die Session: holt alle ab und schafft psychologische Sicherheit.",
    "divergieren": "Erzeugt breit und gleichberechtigt viele Beiträge.",
    "konvergieren": "Verdichtet die Beiträge zu tragfähigen Schwerpunkten.",
    "schließen": "Schließt ab: sichert Erkenntnisse und konkrete nächste Schritte.",
}


class StubClient(LLMClient):
    """Liefert feste, regelbasierte Antworten ohne externen Aufruf."""

    name = "stub"

    def chat(self, messages: list[dict], json: bool = True) -> str:
        context = extract_context(messages)
        task = context.get("task")
        if task == "interview":
            return self._interview(context)
        if task == "sequence":
            return self._sequence(context)
        if task == "consolidate":
            return self._consolidate(context)
        # Unbekannte Aufgabe: leeres, valides JSON-Objekt.
        return "{}"

    # -- Interview ---------------------------------------------------------- #
    def _interview(self, context: dict) -> str:
        answers = context.get("answers") or {}
        required = context.get("required") or []
        dimensions = {d["key"]: d for d in context.get("dimensions") or []}

        def is_set(value) -> bool:
            return value not in (None, "", [], {})

        diagnose = {k: v for k, v in answers.items() if is_set(v)}
        missing = [k for k in required if k not in diagnose]
        open_questions = []
        for key in missing:
            dim = dimensions.get(key, {})
            open_questions.append(
                {
                    "key": key,
                    "label": dim.get("label", key),
                    "hint": dim.get("hint", ""),
                    "input_type": dim.get("input_type", "text"),
                    "options": dim.get("options", []),
                }
            )
        result = {
            "diagnose": diagnose,
            "open_questions": open_questions,
            "ready": len(missing) == 0,
        }
        return json.dumps(result, ensure_ascii=False)

    # -- Sequenzierung ------------------------------------------------------ #
    def _sequence(self, context: dict) -> str:
        candidates = context.get("candidates") or []
        budget = context.get("zeitbudget")
        budget = budget if isinstance(budget, int) and budget > 0 else 10**6

        def has_role(cand, role) -> bool:
            return role in (cand.get("arc_role") or [])

        def dur(cand) -> int:
            return int(cand.get("duration_min") or 0)

        opener = next((c for c in candidates if has_role(c, "öffnen")), None)
        closer = next(
            (
                c
                for c in candidates
                if has_role(c, "schließen") and (not opener or c["slug"] != opener["slug"])
            ),
            None,
        )

        steps: list[dict] = []
        used: set[str] = set()
        total = 0
        closer_dur = dur(closer) if closer else 0

        def add(cand, role):
            nonlocal total
            steps.append(
                {
                    "slug": cand["slug"],
                    "role": role,
                    "duration": dur(cand),
                    "rationale": _ROLE_RATIONALE.get(role, "Trägt zum String bei."),
                    "principles": list(cand.get("embodied_principles") or []),
                }
            )
            used.add(cand["slug"])
            total += dur(cand)

        if opener:
            add(opener, "öffnen")

        # Mittelteil greedy auffüllen, Budget für den Schluss reservieren, max. 4 Schritte.
        for cand in candidates:
            if cand["slug"] in used:
                continue
            if closer and cand["slug"] == closer["slug"]:
                continue
            role = (
                "divergieren"
                if has_role(cand, "divergieren")
                else "konvergieren"
                if has_role(cand, "konvergieren")
                else (cand.get("arc_role") or ["divergieren"])[0]
            )
            if total + dur(cand) + closer_dur <= budget and len(steps) < 4:
                add(cand, role)

        if closer and closer["slug"] not in used:
            add(closer, "schließen")

        # Ziel-String deterministisch aus den objectives der gewählten Strukturen ableiten
        # (Autoren-Methode: erst Ziele Anfang→Mitte→Ende, dann Struktur je Ziel).
        objective_by_slug = {c["slug"]: c.get("objective") for c in candidates}
        objective_string = [
            objective_by_slug[s["slug"]]
            for s in steps
            if objective_by_slug.get(s["slug"])
        ]

        summary = (
            f"Vorgeschlagener String aus {len(steps)} Strukturen "
            f"(deterministischer Stub, Gesamtdauer {total} Minuten)."
        )
        result = {
            "objective_string": objective_string,
            "string": steps,
            "total_duration": total,
            "summary": summary,
            "principle_rationale": (
                "Die Reihenfolge folgt dem Bogen (öffnen → divergieren → konvergieren → "
                "schließen) und stützt sich auf die von den gewählten Strukturen verkörperten "
                "LS-Prinzipien (deterministischer Stub)."
            ),
            "emergent_hinweis": (
                "Im Verlauf können neue oder geschärfte Ziele auftauchen; der String darf dann "
                "angepasst werden (deterministischer Stub)."
            ),
            "alternatives": [],
        }
        return json.dumps(result, ensure_ascii=False)

    # -- Konsolidierung ----------------------------------------------------- #
    def _consolidate(self, context: dict) -> str:
        """Übernimmt deterministisch Vorschlag A (beide Stub-Vorschläge sind identisch)."""
        a = context.get("proposal_a") or {}
        steps = a.get("string") or []
        total = sum(int(s.get("duration") or 0) for s in steps)
        result = {
            "objective_string": a.get("objective_string", []),
            "string": steps,
            "total_duration": total,
            "summary": a.get("summary", ""),
            "principle_rationale": a.get("principle_rationale", ""),
            "emergent_hinweis": (
                "Im Verlauf können neue oder geschärfte Ziele auftauchen; der String darf dann "
                "angepasst werden (deterministischer Stub)."
            ),
            "consolidation": (
                "Vorschlag A und B waren deckungsgleich; Vorschlag A übernommen "
                "(deterministischer Stub)."
            ),
            "alternatives": [],
        }
        return json.dumps(result, ensure_ascii=False)
