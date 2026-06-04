"""DRF-Serializer des Katalogs – sprachaufgelöste, selbstbeschreibende Struktur-Ausgabe.

Jedes Feld trägt einen ``help_text`` und fließt so in die OpenAPI-Doku (``/api/docs/``)
ein. Dadurch sind die Daten gleichermaßen lesbar für Menschen, Screenreader,
Sprachsteuerung, KIs/MCP und Crawler (Leitprinzip). Zweisprachige Felder werden
anhand der Kontext-Sprache (``lang``, gesetzt von der View aus ``?lang=``) auf eine
Sprache aufgelöst; sprachneutrale Felder (Zahlen, Enums, Slugs) bleiben unverändert.
"""
from rest_framework import serializers

from .i18n import DEFAULT_LANG, localize, localize_deep


class StructureSerializer(serializers.Serializer):
    """Eine Liberating Structure, in der angefragten Sprache (``?lang=de|en``)."""

    lang = serializers.SerializerMethodField(
        help_text="Sprachcode, in dem diese Antwort aufgelöst wurde (de | en).",
    )
    structure_id = serializers.IntegerField(
        help_text="Stabile Nummer der Methode (1–43, lückenlos).",
    )
    slug = serializers.SlugField(help_text="Eindeutige Kurzkennung, z. B. 1-2-4-all.")
    name = serializers.SerializerMethodField(help_text="Anzeigename in der gewählten Sprache.")
    type = serializers.CharField(
        help_text="official | variation | punctuation | in_development.",
    )
    edition = serializers.CharField(help_text="original = die 33 Kern-LS; extended = ergänzte.")
    short_desc = serializers.SerializerMethodField(
        help_text="Verständliche Kurzbeschreibung (1–3 Sätze) in der gewählten Sprache.",
    )
    objective = serializers.SerializerMethodField(
        help_text="Kanonisches Ziel (LS Selection Matchmaker) – der Matching-Schlüssel.",
    )
    source_url = serializers.URLField(help_text="Link zur Original-Detailseite (Quelle).")
    purpose_tags = serializers.ListField(
        child=serializers.CharField(),
        help_text="Offizielle Zweck-Kategorie(n): offenlegen, teilen, analysieren, strategie, "
                  "helfen, planen, solo.",
    )
    arc_role = serializers.ListField(
        child=serializers.CharField(),
        help_text="Rolle(n) im Spannungsbogen: öffnen | divergieren | konvergieren | schließen.",
    )
    group_size_min = serializers.IntegerField(help_text="Empfohlene Mindest-Teilnehmerzahl.")
    group_size_max = serializers.IntegerField(
        allow_null=True, help_text="Empfohlene Höchstzahl; null = nach oben offen.",
    )
    duration_min = serializers.IntegerField(help_text="Mindestdauer in Minuten.")
    duration_max = serializers.IntegerField(help_text="Übliche Höchstdauer in Minuten.")
    online_capable = serializers.BooleanField(help_text="True, wenn online (Remote) gut machbar.")
    materials = serializers.SerializerMethodField(
        help_text="Materialien und Raumhinweise in der gewählten Sprache.",
    )
    difficulty = serializers.CharField(help_text="leicht | mittel | fortgeschritten.")
    typical_predecessors = serializers.ListField(
        child=serializers.CharField(), help_text="Slugs typischer Vorgänger-Strukturen.",
    )
    typical_successors = serializers.ListField(
        child=serializers.CharField(), help_text="Slugs typischer Nachfolger-Strukturen.",
    )
    scrum_use = serializers.SerializerMethodField(
        help_text="Einsatz im Scrum-Kontext (Retro, Planning, …) in der gewählten Sprache.",
    )
    design_elements = serializers.SerializerMethodField(
        help_text="Die 5 Designelemente (einladung, raum_materialien, einbindung, "
                  "gruppenkonfiguration, ablauf_dauer), sprachaufgelöst.",
    )
    description_origin = serializers.CharField(
        help_text="uebernommen (mit Attribution) oder eigen.",
    )
    attribution = serializers.SerializerMethodField(
        help_text="Namensnennung + Lizenz in der gewählten Sprache.",
    )
    icon_alt = serializers.SerializerMethodField(
        help_text="Alt-Text fürs LS-Icon (Barrierefreiheit) in der gewählten Sprache.",
    )
    embodied_principles = serializers.ListField(
        child=serializers.CharField(),
        help_text="IDs der besonders verkörperten LS-Prinzipien (P1–P10).",
    )
    guide = serializers.SerializerMethodField(
        help_text="Ausführlicher Detailguide (was_wird_moeglich, einladung, beispielsaetze, "
                  "schritte, varianten, tipps, anlaesse, material_setup, online_durchfuehrung), "
                  "vollständig sprachaufgelöst.",
    )

    # -- Sprachauflösung ---------------------------------------------------- #
    @property
    def _lang(self) -> str:
        return self.context.get("lang", DEFAULT_LANG)

    def get_lang(self, obj) -> str:
        return self._lang

    def get_name(self, obj) -> str:
        return localize(obj.name, self._lang)

    def get_short_desc(self, obj) -> str:
        return localize(obj.short_desc, self._lang)

    def get_objective(self, obj) -> str:
        return localize(obj.objective, self._lang)

    def get_materials(self, obj) -> str:
        return localize(obj.materials, self._lang)

    def get_scrum_use(self, obj) -> str:
        return localize(obj.scrum_use, self._lang)

    def get_attribution(self, obj) -> str:
        return localize(obj.attribution, self._lang)

    def get_icon_alt(self, obj) -> str:
        return localize(obj.icon_alt, self._lang)

    def get_design_elements(self, obj) -> dict:
        return localize_deep(obj.design_elements, self._lang)

    def get_guide(self, obj) -> dict:
        return localize_deep(obj.guide, self._lang)
