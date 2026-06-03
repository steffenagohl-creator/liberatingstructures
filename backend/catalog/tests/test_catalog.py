"""Smoke-Tests für AP2: Seed laden, Konsistenz prüfen, Diagnoseschema laden."""
import json

from django.conf import settings
from django.core.management import call_command
from django.test import TestCase

from catalog.models import Structure, StringTemplate


class CatalogSeedTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")
        call_command("import_string_templates")

    def test_genau_33_originale_strukturen(self):
        self.assertEqual(Structure.objects.filter(edition="original").count(), 33)

    def test_pflichtfelder_und_gueltige_verweise(self):
        slugs = set(Structure.objects.values_list("slug", flat=True))
        for s in Structure.objects.all():
            self.assertTrue(s.short_desc, f"{s.slug}: short_desc leer")
            self.assertTrue(s.design_elements.get("einladung"), f"{s.slug}: einladung leer")
            for ref in list(s.typical_predecessors) + list(s.typical_successors):
                self.assertIn(ref, slugs, f"{s.slug}: Verweis {ref} existiert nicht")

    def test_bogen_abdeckung(self):
        oeffnen = Structure.objects.filter(arc_role__contains=["öffnen"]).count()
        schliessen = Structure.objects.filter(arc_role__contains=["schließen"]).count()
        self.assertGreaterEqual(oeffnen, 1)
        self.assertGreaterEqual(schliessen, 1)

    def test_string_templates_verweisen_auf_echte_strukturen(self):
        self.assertGreaterEqual(StringTemplate.objects.count(), 3)
        slugs = set(Structure.objects.values_list("slug", flat=True))
        for tpl in StringTemplate.objects.all():
            for schritt in tpl.sequence:
                self.assertIn(schritt["slug"], slugs)

    def test_diagnoseschema_laedt_mit_8_dimensionen(self):
        pfad = settings.DATA_DIR / "diagnosis_schema.json"
        daten = json.loads(pfad.read_text(encoding="utf-8"))
        self.assertEqual(len(daten["dimensions"]), 8)

    def test_check_catalog_command_laeuft_durch(self):
        # Wirft CommandError bei Problemen -> Test schlägt sonst fehl.
        call_command("check_catalog")
