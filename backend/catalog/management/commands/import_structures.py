"""Import der Strukturen aus data/structures.json in die Datenbank (idempotent)."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog import constants
from catalog.models import Structure

PFLICHT_DESIGNELEMENTE = [
    "einladung", "raum_materialien", "einbindung", "gruppenkonfiguration", "ablauf_dauer",
]


class Command(BaseCommand):
    help = "Importiert die 33 Strukturen aus data/structures.json (legt an oder aktualisiert)."

    def handle(self, *args, **options):
        pfad = settings.DATA_DIR / "structures.json"
        if not pfad.exists():
            raise CommandError(f"Datei nicht gefunden: {pfad}")

        daten = json.loads(pfad.read_text(encoding="utf-8"))
        strukturen = daten["structures"]

        # Kanonische Ziele (LS Selection Matchmaker) je Slug – werden in 'objective' übernommen.
        objektiv_pfad = settings.DATA_DIR / "ls_objectives.json"
        objectives = {}
        if objektiv_pfad.exists():
            objectives = json.loads(objektiv_pfad.read_text(encoding="utf-8")).get("objectives", {})

        # Icon-Zuordnung (slug -> SVG-Dateiname) aus data/icon_map.json.
        # WICHTIG: Die Dateinummern entsprechen NICHT der structure_id — daher diese Tabelle.
        icon_pfad = settings.DATA_DIR / "icon_map.json"
        icon_map = {}
        if icon_pfad.exists():
            icon_map = json.loads(icon_pfad.read_text(encoding="utf-8")).get("icons", {})

        neu = aktualisiert = 0
        for s in strukturen:
            self._pruefe(s)
            # objective steht nicht in structures.json, sondern kommt zweisprachig {de,en}
            # aus ls_objectives.json (per Slug gemergt). Fallback: leeres Sprachobjekt.
            objective = s.get("objective") or objectives.get(s["slug"]) or {"de": "", "en": ""}
            _, created = Structure.objects.update_or_create(
                structure_id=s["id"],
                defaults={
                    "name": s["name"],
                    "slug": s["slug"],
                    "type": s["type"],
                    "base_structure": s.get("base_structure") or "",
                    "edition": s["edition"],
                    "short_desc": s["short_desc"],
                    "objective": objective,
                    "source_url": s["source_url"],
                    "purpose_tags": s["purpose_tags"],
                    "arc_role": s["arc_role"],
                    "group_size_min": s["group_size_min"],
                    "group_size_max": s["group_size_max"],
                    "duration_min": s["duration_min"],
                    "duration_max": s["duration_max"],
                    "online_capable": s["online_capable"],
                    "materials": s.get("materials") or {},
                    "difficulty": s["difficulty"],
                    "typical_predecessors": s["typical_predecessors"],
                    "typical_successors": s["typical_successors"],
                    "scrum_use": s.get("scrum_use") or {},
                    "design_elements": s["design_elements"],
                    "description_origin": s.get("description_origin", "uebernommen"),
                    "attribution": s.get("attribution") or {},
                    "icon": icon_map.get(s["slug"], ""),
                    "icon_alt": s.get("icon_alt") or {},
                    "embodied_principles": s.get("embodied_principles", []),
                    "guide": s.get("guide", {}),
                },
            )
            neu += int(created)
            aktualisiert += int(not created)

        self.stdout.write(self.style.SUCCESS(
            f"Strukturen importiert: {neu} neu, {aktualisiert} aktualisiert, "
            f"gesamt in DB: {Structure.objects.count()}."
        ))

    def _pruefe(self, s):
        """Validiert eine einzelne Struktur gegen die erlaubten Werte."""
        slug = s.get("slug", "?")
        if s["type"] not in constants.TYPES:
            raise CommandError(f"{slug}: ungültiger type {s['type']!r}")
        if s["edition"] not in constants.EDITIONS:
            raise CommandError(f"{slug}: ungültige edition {s['edition']!r}")
        if s["difficulty"] not in constants.DIFFICULTIES:
            raise CommandError(f"{slug}: ungültige difficulty {s['difficulty']!r}")
        for t in s["purpose_tags"]:
            if t not in constants.PURPOSE_TAGS:
                raise CommandError(f"{slug}: ungültiger purpose_tag {t!r}")
        for a in s["arc_role"]:
            if a not in constants.ARC_ROLES:
                raise CommandError(f"{slug}: ungültige arc_role {a!r}")
        for p in s.get("embodied_principles", []):
            if p not in constants.PRINCIPLE_IDS:
                raise CommandError(f"{slug}: ungültiges Prinzip {p!r}")
        # Zweisprachige Pflichtfelder: deutsche Fassung muss vorhanden sein.
        for feld in ("name", "short_desc"):
            if not (isinstance(s.get(feld), dict) and s[feld].get("de")):
                raise CommandError(f"{slug}: {feld} fehlt deutsche Fassung (erwartet {{de, en}})")
        for k in PFLICHT_DESIGNELEMENTE:
            element = s.get("design_elements", {}).get(k)
            if not (isinstance(element, dict) and element.get("de")):
                raise CommandError(f"{slug}: Designelement {k!r} fehlt oder hat keine deutsche Fassung")
