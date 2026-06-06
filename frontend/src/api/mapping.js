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

// Prototyp-„Schwerpunkt" (5 Werte) → Backend purpose_tags (7 Werte).
// Brücke: 'Entscheiden' hat kein eigenes Tag → 'strategie' (Strategie/Richtung
// entwickeln) ist am nächsten; 'Verbinden' → 'helfen' (gegenseitig helfen /
// Beziehung stärken). Bewusst grob — der Prototyp kennt diese Feinheit nicht.
const ZWECK = {
  'Offenlegen': 'offenlegen',
  'Analysieren': 'analysieren',
  'Entscheiden': 'strategie',
  'Planen': 'planen',
  'Verbinden': 'helfen',
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
