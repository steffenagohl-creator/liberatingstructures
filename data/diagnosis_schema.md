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
| `input_type` | `single_choice`, `multi_choice`, `number` oder `text` (Freitext). |
| `maps_to` | Auf welches Struktur-Feld die Antwort in der Vorfilterung wirkt (`-` = nur Kontext). |
| `options` | Bei Auswahlfragen: erlaubte Werte mit Label. |
| `unit` | Bei Zahlen: Einheit (z. B. `minuten`, `personen`). |

## Die 9 Dimensionen

Nach der Autoren-Methode (Selection Matchmaker) beginnt die Diagnose mit dem **Zweck**: dazu werden
das geschilderte **Problem** (Freitext `situation`, kein Schema-Feld) **und** das vom Nutzer benannte
**Ziel** (`ziel_text`) erhoben. Das genannte Ziel ist oft noch nicht das echte – es darf im Prozess
emergent auftauchen/sich schärfen (Dynamic Incompleteness), daher ist `ziel_text` **erbeten, aber
nicht blockierend** (zählt nicht zu den Pflicht-Dimensionen).

1. **ziel_text** → nur Kontext (`-`), `input_type: text` – das vom Nutzer benannte Ziel (Freitext).
2. **zweck** → `purpose_tags` (Mehrfachauswahl) – die Zweck-Kategorie(n).
3. **phase_bogen** → `arc_role` – Rolle im Spannungsbogen (öffnen/divergieren/konvergieren/schließen).
4. **gruppengroesse** → `group_size` – Anzahl Teilnehmender (filtert min/max).
5. **zeitbudget** → `duration` – verfügbare Minuten (filtert Dauer).
6. **setting** → `online_capable` – Präsenz/Remote/Hybrid.
7. **psychologische_sicherheit** → nur Kontext – beeinflusst die Auswahl (z. B. behutsame Strukturen).
8. **reife_ls_erfahrung** → `difficulty` – steuert die Schwierigkeit der Vorschläge.
9. **scrum_kontext** → `scrum_context` – optionales Preset (Retro, Planning, …).

**Pflicht-Dimensionen** (ohne sie kein Matching): `zweck`, `gruppengroesse`, `zeitbudget`, `setting`.
