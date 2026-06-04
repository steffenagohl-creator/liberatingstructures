"""Sprachauflösung für zweisprachige Inhalte ({de,en}).

Die Datengrundlage ist durchgängig zweisprachig: jedes Textfeld ist ein Objekt
``{"de": …, "en": …}`` (Listen ``{"de": [...], "en": [...]}``), verschachtelt auch
in ``design_elements`` und ``guide``. Diese Helfer lösen eine gewünschte Sprache
sauber auf – für die API (``?lang=``), den LLM-Kontext und Log-/Fehlermeldungen.

Leitprinzip: gleichermaßen nutzbar durch Screenreader, Sprachsteuerung, KIs/MCP und
Crawler – die Sprache ist explizit steuerbar, nichts wird stillschweigend geraten.
"""
from __future__ import annotations

#: Unterstützte Sprachcodes (ISO 639-1). Erweiterbar, falls weitere Sprachen folgen.
SUPPORTED_LANGS = ("de", "en")
#: Standardsprache der App (laut Großauftrag: Deutsch). EN ist additiv.
DEFAULT_LANG = "de"


def normalize_lang(lang: str | None) -> str:
    """Bringt einen angefragten Sprachcode auf einen unterstützten Wert.

    Unbekannte/leere Werte fallen auf :data:`DEFAULT_LANG` zurück (nie ein Fehler –
    so bleibt die API robust für Crawler und KI-Clients).
    """
    if isinstance(lang, str):
        code = lang.strip().lower()[:2]
        if code in SUPPORTED_LANGS:
            return code
    return DEFAULT_LANG


def _is_bilingual_leaf(value: dict) -> bool:
    """True, wenn ``value`` ein zweisprachiges Blatt ist (nur de/en-Schlüssel)."""
    if not value:
        return False
    return set(value.keys()) <= set(SUPPORTED_LANGS)


def localize(value, lang: str = DEFAULT_LANG):
    """Löst genau eine Ebene ``{de,en}`` auf; lässt alles andere unverändert.

    Für einfache Felder wie ``name`` oder ``short_desc``. Mit Fallback auf Deutsch,
    dann auf die jeweils andere Sprache (nie ``None`` für vorhandene Inhalte).
    """
    if isinstance(value, dict) and _is_bilingual_leaf(value):
        return value.get(lang) or value.get(DEFAULT_LANG) or value.get("en") or ""
    return value


def localize_deep(value, lang: str = DEFAULT_LANG):
    """Löst ``{de,en}`` rekursiv über beliebig tiefe Strukturen auf.

    Geeignet für ``design_elements`` und ``guide`` (verschachtelte Objekte, Listen
    von Schritten/Varianten, zweisprachige Listen ``{"de": [...], "en": [...]}``).
    Zahlen, Enums, Slugs und sonstige sprachneutrale Werte bleiben unangetastet.
    """
    if isinstance(value, dict):
        if _is_bilingual_leaf(value):
            return value.get(lang) or value.get(DEFAULT_LANG) or value.get("en") or ""
        return {key: localize_deep(item, lang) for key, item in value.items()}
    if isinstance(value, list):
        return [localize_deep(item, lang) for item in value]
    return value
