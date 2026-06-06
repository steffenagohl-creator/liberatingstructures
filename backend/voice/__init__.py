"""LS-Voice — die Sprachkanal-App (Stufe 1D).

Diese App stellt die **konversationellen** Sprachkanäle des LS-Matchmaker bereit:
Sprache als *Gespräch* (Coach-Dialog), **nicht** als Steuerung. Es gibt hier daher
bewusst **kein** Intent-/Befehls-Register (kein ``ACTION_REGISTRY`` wie bei klara_voice).

Aufbau (Phase 1 = Fundament, ohne Infrastruktur):

* ``sovereignty.py`` – Politik: die drei Souveränitätsstufen ``sov``/``eu``/``us``,
  ihre Provider-Pläne und die (datensparsame) Fallback-Logik (Stufe 1C).
* ``providers/``      – das provider-agnostische Abstraktions-Layer (analog ``matchmaker/llm/``):
  selbstbeschreibende STT-/TTS-/LLM-/Realtime-Bausteine. Die *echten* Engines laufen
  später im LiveKit-Agent-Worker (Phasen 3–5); hier stehen Metadaten + Auswahl.
* ``tokens.py``       – ``TokenSigner``-Schnittstelle für LiveKit-Zugangstoken;
  in Phase 1 nur ein Stub-Signer (der echte kommt mit der LiveKit-Instanz in Phase 2).
* ``views.py``/``urls.py`` – die dokumentierten Endpunkte ``/api/voice/session/`` und
  ``/api/voice/config/``.
"""
