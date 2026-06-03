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

from catalog.models import Structure, StringTemplate

# Felder, die der LLM-Teil pro Kandidat braucht (kompakt halten – spart Tokens).
_CANDIDATE_FIELDS = (
    "slug",
    "name",
    "short_desc",
    "arc_role",
    "purpose_tags",
    "duration_min",
    "duration_max",
    "group_size_min",
    "group_size_max",
    "online_capable",
    "difficulty",
)


@functools.lru_cache(maxsize=1)
def load_diagnosis_schema() -> dict:
    """Lädt das versionierte Diagnoseschema (``data/diagnosis_schema.json``).

    Interview-Agent UND Vorfilterung arbeiten gegen dieselbe Quelle.
    """
    path = settings.DATA_DIR / "diagnosis_schema.json"
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


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
    """Wandelt eine Struktur in das kompakte Kandidaten-Dict für den LLM-Kontext."""
    return {field: getattr(structure, field) for field in _CANDIDATE_FIELDS}


def serialize_template(template: StringTemplate) -> dict:
    """Wandelt eine String-Vorlage in eine kompakte Form für den LLM-Kontext."""
    return {
        "name": template.name,
        "purpose": template.purpose,
        "sequence": [step.get("slug") for step in template.sequence],
        "total_duration": template.total_duration,
    }
