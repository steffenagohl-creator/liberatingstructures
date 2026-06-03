"""Tests für das Quality Gate (``services.validate_string``).

Prüft jede Regel einzeln gegen reale Seed-Strukturen: Zeit, Bogen (öffnen/schließen),
reale Slugs, Gruppengröße und Online-Tauglichkeit bei Remote.
"""
from django.core.management import call_command
from django.test import TestCase

from matchmaker.services import validate_string

OPENER = "1-2-4-all"  # arc: öffnen; online; grp 6+; leicht; 12 min
CLOSER = "what-so-what-now-what"  # arc: schließen; online; grp 4+; leicht; 15 min
NICHT_ONLINE = "25-10-crowd-sourcing"  # online=False; grp 20+


def step(slug, role="divergieren", duration=12):
    return {"slug": slug, "role": role, "duration": duration, "rationale": "Test."}


class QualityGateTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")
        call_command("import_string_templates")

    def test_gueltiger_string_besteht(self):
        steps = [step(OPENER, "öffnen", 12), step(CLOSER, "schließen", 15)]
        diagnose = {"zeitbudget": 60, "gruppengroesse": 8, "setting": "praesenz"}
        ok, violations = validate_string(steps, diagnose)
        self.assertTrue(ok, violations)
        self.assertEqual(violations, [])

    def test_leerer_string_faellt_durch(self):
        ok, violations = validate_string([], {"zeitbudget": 60})
        self.assertFalse(ok)

    def test_zeitbudget_ueberschritten(self):
        steps = [step(OPENER, "öffnen", 12), step(CLOSER, "schließen", 15)]
        ok, violations = validate_string(steps, {"zeitbudget": 20, "gruppengroesse": 8})
        self.assertFalse(ok)
        self.assertTrue(any("Zeitbudget" in v for v in violations), violations)

    def test_fehlender_schluss_faellt_durch(self):
        steps = [step(OPENER, "öffnen", 12)]
        ok, violations = validate_string(steps, {"zeitbudget": 60, "gruppengroesse": 8})
        self.assertFalse(ok)
        self.assertTrue(any("schließend" in v for v in violations), violations)

    def test_unbekannter_slug_faellt_durch(self):
        steps = [step("gibt-es-nicht", "öffnen", 10), step(CLOSER, "schließen", 15)]
        ok, violations = validate_string(steps, {"zeitbudget": 60, "gruppengroesse": 8})
        self.assertFalse(ok)
        self.assertTrue(any("Unbekannte" in v for v in violations), violations)

    def test_gruppengroesse_inkonsistent(self):
        # 1-2-4-All empfiehlt mindestens 6 Personen – mit 2 passt es nicht.
        steps = [step(OPENER, "öffnen", 12), step(CLOSER, "schließen", 15)]
        ok, violations = validate_string(steps, {"zeitbudget": 60, "gruppengroesse": 2})
        self.assertFalse(ok)
        self.assertTrue(any("Gruppengröße" in v for v in violations), violations)

    def test_remote_mit_nicht_online_struktur(self):
        steps = [
            step(OPENER, "öffnen", 12),
            step(NICHT_ONLINE, "divergieren", 25),
            step(CLOSER, "schließen", 15),
        ]
        diagnose = {"zeitbudget": 120, "gruppengroesse": 20, "setting": "remote"}
        ok, violations = validate_string(steps, diagnose)
        self.assertFalse(ok)
        self.assertTrue(any("online" in v.lower() for v in violations), violations)
