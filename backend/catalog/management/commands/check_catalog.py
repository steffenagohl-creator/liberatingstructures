"""Konsistenzprüfung des Katalogs in der Datenbank (dieselben Checks wie in AP1, nun gegen die DB)."""
from django.core.management.base import BaseCommand, CommandError

from catalog import constants
from catalog.models import Structure, StringTemplate

PFLICHT_DESIGNELEMENTE = [
    "einladung", "raum_materialien", "einbindung", "gruppenkonfiguration", "ablauf_dauer",
]


class Command(BaseCommand):
    help = "Prüft Vollständigkeit, erlaubte Werte und gültige Verweise des Katalogs."

    def handle(self, *args, **options):
        probleme = []
        strukturen = list(Structure.objects.all())
        slugs = {s.slug for s in strukturen}

        original = [s for s in strukturen if s.edition == "original"]
        if len(original) != 33:
            probleme.append(f"Erwartet 33 originale Strukturen, gefunden {len(original)}.")

        for s in strukturen:
            # Pflicht: jedes Designelement hat (mindestens) eine deutsche Fassung.
            for k in PFLICHT_DESIGNELEMENTE:
                element = s.design_elements.get(k)
                if not (isinstance(element, dict) and element.get("de")):
                    probleme.append(f"{s.slug}: Designelement {k!r} fehlt/ohne deutsche Fassung.")
            # Pflicht: zweisprachige Kernfelder mit deutscher Fassung.
            for feld in ("name", "short_desc"):
                wert = getattr(s, feld)
                if not (isinstance(wert, dict) and wert.get("de")):
                    probleme.append(f"{s.slug}: {feld} ohne deutsche Fassung.")
            for a in s.arc_role:
                if a not in constants.ARC_ROLES:
                    probleme.append(f"{s.slug}: ungültige arc_role {a!r}.")
            for t in s.purpose_tags:
                if t not in constants.PURPOSE_TAGS:
                    probleme.append(f"{s.slug}: ungültiger purpose_tag {t!r}.")
            for p in (s.embodied_principles or []):
                if p not in constants.PRINCIPLE_IDS:
                    probleme.append(f"{s.slug}: ungültiges Prinzip {p!r}.")
            for ref in list(s.typical_predecessors) + list(s.typical_successors):
                if ref not in slugs:
                    probleme.append(f"{s.slug}: Verweis auf unbekannten Slug {ref!r}.")

        oeffnen = sum(1 for s in strukturen if "öffnen" in s.arc_role)
        schliessen = sum(1 for s in strukturen if "schließen" in s.arc_role)
        if oeffnen < 1 or schliessen < 1:
            probleme.append(f"Bogen unausgewogen: öffnen={oeffnen}, schließen={schliessen}.")

        for tpl in StringTemplate.objects.all():
            for schritt in tpl.sequence:
                if schritt["slug"] not in slugs:
                    probleme.append(f"Template {tpl.slug}: unbekannter Slug {schritt['slug']!r}.")

        if probleme:
            for p in probleme:
                self.stderr.write(self.style.ERROR(" - " + p))
            raise CommandError(f"Konsistenzprüfung fehlgeschlagen ({len(probleme)} Probleme).")

        self.stdout.write(self.style.SUCCESS(
            f"Konsistenz OK: {len(strukturen)} Strukturen ({len(original)} original), "
            f"öffnen={oeffnen}, schließen={schliessen}, "
            f"{StringTemplate.objects.count()} String-Templates – alle Verweise gültig."
        ))
