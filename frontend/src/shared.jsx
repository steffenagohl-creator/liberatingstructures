/* ===================================================================
   LS-MATCHMAKER — geteiltes Fundament  (portiert aus design/ls-data.jsx)
   Theme-Tokens · Fragenmodell · Methoden-Bibliothek · Empfehlung (Mock)
   + kleine geteilte UI-Bausteine (StatusBar, Glyph, ChapterBar)
   Aus window-Globals → echte ES-Module-Exporte. Optik 1:1 zum Prototyp.
   =================================================================== */
import { iconSvg } from './icons.js'

// ---- 1. THEME (verfeinertes "Creme & Bernstein") ------------------
// serif/sans verweisen auf die LOKAL gebündelten Variable-Fonts (@fontsource,
// import in main.jsx) — gleiche Schriften wie der Prototyp, nur ohne Google-CDN.
export const THEME = {
  bg:      '#F7F2E9',   // Creme, etwas wärmer
  surface: '#FFFDF8',   // Kartenfläche
  sand:    '#FBEEDB',   // weicher Bernstein-Wash
  ink:     '#26221C',   // warmes Fast-Schwarz
  muted:   '#857B6D',   // gedämpfter Text
  faint:   '#A99E8D',   // sehr leise
  line:    '#EADFCD',   // feine Linien
  amber:   '#D98A33',   // Primär (Bernstein, etwas tiefer)
  terra:   '#B85827',   // Tiefe (Terrakotta)
  sage:    '#5E8A78',   // kühler Zweitakzent (nur Leinwand-Visual)
  serif:   "'Newsreader Variable', Georgia, 'Times New Roman', serif",
  sans:    "'Hanken Grotesk Variable', system-ui, -apple-system, sans-serif",
};

// Einmaliges Einspielen von CSS-Variablen + Keyframes.
// (Die Fonts werden in main.jsx lokal importiert — daher KEIN Google-Fonts-<link> mehr.)
export function injectTheme() {
  if (document.getElementById('ls-theme')) return;

  const s = document.createElement('style');
  s.id = 'ls-theme';
  s.textContent = `
    :root{
      --bg:${THEME.bg};--surface:${THEME.surface};--sand:${THEME.sand};
      --ink:${THEME.ink};--muted:${THEME.muted};--faint:${THEME.faint};
      --line:${THEME.line};--amber:${THEME.amber};--terra:${THEME.terra};
      --sage:${THEME.sage};
    }
    .ls-app *{box-sizing:border-box;-webkit-font-smoothing:antialiased;}
    .ls-app{font-family:${THEME.sans};color:var(--ink);}
    .ls-app ::selection{background:var(--sand);}
    .ls-serif{font-family:${THEME.serif};}
    /* Echte LS-Icons: erben currentColor, füllen die getönte Kachel. */
    .ls-icon svg{width:100%;height:100%;display:block;fill:currentColor;}
    @keyframes lsRise{from{transform:translateY(10px);}to{transform:translateY(0);}}
    @keyframes lsFade{from{transform:translateY(4px);}to{transform:translateY(0);}}
    @keyframes lsPop{0%{transform:scale(.55);}60%{transform:scale(1.08);}100%{transform:scale(1);}}
    @keyframes lsWave{0%,100%{transform:scaleY(.4);}50%{transform:scaleY(1);}}
    @keyframes lsPulse{0%,100%{opacity:.45;}50%{opacity:1;}}
  `;
  document.head.appendChild(s);
}

// ---- 2. FRAGENMODELL ---------------------------------------------
// Die geführte Diagnose. "chapter" gruppiert für die Fortschrittslogik.
// "adaptive" = wird nur ausgelöst, wenn eine frühere Antwort Spannung
// signalisiert (zeigt die Intelligenz des Beraters).
export const QUESTIONS = [
  {
    id: 'situation', chapter: 'Verstehen', icon: '◑',
    label: 'Situation',
    agent: 'Erzählt mir kurz: Was beschäftigt eure Gruppe gerade?',
    q: 'Was beschäftigt euch gerade?',
    hint: 'Ein, zwei Sätze genügen — oder wählt etwas Passendes.',
    kind: 'text',
    presets: [
      { v: 'Frust nach dem Sprint, in der Retro sagt keiner etwas', tension: true },
      { v: 'Wir treffen eine wichtige Entscheidung und kommen nicht weiter' },
      { v: 'Neues Team, wir kennen uns noch kaum' },
      { v: 'Immer dieselben reden, viele bleiben still', tension: true },
    ],
  },
  {
    id: 'ziel', chapter: 'Verstehen', icon: '◓',
    label: 'Ziel',
    agent: 'Und was soll am Ende der Sitzung anders sein?',
    q: 'Was soll am Ende anders sein?',
    hint: 'Das Ergebnis, das ihr euch wünscht.',
    kind: 'single',
    options: ['Alle reden ehrlich', 'Die Ursache liegt offen', 'Eine Entscheidung steht', 'Ideen sind gesammelt', 'Ein Plan steht'],
  },
  {
    id: 'zweck', chapter: 'Verstehen', icon: '●',
    label: 'Schwerpunkt',
    agent: 'Worauf liegt der Schwerpunkt — was braucht die Gruppe am dringendsten?',
    q: 'Worauf liegt der Schwerpunkt?',
    hint: 'Ein Schritt führt zum nächsten — wir wählen den Einstieg.',
    kind: 'single',
    options: ['Offenlegen', 'Analysieren', 'Entscheiden', 'Planen', 'Verbinden'],
    sub: {
      'Offenlegen': 'Stimmen sichtbar machen, Schweigen lösen',
      'Analysieren': 'Vom Symptom zur eigentlichen Ursache',
      'Entscheiden': 'Aus Optionen gemeinsam wählen',
      'Planen': 'Einsicht in konkrete Schritte übersetzen',
      'Verbinden': 'Vertrauen und Beziehung stärken',
    },
  },
  {
    id: 'sicherheit', chapter: 'Vertiefen', icon: '◔', adaptive: true,
    label: 'Sicherheit',
    agent: 'Wie offen kann das Team aktuell Kritik aussprechen?',
    why: 'Ihr habt Spannung angedeutet — bei heiklen Themen hängt die richtige Methode stark davon ab, wie sicher sich die Gruppe fühlt.',
    q: 'Wie offen kann Kritik ausgesprochen werden?',
    hint: 'Ehrliche Einschätzung — das verändert die Empfehlung spürbar.',
    kind: 'single',
    options: ['Sehr offen', 'Eher vorsichtig', 'Angespannt / heikel', 'Weiß ich nicht'],
  },
  {
    id: 'groesse', chapter: 'Rahmen', icon: '◕',
    label: 'Gruppengröße',
    agent: 'Wie viele Menschen sind dabei?',
    q: 'Wie groß ist die Gruppe?',
    hint: 'Manche Methoden brauchen Kleingruppen, andere tragen einen ganzen Saal.',
    kind: 'single',
    options: ['2–4', '5–9', '10–20', '20+'],
  },
  {
    id: 'zeit', chapter: 'Rahmen', icon: '◷',
    label: 'Zeit',
    agent: 'Und wie viel Zeit habt ihr?',
    q: 'Wie viel Zeit habt ihr?',
    hint: 'Der Vorschlag passt sich eurem Zeitfenster an.',
    kind: 'single',
    options: ['15 Min', '30 Min', '60 Min', 'Halber Tag'],
  },
  {
    id: 'setting', chapter: 'Rahmen', icon: '◶',
    label: 'Setting',
    agent: 'Trefft ihr euch im Raum oder online?',
    q: 'Präsenz oder online?',
    hint: 'Ich schlage nur Methoden vor, die in eurem Setting tragen.',
    kind: 'single',
    options: ['Präsenz', 'Online', 'Hybrid'],
  },
];

// ---- 3. ECHTE LS-ICONS (Inline, aus dem Grundgerüst übernommen) ---
// Äußere Formen ohne fill -> erben currentColor; weiße Details bleiben.
// (Werden in Stufe 2.4 durch die echten 46 SVGs ersetzt — semantisch per Name zugeordnet.)
export const ICONS = {
  '1-2-4-All': { vb: '0 0 49.8 51.3', svg:
    '<polygon points="30 9 36.7 7.1 36.8 0 41.9 11.1 30 9"/><polygon points="9.9 16.7 10.2 9.7 3.6 7.4 15.7 6 9.9 16.7"/><polygon points="40.3 35.8 39.3 42.7 45.7 45.6 33.5 45.9 40.3 35.8"/><circle cx="25" cy="3.8" r="3.8"/><circle cx="46.1" cy="19.2" r="3.8"/><circle cx="46.1" cy="32.8" r="3.8"/><path d="M23.3,50.9c-1.8-1-2.4-3.3-1.4-5.1,1-1.8,3.3-2.4,5.1-1.4,1.8,1,2.4,3.3,1.4,5.1-1,1.8-3.3,2.4-5.1,1.4Z"/><path d="M11,47.2c-1.8-1-2.4-3.3-1.4-5.1,1-1.8,3.3-2.4,5.1-1.4s2.4,3.3,1.4,5.1c-1,1.8-3.3,2.4-5.1,1.4Z"/><path d="M1.2,33c.5-2,2.5-3.2,4.6-2.7,2,.5,3.2,2.6,2.7,4.6-.5,2-2.5,3.2-4.6,2.7-2-.5-3.2-2.5-2.7-4.6Z"/><path d="M.1,19.9c.5-2,2.5-3.2,4.6-2.7,2,.5,3.2,2.5,2.7,4.6-.5,2-2.6,3.2-4.6,2.7-2-.5-3.2-2.5-2.7-4.6Z"/>' },
  '9 Whys': { vb: '0 0 112.3 112.3', svg:
    '<path d="M112.3,56.2c0,31-25.1,56.2-56.2,56.2-31,0-56.2-25.1-56.2-56.2S25.1,0,56.2,0s56.2,25.1,56.2,56.2Z"/><path fill="#fff" d="M20.8,71.1l3.9,9.6,3.9-9.6h2.9l3.9,9.6,3.9-9.6h4.6l-7.4,17h-1.9l-4.5-10.2-4.5,10.2h-1.8l-7.5-17h4.6Z"/><path fill="#fff" d="M50.4,62.9v10.6h.1c1.4-1.8,3.1-2.7,5.1-2.7s3.2.6,4.3,1.7c1.1,1.2,1.6,2.7,1.6,4.6v10.7h-4.4v-9.8c0-1.1-.3-2-.8-2.7s-1.3-1-2.2-1-1.3.2-1.9.6c-.6.4-1.2,1-1.9,1.9v11h-4.4v-24.9h4.4Z"/><path fill="#fff" d="M68.3,71.1l3.9,9,4-9h4.7l-11.5,25.1h-4.7l5.3-11.5-6.5-13.6h4.7Z"/><path fill="#fff" d="M88.6,70.8c.9,0,1.8.1,2.6.3.8.2,1.7.5,2.6,1v3.5c-.8-.5-1.7-1-2.7-1.3-1-.3-1.8-.5-2.6-.5s-1.1.1-1.5.4c-.4.2-.5.6-.5,1s.1.5.4.7c.3.2,1.1.7,2.4,1.4,1.9,1,3.2,1.9,4,2.7.8.8,1.2,1.8,1.2,2.9s-.6,2.9-1.7,3.8c-1.1.9-2.6,1.4-4.5,1.4s-2.3-.1-3.3-.4-1.9-.6-2.6-.9v-3.7c2.1,1.2,3.9,1.8,5.4,1.8s1.4-.1,1.8-.4c.5-.3.7-.6.7-1.1s0-.5-.2-.7c-.2-.2-.4-.4-.8-.7-.3-.2-1.4-.8-3.1-1.6-1.3-.6-2.3-1.3-3-2.1-.6-.8-1-1.7-1-2.7,0-1.5.6-2.7,1.7-3.5,1.2-.9,2.7-1.3,4.5-1.3Z"/><path fill="#fff" d="M68.2,32.2c0,11.3-9.2,20.5-20.5,20.5s-20.5-9.2-20.5-20.5,9.2-20.5,20.5-20.5,20.5,9.2,20.5,20.5Z"/><path d="M47.1,19.6c1.6,0,3,.4,4.2,1.1,1.2.7,2.2,1.8,2.9,3.1.7,1.3,1,2.9,1,4.6,0,2.6-.8,5.4-2.4,8.5s-3.7,5.8-6.3,8.3h-5.4c1.4-1.2,2.9-2.9,4.5-5s2.7-4,3.4-5.6c-.9.4-1.8.6-2.9.6-2,0-3.6-.7-4.9-2.1-1.3-1.4-1.9-3.2-1.9-5.4s.3-2.8,1-4c.7-1.2,1.6-2.2,2.8-2.9s2.6-1.1,4-1.1ZM43.7,27.5c0,1.1.3,2,.9,2.7.6.7,1.5,1.1,2.5,1.1s1.8-.4,2.4-1.1c.6-.7,1-1.6,1-2.6s-.3-2.2-1-2.9c-.6-.7-1.5-1.1-2.5-1.1s-1.8.4-2.4,1.1c-.6.7-.9,1.6-.9,2.8Z"/>' },
  '15% Solutions': { vb: '0 0 66.8 50.2', svg:
    '<path d="M66.8,0c-11.3,16.8-23,33.1-33.9,50.2C13,50.7,1.5,36.5,0,19.5,21.5,12.1,43.5,6.3,66.8,0Z"/><path fill="#fff" d="M14.2,20.6l5.3,18.3-4.1,1.2-5.3-18.3s4.1-1.2,4.1-1.2Z"/><path fill="#fff" d="M27.9,16.7l1.1,3.7-5.9,1.7,1,3.4c1.9-.7,3.6-.7,5.1,0,1.5.8,2.5,2,3,3.7.5,1.8.3,3.4-.6,4.8s-2.4,2.4-4.4,3c-1.8.5-3.4.6-4.7.3l-1-3.3c1.6.4,3.1.4,4.2,0,.8-.2,1.5-.7,1.9-1.3s.5-1.3.3-2.1c-.2-.8-.8-1.4-1.6-1.6-.8-.3-1.8-.2-3,0-.6.2-1.3.5-2,.8l-3-10.5s9.5-2.8,9.5-2.8Z"/><path fill="#fff" d="M33.1,12.9c.9-.3,1.7-.2,2.5.3s1.3,1.1,1.6,2c.3.9.2,1.7-.3,2.5-.4.8-1.1,1.3-2,1.6-.9.3-1.7.2-2.5-.3-.8-.4-1.3-1.1-1.6-2-.3-.9-.2-1.7.3-2.5.4-.8,1.1-1.3,2-1.6ZM34.5,17.6c.4-.1.7-.4.9-.7.2-.4.2-.8.1-1.2-.1-.4-.4-.7-.7-.9s-.7-.3-1.1-.2c-.4.1-.7.4-.9.7-.2.4-.2.8,0,1.2.1.4.4.7.7.9.4.2.7.3,1.1.2ZM42.1,10.3l-5.4,16.6-1.6.5,5.5-16.6,1.6-.5ZM42.2,18.4c.9-.3,1.7-.2,2.5.3s1.3,1.1,1.6,2c.3.9.2,1.7-.3,2.5-.4.8-1.1,1.3-2,1.6-.9.3-1.7.2-2.5-.3-.8-.4-1.3-1.1-1.6-2-.3-.9-.2-1.7.3-2.5s1.1-1.3,2-1.6ZM43.6,23.1c.4-.1.7-.4.9-.7s.2-.8.1-1.2c-.1-.4-.4-.7-.7-.9-.4-.2-.7-.3-1.1-.2-.4.1-.7.4-.9.7-.2.4-.2.8,0,1.2.1.4.4.7.7.9.4.2.7.3,1.1.2Z"/>' },
};

// ---- 4. METHODEN-BIBLIOTHEK --------------------------------------
// Mit Icon = echtes LS-Symbol; sonst typografischer Platzhalter-Glyph.
export const METHODS = {
  '1-2-4-All': {
    purpose: 'Offenlegen', size: '4–∞', time: '5–10 Min', online: true, level: 'leicht',
    desc: 'Jede Person denkt erst allein, dann zu zweit, dann zu viert — so kommen auch stille Stimmen sicher zu Wort.',
    role: 'öffnet',
  },
  'Conversation Café': {
    purpose: 'Offenlegen', size: '5–∞', time: '20–50 Min', online: true, level: 'leicht', glyph: '☕',
    desc: 'Im moderierten Gesprächskreis mit Redestab äußert sich jede Person reihum — ruhig, ohne Unterbrechung.',
    role: 'öffnet',
  },
  'Impromptu Networking': {
    purpose: 'Verbinden', size: '5–∞', time: '15–20 Min', online: true, level: 'leicht', glyph: '⇄',
    desc: 'Schnelle 1:1-Runden zu einer mutigen Frage bringen Energie in den Raum und verbinden alle miteinander.',
    role: 'öffnet',
  },
  '9 Whys': {
    purpose: 'Analysieren', size: '5–∞', time: '15–20 Min', online: true, level: 'mittel',
    desc: 'Durch wiederholtes „Warum?" gräbt sich die Gruppe vom Symptom zur eigentlichen Ursache und zum gemeinsamen Zweck vor.',
    role: 'vertieft',
  },
  'What I Need From You': {
    purpose: 'Verbinden', size: '7–∞', time: '40–55 Min', online: true, level: 'mittel', glyph: '⤝',
    desc: 'Funktionen sagen einander präzise, was sie voneinander brauchen — und bekommen klare Antworten. Löst festgefahrene Spannungen.',
    role: 'vertieft',
  },
  'Min Specs': {
    purpose: 'Entscheiden', size: '4–∞', time: '20–35 Min', online: true, level: 'mittel', glyph: '⊟',
    desc: 'Die Gruppe destilliert die wenigen absolut notwendigen Regeln heraus — und streicht alles, was nur scheinbar nötig ist.',
    role: 'vertieft',
  },
  '15% Solutions': {
    purpose: 'Planen', size: '4–∞', time: '10–15 Min', online: true, level: 'leicht',
    desc: 'Jede Person findet, was sie schon jetzt ohne neue Mittel oder Erlaubnis tun kann — kleine, sofort machbare Schritte.',
    role: 'schließt',
  },
  '25/10 Crowd Sourcing': {
    purpose: 'Entscheiden', size: '12–∞', time: '20–30 Min', online: false, level: 'mittel', glyph: '✦',
    desc: 'Die Gruppe sammelt mutige Ideen und bewertet sie in schnellen Runden — die stärksten steigen sichtbar nach oben.',
    role: 'schließt',
  },
};

// ---- 5. (entfällt) EMPFEHLUNGS-LOGIK ------------------------------
// Die Prototyp-Schein-Logik (buildRecommendation) + Mock-GUIDES wurden in Stufe 3
// durch das echte Backend ersetzt: /api/match/ liefert den begründeten String,
// /api/structures/<slug>/ die volle Anleitung. Siehe api/client.js + Result.jsx.

// ---- 6. GETEILTE UI-BAUSTEINE ------------------------------------
// Schlanke „App"-Statusleiste (kein klobiger Bezel — die UI zählt).
// Früher eine Fake-iOS-Statusleiste (Uhr „9:41" + Akku) — für die Web-App falsch und entfernt
// (Steffen 2026-06-06). Bleibt als schlanker Kopf-Abstand, damit die Screens ihr Spacing behalten.
export function StatusBar() {
  return <div style={{ height: 14, flex: '0 0 auto' }} aria-hidden="true" />;
}

// Echtes LS-Icon in getöntem Tile.
// Bevorzugt `iconFile` (Dateiname aus dem Backend-Feld `icon`, SSOT) → lädt das echte
// offizielle SVG. Fallback für Mock/Übergang: die 3 Inline-ICONS bzw. ein typografischer
// Platzhalter-Glyph nach Methoden-Name. `iconAlt` = Screenreader-Text (sonst dekorativ).
export function Glyph({ name, iconFile, iconAlt, size = 46, tile = true }) {
  const real = iconSvg(iconFile);
  const ic = ICONS[name];
  const m = METHODS[name] || {};
  const inner = tile
    ? { padding: size * 0.16, borderRadius: size * 0.26, background: 'var(--sand)' }
    : {};
  const a11y = iconAlt
    ? { role: 'img', 'aria-label': iconAlt }
    : { 'aria-hidden': 'true' };
  return (
    <span className="ls-icon" {...a11y}
      style={{ display: 'inline-grid', placeItems: 'center', width: size, height: size,
        flex: '0 0 auto', color: 'var(--terra)', ...inner }}>
      {real
        ? <span style={{ width: '100%', height: '100%', display: 'block' }} dangerouslySetInnerHTML={{ __html: real }} />
        : ic
          ? <svg viewBox={ic.vb} width="100%" height="100%" fill="currentColor"
              dangerouslySetInnerHTML={{ __html: ic.svg }} />
          : <span className="ls-serif" style={{ fontSize: size * 0.5, fontWeight: 500, lineHeight: 1 }}>{m.glyph || '◆'}</span>}
    </span>
  );
}

// Fortschritts-Kapitel-Anzeige als feine Segmente
export function ChapterBar({ index, total }) {
  return (
    <div style={{ display: 'flex', gap: 4, flex: 1 }}>
      {Array.from({ length: total }).map((_, i) => (
        <div key={i} style={{ flex: 1, height: 4, borderRadius: 4, transition: 'background .4s',
          background: i < index ? 'var(--amber)' : i === index ? 'var(--amber)' : 'var(--line)',
          opacity: i === index ? 1 : i < index ? 1 : 1 }} />
      ))}
    </div>
  );
}
