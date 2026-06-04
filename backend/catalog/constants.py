"""Erlaubte Werte (eine Quelle der Wahrheit) – gespiegelt aus data/structures.json.

Diese Listen werden von den Modellen (Choices), den Import-Commands (Validierung) und
den Tests genutzt, damit überall dieselben zulässigen Werte gelten.
"""

# Edition: steuert die spätere App-Umschaltung „klein (33)" ↔ „Extended (alle)".
EDITIONS = ["original", "extended"]

# Klassifikation einer Struktur im „33+"-Modell.
TYPES = ["official", "variation", "punctuation", "in_development"]

# Zweck-Kategorien (Purpose-Matchmaker).
PURPOSE_TAGS = ["offenlegen", "teilen", "analysieren", "strategie", "helfen", "planen", "solo"]

# Rolle im Spannungsbogen einer Session.
ARC_ROLES = ["öffnen", "divergieren", "konvergieren", "schließen"]

# Schwierigkeitsgrad der Moderation.
DIFFICULTIES = ["leicht", "mittel", "fortgeschritten"]

# Herkunft der Beschreibung (übernommen mit Attribution oder selbst verfasst).
DESCRIPTION_ORIGINS = ["uebernommen", "eigen"]

# Scrum-Kontext-Presets (für String-Templates und das Diagnoseschema).
SCRUM_CONTEXTS = [
    "retrospektive",
    "planning",
    "review",
    "daily",
    "refinement",
    "team-start",
]

# IDs der 10 Liberating-Structures-Prinzipien (Details in data/ls_principles.json).
PRINCIPLE_IDS = ["P1", "P2", "P3", "P4", "P5", "P6", "P7", "P8", "P9", "P10"]


def as_choices(values):
    """Wandelt eine Werteliste in Django-Choices [(wert, wert), ...] um."""
    return [(v, v) for v in values]
