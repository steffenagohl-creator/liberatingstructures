"""End-to-End-Tests der Endpunkte mit dem Stub-LLM (kein Netz, keine Kosten).

Kern-DoD von AP3: ``/api/match/`` liefert für mehrere Testsituationen valide,
Quality-Gate-konforme Strings. Zusätzlich ein Test für ``/api/interview/``.
"""
from django.core.management import call_command
from django.test import override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from catalog.models import Structure

# Mehrere realistische Situationen (so gewählt, dass Öffner + Schließer verfügbar sind).
SZENARIEN = [
    {
        "zweck": ["offenlegen"], "gruppengroesse": 8, "zeitbudget": 120,
        "setting": "praesenz", "scrum_kontext": "retrospektive",
    },
    {"zweck": ["analysieren"], "gruppengroesse": 6, "zeitbudget": 90, "setting": "remote"},
    {
        "zweck": ["planen"], "gruppengroesse": 10, "zeitbudget": 200,
        "setting": "praesenz", "reife_ls_erfahrung": "fortgeschritten",
    },
    {"zweck": ["helfen"], "gruppengroesse": 5, "zeitbudget": 90, "setting": "praesenz"},
]


@override_settings(LLM_PROVIDER="stub")
class MatchEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")
        call_command("import_string_templates")
        cls.echte_slugs = set(Structure.objects.values_list("slug", flat=True))
        cls.arc = {s.slug: s.arc_role for s in Structure.objects.all()}

    def test_match_liefert_gueltige_strings_fuer_alle_szenarien(self):
        url = reverse("match")
        for diagnose in SZENARIEN:
            with self.subTest(diagnose=diagnose):
                resp = self.client.post(url, {"diagnose": diagnose}, format="json")
                self.assertEqual(resp.status_code, 200, resp.content)
                data = resp.json()

                # Quality Gate ist erfüllt.
                self.assertTrue(data["quality"]["ok"], data["quality"]["violations"])
                self.assertGreaterEqual(len(data["string"]), 2)

                # Zeitbudget eingehalten.
                self.assertLessEqual(data["total_duration"], diagnose["zeitbudget"])

                # Alle Slugs sind reale Katalog-Strukturen.
                slugs = [s["slug"] for s in data["string"]]
                for slug in slugs:
                    self.assertIn(slug, self.echte_slugs)

                # Vollständiger Bogen: öffnen + schließen vorhanden.
                roles = {r for slug in slugs for r in self.arc[slug]}
                self.assertIn("öffnen", roles)
                self.assertIn("schließen", roles)

    def test_match_validiert_eingabe(self):
        # Ohne diagnose -> 400.
        resp = self.client.post(reverse("match"), {}, format="json")
        self.assertEqual(resp.status_code, 400)


@override_settings(LLM_PROVIDER="stub")
class InterviewEndpointTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")

    def test_vollstaendige_antworten_sind_matchmaking_bereit(self):
        payload = {
            "situation": "Retrospektive mit 8 Leuten, 60 Minuten, online.",
            "answers": {
                "zweck": ["offenlegen"],
                "gruppengroesse": 8,
                "zeitbudget": 60,
                "setting": "remote",
            },
        }
        resp = self.client.post(reverse("interview"), payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertTrue(data["ready"])
        self.assertEqual(data["open_questions"], [])
        self.assertEqual(data["diagnose"]["gruppengroesse"], 8)

    def test_fehlende_pflichtangabe_erzeugt_rueckfrage(self):
        payload = {
            "situation": "Wir wollen Ideen sammeln.",
            "answers": {"zweck": ["offenlegen"], "gruppengroesse": 8, "setting": "praesenz"},
        }
        resp = self.client.post(reverse("interview"), payload, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertFalse(data["ready"])
        offene_keys = {q["key"] for q in data["open_questions"]}
        self.assertIn("zeitbudget", offene_keys)
