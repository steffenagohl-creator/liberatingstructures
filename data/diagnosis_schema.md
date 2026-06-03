# Diagnoseschema (`data/diagnosis_schema.json`)

Das Diagnoseschema beschreibt die **strukturierten Merkmale**, die der LS-Matchmaker aus einer
geschilderten Situation erhebt. Es ist die gemeinsame Quelle für den **Interview-Agenten** (er
fragt diese Dimensionen ab) und die **deterministische Vorfilterung** (sie filtert den Katalog
gegen dieselben Merkmale). Versioniert über `schema_version`.

## Felder je Dimension

| Feld | Bedeutung |
|---|---|
| `key` | Eindeutiger, stabiler Bezeichner der Dimension. |
| `label` | Verständliche Frage an die Moderatorin (auch als Sprach-/Screenreader-Label). |
| `hint` | Kurzer Zusatzhinweis. |
| `input_type` | `single_choice`, `multi_choice` oder `number`. |
| `maps_to` | Auf welches Struktur-Feld die Antwort in der Vorfilterung wirkt (`-` = nur Kontext). |
| `options` | Bei Auswahlfragen: erlaubte Werte mit Label. |
| `unit` | Bei Zahlen: Einheit (z. B. `minuten`, `personen`). |

## Die 8 Dimensionen

1. **zweck** → `purpose_tags` (Mehrfachauswahl) – das Ziel der Session.
2. **phase_bogen** → `arc_role` – Rolle im Spannungsbogen (öffnen/divergieren/konvergieren/schließen).
3. **gruppengroesse** → `group_size` – Anzahl Teilnehmender (filtert min/max).
4. **zeitbudget** → `duration` – verfügbare Minuten (filtert Dauer).
5. **setting** → `online_capable` – Präsenz/Remote/Hybrid.
6. **psychologische_sicherheit** → nur Kontext – beeinflusst die Auswahl (z. B. behutsame Strukturen).
7. **reife_ls_erfahrung** → `difficulty` – steuert die Schwierigkeit der Vorschläge.
8. **scrum_kontext** → `scrum_context` – optionales Preset (Retro, Planning, …).
