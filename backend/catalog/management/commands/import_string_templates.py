"""Import der String-Templates aus data/string_templates.json (idempotent)."""
import json

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from catalog.models import Structure, StringTemplate


class Command(BaseCommand):
    help = "Importiert bewährte String-Templates aus data/string_templates.json."

    def handle(self, *args, **options):
        pfad = settings.DATA_DIR / "string_templates.json"
        if not pfad.exists():
            raise CommandError(f"Datei nicht gefunden: {pfad}")

        daten = json.loads(pfad.read_text(encoding="utf-8"))
        templates = daten["templates"]
        bekannte_slugs = set(Structure.objects.values_list("slug", flat=True))

        neu = aktualisiert = 0
        for t in templates:
            for schritt in t["sequence"]:
                if schritt["slug"] not in bekannte_slugs:
                    raise CommandError(
                        f"Template {t['slug']!r}: unbekannter Struktur-Slug "
                        f"{schritt['slug']!r} (zuerst Strukturen importieren?)"
                    )
            _, created = StringTemplate.objects.update_or_create(
                slug=t["slug"],
                defaults={
                    "name": t["name"],
                    "purpose": t["purpose"],
                    "sequence": t["sequence"],
                    "total_duration": t["total_duration"],
                    "context_notes": t.get("context_notes", ""),
                    "scrum_context": t.get("scrum_context", ""),
                },
            )
            neu += int(created)
            aktualisiert += int(not created)

        self.stdout.write(self.style.SUCCESS(
            f"String-Templates importiert: {neu} neu, {aktualisiert} aktualisiert, "
            f"gesamt in DB: {StringTemplate.objects.count()}."
        ))
