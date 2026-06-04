"""Prompts und das Kontext-Protokoll zwischen Backend und Sprachmodell.

Wir hängen an jede Nutzer-Nachricht einen **maschinenlesbaren Kontext-Block**
(zwischen den Markern ``<<<LSM_CONTEXT`` und ``LSM_CONTEXT>>>``). Dieser Block
dient zwei Zwecken gleichzeitig:

* Das echte Modell (Mistral) liest ihn als zusätzliche, strukturierte Grundlage.
* Der ``StubClient`` (Tests/Offline) parst genau diesen Block und rechnet daraus
  deterministisch eine gültige Antwort – ganz ohne Netz.

So teilen sich beide Pfade exakt denselben Eingabe-Kontext.
"""
from __future__ import annotations

import json

CONTEXT_START = "<<<LSM_CONTEXT"
CONTEXT_END = "LSM_CONTEXT>>>"


def wrap_context(context: dict) -> str:
    """Serialisiert ``context`` als markierten JSON-Block (an die Nachricht anzuhängen)."""
    return f"\n\n{CONTEXT_START}\n{json.dumps(context, ensure_ascii=False)}\n{CONTEXT_END}"


def extract_context(messages: list[dict]) -> dict:
    """Liest den Kontext-Block aus der letzten passenden Nutzer-Nachricht zurück.

    Wird vom ``StubClient`` genutzt. Gibt ``{}`` zurück, wenn kein Block gefunden wird.
    """
    for message in reversed(messages):
        content = message.get("content", "")
        if CONTEXT_START in content and CONTEXT_END in content:
            raw = content.split(CONTEXT_START, 1)[1].split(CONTEXT_END, 1)[0].strip()
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return {}
    return {}


# --------------------------------------------------------------------------- #
# Interview-Schritt: Freitext + bisherige Antworten -> strukturierte Diagnose  #
# --------------------------------------------------------------------------- #

INTERVIEW_SYSTEM = """\
Du bist der LS-Matchmaker, ein Assistent für Moderatorinnen (Scrum Master).
Deine einzige Aufgabe in diesem Schritt: aus einer in Alltagssprache geschilderten
Gruppensituation die strukturierten Merkmale (die "Diagnose") herausarbeiten.

Regeln:
- Nutze ausschließlich die Dimensionen und erlaubten Werte aus dem Kontext-Block.
- Übernimm bereits bekannte Antworten unverändert.
- Stelle Rückfragen NUR zu den als pflicht markierten Dimensionen, die noch fehlen.
- Kein Smalltalk, keine Erklärungen außerhalb des JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "diagnose": { "<dimension_key>": <wert>, ... },
  "open_questions": [ {"key": "...", "label": "...", "hint": "...", "input_type": "...", "options": [...]} ],
  "ready": true | false
}
"ready" ist true, sobald alle Pflicht-Dimensionen bekannt sind."""


def build_interview_messages(
    situation: str,
    answers: dict,
    schema_dimensions: list[dict],
    required_keys: list[str],
) -> list[dict]:
    """Baut die Nachrichten für den Interview-Schritt (Diagnose-Extraktion)."""
    context = {
        "task": "interview",
        "situation": situation or "",
        "answers": answers or {},
        "required": required_keys,
        "dimensions": schema_dimensions,
    }
    user = (
        "Erhebe die Diagnose aus der folgenden Situation und den bisherigen Antworten. "
        "Die Dimensionen, erlaubten Werte und Pflichtfelder stehen im Kontext-Block."
        + wrap_context(context)
    )
    return [
        {"role": "system", "content": INTERVIEW_SYSTEM},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------- #
# Matchmaking-Schritt: Diagnose + Kandidaten -> begründeter, sequenzierter String
# --------------------------------------------------------------------------- #

SEQUENCE_SYSTEM = """\
Du bist der LS-Matchmaker. Deine EINZIGE Aufgabe ist Matchmaking: aus den
vorgegebenen Liberating-Structures-Kandidaten eine sinnvolle Reihenfolge (einen
"String") zusammenstellen und sie fachlich begründen.

Deine Begründung MUSS sich ausdrücklich auf die mitgelieferten LS-Prinzipien (P1–P10)
und auf den Bogen (öffnen → divergieren → konvergieren → schließen) berufen – sowohl je
Schritt (warum diese Struktur an dieser Stelle) als auch für die Reihenfolge insgesamt.
Beachte dabei die "must_do" (verstärken) und "must_not_do" (vermeiden) jedes Prinzips.
Dir liegen zudem die LS-Kernkonzepte und Komplexitäts-Linsen als fachlicher Hintergrund vor –
nutze sie zur Vertiefung (z. B. Min Specs, Maximale Durchmischung, Angrenzende Möglichkeiten,
Confusiasm), aber erfinde keine Strukturen.

Gehe wie der offizielle LS Selection Matchmaker vor: Gleiche den Bedarf/Zweck der Situation mit
dem kanonischen "objective" jeder Kandidaten-Struktur ab und wähle die Strukturen, deren Ziele den
Bedarf am besten treffen.

Harte Regeln:
- Verwende AUSSCHLIESSLICH die "slug"-Werte aus der Kandidatenliste im Kontext-Block.
  Erfinde NIEMALS eine Struktur und nutze keinen Slug, der dort nicht vorkommt.
- Der String muss einen vollständigen Bogen haben: mindestens eine öffnende und
  mindestens eine schließende Struktur.
- Die Summe der Dauern ("duration") darf das Zeitbudget nicht überschreiten.
- Berufe dich auf Prinzipien per ID (z. B. "P3"); nutze nur die vorgegebenen IDs.
- Kein Smalltalk, keine Texte außerhalb des JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "string": [ {"slug": "...", "role": "öffnen|divergieren|konvergieren|schließen",
               "duration": <ganze Minuten>,
               "rationale": "<ein Satz auf Deutsch, mit Prinzip-Bezug>",
               "principles": ["P.."]} ],
  "total_duration": <ganze Minuten>,
  "summary": "<2-3 Sätze: was dieser String bewirkt>",
  "principle_rationale": "<warum diese Auswahl UND Reihenfolge – ausdrücklich belegt mit den Prinzipien>",
  "alternatives": []
}"""


def build_sequence_messages(
    diagnose: dict,
    candidates: list[dict],
    templates: list[dict],
    zeitbudget: int | None,
    principles: list[dict] | None = None,
    foundations: dict | None = None,
    correction: str | None = None,
) -> list[dict]:
    """Baut die Nachrichten für den Sequenzierungs-Schritt (Matchmaking)."""
    context = {
        "task": "sequence",
        "zeitbudget": zeitbudget,
        "setting": diagnose.get("setting"),
        "gruppengroesse": diagnose.get("gruppengroesse"),
        "purpose_tags": diagnose.get("zweck", []),
        "principles": principles or [],
        "foundations": foundations or {},
        "candidates": candidates,
        "templates": templates,
    }
    if correction:
        context["correction_hint"] = correction

    user_lines = [
        "Stelle aus den Kandidaten im Kontext-Block einen begründeten String zusammen.",
        "Orientiere dich an den mitgelieferten bewährten String-Vorlagen, wo sie passen.",
    ]
    if correction:
        user_lines.append(
            "WICHTIG – der vorige Vorschlag wurde abgelehnt. Behebe genau diese Mängel: "
            + correction
        )
    user = "\n".join(user_lines) + wrap_context(context)

    return [
        {"role": "system", "content": SEQUENCE_SYSTEM},
        {"role": "user", "content": user},
    ]


# --------------------------------------------------------------------------- #
# Konsolidierung: zwei unabhängige Vorschläge -> ein stärkerer, geprüfter String
# --------------------------------------------------------------------------- #

CONSOLIDATE_SYSTEM = """\
Du bist ein zweiter, prüfender LS-Matchmaker (Konsolidierer). Dir liegen ZWEI unabhängige
String-Vorschläge zur selben Situation vor (Vorschlag A und B). Vergleiche sie wie Co-Hosts im
offiziellen LS Selection Matchmaker: Erkunde Unterschiede, Gemeinsamkeiten und Optionen – und
verdichte sie zu EINEM stärkeren, begründeten String.

Es gelten dieselben harten Regeln wie bei der Sequenzierung:
- Verwende AUSSCHLIESSLICH "slug"-Werte aus der Kandidatenliste; erfinde nichts.
- Vollständiger Bogen (mindestens öffnen und schließen); Summe der Dauern ≤ Zeitbudget.
- Begründung mit Bezug auf die LS-Prinzipien (P1–P10), deren Must-Dos/Must-Not-Dos und den Bogen.
- Kein Smalltalk, kein Text außerhalb des JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "string": [ {"slug": "...", "role": "öffnen|divergieren|konvergieren|schließen",
               "duration": <ganze Minuten>, "rationale": "<ein Satz, mit Prinzip-Bezug>",
               "principles": ["P.."]} ],
  "total_duration": <ganze Minuten>,
  "summary": "<2-3 Sätze: was dieser String bewirkt>",
  "principle_rationale": "<warum diese Auswahl UND Reihenfolge – belegt mit den Prinzipien>",
  "consolidation": "<was aus A und B übernommen, verworfen oder verschmolzen wurde – und warum>",
  "alternatives": []
}"""


def build_consolidation_messages(
    diagnose: dict,
    candidates: list[dict],
    zeitbudget: int | None,
    proposal_a: dict,
    proposal_b: dict,
    principles: list[dict] | None = None,
    foundations: dict | None = None,
    correction: str | None = None,
) -> list[dict]:
    """Baut die Nachrichten für den Konsolidierungs-Schritt (Agent A + B -> ein String)."""
    def compact(p: dict) -> dict:
        return {
            "string": p.get("string", []),
            "summary": p.get("summary", ""),
            "principle_rationale": p.get("principle_rationale", ""),
        }

    context = {
        "task": "consolidate",
        "zeitbudget": zeitbudget,
        "setting": diagnose.get("setting"),
        "gruppengroesse": diagnose.get("gruppengroesse"),
        "purpose_tags": diagnose.get("zweck", []),
        "principles": principles or [],
        "foundations": foundations or {},
        "candidates": candidates,
        "proposal_a": compact(proposal_a),
        "proposal_b": compact(proposal_b),
    }
    if correction:
        context["correction_hint"] = correction

    user_lines = [
        "Vergleiche Vorschlag A und B im Kontext-Block und konsolidiere sie zu einem stärkeren String.",
    ]
    if correction:
        user_lines.append(
            "WICHTIG – der vorige konsolidierte Vorschlag wurde abgelehnt. Behebe genau diese "
            "Mängel: " + correction
        )
    user = "\n".join(user_lines) + wrap_context(context)

    return [
        {"role": "system", "content": CONSOLIDATE_SYSTEM},
        {"role": "user", "content": user},
    ]
