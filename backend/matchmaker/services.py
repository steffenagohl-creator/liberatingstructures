"""Deterministischer Kern + Pipeline des Matchmakings.

Hier wohnt die fest programmierte Logik, die die Qualität garantiert – egal, was
das Sprachmodell vorschlägt:

* ``normalize_diagnose`` – die Diagnose in eine saubere, typisierte Form bringen.
* ``vorfilterung`` – harte Kriterien anwenden → Kandidatenliste.
* ``validate_string`` – das **Quality Gate** (Zeit, Bogen, reale Slugs, Größe, Remote).
* ``run_interview`` / ``match`` – die zwei Pipelines hinter den Endpunkten.

Das LLM wird ausschließlich an den unscharfen Rändern (Diagnose aus Freitext,
Sequenzierung/Begründung) eingesetzt und bleibt durch Vorfilterung + Quality Gate
„eingezäunt".
"""
from __future__ import annotations

import json

from django.conf import settings

from . import prompts, tools
from .llm import LLMError, get_llm_client

# Mindest-Dimensionen, ohne die kein sinnvolles Matchmaking möglich ist.
REQUIRED_DIMENSIONS = ["zweck", "gruppengroesse", "zeitbudget", "setting"]

# Wenn die Zweck-Filterung zu wenige Kandidaten lässt, lockern wir sie wieder.
MIN_CANDIDATES = 4


# --------------------------------------------------------------------------- #
# Diagnose normalisieren                                                       #
# --------------------------------------------------------------------------- #
def _as_int(value):
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def normalize_diagnose(raw: dict | None) -> dict:
    """Bringt eine (ggf. unvollständige) Diagnose in eine saubere, typisierte Form."""
    raw = raw or {}
    return {
        "zweck": list(raw.get("zweck") or []),
        "phase_bogen": list(raw.get("phase_bogen") or []),
        "gruppengroesse": _as_int(raw.get("gruppengroesse")),
        "zeitbudget": _as_int(raw.get("zeitbudget")),
        "setting": raw.get("setting") or None,
        "psychologische_sicherheit": raw.get("psychologische_sicherheit") or None,
        "reife_ls_erfahrung": raw.get("reife_ls_erfahrung") or None,
        "scrum_kontext": raw.get("scrum_kontext") or None,
    }


# --------------------------------------------------------------------------- #
# Vorfilterung (deterministisch)                                               #
# --------------------------------------------------------------------------- #
def vorfilterung(diagnose: dict) -> list:
    """Wendet die harten Kriterien an und liefert die Kandidatenliste.

    Harte Kriterien (immer): Gruppengröße, Zeitbudget (eine Struktur muss überhaupt
    hineinpassen), Online-Tauglichkeit bei Remote, Schwierigkeit je nach Erfahrung.

    Der **Zweck** schränkt die inhaltlichen Strukturen ein – aber Öffner und Schließer
    (die Bogen-Strukturen) bleiben **immer** in der Liste. Grund: Ein Zweck wie „planen"
    hat im Katalog gar keinen passenden Öffner; ohne diese Ausnahme könnte der Bogen
    nie geschlossen werden. Bleiben am Ende zu wenige Kandidaten, lockern wir den
    Zweck-Filter ganz.
    """
    diagnose = normalize_diagnose(diagnose)

    difficulties = None
    if diagnose["reife_ls_erfahrung"] == "anfaenger":
        difficulties = ["leicht", "mittel"]

    # Schritt 1: harte Kriterien (ohne Zweck) → Grundmenge.
    hard = tools.query_structures(
        purpose_tags=None,
        group_size=diagnose["gruppengroesse"],
        max_duration=diagnose["zeitbudget"],
        online_only=diagnose["setting"] == "remote",
        difficulties=difficulties,
    )

    zweck = set(diagnose["zweck"])
    if not zweck:
        return hard

    # Schritt 2: Zweck-passende Strukturen + immer alle Öffner/Schließer (Bogen sichern).
    seen: set[str] = set()
    candidates = []
    for structure in hard:
        purpose_match = zweck & set(structure.purpose_tags or [])
        is_arc = {"öffnen", "schließen"} & set(structure.arc_role or [])
        if (purpose_match or is_arc) and structure.slug not in seen:
            seen.add(structure.slug)
            candidates.append(structure)

    # Zu wenige übrig? Dann lieber die ganze harte Grundmenge anbieten.
    if len(candidates) < MIN_CANDIDATES:
        return hard
    return candidates


# --------------------------------------------------------------------------- #
# Quality Gate (deterministisch)                                              #
# --------------------------------------------------------------------------- #
def validate_string(steps: list[dict], diagnose: dict) -> tuple[bool, list[str]]:
    """Prüft einen vorgeschlagenen String nach festen Regeln.

    :returns: ``(ok, violations)`` – ``ok`` ist ``True``, wenn keine Regel verletzt ist.
    """
    diagnose = normalize_diagnose(diagnose)
    violations: list[str] = []

    if not steps:
        return False, ["Der String ist leer."]

    slugs = [step.get("slug") for step in steps]
    structs = tools.get_structures_by_slugs([s for s in slugs if s])

    # 1) Alle Slugs müssen reale Katalog-Strukturen sein.
    unknown = [s for s in slugs if s not in structs]
    if unknown:
        violations.append("Unbekannte Struktur(en): " + ", ".join(map(str, unknown)) + ".")

    valid = [structs[s] for s in slugs if s in structs]

    # 2) Zeitsumme darf das Budget nicht überschreiten.
    total = sum(_as_int(step.get("duration")) or 0 for step in steps)
    budget = diagnose["zeitbudget"]
    if budget is not None and total > budget:
        violations.append(f"Zeitbudget überschritten: {total} > {budget} Minuten.")

    # 3) Bogen vollständig: mindestens eine öffnende und eine schließende Struktur.
    roles_union = set()
    for structure in valid:
        roles_union.update(structure.arc_role or [])
    if "öffnen" not in roles_union:
        violations.append("Kein öffnendes Element – der String hat keinen Einstieg.")
    if "schließen" not in roles_union:
        violations.append("Kein schließendes Element – der String hat keinen Abschluss.")

    # 4) Gruppengröße muss zu jeder Struktur passen.
    group = diagnose["gruppengroesse"]
    if group is not None:
        for structure in valid:
            too_small = group < structure.group_size_min
            too_big = structure.group_size_max is not None and group > structure.group_size_max
            if too_small or too_big:
                violations.append(
                    f"Gruppengröße {group} passt nicht zu „{structure.name}“ "
                    f"(empfohlen {structure.group_size_min}–"
                    f"{structure.group_size_max or '∞'})."
                )

    # 5) Bei Remote müssen alle Strukturen online-tauglich sein.
    if diagnose["setting"] == "remote":
        for structure in valid:
            if not structure.online_capable:
                violations.append(f"„{structure.name}“ ist nicht online-tauglich (Remote).")

    return len(violations) == 0, violations


# --------------------------------------------------------------------------- #
# JSON robust parsen                                                           #
# --------------------------------------------------------------------------- #
def _parse_json(raw: str) -> dict | None:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        # Toleranter Versuch: den äußersten {...}-Block herausschneiden.
        if isinstance(raw, str) and "{" in raw and "}" in raw:
            try:
                return json.loads(raw[raw.index("{") : raw.rindex("}") + 1])
            except json.JSONDecodeError:
                return None
        return None


# --------------------------------------------------------------------------- #
# Pipeline 1: Interview-Schritt                                                #
# --------------------------------------------------------------------------- #
def _compact_dimensions(schema: dict) -> list[dict]:
    """Reduziert das Diagnoseschema auf die Felder, die der Prompt/Stub braucht."""
    compact = []
    for dim in schema.get("dimensions", []):
        compact.append(
            {
                "key": dim["key"],
                "label": dim["label"],
                "hint": dim.get("hint", ""),
                "input_type": dim.get("input_type", "text"),
                "options": dim.get("options", []),
            }
        )
    return compact


def run_interview(situation: str, answers: dict | None) -> dict:
    """Extrahiert über das LLM die Diagnose aus Freitext + bisherigen Antworten.

    :returns: ``{"diagnose": {...}, "open_questions": [...], "ready": bool}``.
    """
    schema = tools.load_diagnosis_schema()
    messages = prompts.build_interview_messages(
        situation=situation or "",
        answers=answers or {},
        schema_dimensions=_compact_dimensions(schema),
        required_keys=REQUIRED_DIMENSIONS,
    )
    client = get_llm_client()
    raw = client.chat(messages, json=True)
    parsed = _parse_json(raw)
    if parsed is None:
        raise LLMError("Die Interview-Antwort des Modells war kein gültiges JSON.")

    return {
        "diagnose": parsed.get("diagnose", {}),
        "open_questions": parsed.get("open_questions", []),
        "ready": bool(parsed.get("ready", False)),
    }


# --------------------------------------------------------------------------- #
# Pipeline 2: Matchmaking                                                      #
# --------------------------------------------------------------------------- #
def _run_with_gate(messages_builder, diagnose: dict, candidate_count: int,
                   max_iter: int, client) -> dict:
    """Führt eine LLM-Stufe mit Quality-Gate-Korrekturschleife aus und verpackt das Ergebnis.

    ``messages_builder(correction)`` liefert die Nachrichten für einen Versuch (``correction`` ist
    beim ersten Versuch ``None``, danach der Mängel-Hinweis). Gibt das beste Ergebnis-Dict zurück
    (das erste Quality-Gate-konforme – sonst den jüngsten Versuch mit transparentem Hinweis).
    """
    correction = None
    best = None
    for attempt in range(1, max_iter + 1):
        raw = client.chat(messages_builder(correction), json=True)
        parsed = _parse_json(raw)
        if parsed is None:
            correction = "Die Antwort war kein gültiges JSON-Objekt. Liefere reines JSON."
            continue

        steps = parsed.get("string", []) or []
        ok, violations = validate_string(steps, diagnose)
        total = sum(_as_int(s.get("duration")) or 0 for s in steps)
        result = {
            "string": steps,
            "total_duration": total,
            "summary": parsed.get("summary", ""),
            "principle_rationale": parsed.get("principle_rationale", ""),
            "consolidation": parsed.get("consolidation", ""),
            "alternatives": parsed.get("alternatives", []),
            "quality": {"ok": ok, "violations": violations, "iterations": attempt},
            "candidate_count": candidate_count,
        }
        if ok:
            return result
        best = result
        correction = " ".join(violations)

    if best is None:
        best = {
            "string": [], "total_duration": 0, "summary": "", "principle_rationale": "",
            "consolidation": "", "alternatives": [],
            "quality": {
                "ok": False,
                "violations": ["Es konnte kein gültiger Vorschlag erzeugt werden."],
                "iterations": max_iter,
            },
            "candidate_count": candidate_count,
        }
    best["hinweis"] = (
        "Hinweis: Dieser Vorschlag erfüllt noch nicht alle Qualitätskriterien "
        "(siehe quality.violations). Bitte vor dem Einsatz prüfen."
    )
    return best


def match(diagnose_raw: dict) -> dict:
    """Erzeugt aus der Diagnose einen validierten, begründeten String.

    Ablauf: Vorfilterung → zwei unabhängige LLM-Vorschläge (Agent A & B) → Konsolidierung durch
    einen prüfenden Agenten (vergleicht Unterschiede/Gemeinsamkeiten/Optionen, wie Co-Hosts im
    offiziellen LS Selection Matchmaker) → Quality Gate mit Korrekturschleife. Über
    ``MATCHMAKER_CONSOLIDATE`` abschaltbar (dann nur ein Vorschlag).
    """
    diagnose = normalize_diagnose(diagnose_raw)
    candidates = vorfilterung(diagnose)
    candidate_dicts = [tools.serialize_candidate(c) for c in candidates]
    templates = tools.get_string_templates(
        scrum_context=diagnose["scrum_kontext"], purpose_tags=diagnose["zweck"]
    )
    template_dicts = [tools.serialize_template(t) for t in templates]
    principles = tools.load_principles()
    foundations = tools.load_foundations()

    client = get_llm_client()
    budget = diagnose["zeitbudget"]
    max_iter = getattr(settings, "MATCHMAKER_MAX_ITERATIONS", 3)
    n = len(candidate_dicts)

    def seq_builder(correction):
        return prompts.build_sequence_messages(
            diagnose, candidate_dicts, template_dicts, budget,
            principles=principles, foundations=foundations, correction=correction,
        )

    # Vorschlag von Agent A.
    proposal_a = _run_with_gate(seq_builder, diagnose, n, max_iter, client)

    if not getattr(settings, "MATCHMAKER_CONSOLIDATE", True):
        return proposal_a

    # Unabhängiger Vorschlag von Agent B, dann Konsolidierung durch einen prüfenden Agenten.
    proposal_b = _run_with_gate(seq_builder, diagnose, n, max_iter, client)

    def cons_builder(correction):
        return prompts.build_consolidation_messages(
            diagnose, candidate_dicts, budget, proposal_a, proposal_b,
            principles=principles, foundations=foundations, correction=correction,
        )

    final = _run_with_gate(cons_builder, diagnose, n, max_iter, client)
    final["drafts"] = [
        {"string": proposal_a.get("string", []), "summary": proposal_a.get("summary", "")},
        {"string": proposal_b.get("string", []), "summary": proposal_b.get("summary", "")},
    ]
    return final
