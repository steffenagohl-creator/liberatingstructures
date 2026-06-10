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
        # 25/10 Crowd Sourcing ist physisch (Umhergehen, Karten weiterreichen) -> nicht remote.
        # (simple-ethnography ist laut Quelle auch virtuell beobachtbar und damit online_capable.)
        self.assertNotIn("25-10-crowd-sourcing", slugs)

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

    def test_hybrid_nur_online_taugliche(self):
        # Hybrid: ein Teil nimmt remote teil → nur online-taugliche Strukturen.
        candidates = vorfilterung({"gruppengroesse": 25, "zeitbudget": 300, "setting": "hybrid"})
        for s in candidates:
            self.assertTrue(s.online_capable, f"{s.slug} ist nicht online-tauglich")
        self.assertNotIn("25-10-crowd-sourcing", {s.slug for s in candidates})

    def test_zeitbudget_reserviert_bogen(self):
        # Knappes Budget: Neben jeder Struktur müssen kürzester Öffner + Schließer passen.
        budget = 30
        candidates = vorfilterung(
            {"gruppengroesse": 8, "zeitbudget": budget, "setting": "praesenz"}
        )
        opens = [s.duration_min for s in candidates if "öffnen" in s.arc_role]
        closes = [s.duration_min for s in candidates if "schließen" in s.arc_role]
        self.assertTrue(opens and closes, "Bogen muss im Budget möglich bleiben")
        min_open, min_close = min(opens), min(closes)
        for s in candidates:
            reserve = min_open + min_close
            if "öffnen" in s.arc_role:
                reserve = min(reserve, min_close)
            if "schließen" in s.arc_role:
                reserve = min(reserve, min_open)
            self.assertLessEqual(
                s.duration_min + reserve, budget,
                f"{s.slug} lässt keinen Platz mehr für den Bogen",
            )

    def test_zweck_lockerung_haelt_treffer_vorn(self):
        # Wird gelockert, stehen Zweck-/Bogen-Treffer vor den aufgefüllten Strukturen.
        diagnose = {"zweck": ["helfen"], "gruppengroesse": 8, "zeitbudget": 300,
                    "setting": "praesenz"}
        candidates = vorfilterung(diagnose)

        def passt(s):
            return ("helfen" in (s.purpose_tags or [])
                    or {"öffnen", "schließen"} & set(s.arc_role or []))

        # Alle Treffer müssen VOR dem ersten Nicht-Treffer stehen (stabile Priorität).
        nicht_treffer_gesehen = False
        for s in candidates:
            if passt(s):
                self.assertFalse(nicht_treffer_gesehen,
                                 f"Treffer {s.slug} steht hinter aufgefüllten Strukturen")
            else:
                nicht_treffer_gesehen = True
