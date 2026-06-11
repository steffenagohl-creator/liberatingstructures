/* ===================================================================
   LS-MATCHMAKER APP — Orchestrator  (portiert aus design/lsc-app.jsx)
   Phasen: onboarding → sov → diagnose → morph → result
   PhoneStage (skaliert 390×844) · Onboarding · Souveränität · MorphView.
   Render passiert in main.jsx (hier nur die Komponenten + default export).
   =================================================================== */
import { useState, useEffect, useRef } from 'react'
import { THEME, StatusBar, Glyph, QUESTIONS } from './shared.jsx'
import { Constellation, DiagnoseCanvas, LSC } from './Diagnose.jsx'
import ArcadeLoader from './ArcadeLoader.jsx'
import { ResultString } from './Result.jsx'
import { Button } from './ui.jsx'
import { fetchMatch, fetchStructure } from './api/client.js'
import { answersToDiagnose, diagnoseToAnswers } from './api/mapping.js'
import { startVoiceSession } from './api/voice.js'

// ---- Stage: responsiver, raumfüllender Container (kein Fake-Handy mehr) ----
// Web nutzt die volle Höhe; der Inhalt liegt in einer angenehm breiten Spalte auf
// warmem Hintergrund (auf dem Handy randlos, am Desktop zentrierte App-Spalte).
// Der frühere 390×844-Geräterahmen + die Fake-Statusleiste sind entfernt (Steffen 2026-06-06).
function PhoneStage({ children }) {
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'grid', placeItems: 'center', overflow: 'hidden',
      background: 'radial-gradient(120% 90% at 50% 0%, #F3E7D4 0%, #EAE0CE 55%, #E2D6C0 100%)' }}>
      <div style={{ width: '100%', maxWidth: 720, height: '100dvh', position: 'relative',
        background: 'var(--bg)', overflow: 'hidden', boxShadow: '0 24px 70px rgba(70,45,20,.16)' }}>
        {children}
      </div>
    </div>
  );
}

// ---- Onboarding ---------------------------------------------------
function Onboarding({ onStart }) {
  return (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', padding: '8px 30px 30px' }}>
        {/* Hero-Konstellation (rein dekorativ → für Screenreader ausgeblendet) */}
        <div style={{ position: 'relative', height: 250, margin: '6px 0 8px' }} aria-hidden="true">
          <svg viewBox="0 0 300 250" width="100%" height="100%" style={{ position: 'absolute', inset: 0 }}>
            <path d="M150,125 Q90,70 70,52" fill="none" stroke="var(--line)" strokeWidth="1.4" strokeLinecap="round" />
            <path d="M150,125 Q220,80 244,66" fill="none" stroke="var(--sage)" strokeWidth="1.6" strokeLinecap="round" />
            <path d="M150,125 Q250,150 262,186" fill="none" stroke="var(--line)" strokeWidth="1.4" strokeLinecap="round" />
            <path d="M150,125 Q95,180 60,196" fill="none" stroke="var(--sage)" strokeWidth="1.6" strokeLinecap="round" />
            <path d="M150,125 Q140,205 150,222" fill="none" stroke="var(--line)" strokeWidth="1.4" strokeLinecap="round" />
            <circle cx="70" cy="52" r="6" fill="var(--surface)" stroke="var(--line)" strokeWidth="1.4" />
            <circle cx="244" cy="66" r="7" fill="var(--surface)" stroke="var(--sage)" strokeWidth="1.6" />
            <circle cx="262" cy="186" r="6" fill="var(--surface)" stroke="var(--line)" strokeWidth="1.4" />
            <circle cx="60" cy="196" r="7" fill="var(--surface)" stroke="var(--sage)" strokeWidth="1.6" />
            <circle cx="150" cy="222" r="6" fill="var(--surface)" stroke="var(--line)" strokeWidth="1.4" />
          </svg>
          <div style={{ position: 'absolute', left: '50%', top: '50%', transform: 'translate(-50%,-50%)',
            width: 92, height: 92, borderRadius: 50, background: 'var(--terra)', color: '#fff', display: 'grid',
            placeItems: 'center', textAlign: 'center', lineHeight: 1.15, boxShadow: '0 12px 30px rgba(184,88,39,.35)' }}>
            <span className="ls-serif" style={{ fontSize: 17, fontWeight: 500 }}>Euer<br />Thema</span>
          </div>
        </div>

        <div style={{ marginTop: 'auto' }}>
          <div style={{ fontSize: 12.5, fontWeight: 700, letterSpacing: '.12em', textTransform: 'uppercase', color: 'var(--terra)', marginBottom: 10 }}>LS-Matchmaker</div>
          <h1 className="ls-serif" style={{ margin: '0 0 12px', fontSize: 34, lineHeight: 1.1, fontWeight: 500, letterSpacing: '-.02em', color: 'var(--ink)', textWrap: 'balance' }}>
            Bringt euer Problem. Wir zeichnen das Lagebild.</h1>
          <p style={{ margin: '0 0 24px', fontSize: 15.5, lineHeight: 1.55, color: 'var(--muted)' }}>
            Ein paar ruhige Fragen — und Schritt für Schritt entsteht ein Bild eurer Situation. Am Ende
            schlägt euch der Berater eine passende Abfolge bewährter Methoden vor.</p>
          {/* Trägerwörter: beginnen, starten, los, anfangen, loslegen. */}
          <Button variant="primary" ariaLabel="Diagnose beginnen" onClick={onStart}
            style={{ width: '100%', borderRadius: 15, padding: '17px', fontSize: 16.5 }}>Beginnen</Button>
          <p style={{ textAlign: 'center', margin: '14px 0 0', fontSize: 12.5, color: 'var(--faint)' }}>Für Moderator:innen, Teams & Coaches</p>
        </div>
      </div>
    </div>
  );
}

// ---- Souveränität -------------------------------------------------
function Sovereignty({ value, onChange, onContinue, onBack }) {
  const cards = [
    { id: 'sov', ico: '🔒', t: 'Maximal souverän', where: 'Nur euer eigener Server (EU)', ex: 'Nichts verlässt eure Maschine. Tippen statt Echtzeit-Sprache.' },
    { id: 'eu', ico: '🇪🇺', t: 'EU', where: 'EU-Dienstleister (Mistral)', ex: 'Volle Qualität, DSGVO-konform. Empfohlen.' },
    { id: 'us', ico: '🇺🇸', t: 'Komfort', where: 'USA erlaubt (z. B. OpenAI)', ex: 'Bestes natürliches Sprachgespräch. Daten gehen in die USA.' },
  ];
  return (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', overflowY: 'auto', padding: '6px 26px 22px' }}>
        <button onClick={onBack} aria-label="Zurück zum Start" style={{ alignSelf: 'flex-start', border: 'none', background: 'none', cursor: 'pointer', fontSize: 22, color: 'var(--muted)', padding: 0, marginBottom: 6 }}>‹</button>
        <h2 className="ls-serif" style={{ margin: '4px 0 6px', fontSize: 27, lineHeight: 1.12, fontWeight: 500, letterSpacing: '-.015em' }}>Wohin dürfen eure Daten?</h2>
        <p style={{ margin: '0 0 8px', fontSize: 14.5, lineHeight: 1.5, color: 'var(--muted)' }}>
          Ihr entscheidet, wie weit eure Gesprächsinhalte reisen. Das gilt für die ganze Gruppe.</p>
        <p style={{ fontSize: 12.5, color: 'var(--faint)', margin: '0 0 16px', lineHeight: 1.4 }}>
          🧭 Üblicherweise stellt das die Moderation einmal bei der Einführung ein.</p>

        <div style={{ display: 'flex', flexDirection: 'column', gap: 11 }}>
          {cards.map((c) => {
            const on = value === c.id;
            return (
              <button key={c.id} onClick={() => onChange(c.id)} aria-pressed={on}
                aria-label={`Datenschutz-Stufe ${c.t} — ${c.where}. ${c.ex}`} style={{ textAlign: 'left', cursor: 'pointer',
                border: `1.5px solid ${on ? 'var(--terra)' : 'var(--line)'}`, background: on ? 'var(--sand)' : 'var(--surface)',
                borderRadius: 16, padding: '14px 16px', display: 'flex', gap: 13, alignItems: 'flex-start', transition: 'border-color .15s, background .15s' }}>
                <span style={{ fontSize: 22, flex: '0 0 auto', lineHeight: 1.2 }}>{c.ico}</span>
                <span style={{ flex: 1 }}>
                  <span style={{ display: 'block', fontSize: 16, fontWeight: 700, color: 'var(--ink)' }}>{c.t}</span>
                  <span style={{ display: 'block', fontSize: 13, fontWeight: 600, color: 'var(--terra)', margin: '1px 0 3px' }}>{c.where}</span>
                  <span style={{ display: 'block', fontSize: 13, color: 'var(--muted)', lineHeight: 1.4 }}>{c.ex}</span>
                </span>
                <span style={{ width: 20, height: 20, borderRadius: 11, flex: '0 0 auto', marginTop: 2, display: 'grid', placeItems: 'center',
                  border: `1.5px solid ${on ? 'var(--terra)' : 'var(--line)'}`, background: on ? 'var(--terra)' : 'transparent' }}>
                  {on && <span style={{ width: 7, height: 7, borderRadius: 5, background: '#fff' }} />}
                </span>
              </button>
            );
          })}
        </div>

        {/* Trägerwörter: weiter, fortfahren, nächster Schritt, bestätigen. */}
        <Button variant="primary" ariaLabel="Weiter zur Diagnose" onClick={onContinue}
          style={{ marginTop: 22, width: '100%', borderRadius: 15, padding: '16px', fontSize: 16 }}>Weiter →</Button>
      </div>
    </div>
  );
}

// ---- Morph: Konstellation → echter String (mit Lade-/Fehlerzustand) ----
// Die Morph-Animation IST der ehrliche Ladezustand: Solange das Backend rechnet
// (Mistral braucht Sekunden), läuft „Ich verdichte euer Lagebild …". Kommt der
// echte Match, kollabiert die Konstellation in die Spine mit den echten Methoden.
// Schlägt der Call fehl, erscheint ein Fehlerzustand mit „Nochmal versuchen".
function MorphView({ answers, match, details, matchError, onDone, onRetry, onBack }) {
  const tension = (() => { const s = (answers.situation || '').toLowerCase(); return answers._tension || /frust|still|schweig|konflikt|spannung|streit|nicht weiter/.test(s); })();
  // Adaptive Knoten (psychologische Sicherheit) auch zeigen, wenn sie erhoben wurden — im
  // Sprach-Modus ist das immer der Fall (sonst zeigte die Ergebnis-/Morph-Spinne nur 6 statt 7).
  const seq = QUESTIONS.filter((q) => !q.adaptive || tension || answers[q.id] != null);
  const [stage, setStage] = useState(0);
  // „thinking" = Backend verdichtet noch. Solange poppt das Arcade-Spiel als Overlay auf
  // (mit Wartemusik) und blendet sanft aus, sobald das Ergebnis da ist.
  const thinking = !match && !matchError;
  const [gameVisible, setGameVisible] = useState(() => !match && !matchError);

  // Sobald der echte Match da ist: kollabieren, kurz die Spine zeigen, dann weiter.
  useEffect(() => {
    if (matchError || !match) return;
    const t1 = setTimeout(() => setStage(1), 400);
    const t2 = setTimeout(() => onDone(), 2400);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, [match, matchError]);

  // --- Wartemusik: überbrückt sanft die ~60 s Verdichtung. Blendet beim Start ein und —
  // sobald das Ergebnis da ist — wieder aus (kein abrupter Schnitt). Datei liegt optional
  // unter public/wait-music.mp3; fehlt sie oder blockt Autoplay, passiert einfach nichts.
  const musicRef = useRef(null);
  const musicStartRef = useRef(null);  // Timer für den verzögerten Musikstart (s. u.)
  useEffect(() => {
    const el = musicRef.current;
    if (!el) return;
    el.volume = 0;
    let t;
    // Musik bewusst erst nach ~10 s starten: So kann die KI ihren letzten Satz ("…einen kleinen
    // Moment, ich stelle euch einen Vorschlag zusammen") noch ungestört zu Ende sprechen, bevor die
    // Wartemusik einsetzt (Steffen-Wunsch). Kommt das Ergebnis vorher, wird der Start abgebrochen.
    musicStartRef.current = setTimeout(() => {
      el.play().then(() => {
        const fadeIn = () => { el.volume = Math.min(0.45, el.volume + 0.02); if (el.volume < 0.45) t = setTimeout(fadeIn, 90); };
        fadeIn();
      }).catch(() => { /* Autoplay/keine Datei → still ignorieren */ });
    }, 10000);
    return () => { clearTimeout(musicStartRef.current); clearTimeout(t); el.pause(); };
  }, []);
  useEffect(() => {
    if (!match) return;
    const el = musicRef.current;
    if (!el) return;
    clearTimeout(musicStartRef.current);  // Ergebnis < 10 s da → verspäteten Musikstart verhindern
    let t;
    const fadeOut = () => {
      el.volume = Math.max(0, el.volume - 0.03);
      if (el.volume > 0.001) t = setTimeout(fadeOut, 70); else el.pause();
    };
    fadeOut();
    return () => clearTimeout(t);
  }, [match]);

  const { CW, CH, cx } = LSC;
  const steps = match?.string || [];
  const n = steps.length || 3;
  const spineY = steps.map((_, i) => CH * (0.2 + 0.6 * (n > 1 ? i / (n - 1) : 0.5)));
  const spineX = steps.map((_, i) => cx + (i % 2 ? 14 : -6));
  const spinePath = spineX.map((x, i) => i === 0
    ? `M${x},${spineY[i]}`
    : `Q${spineX[i - 1] + (i % 2 ? 26 : -26)},${(spineY[i - 1] + spineY[i]) / 2} ${x},${spineY[i]}`).join(' ');

  // --- Fehlerzustand (ehrliches Produkt: das LLM kann fehlschlagen) ---
  if (matchError) {
    return (
      <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
        <StatusBar />
        <div role="alert" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 32px', textAlign: 'center' }}>
          <div style={{ fontSize: 34, marginBottom: 12 }} aria-hidden="true">🛠️</div>
          <h2 className="ls-serif" style={{ margin: '0 0 8px', fontSize: 22, fontWeight: 500, color: 'var(--ink)' }}>Der Vorschlag konnte nicht erstellt werden</h2>
          <p style={{ margin: '0 0 22px', fontSize: 14, lineHeight: 1.5, color: 'var(--muted)' }}>
            {matchError.status === 0 ? 'Keine Verbindung zum Server.' : 'Beim Erstellen ist etwas schiefgelaufen.'} Bitte versuche es noch einmal.</p>
          <Button variant="primary" ariaLabel="Vorschlag nochmal versuchen" onClick={onRetry} style={{ width: '100%', maxWidth: 260, borderRadius: 15, padding: '15px' }}>Nochmal versuchen</Button>
          <Button variant="ghost" ariaLabel="Zurück zur Diagnose" onClick={onBack} style={{ width: '100%', maxWidth: 260, marginTop: 9, borderRadius: 15, padding: '15px' }}>Zurück</Button>
        </div>
      </div>
    );
  }

  return (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)', position: 'relative', overflow: 'hidden' }}>
      <StatusBar />
      <audio ref={musicRef} src="/wait-music.mp3" loop preload="auto" aria-hidden="true" />
      <div style={{ position: 'relative', flex: '0 0 auto' }}>
        <Constellation seq={seq} answers={answers} filled={seq.length} collapse={stage >= 1} />
        {/* String-Spine erscheint mit den ECHTEN Methoden aus dem Match */}
        <div style={{ position: 'absolute', inset: 0, opacity: stage >= 1 ? 1 : 0, transition: 'opacity .6s .2s', pointerEvents: 'none' }}>
          <svg width={CW} height={CH} style={{ position: 'absolute', inset: 0 }} aria-hidden="true">
            <path d={spinePath} fill="none" stroke="var(--amber)" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {steps.map((step, i) => {
            const struct = details?.[step.slug];
            return (
              <div key={step.slug + i} style={{ position: 'absolute', left: spineX[i], top: spineY[i], transform: `translate(-50%,-50%) scale(${stage >= 1 ? 1 : .6})`,
                transition: `transform .5s ${0.25 + i * 0.13}s cubic-bezier(.5,1.5,.4,1)`, display: 'flex', alignItems: 'center', gap: 10 }}>
                <span style={{ background: 'var(--surface)', border: '1.5px solid var(--amber)', borderRadius: 14, padding: 5, boxShadow: '0 4px 14px rgba(184,88,39,.18)' }}>
                  <Glyph iconFile={struct?.icon} size={38} tile={false} />
                </span>
                <span style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 9, padding: '4px 9px', whiteSpace: 'nowrap' }}>
                  <span style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--terra)', display: 'block' }}>{step.role}</span>
                  <span className="ls-serif" style={{ fontSize: 14, fontWeight: 500, color: 'var(--ink)' }}>{struct?.name || step.slug}</span>
                </span>
              </div>
            );
          })}
        </div>
      </div>

      <div aria-live="polite" style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 30px', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: 5, marginBottom: 14 }} aria-hidden="true">
          {[0, 1, 2].map((i) => <span key={i} style={{ width: 7, height: 7, borderRadius: 5, background: 'var(--terra)', animation: `lsPulse 1s ${i * 0.18}s infinite` }} />)}
        </div>
        <h2 className="ls-serif" style={{ margin: 0, fontSize: 22, fontWeight: 500, color: 'var(--ink)', lineHeight: 1.2 }}>
          {stage >= 1 ? 'Euer Weg: öffnen → vertiefen → schließen' : 'Ich verdichte euer Lagebild …'}</h2>
      </div>

      {/* Arcade-Spiel als Wartespiel-Overlay: poppt auf während der Verdichtung, blendet
          sanft aus, sobald das Ergebnis da ist (onExit räumt das Overlay dann ganz weg).
          Hintergrund ist var(--bg) wie der Screen darunter → kein harter Schnitt. */}
      {gameVisible && (
        <div style={{ position: 'absolute', inset: 0, zIndex: 10, background: 'var(--bg)',
          display: 'grid', placeItems: 'center', padding: 16 }}>
          <ArcadeLoader active={thinking} onExit={() => setGameVisible(false)}
            width={320} height={400} message="Ich stelle euren Vorschlag zusammen …" />
        </div>
      )}
    </div>
  );
}

// ---- App ----------------------------------------------------------
// Dev-Deep-Link: ?phase=onboarding|sov|diagnose|morph|result springt direkt in eine
// Phase (nur im Dev-Modus; in Produktion ignoriert). Praktisch zum Bauen/Vergleichen.
function initialPhase() {
  if (import.meta.env.DEV) {
    const p = new URLSearchParams(window.location.search).get('phase');
    if (['onboarding', 'sov', 'diagnose', 'morph', 'result'].includes(p)) return p;
  }
  return 'onboarding';
}

// Demo-Antworten für den Dev-Deep-Link (?phase=morph|result) — lädt einen echten Match,
// damit der Ergebnis-Screen ohne manuellen Durchlauf geprüft werden kann (nur im Dev-Modus).
const DEMO_ANSWERS = {
  situation: 'Frust nach dem Sprint, in der Retro sagt keiner etwas', ziel: 'Alle reden ehrlich',
  zweck: 'Offenlegen', sicherheit: 'Angespannt / heikel', groesse: '5–9', zeit: '60 Min',
  setting: 'Präsenz', _tension: true,
};

export default function App() {
  const [phase, setPhase] = useState(initialPhase);
  const [sov, setSov] = useState('eu');
  const [answers, setAnswers] = useState({});
  const [match, setMatch] = useState(null);
  const [details, setDetails] = useState({});
  const [matchError, setMatchError] = useState(null);
  const [running, setRunning] = useState(false);

  // --- Sprach-Sitzung: lebt auf App-Ebene, überlebt Phasen-/Schrittwechsel ---------------
  // (Steffen 2026-06-06: ein Seitenwechsel darf den Sprachkanal NICHT mehr töten.)
  const voiceRef = useRef(null);            // die laufende LiveKit-Sitzung (oder null)
  const voiceAnswersRef = useRef({});       // stets aktuelle Diagnose (gegen stale Closures)
  const resultHandledRef = useRef(false);   // schützt vor doppeltem Ergebnis-Übergang
  const [voiceStatus, setVoiceStatus] = useState('idle');
  const [voiceAnswers, setVoiceAnswers] = useState({});
  const [voiceMuted, setVoiceMuted] = useState(false);

  // Diagnose abgeschlossen → echten Match laden (läuft, während die Morph-Animation spielt).
  // Danach für jeden Slug die vollen Struktur-Details (Name, Badges, Anleitung, Icon).
  async function runMatch(a) {
    setAnswers(a); setMatch(null); setDetails({}); setMatchError(null); setRunning(true); setPhase('morph');
    try {
      const m = await fetchMatch(answersToDiagnose(a));
      const slugs = [...new Set((m.string || []).map((s) => s.slug))];
      const structs = await Promise.all(slugs.map((s) => fetchStructure(s, 'de').catch(() => null)));
      const byslug = {};
      structs.forEach((s) => { if (s) byslug[s.slug] = s; });
      setDetails(byslug); setMatch(m);
    } catch (e) {
      setMatchError(e);
    } finally {
      setRunning(false);
    }
  }

  // Startet die Sprach-Sitzung (Mikro). Diagnose-Updates füllen live die Spinne; meldet der
  // Agent das fertige Match, gleiten wir zum Ergebnis — die Sitzung bleibt aktiv, damit die
  // Coachin den Vorschlag noch vorlesen kann.
  async function startVoice() {
    if (voiceRef.current) return;
    resultHandledRef.current = false;
    voiceAnswersRef.current = {};
    setVoiceAnswers({});
    setVoiceMuted(false);
    try {
      const h = await startVoiceSession({
        sovereignty: sov,
        onStatus: setVoiceStatus,
        // Der Agent meldet „ich rechne jetzt den Vorschlag" → SOFORT in die Morph-Ansicht mit
        // laufendem Wartespiel wechseln (überbrückt die 1–2 Min Verdichtung). Ohne dieses Signal
        // erschien das Spiel nur kurz beim Eintreffen des Ergebnisses.
        onThinking: () => {
          if (resultHandledRef.current) return;
          setAnswers(voiceAnswersRef.current);
          setMatch(null); setDetails({}); setMatchError(null); setRunning(true); setPhase('morph');
        },
        onDiagnose: (d) => {
          const a = diagnoseToAnswers(d?.diagnose || {});
          if (!a.situation && d?.situation) a.situation = d.situation;  // Mittelpunkt beschriften
          voiceAnswersRef.current = a;
          setVoiceAnswers(a);
        },
        onResult: (r) => handleVoiceResult(r),
        // Der Agent hat die Sitzung selbst beendet (Kostenschutz: Inaktivität/Zeitlimit/nach dem
        // Ergebnis). Den Handle freigeben, damit ein Tipp aufs Mikro wieder ein NEUES Gespräch
        // starten kann — sonst blockiert das alte voiceRef den Neustart (startVoice bricht früh ab).
        // Den Status übernimmt das 'closed'-Event (zeigt „Gespräch beendet …").
        onEnded: () => { voiceRef.current = null; },
      });
      voiceRef.current = h;
    } catch {
      setVoiceStatus('error');
    }
  }

  function stopVoice() {
    if (voiceRef.current) { voiceRef.current.stop(); voiceRef.current = null; }
    setVoiceStatus('idle'); setVoiceMuted(false);
  }

  // Mikro stumm/laut — beendet die Sitzung NICHT (Gespräch läuft weiter, kein Neustart).
  function toggleVoiceMute() {
    if (!voiceRef.current) return;
    const next = !voiceMuted;
    voiceRef.current.setMuted(next);
    setVoiceMuted(next);
  }

  // Der Agent liefert das fertige Match über den Data-Channel → zum Ergebnis gleiten und nur
  // die Struktur-Details nachladen (das Matching selbst hat der Agent bereits erledigt).
  async function handleVoiceResult(m) {
    // DIAGNOSE (2026-06-08): exakt zeigen, WAS der Agent über den Data-Channel liefert. So sehen
    // wir bei der „leere-Seite"-Suche in der Browser-Konsole sofort, ob/welches Ergebnis ankommt.
    // eslint-disable-next-line no-console
    console.log('[LS] Sprach-Ergebnis empfangen:', m);
    if (resultHandledRef.current) return;  // Doppel-Event: Ergebnis ist schon verarbeitet.
    const steps = Array.isArray(m?.string) ? m.string : [];
    // EHRLICHER Fehlerzustand statt stiller weißer Seite: kam ein Ergebnis OHNE verwertbaren String,
    // zeigen wir die Fehleransicht (mit „Nochmal"). Bewusst NICHT als „verarbeitet" markieren, damit
    // ein evtl. nachfolgendes, vollständiges Ergebnis noch greifen darf.
    if (!steps.length) {
      // eslint-disable-next-line no-console
      console.warn('[LS] Ergebnis ohne verwertbaren String — zeige Fehleransicht:', m);
      setMatch(null); setDetails({});
      setMatchError({ status: 200, message: 'Das Ergebnis kam an, enthielt aber keinen Vorschlag.' });
      setRunning(false); setPhase('morph');
      return;
    }
    resultHandledRef.current = true;
    setAnswers(voiceAnswersRef.current);
    setMatch(null); setDetails({}); setMatchError(null); setRunning(true); setPhase('morph');
    try {
      const slugs = [...new Set(steps.map((s) => s.slug))];
      const structs = await Promise.all(slugs.map((s) => fetchStructure(s, 'de').catch(() => null)));
      const byslug = {};
      structs.forEach((s) => { if (s) byslug[s.slug] = s; });
      setDetails(byslug); setMatch(m);
    } catch (e) {
      // eslint-disable-next-line no-console
      console.error('[LS] Aufbau des Ergebnis-Bildschirms fehlgeschlagen:', e);
      setMatchError(e);
    } finally {
      setRunning(false);
    }
  }

  // Dev-Komfort: Deep-Link direkt auf morph/result lädt automatisch eine Demo.
  useEffect(() => {
    if (import.meta.env.DEV && (phase === 'morph' || phase === 'result') && !match && !matchError && !running) {
      runMatch(DEMO_ANSWERS);
      setPhase('morph');
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  let screen;
  if (phase === 'onboarding') screen = <Onboarding onStart={() => setPhase('sov')} />;
  else if (phase === 'sov') screen = <Sovereignty value={sov} onChange={setSov} onBack={() => setPhase('onboarding')} onContinue={() => setPhase('diagnose')} />;
  else if (phase === 'diagnose') screen = <DiagnoseCanvas sovereignty={sov}
    onBack={() => { stopVoice(); setPhase('sov'); }} onComplete={runMatch}
    voiceStatus={voiceStatus} voiceAnswers={voiceAnswers} voiceMuted={voiceMuted}
    onVoiceStart={startVoice} onVoiceStop={stopVoice} onVoiceToggleMute={toggleVoiceMute} />;
  else if (phase === 'morph') screen = <MorphView answers={answers} match={match} details={details} matchError={matchError}
    onDone={() => setPhase('result')} onRetry={() => runMatch(answers)} onBack={() => setPhase('diagnose')} />;
  else screen = (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />
      <ResultString match={match} details={details}
        onRestart={() => { stopVoice(); setAnswers({}); setMatch(null); setDetails({}); setMatchError(null); setPhase('onboarding'); }} />
    </div>
  );

  return <PhoneStage>{screen}</PhoneStage>;
}
