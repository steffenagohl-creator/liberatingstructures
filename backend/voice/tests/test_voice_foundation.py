"""Tests des Sprachkanal-Fundaments (Phase 1) – komplett netzfrei, ohne Schlüssel.

Schwerpunkte:
* Der **datensparsame Fallback** stuft nur Richtung *mehr* Souveränität herunter
  (wer ``eu`` wählt, landet nie bei ``us``).
* Die Endpunkte ``/api/voice/config/`` und ``/api/voice/session/`` liefern die erwartete Form.
* Das Token ist in Phase 1 klar als **Stub** markiert.
"""
from django.test import SimpleTestCase, override_settings
from django.urls import reverse
from rest_framework.test import APITestCase

from voice import sovereignty
from voice.providers import base, factory


# Basis: nichts konfiguriert -> deterministisch unabhängig von der Container-.env.
NICHTS_KONFIGURIERT = dict(
    LLM_API_KEY="", OPENAI_API_KEY="",
    VOICE_SELFHOSTED_ENABLED=False, VOICE_FORCE_STUB=False,
)


class SovereigntyRoutingTests(SimpleTestCase):
    """Die Kern-Politik: Auflösung + datensparsamer Fallback (Stufe 1C)."""

    def test_normalize_tier_unbekanntes_wird_default(self):
        self.assertEqual(sovereignty.normalize_tier(None), "eu")
        self.assertEqual(sovereignty.normalize_tier("blah"), "eu")
        self.assertEqual(sovereignty.normalize_tier("  US "), "us")

    @override_settings(LLM_API_KEY="x", OPENAI_API_KEY="",
                       VOICE_SELFHOSTED_ENABLED=False, VOICE_FORCE_STUB=False)
    def test_us_faellt_auf_eu_zurueck_wenn_us_unkonfiguriert(self):
        r = sovereignty.resolve_tier("us")
        self.assertEqual(r.effective, "eu")
        self.assertTrue(r.fell_back)
        self.assertTrue(r.configured)

    @override_settings(LLM_API_KEY="", OPENAI_API_KEY="schluessel",
                       VOICE_SELFHOSTED_ENABLED=True, VOICE_FORCE_STUB=False)
    def test_eu_faellt_niemals_auf_us_zurueck(self):
        # eu nicht konfiguriert (kein LLM_API_KEY), us WÄRE konfiguriert – darf aber nicht genutzt werden.
        r = sovereignty.resolve_tier("eu")
        self.assertNotEqual(r.effective, "us")
        self.assertEqual(r.effective, "sov")  # souveränere Stufe, nicht die weniger souveräne

    @override_settings(**NICHTS_KONFIGURIERT)
    def test_nichts_konfiguriert_endet_souveraen_aber_unkonfiguriert(self):
        r = sovereignty.resolve_tier("eu")
        self.assertEqual(r.effective, "sov")
        self.assertFalse(r.configured)

    @override_settings(VOICE_FORCE_STUB=True)
    def test_force_stub_macht_jede_stufe_nutzbar(self):
        for tier in ("sov", "eu", "us"):
            r = sovereignty.resolve_tier(tier)
            self.assertEqual(r.effective, tier)
            self.assertTrue(r.configured)

    def test_llm_provider_mapping(self):
        self.assertEqual(sovereignty.llm_provider_for_tier("eu"), "mistral")
        self.assertEqual(sovereignty.llm_provider_for_tier("sov"), "stub")
        self.assertEqual(sovereignty.llm_provider_for_tier("us"), "openai")


class ProviderFactoryTests(SimpleTestCase):
    """Das Abstraktions-Layer: je Stufe der richtige Bauplan."""

    def test_eu_ist_pipeline_us_ist_realtime(self):
        eu = factory.plan_for_tier("eu")
        self.assertEqual(eu.to_dict()["mode"], "pipeline")
        self.assertEqual(eu.llm.id, "mistral")
        us = factory.plan_for_tier("us")
        self.assertEqual(us.to_dict()["mode"], "realtime")
        self.assertEqual(us.realtime.region, base.REGION_US)

    def test_unbekannte_stufe_wirft_voiceerror(self):
        with self.assertRaises(base.VoiceError):
            factory.plan_for_tier("mond")

    @override_settings(VOICE_FORCE_STUB=True)
    def test_force_stub_liefert_offline_plan(self):
        plan = factory.plan_for_tier("eu")
        self.assertEqual(plan.stt.id, "stub-stt")


class VoiceConfigEndpointTests(APITestCase):
    def test_config_liefert_drei_stufen(self):
        resp = self.client.get(reverse("voice-config"))
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["default_tier"], "eu")
        ids = [t["id"] for t in data["tiers"]]
        self.assertEqual(ids, ["sov", "eu", "us"])
        # Bauplan-Modus je Stufe stimmt.
        modes = {t["id"]: t["plan"]["mode"] for t in data["tiers"]}
        self.assertEqual(modes["eu"], "pipeline")
        self.assertEqual(modes["us"], "realtime")


class VoiceSessionEndpointTests(APITestCase):
    @override_settings(VOICE_FORCE_STUB=True)
    def test_session_liefert_stub_token_und_bauplan(self):
        resp = self.client.post(reverse("voice-session"), {"sovereignty": "eu"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["effective_tier"], "eu")
        self.assertTrue(data["token_is_stub"])
        self.assertTrue(data["token"].startswith("stub."))
        self.assertTrue(data["room"])
        self.assertTrue(data["identity"])
        self.assertEqual(data["plan"]["tier"], "eu")

    @override_settings(LLM_API_KEY="x", OPENAI_API_KEY="",
                       VOICE_SELFHOSTED_ENABLED=False, VOICE_FORCE_STUB=False)
    def test_session_stuft_us_datensparsam_auf_eu(self):
        resp = self.client.post(reverse("voice-session"), {"sovereignty": "us"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        data = resp.json()
        self.assertEqual(data["requested_tier"], "us")
        self.assertEqual(data["effective_tier"], "eu")
        self.assertTrue(data["fell_back"])

    def test_session_unbekannte_stufe_wird_eu(self):
        resp = self.client.post(reverse("voice-session"), {"sovereignty": "quatsch"}, format="json")
        self.assertEqual(resp.status_code, 200, resp.content)
        self.assertEqual(resp.json()["requested_tier"], "eu")
