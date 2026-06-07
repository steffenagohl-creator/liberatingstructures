/* ===================================================================
   MAPPING — Prototyp-Oberfläche → Backend-Diagnose  (Kern der „Hochzeit")
   ===================================================================
   WICHTIG: Der genehmigte Prototyp (Variante C) ist reine OBERFLÄCHE — er
   wurde gebaut, OHNE das Backend zu kennen, und nutzt vereinfachte, eigene
   Werte. Dieses Modul übersetzt die Prototyp-Antworten in die Sprache des
   echten Diagnoseschemas (data/diagnosis_schema.json). Das Backend ist die
   Wahrheit; die Oberfläche dient ihm. Unscharfe Zuordnungen sind hier offen
   dokumentiert (der Prototyp ist gröber als das Backend).

   Prototyp-Frage  →  Backend-Dimension
   - situation     →  situation     (Freitext, 1:1)
   - ziel (Label)  →  ziel_text     (Freitext; das Label dient als Zieltext)
   - zweck         →  zweck[]       (purpose_tags — Brücke, s. u.)
   - sicherheit    →  psychologische_sicherheit
   - groesse       →  gruppengroesse (Bereich → repräsentative Zahl)
   - zeit          →  zeitbudget     (Label → Minuten)
   - setting       →  setting
   =================================================================== */

// „Schwerpunkt" → Backend purpose_tags. Seit 2026-06-07 zeigen die Chips die echten 6
// offiziellen Kategorien (gleiche Wörter wie das Ergebnis), daher ist die Brücke jetzt
// eine direkte 1:1-Zuordnung Label→Slug (7. Tag 'solo' ist app-intern, keine eigene Chip-Wahl).
const ZWECK = {
  'Offenlegen': 'offenlegen',
  'Teilen': 'teilen',
  'Analysieren': 'analysieren',
  'Strategie': 'strategie',
  'Helfen': 'helfen',
  'Planen': 'planen',
};

// Prototyp-Sicherheit → psychologische_sicherheit. 'Weiß ich nicht' → weglassen
// (Backend behandelt fehlend als unbekannt, nicht als „niedrig").
const SICHERHEIT = {
  'Sehr offen': 'hoch',
  'Eher vorsichtig': 'mittel',
  'Angespannt / heikel': 'niedrig',
};

// Gruppengrößen-Bereich → repräsentative Zahl (Mitte des Bereichs).
const GROESSE = { '2–4': 3, '5–9': 7, '10–20': 15, '20+': 25 };

// Zeit-Label → Minuten. 'Halber Tag' ≈ 240 Min.
const ZEIT = { '15 Min': 15, '30 Min': 30, '60 Min': 60, 'Halber Tag': 240 };

// Setting-Label → Backend-Wert.
const SETTING = { 'Präsenz': 'praesenz', 'Online': 'remote', 'Hybrid': 'hybrid' };

/**
 * answersToDiagnose — baut aus den im Prototyp-Fluss gesammelten Antworten die
 * Backend-Diagnose. Nur gesetzte Felder werden übernommen (das Backend ist
 * tolerant gegenüber fehlenden Dimensionen — Dynamic Incompleteness).
 */
export function answersToDiagnose(a = {}) {
  const d = {};
  if (a.situation) d.situation = a.situation;
  if (a.ziel) d.ziel_text = a.ziel;
  if (ZWECK[a.zweck]) d.zweck = [ZWECK[a.zweck]];
  if (SICHERHEIT[a.sicherheit]) d.psychologische_sicherheit = SICHERHEIT[a.sicherheit];
  if (GROESSE[a.groesse]) d.gruppengroesse = GROESSE[a.groesse];
  if (ZEIT[a.zeit]) d.zeitbudget = ZEIT[a.zeit];
  if (SETTING[a.setting]) d.setting = SETTING[a.setting];
  return d;
}

// ---- Rückrichtung: Backend-Diagnose → Prototyp-Antworten -----------
// Wird im SPRACH-Modus gebraucht: Das Backend (/api/interview/) liefert die laufend
// erkannten Dimensionen; daraus füllt sich live die „Spinne" (Constellation), die in den
// Prototyp-Antworten denkt. Umkehrung der Maps oben + Zahl→Label für Größe/Zeit.
const ZWECK_REV = Object.fromEntries(Object.entries(ZWECK).map(([k, v]) => [v, k]));
const SICHERHEIT_REV = Object.fromEntries(Object.entries(SICHERHEIT).map(([k, v]) => [v, k]));
const SETTING_REV = Object.fromEntries(Object.entries(SETTING).map(([k, v]) => [v, k]));

function groesseLabel(n) {
  if (n == null) return undefined;
  if (n <= 4) return '2–4';
  if (n <= 9) return '5–9';
  if (n <= 20) return '10–20';
  return '20+';
}
function zeitLabel(min) {
  if (min == null) return undefined;
  // Präzise anzeigen statt in feste Stufen bucketen (sonst sah jede Zeit > 60 Min wie „Halber
  // Tag" aus). Bis 2 h die genaue Minutenzahl, darüber in Stunden; 240/480 Min als halber/ganzer Tag.
  if (min === 240) return 'Halber Tag';
  if (min === 480) return 'Ganzer Tag';
  if (min >= 120) return `${String(Math.round((min / 60) * 10) / 10).replace('.', ',')} Std`;
  return `${min} Min`;
}

/**
 * diagnoseToAnswers — übersetzt die Backend-Diagnose aus dem Sprach-Interview zurück in
 * Prototyp-Antworten, damit die Spinne sich live aus dem Gespräch füllt. Nur tatsächlich
 * erkannte Dimensionen werden gesetzt (fehlende bleiben offen = ungefüllter Knoten).
 */
export function diagnoseToAnswers(d = {}) {
  const a = {};
  if (d.ziel_text) a.ziel = d.ziel_text;
  // Das Backend kann MEHRERE Zweck-Tags halten (z. B. „offenlegen" UND „planen"). Alle
  // anzeigen, damit kein gewünschter Schwerpunkt unter den Tisch fällt (Wunsch 2026-06-06).
  if (Array.isArray(d.zweck) && d.zweck.length) {
    // Auch dem Frontend UNBEKANNTE Backend-Werte (z. B. "teilen", "entscheiden") anzeigen, statt
    // sie zu verschlucken → der Schwerpunkt-Strang bleibt nie fälschlich leer, obwohl ein Wert da ist.
    const cap = (z) => String(z).charAt(0).toUpperCase() + String(z).slice(1);
    const labels = d.zweck.map((z) => ZWECK_REV[z] || cap(z)).filter(Boolean);
    if (labels.length) a.zweck = labels.join(' + ');
  }
  if (d.psychologische_sicherheit && SICHERHEIT_REV[d.psychologische_sicherheit]) a.sicherheit = SICHERHEIT_REV[d.psychologische_sicherheit];
  const g = groesseLabel(d.gruppengroesse); if (g) a.groesse = g;
  const z = zeitLabel(d.zeitbudget); if (z) a.zeit = z;
  if (d.setting && SETTING_REV[d.setting]) a.setting = SETTING_REV[d.setting];
  // Das Backend gibt keinen Situations-Freitext zurück; der erkannte scrum_kontext dient
  // als kurze, sprechende Beschriftung des Situations-Knotens (z. B. „Retrospektive").
  if (d.scrum_kontext) a.situation = String(d.scrum_kontext).charAt(0).toUpperCase() + String(d.scrum_kontext).slice(1);
  return a;
}
