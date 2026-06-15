# LS-Matchmaker · Web-V2 (Redesign)

Komplettes Redesign der Marketing-Site des [LS-Matchmaker](https://github.com/steffenagohl-creator/liberatingstructures).
**Auf dem Branch `wip/pi-minimax/liberatingstructures-redesign`**, nicht auf `main` — `main` und die Originaldateien in `frontend/public/` sind **unangetastet**.

## Was ist neu (vs. `frontend/public/`)

| | Original (v1) | Redesign (v2) |
|---|---|---|
| **Theme** | „Creme & Bernstein" (warm, terracotta) | Helles Off-White + Salbei-Grün + Gold-Akzent |
| **Schrift Headings** | Inter (durchgängig Sans) | System-Serif (Iowan Old Style / Lora) |
| **Schrift Body** | Inter (lokal gehostet) | System-Sans (schneller, kein Download) |
| **DSGVO-Fonts** | ja (lokal) | ja (System-Stack, kein CDN) |
| **Layout** | Karten mit 1px-Border | Karten mit weicher Schatten-Hierarchie |
| **Hero** | Textbasiert, mittig | Textbasiert, Eyebrow-Pill, klare Hierarchie |
| **CTA-Hierarchie** | Ein Primär-Button | Primär (grün) + Akzent (gold) + Ghost |
| **Sektion "Du hast die Wahl"** | 3 Karten mit Emojis | 3 Karten mit Icon-Pill, klarem „Empfohlen"-Badge |

## Was ist **gleich geblieben** (semantisch)

- **Zweisprachigkeit DE/EN** (gleiches `<div class="block de|en">`-Pattern, gleicher JS-Mechanismus mit `localStorage`)
- **Alle Texte 1:1** vom Original übernommen (Hero, So funktioniert's, Du hast die Wahl, Was sind LS, Open Source, Impressum, Datenschutz, Cookies, Nutzungsbedingungen)
- **App-Integration:** nur verlinkt via `<a href="/app.html">` (kein iFrame, kein Eingriff in `frontend/src/`)
- **CC BY-SA 4.0 Attribution** und alle Lizenzhinweise wie im Original

## Dateistruktur

```
web-v2/
├── index.html                              ← Landing-Page (Hero + Steps + Modi + CTA)
├── was-sind-liberating-structures.html     ← Ausführliche Einführung
├── impressum.html
├── datenschutz.html
├── cookies.html
├── nutzungsbedingungen.html
├── assets/
│   ├── css/styles.css                      ← Geteilte CSS (~12 KB, kein Build)
│   └── js/lang.js                          ← Sprachumschaltung (DE/EN, ~1.3 KB)
└── README.md
```

## Was die App **nicht** berührt

- `frontend/app.html` — die React/Vite-App (unverändert)
- `frontend/src/*` — App-Komponenten
- `frontend/public/index.html` + `*.html` — Original-Marketing-Site
- `backend/`, `data/`, `voice-agent/`, `infra/`, `LS ICONS SVG/` — alles

## Lokal ansehen

Einfach `web-v2/index.html` in einem Browser öffnen — keine Build-Schritte, keine Dependencies.

## Deploy-Strategie (Vorschlag)

1. **Preview:** den `web-v2/`-Ordner lokal öffnen
2. **Vergleich:** neben `frontend/public/index.html` im Browser öffnen
3. **Aktivierung (später, nach Steffens Go):** `web-v2/*` nach `frontend/public/` kopieren und alte Dateien ersetzen ODER direkt den nginx-`root` auf `web-v2/` umstellen (z. B. via Sub-Pfad `/v2/`)

## Status

- ✅ Branch angelegt: `wip/pi-minimax/liberatingstructures-redesign`
- ✅ Alle 6 HTML-Seiten + CSS + JS geschrieben
- ⏳ Commit + Push stehen aus
- ⏳ Steffen-Review + Merge-Genehmigung auf `main` stehen aus
