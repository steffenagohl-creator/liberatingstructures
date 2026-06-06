/* ===================================================================
   LS-MATCHMAKER — Design-System (generisch & wiederverwendbar)
   ===================================================================
   Ziel (Steffen 2026-06-06): EIN übertragbares Design-System für alle
   künftigen Seiten/Elemente (App, Landing, Plattform) — statt duplizierter
   Inline-Styles. Zwei Säulen:

   1) TOKENS  — die einzige Quelle für Farbe/Schrift/Radius/Abstand. Farben
      kommen als CSS-Variablen aus injectTheme() (--terra, --sand, …); hier
      ergänzt um benannte Radius-/Abstands-Skalen. Optik bleibt 1:1 zum
      genehmigten Prototyp (Variante C) — das System fasst nur zusammen.

   2) PRIMITIVE — Button, Chip, Badge, Card, Eyebrow. Jedes ist von Haus aus
      BARRIEREFREI & maschinenlesbar (Leitprinzip): semantisches HTML +
      aria-label (Screenreader), und jeder Baustein ist im Code mit
      Titel/Beschreibung/Trägerwörtern dokumentiert (ein separater Crawler
      sammelt das später ein — wir liefern nur die saubere Beschriftung).

   Trägerwörter = Trigger-/Synonym-Wörter, an denen eine Sprachsteuerung das
   Element erkennen kann (z. B. „Beginnen" → starten/los/anfangen). Stehen als
   Docstring an der jeweiligen Aufrufstelle, nicht als Laufzeit-System.
   =================================================================== */
import { THEME } from './shared.jsx'

// ---- 1. TOKENS (zusätzlich zu den CSS-Variablen aus injectTheme) ----
export const tokens = {
  radius: { sm: 7, md: 12, lg: 15, xl: 16, pill: 999 },
  space:  { xs: 4, sm: 8, md: 12, lg: 16, xl: 22, xxl: 30 },
  font:   { serif: THEME.serif, sans: THEME.sans },
};

// ---- 2. PRIMITIVE ---------------------------------------------------

/**
 * Button — primäre/sekundäre Aktionsschaltfläche.
 * Titel:        Aktions-Button.
 * Beschreibung: Löst eine Aktion aus (z. B. weiter, speichern, neu starten).
 * Barrierefrei: rendert ein echtes <button>; `ariaLabel` beschriftet es für
 *               Screenreader (Pflicht, wenn der sichtbare Text nicht eindeutig ist).
 * Varianten:    'primary' (gefüllt, Terrakotta) · 'ghost' (Umriss, Bernstein).
 * Maße:         Default = Karten-Button; per `style` exakt überschreibbar
 *               (der Prototyp nutzt je Screen leicht andere Maße → Optik 1:1).
 * @param {'primary'|'ghost'} variant
 * @param {string} ariaLabel  sprechende Beschriftung für Screenreader/Sprachsteuerung
 */
export function Button({ variant = 'primary', ariaLabel, style, children, ...rest }) {
  const base = {
    border: 'none', borderRadius: tokens.radius.md, padding: '13px 18px',
    fontFamily: tokens.font.sans, fontSize: 15, fontWeight: 600, cursor: 'pointer',
  };
  const variants = {
    primary: { background: 'var(--terra)', color: '#fff' },
    ghost: { background: 'var(--surface)', color: 'var(--terra)', border: '1px solid var(--amber)' },
  };
  return (
    <button aria-label={ariaLabel} style={{ ...base, ...variants[variant], ...style }} {...rest}>
      {children}
    </button>
  );
}

/**
 * Chip — auswählbare Antwort-/Optionsschaltfläche (Diagnose-Eingabe, Tippen-Modus).
 * Titel:        Auswahl-Chip.
 * Beschreibung: Wählt eine vorgegebene Antwort in der geführten Diagnose.
 * Barrierefrei: echtes <button>; `ariaLabel` default = Textinhalt.
 */
export function Chip({ ariaLabel, style, children, ...rest }) {
  const base = {
    border: '1px solid var(--line)', background: 'var(--surface)', color: 'var(--ink)',
    borderRadius: 13, padding: '11px 15px', cursor: 'pointer', fontFamily: tokens.font.sans,
    fontSize: 14.5, fontWeight: 500, lineHeight: 1.3, transition: 'border-color .15s, background .15s',
  };
  return (
    <button aria-label={ariaLabel} style={{ ...base, ...style }} {...rest}>{children}</button>
  );
}

/**
 * Badge — kleines, nicht-interaktives Eigenschafts-Etikett (Zweck, Dauer, Gruppengröße …).
 * Titel:        Eigenschafts-Badge.
 * Beschreibung: Zeigt ein Merkmal einer Struktur an (rein informativ, kein Button).
 * `primary`:    hebt das wichtigste Merkmal hervor (Bernstein statt grau).
 */
export function Badge({ primary = false, children, style }) {
  return (
    <span style={{
      fontFamily: tokens.font.sans, fontSize: 12, fontWeight: 500,
      borderRadius: tokens.radius.sm, padding: '4px 9px', whiteSpace: 'nowrap',
      background: primary ? 'var(--sand)' : 'var(--bg)',
      border: `1px solid ${primary ? 'var(--amber)' : 'var(--line)'}`,
      color: primary ? 'var(--terra)' : 'var(--muted)', ...style,
    }}>{children}</span>
  );
}

/**
 * Card — Inhaltskarte auf heller Fläche (Methoden-Karte, Auswahlkarte …).
 * Titel:        Inhaltskarte.
 * Beschreibung: Gruppiert zusammengehörige Inhalte in einer abgesetzten Fläche.
 */
export function Card({ style, children, ...rest }) {
  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--line)',
      borderRadius: tokens.radius.xl, padding: 16, ...style,
    }} {...rest}>{children}</div>
  );
}

/**
 * Eyebrow — kleine, großgeschriebene Bereichs-Überschrift über einer Hauptüberschrift.
 * Titel:        Bereichs-Label.
 * Beschreibung: Ordnet den folgenden Inhalt thematisch ein (z. B. „DEIN VORSCHLAG").
 * Barrierefrei: rein dekorativ/strukturierend; keine Interaktion.
 */
export function Eyebrow({ tone = 'var(--faint)', children, style }) {
  return (
    <div style={{
      fontSize: 12, fontWeight: 600, letterSpacing: '.08em', textTransform: 'uppercase',
      color: tone, ...style,
    }}>{children}</div>
  );
}
