"""Tests für die Agenten-Werkzeuge (``matchmaker.tools``).

Schwerpunkt: ``get_string_templates`` – die Zweck-Eingrenzung der Vorlagen
(Vorlagen tragen selbst keine Tags; der Zweck wird aus den Strukturen der
Sequenz abgeleitet).
"""
from django.core.management import call_command
from django.test import TestCase

from catalog.models import Structure
from matchmaker.tools import get_string_templates


class StringTemplateAuswahlTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("import_structures")
        call_command("import_string_templates")

    def _tags_der_vorlage(self, template) -> set[str]:
        slugs = [step.get("slug") for step in template.sequence]
        tags: set[str] = set()
        for s in Structure.objects.filter(slug__in=slugs):
            tags.update(s.purpose_tags or [])
        return tags

    def test_scrum_kontext_hat_vorrang(self):
        templates = get_string_templates(scrum_context="retrospektive")
        self.assertTrue(templates)
        for t in templates:
            self.assertEqual(t.scrum_context, "retrospektive")

    def test_zweck_grenzt_vorlagen_ein(self):
        alle = get_string_templates()
        passende = get_string_templates(purpose_tags=["helfen"])
        self.assertTrue(passende)
        self.assertLess(len(passende), len(alle), "Zweck-Filter grenzt nicht ein")
        for t in passende:
            self.assertIn("helfen", self._tags_der_vorlage(t), t.slug)

    def test_ohne_treffer_alle_vorlagen(self):
        # Ein Tag, das keine Vorlage trifft → Rückfall auf alle (kein leerer Kontext).
        alle = get_string_templates()
        ergebnis = get_string_templates(purpose_tags=["gibt-es-nicht"])
        self.assertEqual(len(ergebnis), len(alle))
