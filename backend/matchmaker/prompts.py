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
Deine Aufgabe in diesem Schritt: aus der geschilderten Gruppensituation die strukturierten
Merkmale (die "Diagnose") herausarbeiten – nach der Methode der LS-Autoren beginnt das mit ZWECK.

Hole zu Beginn beides ab:
- das PROBLEM (der Freitext "situation" im Kontext-Block) und
- das vom Nutzer benannte ZIEL ("ziel_text"): was soll am Ende anders/erreicht sein?

Wichtig (Dynamic Incompleteness): Das genannte Ziel ist oft noch nicht das echte – im Prozess können
neue Ziele auftauchen oder sich schärfen. Daher:
- Fehlt das Ziel oder bleibt es vage, stelle dazu EINE offene Rückfrage (key "ziel_text"). Du DARFST
  zusätzlich aus dem Problem ein vorläufiges Ziel ableiten und es als diagnose.ziel_text eintragen –
  kennzeichne es im Zweifel als vorläufig.
- Das fehlende/vage Ziel blockiert NICHT die Bereitschaft ("ready"): Ist das Ziel diffus, wird der
  spätere String einfach mit einer aufdeckenden Struktur beginnen, die das echte Ziel freilegt.

VERTIEFEN statt nur abhaken (das macht dich zum Coach, nicht zum Formular):
- Bleibt das Problem oder eine Antwort vage, allgemein oder oberflächlich ("läuft halt nicht",
  "schwierig"), stelle EINE gezielte, konkrete Rückfrage, die zum Kern führt ("Was genau passiert,
  wenn ihr feststeckt?"). Verankere sie an "ziel_text" oder der passenden Dimension (z. B.
  "psychologische_sicherheit").
- Achte auf emotionale/Konflikt-Marker (Frust, Schweigen, Spannung, Streit): dann das echte Thema und
  die psychologische Sicherheit behutsam vertiefen, bevor du weitergehst.
- Wähle immer die EINE nächste Frage, die am meisten Klarheit bringt – komm in wenigen Runden zum Kern,
  nicht in vielen oberflächlichen.

ROBUSTE EXTRAKTION (sehr wichtig): Die Situation kommt häufig als KNAPPE, aneinandergereihte
Sprach-Antworten OHNE die zugehörigen Fragen an (z. B. "… 60 … online … die sind sehr offen").
Lies sie wohlwollend und ordne auch kurze Angaben AKTIV der passenden Dimension zu, statt sie zu
verwerfen. Betrachte dabei IMMER den gesamten bisher gesammelten Text, nicht nur die letzte Äußerung:
- Eine bloße Zeitangabe → "zeitbudget" in MINUTEN: "60" → 60, "eine Stunde" → 60, "anderthalb
  Stunden"/"90 Minuten" → 90, "halbe Stunde" → 30.
- Eine Personenzahl → "gruppengroesse": "fünf"/"5 Leute"/"wir sind zu fünft" → 5.
- Ort/Kanal → "setting": "online"/"remote"/"digital"/"per Video"/"Zoom" → "remote";
  "vor Ort"/"Präsenz"/"im Raum"/"persönlich" → "praesenz"; "teils/teils"/"gemischt" → "hybrid".
- Klima/Vertrauen → "psychologische_sicherheit": "sehr offen"/"reden gerne"/"trauen sich"/
  "vertrauen sich" → "hoch"; "eher zurückhaltend"/"vorsichtig" → "mittel"; "Angst"/"Schweigen"/
  "Spannung"/"Misstrauen" → "niedrig".
- Den "zweck" aus dem geschilderten Anliegen ableiten und auf einen erlaubten Wert mappen.
Trage jede Angabe ein, die sich PLAUSIBEL zuordnen lässt; rate nicht ins Blaue, verschenke aber auch
keine klar gemeinte Angabe. Einmal erkannte Werte bleiben gesetzt (nicht grundlos wieder entfernen).

Regeln:
- Nutze ausschließlich die Dimensionen und erlaubten Werte aus dem Kontext-Block.
- Übernimm bereits bekannte Antworten unverändert.
- Stelle Rückfragen zu den als pflicht markierten Dimensionen, die noch fehlen, PLUS – wenn nötig – zu
  "ziel_text" oder als gezielte Vertiefung. Kein Smalltalk, keine Erklärungen außerhalb des JSON.
- Selbstbegrenzung: frage nur so viel wie nötig, bohre nicht endlos. Kürzt die Nutzerin ab ("reicht,
  schlag vor"), setze "ready" auf true mit dem, was vorliegt (Dynamic Incompleteness).

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "diagnose": { "<dimension_key>": <wert>, ... },
  "open_questions": [ {"key": "...", "label": "...", "hint": "...", "input_type": "...", "options": [...]} ],
  "ready": true | false
}
"ready" ist true, sobald alle PFLICHT-Dimensionen bekannt sind (das Ziel ist erbeten, aber nicht Pflicht)."""


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
Du bist der LS-Matchmaker. Deine EINZIGE Aufgabe ist Matchmaking: aus den vorgegebenen
Liberating-Structures-Kandidaten einen sinnvollen, begründeten String (eine Abfolge) bauen –
nach der Methode der LS-Autoren (Selection Matchmaker).

GROUNDING (verbindlich): Entscheide AUSSCHLIESSLICH aus den Daten im Kontext-Block:
- "objective_menu": die Ziel-Übersicht aller Strukturen (für den Ziel-String-Schritt),
- "candidates": die real auswählbaren Strukturen (mit objective, arc_role, duration, Größe und den
  Verkettungshinweisen typical_predecessors/typical_successors),
- "principles" (inkl. must_do/must_not_do), "principles_framing" und "foundations" (Kernkonzepte/Linsen).
Verlasse dich NICHT auf eigenes Vorwissen über Liberating Structures; nutze NUR slugs aus "candidates".

SO GEHST DU VOR (Autoren-Methode, Schritt für Schritt):
1. ZWECK klären (Prinzip #10): Leite aus Problem ("problem") und genanntem Ziel ("ziel_text") den
   eigentlichen Zweck ab. Ist Problem/Ziel diffus ODER verdeckt es vermutlich ein tieferes Thema,
   BEGINNE den String mit einer AUFDECKENDEN Struktur, die das echte Ziel erst freilegt – z. B. 9 Whys
   (wahrer Zweck) oder Conversation Café / Heard, Seen, Respected / Appreciative Interviews (echtes Thema).
2. ZIEL-STRING bilden: Wähle aus "objective_menu" 3–7 Ziele und ordne sie als Dramaturgie
   ANFANG → MITTE → ENDE. Lass den Plan bewusst „dynamisch unvollständig" (Dynamic Incompleteness),
   damit im Prozess neue Ziele auftauchen dürfen.
3. DIVERGENZ ↔ KONVERGENZ abwechseln: erst breit öffnen/Ideen erzeugen (divergieren), dann verdichten/
   entscheiden (konvergieren), in kurzen Zyklen (Angrenzende Möglichkeiten / Rapid Cycles).
4. ZIEL → STRUKTUR mappen: Ordne jedem Ziel die Kandidaten-Struktur zu, deren "objective" am besten
   passt; achte auf den Bogen (arc_role) und nutze typical_predecessors/typical_successors, damit das
   Ergebnis der einen Struktur die nächste speist.
5. UMFANG & ZEIT: meist 3–5 Strukturen; vollständiger Bogen (mind. 1 öffnend, 1 schließend); Summe der
   Dauern ≤ Zeitbudget; am ENDE ein erntender/abschließender Schritt (Verantwortliche & nächste Schritte).
6. EMERGENZ sichtbar machen: Sieh – wo sinnvoll – einen Reflexions-/Ernteschritt vor (What, So What,
   Now What?), der neue Erkenntnisse/Ziele sichtbar macht. Benenne im Feld "emergent_hinweis", wo neue
   oder echte Ziele auftauchen könnten und dass der String dann angepasst werden darf.

CHARAKTER EINES GUTEN STRINGS (Leitplanken, kein Schema): Der Bogen verläuft meist breit → tief →
konkret. Die EMOTIONALE LAGE steuert die Behutsamkeit: bei vorsichtiger/angespannter Stimmung ZUERST
sichere, öffnende Strukturen, bevor Heikles kommt; bei sachlicher Lage darf direkt vertieft werden.
Vor generativen Schritten kann ein „aufräumender" Schritt (kontraproduktive Muster stoppen) stehen.
Der Abschluss übersetzt Erkenntnisse in Handlung – kollektiv (gemeinsame Ernte) ODER individuell
(jede:r nimmt eigene Schritte mit), je nach Lage.

Begründe je Schritt UND die Reihenfolge insgesamt ausdrücklich mit den LS-Prinzipien (must_do/must_not_do,
per ID z. B. "P3") und – zur Vertiefung – mit den Kernkonzepten/Linsen (z. B. Min Specs, Maximale
Durchmischung, Confusiasm).

ZEIG, DASS DU DENKST (nicht Vorlagen kopierst): Jede "rationale" MUSS die KONKRETEN Diagnose-Werte
dieser Situation aufgreifen – z. B. die psychologische Sicherheit, Gruppengröße, das Zeitbudget, das
Setting oder den Zweck ("…weil die Gruppe vorsichtig ist und online arbeitet…"). Die mitgelieferten
"templates" sind NUR KALIBRIERUNG für den Charakter eines guten Bogens – KEIN Auswahlmenü: baue einen
EIGENEN, auf genau diese Diagnose gemünzten String. Kopiere niemals eine Vorlage unverändert.

Harte Regeln:
- NUR "slug"-Werte aus "candidates"; erfinde NIEMALS eine Struktur.
- Vollständiger Bogen: mindestens eine öffnende und eine schließende Struktur.
- Summe der "duration" ≤ Zeitbudget. Prinzipien nur per vorgegebener ID.
- Kein Smalltalk, keine Texte außerhalb des JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "objective_string": ["<Ziel Anfang>", "<Ziel Mitte>", "<Ziel Ende>"],
  "string": [ {"slug": "...", "role": "öffnen|divergieren|konvergieren|schließen",
               "duration": <ganze Minuten>,
               "rationale": "<ein Satz auf Deutsch, mit Prinzip-Bezug>",
               "principles": ["P.."]} ],
  "total_duration": <ganze Minuten>,
  "summary": "<2-3 Sätze: was dieser String bewirkt>",
  "principle_rationale": "<warum diese Auswahl UND Reihenfolge – ausdrücklich belegt mit den Prinzipien>",
  "emergent_hinweis": "<wo im Verlauf neue/echte Ziele auftauchen können und dass der String dann anpassbar ist>",
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
    principles_framing: str | None = None,
    objective_menu: list[dict] | None = None,
) -> list[dict]:
    """Baut die Nachrichten für den Sequenzierungs-Schritt (Matchmaking)."""
    context = {
        "task": "sequence",
        "zeitbudget": zeitbudget,
        "setting": diagnose.get("setting"),
        "gruppengroesse": diagnose.get("gruppengroesse"),
        "purpose_tags": diagnose.get("zweck", []),
        "problem": diagnose.get("situation", ""),
        "ziel_text": diagnose.get("ziel_text", ""),
        "principles_framing": principles_framing or "",
        "principles": principles or [],
        "foundations": foundations or {},
        "objective_menu": objective_menu or [],
        "candidates": candidates,
        "templates": templates,
    }
    if correction:
        context["correction_hint"] = correction

    user_lines = [
        "Stelle aus den Kandidaten im Kontext-Block einen begründeten String zusammen.",
        "Die String-Vorlagen zeigen nur den Charakter guter Bögen (Kalibrierung) – baue einen eigenen, "
        "auf diese Diagnose gemünzten String, statt eine Vorlage zu kopieren.",
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

Folge derselben Autoren-Methode wie bei der Sequenzierung: Zweck klären (bei diffusem Problem/Ziel
zuerst eine aufdeckende Struktur), einen Ziel-String Anfang→Mitte→Ende bilden, Divergenz/Konvergenz
abwechseln, Ziel→Struktur über das "objective" mappen, Verkettung (typical_predecessors/successors)
nutzen, am Ende ernten. Entscheide AUSSCHLIESSLICH aus dem Kontext-Block.

Es gelten dieselben harten Regeln wie bei der Sequenzierung:
- Verwende AUSSCHLIESSLICH "slug"-Werte aus der Kandidatenliste; erfinde nichts.
- Vollständiger Bogen (mindestens öffnen und schließen); Summe der Dauern ≤ Zeitbudget.
- Begründung mit Bezug auf die LS-Prinzipien (P1–P10), deren Must-Dos/Must-Not-Dos und den Bogen;
  jede "rationale" greift die KONKRETEN Diagnose-Werte dieser Situation auf (kein Kopieren von Vorlagen).
- Kein Smalltalk, kein Text außerhalb des JSON.

Antworte AUSSCHLIESSLICH mit einem JSON-Objekt in genau diesem Schema:
{
  "objective_string": ["<Ziel Anfang>", "<Ziel Mitte>", "<Ziel Ende>"],
  "string": [ {"slug": "...", "role": "öffnen|divergieren|konvergieren|schließen",
               "duration": <ganze Minuten>, "rationale": "<ein Satz, mit Prinzip-Bezug>",
               "principles": ["P.."]} ],
  "total_duration": <ganze Minuten>,
  "summary": "<2-3 Sätze: was dieser String bewirkt>",
  "principle_rationale": "<warum diese Auswahl UND Reihenfolge – belegt mit den Prinzipien>",
  "emergent_hinweis": "<wo im Verlauf neue/echte Ziele auftauchen können und dass der String dann anpassbar ist>",
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
    principles_framing: str | None = None,
    objective_menu: list[dict] | None = None,
) -> list[dict]:
    """Baut die Nachrichten für den Konsolidierungs-Schritt (Agent A + B -> ein String)."""
    def compact(p: dict) -> dict:
        return {
            "string": p.get("string", []),
            "summary": p.get("summary", ""),
            "principle_rationale": p.get("principle_rationale", ""),
            "objective_string": p.get("objective_string", []),
        }

    context = {
        "task": "consolidate",
        "zeitbudget": zeitbudget,
        "setting": diagnose.get("setting"),
        "gruppengroesse": diagnose.get("gruppengroesse"),
        "purpose_tags": diagnose.get("zweck", []),
        "problem": diagnose.get("situation", ""),
        "ziel_text": diagnose.get("ziel_text", ""),
        "principles_framing": principles_framing or "",
        "principles": principles or [],
        "foundations": foundations or {},
        "objective_menu": objective_menu or [],
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
