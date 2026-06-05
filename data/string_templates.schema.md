# Schema der String-Templates (`data/string_templates.json`)

Ein **String-Template** ist eine bewährte Abfolge von Liberating Structures, die als Anker fürs
Matchmaking dient. Die Datei hat einen Kopfbereich (Meta) und eine Liste `templates`.

## Felder je Template

| Feld | Bedeutung |
|---|---|
| `slug` | Eindeutige Kurzkennung des Strings. |
| `name` | Anzeigename. |
| `purpose` | Wofür der String gedacht ist (1–2 Sätze). |
| `scrum_context` | Optionales Scrum-Preset (`retrospektive`, `planning`, … oder leer). |
| `total_duration` | Geschätzte Gesamtdauer in **Minuten**. |
| `context_notes` | Hinweise zum Einsatz. |
| `idea_source` | *(optional)* Knappe Herkunft der **Abfolge-Idee** (Provenienz). Nur die Idee/Abfolge wird übernommen — **alle Texte (`purpose`, `note`, …) sind eigene Formulierungen**, niemals fremde Texte 1:1. Sichert kommerzielle Nutzbarkeit (CC BY-SA 4.0). |
| `sequence` | Geordnete Liste von Schritten. Jeder Schritt: `slug` (verweist auf eine Struktur in `structures.json`) und `note` (warum dieser Schritt hier steht). |

**Regel 1:** Jeder `slug` in `sequence` muss einer realen Struktur entsprechen (wird beim Import
und in `check_catalog` geprüft).

**Regel 2 (Bogen):** Ein guter String hat einen vollständigen Bogen — mindestens eine **öffnende**
und eine **schließende** Struktur (über `arc_role` der enthaltenen Strukturen). Das Quality Gate
prüft dies zur Laufzeit.
