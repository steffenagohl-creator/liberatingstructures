# LS-Matchmaker · Web-V3 (produktives Redesign)

Komplettes Redesign der Marketing-Site des [LS-Matchmaker](https://github.com/steffenagohl-creator/liberatingstructures).
**Branch `wip/pi-minimax/liberatingstructures-v3`** — basiert auf `main` (nicht auf dem v2-Branch). `main` und alle Originaldateien (`frontend/public/`, `frontend/src/`, `backend/`, `data/`, `LS ICONS SVG/`, `infra/`, `voice-agent/`) sind **unangetastet**.

## Was ist neu (vs. `frontend/public/`)

| | Original (v1) | Fingerübung (v2) | **Produktiv (v3)** |
|---|---|---|---|
| **Status** | produktiv (live) | Test, weggeworfen | **produktiv, merge-fähig** |
| **Theme** | „Creme & Bernstein" (warm, terracotta) | Off-White + Salbei-Grün + Gold | **Warme Erdtöne (Terracotta + Senf), moderner** |
| **Schrift Headings** | Inter (Sans) | System-Serif | **System-Serif-Stack mit Fraunces-Fallback** |
| **Schrift Body** | Inter (lokal) | System-Sans | **System-Sans-Stack (Inter, system-ui)** |
| **DSGVO-Fonts** | ja (lokal) | ja (System-Stack) | **ja (System-Stack, kein CDN)** |
| **Souveränität-Block** | 3 Karten mit Emojis 🔒🇪🇺🇺🇸 | 3 Karten mit Icon-Pills | **Vergleichsmatrix + 3 Erklär-Karten (ohne Emojis, ohne LS-Piktogramme)** |
| **Sicherheits-Sektion** | im Footer versteckt | im Footer versteckt | **eigene prominente Sektion auf der Landing-Page** |
| **App-Button** | mittig im Hero + unten | 2× im Hero | **sticky im Header + 2× im Hero = 3× sichtbar** |
| **Hero-Aussage** | „Hallo und schön, dass du da bist" | „Die passende Methode ... in Minuten" | **„Die passende Methode für eure Gruppe. In Minuten, nicht Stunden." + Unterzeile: „Du musst das Buch nicht gelesen haben"** |
| **Animationen** | statisch | minimal | **smooth scroll, reveal-on-scroll, hover-micros, animated hero-glow** |
| **Datenschutz-Sichtbarkeit** | Footer | Footer | **eigene Section auf der Landing + Link in der Top-Nav** |

## Was ist **gleich geblieben** (semantisch)

- **Zweisprachigkeit DE/EN** (gleiches `<div class="block de|en">`-Pattern, gleicher JS-Mechanismus mit `localStorage`)
- **Alle Texte 1:1** vom Original übernommen (Hero, So funktioniert's, Was sind LS, Offen und nachvollziehbar, Impressum, Datenschutz, Cookies, Nutzungsbedingungen)
- **App-Integration:** nur verlinkt via `<a href="/app.html">` (kein iFrame, kein Eingriff in `frontend/src/`)
- **CC BY-SA 4.0 Attribution** und alle Lizenzhinweise wie im Original

## Was die App **nicht** berührt

- `frontend/app.html` — die React/Vite-App (unverändert)
- `frontend/src/*` — App-Komponenten
- `frontend/public/index.html` + `*.html` — Original-Marketing-Site
- `backend/`, `data/`, `voice-agent/`, `infra/`, `LS ICONS SVG/` — alles

## Dateistruktur

```
web-v3/
├── index.html                              ← Landing-Page
│                                            (Hero + Worauf + Sicherheit-Matrix + 3 Modi
│                                             + So funktioniert's + Was sind LS + Offen + CTA)
├── was-sind-liberating-structures.html     ← Ausführliche Einführung
├── impressum.html
├── datenschutz.html
├── cookies.html
├── nutzungsbedingungen.html
├── assets/
│   ├── css/styles.css                      ← Geteilte CSS (~19 KB, kein Build)
│   └── js/lang.js                          ← Sprache + Sticky-Header + Reveal (~3 KB)
├── tests/
│   └── test-html-structure.sh              ← Smoke-Tests für HTML-Konsistenz
└── README.md
```

## Farbsystem (V3)

| Token | Hex | Verwendung |
|---|---|---|
| `--bg` | `#FAF6EE` | warmes Off-White, Body |
| `--surface` | `#FFFFFF` | Karten |
| `--surface-2` | `#F1E9D8` | Sektion-Trennung (Sicherheit) |
| `--ink` | `#2A2520` | Haupttext |
| `--primary` | `#B85827` | Terracotta — Buttons, Headings-Akzent |
| `--accent` | `#D4A017` | Senf-Gelb — finale CTAs, Hervorhebungen |

## Souveränitäts-Block — das „Rad neu erfunden"

Statt drei Emoji-Karten: **eine Vergleichsmatrix** (5 Zeilen × 3 Stufen) mit klaren Spaltenüberschriften, plus **drei Erklär-Karten darunter** mit selbstgemachten SVG-Checkmark-Icons (kein Emoji, kein LS-Piktogramm, keine Copyright-Konflikte).

**Die 5 Matrix-Zeilen:**
1. Wo werden die Daten verarbeitet?
2. Wer sieht deine Eingaben?
3. Wie spricht die KI mit dir?
4. Wer bezahlt die KI-Kosten?
5. Wer sieht den Vorschlag?

**Die 3 Stufen:** Souverän · EU (Mistral, empfohlen) · Komfort (OpenAI Realtime)

## Animationen („Vibration")

- **Smooth scroll** zwischen Ankern
- **Header bekommt `.scrolled`-Klasse** ab 8 px Scroll-Tiefe (Hintergrund-Intensität + Schatten)
- **Cards + Modis reveal-on-scroll** (IntersectionObserver, einmal pro Element, 12% Sichtbarkeit)
- **Hero-Hintergrund atmet** (sehr subtil, 12s alternierende Animation)
- **Hover-Mikrointeraktionen** (Buttons heben sich, Icons rotieren leicht, Karten heben sich, Mark-Logo wackelt beim Hover)
- **`prefers-reduced-motion` respektiert** (alle Animationen werden auf 0.01ms gesetzt, Karten werden direkt angezeigt)

## Was die Webseiten-Originale **NICHT** haben, was v3 hat

- **Vergleichsmatrix** für Souveränität (Original: 3 einfache Karten)
- **Sticky App-CTA** im Header (Original: nur Hero)
- **Sicherheits-Anker** in der Top-Nav, der auf die prominente Sektion auf der Landing springt
- **Animationen / Reveal-on-scroll** (Original: statisch)
- **Gradient-Hero** statt solidem Hintergrund

## Was v3 **nicht** hat, was das Original hat

- **Spenden-Hinweis / Kaffeetasse** (bewusst weggelassen für jetzt — Steffen: "keine Spendenseite für jetzt, auch kein Spendenaufruf")
- **QR-Code** (Original hatte einen Platzhalter; im v3 bewusst weggelassen, weil der Google-Play-Link dahinter unklar ist)
- **Emojis als Icons** (Original: 🔒🇪🇺🇺🇸 — v3: selbstgemachte SVG-Checkmark-Icons)
- **LS-Piktogramme** (Original verwendete teilweise; v3 verzichtet aus Copyright-Gründen)

## Smoke-Tests

```bash
bash web-v3/tests/test-html-structure.sh
```

Prüft:
- Alle 6 HTML-Seiten existieren
- Jede hat Header, Footer, `lang.js`
- Sticky-App-Button ist auf jeder Seite
- Datenschutz-Links funktionieren (Datenschutz → Index#sicherheit)
- DE/EN-Blöcke sind parallel vorhanden
- Keine `TODO`-Platzhalter oder leeren `<div>`s
- App-Links zeigen auf `/app.html`

## Lokal ansehen

Einfach `web-v3/index.html` im Browser öffnen — keine Build-Schritte, keine Dependencies.

## Deploy-Strategie (Vorschlag)

1. **Preview:** Branch `wip/pi-minimax/liberatingstructures-v3` auf GitHub öffnen
2. **Vergleich:** Side-by-side mit `frontend/public/index.html`
3. **Aktivierung (nach Steffens Go):**
   - **Option A — Ordner ersetzen:** `web-v3/*` nach `frontend/public/` kopieren, alte `*.html` ersetzen
   - **Option B — Parallel:** v3 unter `frontend/public/v3/` ausliefern, Besucher können wählen
   - **Option C — nginx-Root umstellen:** v3 als neuen Root konfigurieren, alte Dateien archivieren

## Lessons für die nächste Mission

- **Erst Briefing, dann Bauen** — Steffens Fingerübungs-Test hat gezeigt, dass ich ohne Briefing zwar etwas Bauen kann, das „besser als vorher" ist, aber nicht „produktiv richtig". Beim nächsten Mal: zuerst die 18-Fragen-Runde.
- **Skill-Vorschläge sind Anregungen, keine Pflicht** — `ui-ux-pro-max` schlug Neumorphism vor; ich habe Terracotta gewählt, weil das zur Marke passt und Steffen mag.
- **Souveränität verdient eine eigene Sektion, nicht 3 Emoji-Karten im Footer.**
- **West-Coast-Lockerheit ≠ infantil** — die Tonalität muss casual sein, aber seriös in der Substanz.
- **„Mehr Vibration" durch native CSS-Animationen, nicht durch JS-Frameworks.**

## Status

- ✅ Branch angelegt: `wip/pi-minimax/liberatingstructures-v3` (basiert auf `main`)
- ✅ Alle 6 HTML-Seiten + CSS + JS geschrieben
- ✅ Smoke-Tests vorhanden
- ⏳ Commit + Push stehen aus
- ⏳ Steffen-Review + Merge-Genehmigung auf `main` stehen aus
