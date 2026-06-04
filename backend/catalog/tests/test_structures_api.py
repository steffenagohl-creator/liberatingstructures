"""Tests des read-only Katalog-Endpunkts inkl. Sprachsteuerung (?lang=)."""
from django.core.management import call_command
from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.models import Structure


class StructuresApiTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")

    def test_liste_liefert_alle_43_strukturen(self):
        resp = self.client.get(reverse("structures-list"))
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 43)

    def test_default_sprache_ist_deutsch(self):
        resp = self.client.get(reverse("structures-detail", args=["1-2-4-all"]))
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["lang"], "de")
        # name.de aus den Daten
        s = Structure.objects.get(slug="1-2-4-all")
        self.assertEqual(body["name"], s.name["de"])
        self.assertIsInstance(body["short_desc"], str)  # aufgelöst, kein {de,en}

    def test_lang_en_schaltet_um(self):
        resp = self.client.get(reverse("structures-detail", args=["1-2-4-all"]) + "?lang=en")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["lang"], "en")
        s = Structure.objects.get(slug="1-2-4-all")
        self.assertEqual(body["name"], s.name["en"])
        # guide ist tief aufgelöst -> reiner String, kein verschachteltes {de,en}
        self.assertIsInstance(body["guide"]["was_wird_moeglich"], str)
        self.assertEqual(body["guide"]["was_wird_moeglich"], s.guide["was_wird_moeglich"]["en"])

    def test_unbekannte_sprache_faellt_auf_deutsch_zurueck(self):
        resp = self.client.get(reverse("structures-detail", args=["1-2-4-all"]) + "?lang=fr")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["lang"], "de")

    def test_edition_filter(self):
        resp = self.client.get(reverse("structures-list") + "?edition=original")
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(len(resp.json()), 33)

    def test_unbekannter_slug_gibt_404(self):
        resp = self.client.get(reverse("structures-detail", args=["gibt-es-nicht"]))
        self.assertEqual(resp.status_code, 404)
