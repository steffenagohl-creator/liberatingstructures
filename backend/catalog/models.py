"""Datenmodell des LS-Katalogs.

Jedes Feld ist sprechend benannt und mit ``help_text`` beschriftet (Leitprinzip:
selbstbeschreibend bis in den Code – für Menschen, KIs/MCP und Crawler).
"""
from django.contrib.postgres.fields import ArrayField
from django.db import models

from . import constants


class Structure(models.Model):
    """Eine einzelne Liberating Structure (Mikrostruktur) mit allen Metadaten.

    Entspricht 1:1 einem Eintrag aus ``data/structures.json`` (siehe data/schema.md).
    """

    structure_id = models.PositiveIntegerField(
        unique=True, help_text="Stabile Nummer der Methode aus dem Seed-Datensatz."
    )
    name = models.CharField(max_length=120, help_text="Anzeigename, zum Beispiel 1-2-4-All.")
    slug = models.SlugField(
        max_length=80, unique=True,
        help_text="Kurzkennung für Verknüpfungen, zum Beispiel 1-2-4-all.",
    )
    type = models.CharField(
        max_length=20, choices=constants.as_choices(constants.TYPES), default="official",
        help_text="official | variation | punctuation | in_development.",
    )
    base_structure = models.CharField(
        max_length=80, blank=True, default="",
        help_text="Bei Varianten: Slug der Original-Struktur. Sonst leer.",
    )
    edition = models.CharField(
        max_length=20, choices=constants.as_choices(constants.EDITIONS), default="original",
        help_text="original = die 33 Kern-LS; extended = später ergänzte.",
    )
    short_desc = models.TextField(help_text="Verständliche Kurzbeschreibung (1–3 Sätze).")
    objective = models.CharField(
        max_length=300, blank=True, default="",
        help_text="Kanonisches Ziel (LS Selection Matchmaker): das eine Ziel, das die Struktur "
                  "erfüllt – Matching-Schlüssel. Quelle: data/ls_objectives.json.",
    )
    source_url = models.URLField(max_length=300, help_text="Link zur Original-Detailseite (Quelle).")

    purpose_tags = ArrayField(
        models.CharField(max_length=20), default=list,
        help_text="Zweck-Kategorien (eine oder mehrere) aus den erlaubten Werten.",
    )
    arc_role = ArrayField(
        models.CharField(max_length=20), default=list,
        help_text="Bogen-Rolle(n): öffnen/divergieren/konvergieren/schließen.",
    )

    group_size_min = models.PositiveIntegerField(help_text="Empfohlene Mindest-Teilnehmerzahl.")
    group_size_max = models.PositiveIntegerField(
        null=True, blank=True, help_text="Empfohlene Höchstzahl; leer = nach oben offen.",
    )
    duration_min = models.PositiveIntegerField(help_text="Mindestdauer in Minuten.")
    duration_max = models.PositiveIntegerField(help_text="Übliche Höchstdauer in Minuten.")
    online_capable = models.BooleanField(help_text="True, wenn online (Remote) gut durchführbar.")
    materials = models.TextField(blank=True, default="", help_text="Materialien und Raumhinweise.")
    difficulty = models.CharField(
        max_length=20, choices=constants.as_choices(constants.DIFFICULTIES),
        help_text="leicht | mittel | fortgeschritten.",
    )

    typical_predecessors = ArrayField(
        models.CharField(max_length=80), default=list,
        help_text="Slugs von Strukturen, die typischerweise davor stehen.",
    )
    typical_successors = ArrayField(
        models.CharField(max_length=80), default=list,
        help_text="Slugs von Strukturen, die typischerweise danach stehen.",
    )

    scrum_use = models.TextField(
        blank=True, default="", help_text="Einsatz im Scrum-Kontext (Retro, Planning, …).",
    )
    design_elements = models.JSONField(
        default=dict,
        help_text="Die 5 Designelemente: einladung, raum_materialien, einbindung, "
                  "gruppenkonfiguration, ablauf_dauer.",
    )
    description_origin = models.CharField(
        max_length=20, choices=constants.as_choices(constants.DESCRIPTION_ORIGINS),
        default="uebernommen", help_text="uebernommen (mit Attribution) oder eigen.",
    )
    attribution = models.TextField(
        blank=True, default="", help_text="Namensnennung + Lizenz bei übernommenen Inhalten.",
    )

    embodied_principles = ArrayField(
        models.CharField(max_length=4), default=list, blank=True,
        help_text="IDs der besonders verkörperten LS-Prinzipien (P1–P10), "
                  "siehe data/ls_principles.json.",
    )
    guide = models.JSONField(
        default=dict, blank=True,
        help_text="Ausführlicher Detailguide (Ebene 2, spiegelt die Quellseite): "
                  "was_wird_moeglich, einladung, beispielsaetze[], schritte[], "
                  "varianten[], tipps[], anlaesse[], material_setup.",
    )

    class Meta:
        ordering = ["structure_id"]
        verbose_name = "Struktur"
        verbose_name_plural = "Strukturen"

    def __str__(self):
        return f"{self.name} ({self.slug})"


class StringTemplate(models.Model):
    """Eine bewährte Abfolge von Strukturen (Matchmaking-Anker).

    Entspricht einem Eintrag aus ``data/string_templates.json``.
    """

    slug = models.SlugField(max_length=80, unique=True, help_text="Kurzkennung des Strings.")
    name = models.CharField(max_length=160, help_text="Anzeigename des Strings.")
    purpose = models.TextField(help_text="Wofür dieser String gedacht ist.")
    sequence = models.JSONField(
        default=list,
        help_text="Geordnete Liste von Schritten: [{\"slug\": ..., \"note\": ...}, ...].",
    )
    total_duration = models.PositiveIntegerField(help_text="Geschätzte Gesamtdauer in Minuten.")
    context_notes = models.TextField(blank=True, default="", help_text="Hinweise zum Einsatz.")
    scrum_context = models.CharField(
        max_length=30, blank=True, default="",
        help_text="Optionaler Scrum-Kontext (z. B. retrospektive, planning).",
    )

    class Meta:
        ordering = ["slug"]
        verbose_name = "String-Template"
        verbose_name_plural = "String-Templates"

    def __str__(self):
        return f"{self.name} ({self.slug})"
