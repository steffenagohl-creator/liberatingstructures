"""Agenten-Werkzeuge: deterministische Abfragen gegen die Wissens-Datenbank.

Diese Funktionen bilden den „erlaubten Werkzeugkasten" – der LLM-Teil schlägt
nur Strukturen vor, die es hier real gibt. Jede Funktion ist sprechend benannt
und liefert Daten in der Form, die die übrigen Schichten (Vorfilterung,
Sequenzierung, Quality Gate) erwarten.
"""
from __future__ import annotations

import functools
import json

from django.conf import settings
from django.db.models import Q

from catalog.i18n import localize
from catalog.models import Structure, StringTemplate

# Sprache des LLM-Kontexts. Die Prompts sind deutsch (App-Sprache laut Großauftrag),
# daher werden zweisprachige Felder hier auf Deutsch aufgelöst (spart Tokens, vermeidet
# Mehrdeutigkeit). EN bleibt über die API (?lang=) verfügbar.
_LLM_LANG = "de"

# Zweisprachige Felder, die für den LLM-Kontext auf eine Sprache reduziert werden.
_BILINGUAL_CANDIDATE_FIELDS = ("name", "objective", "short_desc")

# Felder, die der LLM-Teil pro Kandidat braucht (kompakt halten – spart Tokens).
_CANDIDATE_FIELDS = (
    "slug",
    "name",
    "objective",
    "short_desc",
    "arc_role",
    "purpose_tags",
    "duration_min",
    "duration_max",
    "group_size_min",
    "group_size_max",
    "online_capable",
    "difficulty",
    "embodied_principles",
)


@functools.lru_cache(maxsize=1)
def load_diagnosis_schema() -> dict:
    """Lädt das versionierte Diagnoseschema (``data/diagnosis_schema.json``).

    Interview-Agent UND Vorfilterung arbeiten gegen dieselbe Quelle.
    """
    path = settings.DATA_DIR / "diagnosis_schema.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


@functools.lru_cache(maxsize=1)
def load_principles() -> list[dict]:
    """Lädt die 10 LS-Prinzipien (``data/ls_principles.json``) für das KI-Harness.

    Liefert eine kompakte Liste ``[{"id", "name_de", "beschreibung"}, ...]``, auf die sich
    das Sprachmodell bei Auswahl und Begründung berufen muss.
    """
    path = settings.DATA_DIR / "ls_principles.json"
    with open(path, encoding="utf-8") as fh:
        principles = json.load(fh)["principles"]
    return [
        {
            "id": p["id"],
            "name_de": p["name_de"],
            "beschreibung": p["beschreibung"],
            "must_do": p.get("must_do", ""),
            "must_not_do": p.get("must_not_do", ""),
        }
        for p in principles
    ]


@functools.lru_cache(maxsize=1)
def load_principles_framing() -> str:
    """Lädt das deutsche ``framing``-Intro der Prinzipien (Must-Do = starten/verstärken,
    Must-Not-Do = stoppen/reduzieren) für den LLM-Kontext. Leerer String, falls nicht gesetzt."""
    path = settings.DATA_DIR / "ls_principles.json"
    with open(path, encoding="utf-8") as fh:
        framing = json.load(fh).get("framing", {})
    return framing.get("de", "") if isinstance(framing, dict) else ""


@functools.lru_cache(maxsize=1)
def load_foundations() -> dict:
    """Lädt das theoretische Fundament (Kernkonzepte + Komplexitäts-Linsen) fürs Harness.

    Liefert eine kompakte Form, auf die sich das Sprachmodell zur fachlichen Vertiefung der
    Begründung stützen kann (``data/ls_foundations.json``).
    """
    path = settings.DATA_DIR / "ls_foundations.json"
    with open(path, encoding="utf-8") as fh:
        data = json.load(fh)
    return {
        "core_concepts": [
            {"name": c["name_de"], "insight": c["insight"]}
            for c in data.get("core_concepts", [])
        ],
        "complexity_lenses": [
            {"name": lens["name"], "ls_bezug": lens["ls_bezug"]}
            for lens in data.get("complexity_lenses", [])
        ],
    }


def query_structures(
    *,
    purpose_tags: list[str] | None = None,
    group_size: int | None = None,
    max_duration: int | None = None,
    online_only: bool = False,
    difficulties: list[str] | None = None,
    edition: str = "original",
    types: list[str] | None = None,
) -> list[Structure]:
    """Filtert den Katalog nach harten Kriterien und gibt passende Strukturen zurück.

    :param purpose_tags: nur Strukturen, deren ``purpose_tags`` mind. einen Wert teilen.
    :param group_size: Teilnehmerzahl muss in ``[group_size_min, group_size_max]`` liegen.
    :param max_duration: nur Strukturen, deren ``duration_min`` in dieses Budget passt.
    :param online_only: bei Remote – nur ``online_capable`` Strukturen.
    :param difficulties: erlaubte Schwierigkeitsgrade.
    :param edition: ``original`` (die 33) oder ``extended``.
    :param types: erlaubte Typen (Default: nur ``official``).
    """
    qs = Structure.objects.filter(edition=edition, type__in=types or ["official"])

    if group_size is not None:
        qs = qs.filter(group_size_min__lte=group_size).filter(
            Q(group_size_max__isnull=True) | Q(group_size_max__gte=group_size)
        )
    if max_duration is not None:
        qs = qs.filter(duration_min__lte=max_duration)
    if online_only:
        qs = qs.filter(online_capable=True)
    if difficulties:
        qs = qs.filter(difficulty__in=difficulties)
    if purpose_tags:
        qs = qs.filter(purpose_tags__overlap=purpose_tags)

    return list(qs)


def get_structure(slug: str) -> Structure | None:
    """Holt eine einzelne Struktur per Slug (oder ``None``, wenn es sie nicht gibt)."""
    return Structure.objects.filter(slug=slug).first()


def get_structures_by_slugs(slugs: list[str]) -> dict[str, Structure]:
    """Lädt mehrere Strukturen auf einmal als ``{slug: Structure}`` (für das Quality Gate)."""
    return {s.slug: s for s in Structure.objects.filter(slug__in=slugs)}


def get_string_templates(
    *, scrum_context: str | None = None, purpose_tags: list[str] | None = None
) -> list[StringTemplate]:
    """Liefert bewährte String-Vorlagen, bevorzugt passend zum Scrum-Kontext."""
    if scrum_context:
        matches = list(StringTemplate.objects.filter(scrum_context=scrum_context))
        if matches:
            return matches
    return list(StringTemplate.objects.all())


def serialize_candidate(structure: Structure) -> dict:
    """Wandelt eine Struktur in das kompakte Kandidaten-Dict für den LLM-Kontext.

    Zweisprachige Felder (name, objective, short_desc) werden auf die LLM-Sprache
    (Deutsch) reduziert, damit der Prompt eindeutig und tokensparsam bleibt.
    """
    candidate = {}
    for field in _CANDIDATE_FIELDS:
        value = getattr(structure, field)
        if field in _BILINGUAL_CANDIDATE_FIELDS:
            value = localize(value, _LLM_LANG)
        candidate[field] = value
    return candidate


def serialize_template(template: StringTemplate) -> dict:
    """Wandelt eine String-Vorlage in eine kompakte Form für den LLM-Kontext."""
    return {
        "name": template.name,
        "purpose": template.purpose,
        "sequence": [step.get("slug") for step in template.sequence],
        "total_duration": template.total_duration,
    }
