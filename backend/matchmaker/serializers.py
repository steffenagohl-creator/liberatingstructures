"""DRF-Serializer für Interview und Matchmaking.

Sie validieren die Eingaben **und** beschreiben Request/Response für die
OpenAPI-Doku (`/api/docs/`) – damit die Endpunkte für Menschen, KIs/MCP und
Crawler selbsterklärend sind (Leitprinzip).
"""
from rest_framework import serializers


class DiagnoseSerializer(serializers.Serializer):
    """Die strukturierten Merkmale einer Situation (Diagnoseschema).

    Nach der Autoren-Methode (Selection Matchmaker) gehören dazu auch das geschilderte
    Problem (``situation``) und das vom Nutzer benannte Ziel (``ziel_text``) – beide erbeten,
    aber nicht blockierend (Ziele dürfen im Prozess emergent auftauchen/sich schärfen).
    """

    situation = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="Das geschilderte Problem in eigenen Worten (Freitext).",
    )
    ziel_text = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="Das vom Nutzer benannte Ziel: was soll am Ende anders/erreicht sein? (Freitext)",
    )
    zweck = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
        help_text="Zweck-Kategorien, z. B. offenlegen, planen, helfen.",
    )
    phase_bogen = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
        help_text="Phase(n) im Bogen: öffnen/divergieren/konvergieren/schließen.",
    )
    gruppengroesse = serializers.IntegerField(
        required=False, allow_null=True, help_text="Anzahl der Teilnehmenden.",
    )
    zeitbudget = serializers.IntegerField(
        required=False, allow_null=True, help_text="Verfügbare Gesamtzeit in Minuten.",
    )
    setting = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="praesenz | remote | hybrid.",
    )
    psychologische_sicherheit = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="niedrig | mittel | hoch.",
    )
    reife_ls_erfahrung = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="anfaenger | fortgeschritten.",
    )
    scrum_kontext = serializers.CharField(
        required=False, allow_blank=True, allow_null=True,
        help_text="Optionales Preset, z. B. retrospektive, planning.",
    )


# -- Interview -------------------------------------------------------------- #
class InterviewRequestSerializer(serializers.Serializer):
    """Eingabe des Interview-Schritts: Freitext + bisher gegebene Antworten."""

    situation = serializers.CharField(
        help_text="Die in Alltagssprache geschilderte Gruppensituation.",
    )
    answers = serializers.DictField(
        required=False, default=dict,
        help_text="Bereits beantwortete Diagnose-Dimensionen (Key → Wert).",
    )
    tier = serializers.CharField(
        required=False, default="us",
        help_text=(
            "Souveränitäts-/Modellpfad: 'eu'/'sov' nutzen die vorsichtige Erhebung "
            "(errät nichts, Korrekturen gewinnen); sonst der eingefrorene US-/Default-Prompt."
        ),
    )


class OpenQuestionSerializer(serializers.Serializer):
    """Eine offene Rückfrage des Interviews (für die adaptive UI in AP4)."""

    key = serializers.CharField(help_text="Dimension, die noch fehlt.")
    label = serializers.CharField(help_text="Frage-Text für die Nutzerin.")
    hint = serializers.CharField(required=False, allow_blank=True, help_text="Hilfetext.")
    input_type = serializers.CharField(help_text="Eingabetyp, z. B. multi_choice, number.")
    options = serializers.ListField(
        required=False, default=list, help_text="Auswahloptionen, falls vorhanden.",
    )


class InterviewResponseSerializer(serializers.Serializer):
    """Antwort des Interview-Schritts."""

    diagnose = serializers.DictField(help_text="Bisher erhobene Diagnose-Merkmale.")
    open_questions = OpenQuestionSerializer(many=True)
    ready = serializers.BooleanField(
        help_text="True, wenn alle Pflicht-Dimensionen vorliegen (matchmaking-bereit).",
    )


# -- Matchmaking ------------------------------------------------------------ #
class MatchRequestSerializer(serializers.Serializer):
    """Eingabe des Matchmakings: die (vollständige) Diagnose."""

    diagnose = DiagnoseSerializer()


class StringStepSerializer(serializers.Serializer):
    """Ein Schritt im vorgeschlagenen String."""

    slug = serializers.CharField(help_text="Slug der Struktur (real im Katalog).")
    role = serializers.CharField(help_text="Rolle im Bogen für diesen Schritt.")
    duration = serializers.IntegerField(help_text="Geplante Dauer in Minuten.")
    rationale = serializers.CharField(
        help_text="Ein-Satz-Begründung für diesen Schritt (mit Bezug auf ein LS-Prinzip).",
    )
    principles = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
        help_text="IDs der LS-Prinzipien (P1–P10), die diesen Schritt begründen.",
    )


class QualitySerializer(serializers.Serializer):
    """Transparenter Status des Quality Gate."""

    ok = serializers.BooleanField(help_text="True, wenn alle Qualitätsregeln erfüllt sind.")
    violations = serializers.ListField(
        child=serializers.CharField(), help_text="Liste verletzter Regeln (leer, wenn ok).",
    )
    iterations = serializers.IntegerField(help_text="Anzahl benötigter Versuche.")


class MatchResponseSerializer(serializers.Serializer):
    """Antwort des Matchmakings: der validierte, begründete String."""

    objective_string = serializers.ListField(
        child=serializers.CharField(), required=False, default=list,
        help_text="Der String von Zielen (Anfang bis Mitte bis Ende) aus der Autoren-Methode, aus "
                  "dem der String von Strukturen abgeleitet wurde.",
    )
    string = StringStepSerializer(many=True)
    total_duration = serializers.IntegerField(help_text="Summe der Schritt-Dauern in Minuten.")
    summary = serializers.CharField(help_text="Kurze Zusammenfassung, was der String bewirkt.")
    principle_rationale = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Begründung von Auswahl UND Reihenfolge, belegt mit den LS-Prinzipien.",
    )
    emergent_hinweis = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Wo im Verlauf neue/echte Ziele auftauchen können und dass der String dann "
                  "angepasst werden darf (Dynamic Incompleteness).",
    )
    consolidation = serializers.CharField(
        required=False, allow_blank=True,
        help_text="Was der Konsolidierer aus den zwei Vorschlägen übernommen/verschmolzen hat.",
    )
    alternatives = serializers.ListField(
        required=False, default=list, help_text="Optionale Alternativen (v1: meist leer).",
    )
    quality = QualitySerializer()
    candidate_count = serializers.IntegerField(
        help_text="Anzahl Kandidaten nach der Vorfilterung.",
    )
    hinweis = serializers.CharField(
        required=False, help_text="Nur gesetzt, wenn der Vorschlag nicht voll Gate-konform ist.",
    )
    drafts = serializers.ListField(
        required=False, default=list,
        help_text="Die zwei unabhängigen Vorentwürfe (Agent A & B) zur Transparenz.",
    )
