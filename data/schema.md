# Daten-Schema der Wissens-Datenbank (`data/structures.json`)

Diese Datei **beschriftet** jedes Feld der Wissens-Datenbank in klarer Sprache — damit
Menschen, KIs/Agenten und Crawler die Daten zuverlässig verstehen (siehe Leitprinzip in
`CLAUDE.md`). Die Datenbank ist eine JSON-Datei mit einem Kopfbereich (Meta-Infos) und einer
Liste `structures` (die einzelnen Methoden).

## Kopfbereich (Meta)

| Feld | Bedeutung |
|---|---|
| `schema_version` | Version dieses Schemas (für spätere Änderungen). |
| `beschreibung` | Kurzbeschreibung, was die Datei enthält. |
| `quelle` | Haupt-Herkunft der Inhalte. |
| `lizenz_hinweis` | Lizenz/Attribution der Inhalte (Verweis auf `NOTICE.md`). |
| `erlaubte_werte` | Listen der zulässigen Werte für `edition`, `type`, `purpose_tags`, `arc_role`, `difficulty`. |

## Felder pro Struktur (`structures[]`)

| Feld | Typ | Bedeutung |
|---|---|---|
| `id` | Ganzzahl | Eindeutige, stabile Nummer der Methode. |
| `name` | Text | Anzeigename, z. B. „1-2-4-All". |
| `slug` | Text | Kurzkennung für URLs/Verknüpfungen, z. B. „1-2-4-all". Wird in `typical_predecessors`/`successors` referenziert. |
| `type` | Text | Klassifikation: `official` (die 33 aus dem Buch), `variation` (Abwandlung einer Original-LS), `punctuation` („Satzzeichen" zwischen Strukturen), `in_development` (neuer Prototyp). |
| `base_structure` | Text (`slug`) oder `null` | Bei `variation`: die Original-Struktur, von der sie abgewandelt ist (z. B. `1-2-4-all`). Sonst `null`. |
| `edition` | Text | `original` = die 33 Kern-LS; `extended` = später ergänzte Methoden. Steuert die App-Umschaltung „klein (33)" ↔ „Extended (alle)". |
| `short_desc` | Text | Verständliche Kurzbeschreibung (1–3 Sätze): Worum geht es, was bewirkt die Methode. |
| `objective` | Text | Kanonisches Ziel (offizieller **LS Selection Matchmaker**): das eine Ziel, das die Struktur erfüllt – zentraler Matching-Schlüssel. Gepflegt in `ls_objectives.json`, beim Import übernommen. |
| `source_url` | Text (URL) | Link zur Original-Detailseite (Quelle/Attribution). **Pflicht.** |
| `purpose_tags` | Liste | Zweck-Kategorien aus den erlaubten Werten: `offenlegen, teilen, analysieren, strategie, helfen, planen, solo`. Eine oder mehrere. |
| `arc_role` | Liste | Rolle(n) im Spannungsbogen einer Session: `öffnen, divergieren, konvergieren, schließen`. Wichtig fürs spätere Quality Gate (ein guter String hat u. a. etwas Öffnendes und etwas Schließendes). |
| `group_size_min` | Ganzzahl | Empfohlene Mindest-Teilnehmerzahl. |
| `group_size_max` | Ganzzahl oder `null` | Empfohlene Höchstzahl; `null` = nach oben offen/unbegrenzt. |
| `duration_min` | Ganzzahl | Mindestdauer in **Minuten**. |
| `duration_max` | Ganzzahl | Übliche Höchstdauer in **Minuten**. |
| `online_capable` | Wahrheitswert | `true`, wenn die Methode online (Remote) gut durchführbar ist. |
| `materials` | Text | Benötigte/empfohlene Materialien und Raumhinweise (inkl. Online-Hinweise). |
| `difficulty` | Text | Schwierigkeitsgrad der Moderation: `leicht, mittel, fortgeschritten`. |
| `typical_predecessors` | Liste von `slug` | Methoden, die typischerweise **davor** in einem String stehen. |
| `typical_successors` | Liste von `slug` | Methoden, die typischerweise **danach** in einem String stehen. |
| `scrum_use` | Text | Wie/wofür die Methode im Scrum-Kontext eingesetzt wird (Retro, Planning, Review, Daily, Refinement, Team-Start). |
| `design_elements` | Objekt | Die 5 Designelemente (siehe unten). |
| `description_origin` | Text | `uebernommen` (Text aus der Quelle, mit Attribution) oder `eigen` (selbst verfasst). |
| `attribution` | Text | Namensnennung + Lizenz, wenn Inhalte übernommen wurden. |
| `embodied_principles` | Liste | IDs der besonders verkörperten LS-Prinzipien (`P1`–`P10`); Details in `ls_principles.json`. |
| `guide` | Objekt | Ausführlicher **Detailguide** (Ebene 2) – die vollständige, ins Deutsche übertragene Quellseite als Gedächtnisstütze. Aufbau siehe unten. |

### `design_elements` (die 5 Designelemente jeder Mikrostruktur)

| Feld | Bedeutung |
|---|---|
| `einladung` | Die präzise Frage/Aufgabe, die den Beitrag rahmt. |
| `raum_materialien` | Physische/digitale Anordnung und benötigte Materialien. |
| `einbindung` | Wer spricht, wie lange, wie oft (Verteilung der Beteiligung). |
| `gruppenkonfiguration` | Abfolge der Gruppengrößen (z. B. einzeln → Paare → Vierer → alle). |
| `ablauf_dauer` | Schritte und ihre Zeiten (Rhythmus/Timing). |

### `guide` (Detailguide – Ebene 2)

Die Stichwortkarte (Felder oben) ist die schnelle Übersicht. Der `guide` ist die **tiefe
Anleitung**: die vollständige Quellseite, ins Deutsche übertragen (CC BY-SA 4.0, mit Attribution),
sodass eine Moderatorin ohne Vorwissen die Methode durchführen kann. Felder (alle optional):

| Feld | Bedeutung |
|---|---|
| `was_wird_moeglich` | Ausführlicher Zweck („What is made possible"): wozu die Methode dient. |
| `einladung` | Die vollständige Einladung (Structuring Invitation) im Wortlaut. |
| `beispielsaetze` | Liste konkreter Beispiel-/Satzanfänge oder Beispielfragen. |
| `schritte` | Geordnete Liste: `{ "phase", "dauer_min", "beschreibung" }`. |
| `varianten` | Variationen/Riffs (inkl. Online-Variante): `{ "name", "beschreibung" }`. |
| `tipps` | Tipps & Fallstricke („Tips and Traps"). |
| `anlaesse` | Typische Einsatzanlässe („Wann einsetzen"). |
| `material_setup` | Ausführliche Material- und Raum-/Setup-Hinweise. |
