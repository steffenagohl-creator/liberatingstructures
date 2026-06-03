"""Tests für die deterministische Vorfilterung (``services.vorfilterung``).

Prüft, dass die harten Kriterien greifen (Gruppengröße, Remote, Zeitbudget,
Schwierigkeit) und dass die Bogen-Sicherung den Öffner/Schließer auch dann erhält,
wenn der Zweck (z. B. „planen") selbst keinen Öffner mitbringt.
"""
from django.core.management import call_command
from django.test import TestCase

from matchmaker.services import vorfilterung


class VorfilterungTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")
        call_command("import_string_templates")

    def _slugs(self, diagnose):
        return {s.slug for s in vorfilterung(diagnose)}

    def test_kleine_gruppe_schliesst_grosse_strukturen_aus(self):
        # 1-2-4-All braucht >= 6 Personen; bei 3 darf es nicht erscheinen.
        slugs = self._slugs({"gruppengroesse": 3, "zeitbudget": 120, "setting": "praesenz"})
        self.assertNotIn("1-2-4-all", slugs)
        # nine-whys (ab 2 Personen) ist erlaubt.
        self.assertIn("nine-whys", slugs)

    def test_remote_nur_online_taugliche(self):
        candidates = vorfilterung({"gruppengroesse": 25, "zeitbudget": 300, "setting": "remote"})
        for s in candidates:
            self.assertTrue(s.online_capable, f"{s.slug} ist nicht online-tauglich")
        slugs = {s.slug for s in candidates}
        self.assertNotIn("25-10-crowd-sourcing", slugs)
        self.assertNotIn("simple-ethnography", slugs)

    def test_kleines_zeitbudget_schliesst_lange_strukturen_aus(self):
        candidates = vorfilterung({"gruppengroesse": 8, "zeitbudget": 20, "setting": "praesenz"})
        for s in candidates:
            self.assertLessEqual(s.duration_min, 20, f"{s.slug} dauert mindestens {s.duration_min}")

    def test_anfaenger_bekommt_keine_fortgeschrittenen(self):
        candidates = vorfilterung(
            {
                "gruppengroesse": 10,
                "zeitbudget": 480,
                "setting": "praesenz",
                "reife_ls_erfahrung": "anfaenger",
            }
        )
        for s in candidates:
            self.assertIn(s.difficulty, ["leicht", "mittel"])
        self.assertNotIn("open-space-technology", {s.slug for s in candidates})

    def test_zweck_planen_behaelt_oeffner_und_schliesser(self):
        # „planen" hat selbst keinen Öffner – die Bogen-Sicherung muss greifen.
        candidates = vorfilterung(
            {"zweck": ["planen"], "gruppengroesse": 8, "zeitbudget": 300, "setting": "praesenz"}
        )
        hat_oeffner = any("öffnen" in s.arc_role for s in candidates)
        hat_schliesser = any("schließen" in s.arc_role for s in candidates)
        self.assertTrue(hat_oeffner, "Kein Öffner trotz Bogen-Sicherung")
        self.assertTrue(hat_schliesser, "Kein Schließer trotz Bogen-Sicherung")
