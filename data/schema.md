# Daten-Schema der Wissens-Datenbank (`data/structures.json`)

Diese Datei **beschriftet** jedes Feld der Wissens-Datenbank in klarer Sprache — damit
Menschen, KIs/Agenten und Crawler die Daten zuverlässig verstehen (siehe Leitprinzip in
`CLAUDE.md`). Die Datenbank ist eine JSON-Datei mit einem Kopfbereich (Meta-Infos) und einer
Liste `structures` (die einzelnen Methoden).

## Leitprinzip: barrierefrei & maschinen-/KI-bedienbar (gilt für ALLE Felder)

Alles ist gleichermaßen nutzbar durch **Screenreader**, **Sprachsteuerung**, **KIs/Agenten
(MCP)** und **Crawler**. Daraus folgen verbindliche Regeln für die Daten:

- **Sprechende Feldnamen + dieses dokumentierte Schema** (selbstbeschreibende Datengrundlage).
- **Stabile, eindeutige Bezeichner:** jede Struktur hat `id` **und** `slug`; Prinzipien `P1–P10`;
  alle Enum-Werte sind unten dokumentiert. So können Sprachsteuerung/MCP/Crawler jedes Element
  eindeutig ansteuern und referenzieren.
- **Echte, gespeicherte Texte in beiden Sprachen** (kein Laufzeit-Übersetzer) → saubere
  Inhalte für Screenreader und Crawler in DE und EN. Beim Rendern bekommt jeder Textblock seine
  **Sprachauszeichnung** (`lang="de"` bzw. `lang="en"`).
- **Alt-Texte:** jede Struktur trägt `icon_alt` (Beschreibung des LS-Icons) — für blinde
  Menschen und Crawler.

## Zweisprachigkeit (DE/EN)

Die App wird zweisprachig (Umschalt-Knopf, kein Auto-Übersetzer). Deshalb gilt:

- **Sprachabhängige Textfelder** werden als Objekt `{ "de": "…", "en": "…" }` gespeichert.
  Bei **Text-Listen** (z. B. `beispielsaetze`, `tipps`, `anlaesse`) als `{ "de": [ … ], "en": [ … ] }`.
- **Sprachneutrale Felder** bleiben einfach: `id`, `slug`, `type`, `base_structure`, `edition`,
  `source_url`, `purpose_tags`, `arc_role`, Gruppengrößen, Dauern, `online_capable`, `difficulty`,
  `typical_predecessors`/`successors`, `embodied_principles`, `description_origin`, `icon`.
  (Enum-Werte sind sprachneutrale Codes; ihre Anzeige-Labels stehen zweisprachig in `erlaubte_werte`.)

## Kopfbereich (Meta)

| Feld | Bedeutung |
|---|---|
| `schema_version` | Version dieses Schemas (für spätere Änderungen). |
| `beschreibung` | Kurzbeschreibung, was die Datei enthält. |
| `quelle` | Haupt-Herkunft der Inhalte. |
| `lizenz_hinweis` | Lizenz/Attribution der Inhalte (Verweis auf `NOTICE.md`). |
| `matchmaker_hinweis` | Offizieller Disclaimer des Kategorien-Matchmakers: Die Zweck-Kategorie (`purpose_tags`) ist eine „ungenaue, aber zu Beginn hilfreiche Vereinfachung – fast jede LS wirkt auch in anderen Kategorien." Wird der KI als Gewichtungs-Hinweis mitgegeben. |
| `erlaubte_werte` | Zulässige Werte (sprachneutrale Codes) für `edition`, `type`, `purpose_tags`, `arc_role`, `difficulty`. |
| `enum_labels` | Zweisprachige Anzeige-Labels `{de, en}` zu den Enum-Codes (für UI, Screenreader, Crawler) – z. B. `analysieren → {de:"Analysieren", en:"Analyze"}`. |

## Felder pro Struktur (`structures[]`)

Spalte **„Sprache"**: `{de,en}` = zweisprachiges Textfeld; `neutral` = sprachneutral.

| Feld | Sprache | Typ | Bedeutung |
|---|---|---|---|
| `id` | neutral | Ganzzahl | Eindeutige, stabile Nummer der Methode. |
| `slug` | neutral | Text | Stabile Kurzkennung für URLs/Verknüpfungen (z. B. `1-2-4-all`). Referenziert in `typical_predecessors`/`successors`. |
| `name` | `{de,en}` | Text | Anzeigename je Sprache (z. B. „9 Whys"/„Nine Whys"). |
| `type` | neutral | Text | `official` (Buch-LS), `variation` (Abwandlung), `punctuation` („Satzzeichen"), `in_development` (Prototyp). |
| `base_structure` | neutral | `slug`/`null` | Bei `variation`: die Original-Struktur. Sonst `null`. |
| `edition` | neutral | Text | `original` = die 33 Kern-LS; `extended` = später ergänzte (die 10 neuen). Steuert die App-Umschaltung „klein (33)" ↔ „alle (43)". |
| `short_desc` | `{de,en}` | Text | Verständliche Kurzbeschreibung (1–3 Sätze) für die Karte (Ebene 1). |
| `objective` | `{de,en}` | Text | Kanonisches Ziel aus dem **offiziellen LS Selection Matchmaker** (Fieldbook 2026) – zentraler Matching-Schlüssel. Gepflegt in `ls_objectives.json`, beim Import je `slug` übernommen. |
| `source_url` | neutral | URL | Link zur Original-Detailseite. **Pflicht.** |
| `purpose_tags` | neutral | Liste | **Offizielle Zweck-Kategorie(n)** aus dem deutschen LS-Matchmaker, **1:1 übernommen** (nicht interpretiert), leer wenn das Original keine vergibt: `offenlegen, teilen, analysieren, strategie, helfen, planen, solo`. Anzeige-Labels in `erlaubte_werte`. Siehe `matchmaker_hinweis`. |
| `arc_role` | neutral | Liste | **Internes Hilfsfeld** (nicht aus dem Original): Rolle(n) im Spannungsbogen – `öffnen, divergieren, konvergieren, schließen`. Dient dem Quality Gate des Matchmakers (ein guter String hat Öffnendes und Schließendes). In der UI nicht als offizielle LS-Kategorie darstellen. |
| `group_size_min` | neutral | Ganzzahl | Empfohlene Mindest-Teilnehmerzahl. |
| `group_size_max` | neutral | Ganzzahl/`null` | Höchstzahl; `null` = nach oben offen. |
| `duration_min` | neutral | Ganzzahl | Mindestdauer in **Minuten**. |
| `duration_max` | neutral | Ganzzahl | Übliche Höchstdauer in **Minuten**. |
| `online_capable` | neutral | Wahrheitswert | `true`, wenn online (Remote) gut durchführbar. Die ausführliche Online-Anleitung steht in `guide.online_durchfuehrung`. |
| `materials` | `{de,en}` | Text | Benötigte/empfohlene Materialien und Raumhinweise. |
| `difficulty` | neutral | Text | Moderations-Schwierigkeit: `leicht, mittel, fortgeschritten`. |
| `typical_predecessors` | neutral | Liste `slug` | Methoden, die typischerweise **davor** in einem String stehen. |
| `typical_successors` | neutral | Liste `slug` | Methoden, die typischerweise **danach** stehen. Aus `guide.optional_string` quellentreu abgeleitet. |
| `scrum_use` | `{de,en}` | Text | Einsatz im Scrum-Kontext (Retro, Planning, Review, Daily, Refinement, Team-Start). |
| `icon` | neutral | Text | Datei-/Pfadkennung des offiziellen LS-Icons. |
| `icon_alt` | `{de,en}` | Text | **Alt-Text**: beschreibt das Icon für Screenreader und Crawler. |
| `design_elements` | gemischt | Objekt | Die 5 Designelemente (Texte je `{de,en}`, siehe unten). |
| `description_origin` | neutral | Text | Herkunft der **deutschen** Texte: `eigen` (selbst verfasst – v. a. die 10 neueren Strukturen), `uebersetzt_aus_en` (eigenständige Übersetzung aus dem englischen BY-SA-Feld dieses Datensatzes – die klassischen 33) oder `uebernommen` (übernommener Quelltext mit Attribution). Alle Varianten stehen unter CC BY-SA 4.0. |
| `attribution` | `{de,en}` | Text | Namensnennung + Lizenz (CC BY-SA 4.0). |
| `embodied_principles` | neutral | Liste | **Internes Hilfsfeld:** IDs besonders verkörperter LS-Prinzipien (`P1`–`P10`); Details in `ls_principles.json`. |
| `guide` | gemischt | Objekt | Ausführlicher **Detailguide** (Ebene 2); Aufbau siehe unten. |

### `design_elements` (die 5 Designelemente; alle Texte `{de,en}`)

| Feld | Bedeutung |
|---|---|
| `einladung` | Die präzise Frage/Aufgabe, die den Beitrag rahmt. |
| `raum_materialien` | Physische/digitale Anordnung und benötigte Materialien. |
| `einbindung` | Wer spricht, wie lange, wie oft (Verteilung der Beteiligung). |
| `gruppenkonfiguration` | Abfolge der Gruppengrößen (einzeln → Paare → … → alle). |
| `ablauf_dauer` | Schritte und ihre Zeiten (Rhythmus/Timing). |

### `guide` (Detailguide – Ebene 2)

Die Karte (Felder oben) ist die schnelle Übersicht. Der `guide` ist die **tiefe Anleitung**:
die aus DE- und EN-Quellseite zusammengeführte, ins Deutsche **und** Englische gepflegte
Vollanleitung (CC BY-SA 4.0), sodass eine Moderatorin ohne Vorwissen die Methode durchführen
kann. Alle Texte zweisprachig `{de,en}`. Felder (alle optional):

| Feld | Sprache | Bedeutung |
|---|---|---|
| `was_wird_moeglich` | `{de,en}` | Ausführlicher Zweck („What is made possible"). |
| `einladung` | `{de,en}` | Die vollständige Einladung (Structuring Invitation) im Wortlaut. |
| `beispielsaetze` | `{de,en}` (Listen) | Konkrete Beispiel-/Satzanfänge oder Beispielfragen. |
| `schritte` | gemischt | Geordnete Liste: `{ "phase": {de,en}, "dauer_min": Ganzzahl, "beschreibung": {de,en} }`. |
| `varianten` | gemischt | Variationen/Riffs: `{ "name": {de,en}, "beschreibung": {de,en} }`. |
| `tipps` | `{de,en}` (Listen) | Tipps & Fallstricke („Tips and Traps"). |
| `anlaesse` | `{de,en}` (Listen) | Typische Einsatzanlässe („Wann einsetzen"). |
| `material_setup` | `{de,en}` | Ausführliche Material-/Raum-/Setup-Hinweise. |
| `online_durchfuehrung` | `{de,en}` | **Ausführliche Online-/Remote-Anleitung:** wie man die Struktur per Videokonferenz durchführt (Tools, Breakout-Räume, Chat/Whiteboard, konkrete Anpassungen). |
| `optional_string` | `{de,en}` | **Optional String** (offizielle LS-Empfehlung): Wortlaut der Quelle, welche anderen Strukturen sich davor/danach/zusammen anbieten. EN quellentreu, DE als Übersetzung. Aus diesem Text sind die sprachneutralen `typical_predecessors`/`typical_successors` (oben) abgeleitet. Für die Detailansicht; nicht in jeden Match injiziert. |
