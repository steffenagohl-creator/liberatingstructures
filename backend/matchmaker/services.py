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

from catalog.i18n import localize

from . import prompts, tools
from .llm import LLMError, get_llm_client


def _name(structure) -> str:
    """Deutscher Anzeigename einer Struktur (für Quality-Gate-Meldungen)."""
    return localize(structure.name, "de")


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
        # Problem (Freitext) + vom Nutzer benanntes Ziel: Grundlage des Zweck-Schritts der
        # Autoren-Methode. Beide sind erbeten, blockieren das Matching aber nicht (Emergenz).
        "situation": (raw.get("situation") or "").strip(),
        "ziel_text": (raw.get("ziel_text") or "").strip(),
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
    nie geschlossen werden. Bleiben am Ende zu wenige Kandidaten, wird stufenweise
    gelockert: Die übrige Grundmenge wird HINTEN angefügt (Zweck-Treffer stehen vorn
    und behalten so die höchste Priorität), statt den Zweck-Filter ganz zu verwerfen.

    Zeitbudget-Reserve: Eine Struktur ist nur dann ein sinnvoller Kandidat, wenn neben
    ihr auch noch der Bogen (kürzester Öffner + kürzester Schließer) ins Budget passt –
    sonst stehen im Prompt Kandidaten, die das Quality Gate nie passieren lassen würde.
    """
    diagnose = normalize_diagnose(diagnose)

    difficulties = None
    if diagnose["reife_ls_erfahrung"] == "anfaenger":
        difficulties = ["leicht", "mittel"]

    # Schritt 1: harte Kriterien (ohne Zweck) → Grundmenge.
    # Hybrid braucht wie Remote online-taugliche Strukturen (ein Teil nimmt remote teil).
    hard = tools.query_structures(
        purpose_tags=None,
        group_size=diagnose["gruppengroesse"],
        max_duration=diagnose["zeitbudget"],
        online_only=diagnose["setting"] in ("remote", "hybrid"),
        difficulties=difficulties,
    )

    # Schritt 1b: Zeitbudget-Reserve – neben jeder Struktur muss der Bogen noch passen.
    hard = _mit_bogen_reserve(hard, diagnose["zeitbudget"])

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

    # Zu wenige übrig? Stufenweise lockern: restliche Grundmenge HINTEN anfügen –
    # die Zweck-Treffer bleiben vorn (Reihenfolge signalisiert dem LLM die Priorität).
    if len(candidates) < MIN_CANDIDATES:
        candidates.extend(s for s in hard if s.slug not in seen)
    return candidates


def _mit_bogen_reserve(structures: list, budget: int | None) -> list:
    """Filtert Strukturen heraus, neben denen der Bogen nicht mehr ins Budget passt.

    Reserve = kürzester Öffner + kürzester Schließer der Grundmenge. Kann eine Struktur
    selbst öffnen bzw. schließen, entfällt der jeweilige Anteil der Reserve.
    """
    if budget is None:
        return structures

    def dmin(s) -> int:
        return s.duration_min or 0

    openers = [dmin(s) for s in structures if "öffnen" in (s.arc_role or [])]
    closers = [dmin(s) for s in structures if "schließen" in (s.arc_role or [])]
    min_open = min(openers) if openers else 0
    min_close = min(closers) if closers else 0

    kept = []
    for s in structures:
        roles = set(s.arc_role or [])
        reserve = min_open + min_close
        if "öffnen" in roles:
            reserve = min(reserve, min_close)  # kann selbst öffnen → nur Schließer nötig
        if "schließen" in roles:
            reserve = min(reserve, min_open)  # kann selbst schließen → nur Öffner nötig
        if dmin(s) + reserve <= budget:
            kept.append(s)
    return kept


# --------------------------------------------------------------------------- #
# Quality Gate (deterministisch)                                              #
# --------------------------------------------------------------------------- #
def validate_string(
    steps: list[dict], diagnose: dict, allowed_slugs: set[str] | None = None
) -> tuple[bool, list[str]]:
    """Prüft einen vorgeschlagenen String nach festen Regeln.

    :param allowed_slugs: optional die Slugs der Vorfilterung – nur diese sind erlaubt
        (setzt z. B. die Schwierigkeits-Grenze für Anfänger deterministisch durch).
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

    # 1b) Nur Strukturen aus der Kandidatenliste der Vorfilterung sind erlaubt.
    if allowed_slugs is not None:
        outside = [s for s in slugs if s in structs and s not in allowed_slugs]
        if outside:
            violations.append(
                "Nicht in der Kandidatenliste (Vorfilterung): " + ", ".join(outside) + "."
            )

    # 1c) Keine Struktur darf doppelt im String vorkommen.
    duplicates = sorted({s for s in slugs if s and slugs.count(s) > 1})
    if duplicates:
        violations.append("Doppelte Struktur(en) im String: " + ", ".join(duplicates) + ".")

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

    # 3b) Bogen-Reihenfolge: Der String muss mit Öffnen BEGINNEN und mit Schließen ENDEN.
    first = structs.get(slugs[0]) if slugs else None
    last = structs.get(slugs[-1]) if slugs else None
    if "öffnen" in roles_union and first and "öffnen" not in (first.arc_role or []):
        violations.append(
            f"Der String beginnt nicht mit einer öffnenden Struktur – "
            f"„{_name(first)}“ kann nicht öffnen."
        )
    if "schließen" in roles_union and last and "schließen" not in (last.arc_role or []):
        violations.append(
            f"Der String endet nicht mit einer schließenden Struktur – "
            f"„{_name(last)}“ kann nicht schließen."
        )

    # 3c) Schritt-Dauer muss zur Struktur passen (innerhalb von duration_min–duration_max).
    for step in steps:
        structure = structs.get(step.get("slug"))
        if structure is None:
            continue
        duration = _as_int(step.get("duration"))
        too_short = duration is None or duration < structure.duration_min
        too_long = structure.duration_max is not None and (duration or 0) > structure.duration_max
        if too_short or too_long:
            violations.append(
                f"Dauer {duration} Min passt nicht zu „{_name(structure)}“ "
                f"(vorgesehen {structure.duration_min}–{structure.duration_max or '∞'} Min)."
            )

    # 4) Gruppengröße muss zu jeder Struktur passen.
    group = diagnose["gruppengroesse"]
    if group is not None:
        for structure in valid:
            too_small = group < structure.group_size_min
            too_big = structure.group_size_max is not None and group > structure.group_size_max
            if too_small or too_big:
                violations.append(
                    f"Gruppengröße {group} passt nicht zu „{_name(structure)}“ "
                    f"(empfohlen {structure.group_size_min}–"
                    f"{structure.group_size_max or '∞'})."
                )

    # 5) Bei Remote UND Hybrid müssen alle Strukturen online-tauglich sein.
    if diagnose["setting"] in ("remote", "hybrid"):
        for structure in valid:
            if not structure.online_capable:
                violations.append(
                    f"„{_name(structure)}“ ist nicht online-tauglich "
                    f"({diagnose['setting']})."
                )

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


def run_interview(situation: str, answers: dict | None, tier: str = "us") -> dict:
    """Extrahiert über das LLM die Diagnose aus Freitext + bisherigen Antworten.

    ``tier`` wählt den pfad-getrennten Erhebungs-Prompt (s. ``build_interview_messages``):
    ``"eu"``/``"sov"`` → vorsichtig, sonst → eingefrorener US-/Default-Prompt.

    :returns: ``{"diagnose": {...}, "open_questions": [...], "ready": bool}``.
    """
    schema = tools.load_diagnosis_schema()
    messages = prompts.build_interview_messages(
        situation=situation or "",
        answers=answers or {},
        schema_dimensions=_compact_dimensions(schema),
        required_keys=REQUIRED_DIMENSIONS,
        tier=tier,
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
                   max_iter: int, client, allowed_slugs: set[str] | None = None) -> dict:
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
        ok, violations = validate_string(steps, diagnose, allowed_slugs)
        total = sum(_as_int(s.get("duration")) or 0 for s in steps)
        result = {
            "objective_string": parsed.get("objective_string", []),
            "string": steps,
            "total_duration": total,
            "summary": parsed.get("summary", ""),
            "principle_rationale": parsed.get("principle_rationale", ""),
            "emergent_hinweis": parsed.get("emergent_hinweis", ""),
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
            "objective_string": [], "string": [], "total_duration": 0, "summary": "",
            "principle_rationale": "", "emergent_hinweis": "", "consolidation": "", "alternatives": [],
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
    principles_framing = tools.load_principles_framing()
    # Volle Ziel-Übersicht für den „Ziel-String"-Schritt der Autoren-Methode (sprachneutral grounded).
    objective_menu = tools.load_objective_menu()

    client = get_llm_client()
    budget = diagnose["zeitbudget"]
    max_iter = getattr(settings, "MATCHMAKER_MAX_ITERATIONS", 3)
    n = len(candidate_dicts)
    # Das Quality Gate setzt die Kandidatenliste durch: Das LLM darf NUR daraus wählen
    # (sonst könnten z. B. für Anfänger gefilterte schwere Strukturen zurückkommen).
    allowed = {c.slug for c in candidates}

    def seq_builder(correction):
        return prompts.build_sequence_messages(
            diagnose, candidate_dicts, template_dicts, budget,
            principles=principles, foundations=foundations, correction=correction,
            principles_framing=principles_framing, objective_menu=objective_menu,
        )

    # Vorschlag von Agent A.
    proposal_a = _run_with_gate(seq_builder, diagnose, n, max_iter, client, allowed)

    if not getattr(settings, "MATCHMAKER_CONSOLIDATE", True):
        return proposal_a

    # Unabhängiger Vorschlag von Agent B, dann Konsolidierung durch einen prüfenden Agenten.
    proposal_b = _run_with_gate(seq_builder, diagnose, n, max_iter, client, allowed)

    def cons_builder(correction):
        return prompts.build_consolidation_messages(
            diagnose, candidate_dicts, budget, proposal_a, proposal_b,
            principles=principles, foundations=foundations, correction=correction,
            principles_framing=principles_framing, objective_menu=objective_menu,
        )

    final = _run_with_gate(cons_builder, diagnose, n, max_iter, client, allowed)
    final["drafts"] = [
        {"string": proposal_a.get("string", []), "summary": proposal_a.get("summary", "")},
        {"string": proposal_b.get("string", []), "summary": proposal_b.get("summary", "")},
    ]
    return final
