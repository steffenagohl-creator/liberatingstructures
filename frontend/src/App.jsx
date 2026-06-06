/* ===================================================================
   LS-MATCHMAKER APP — Orchestrator  (portiert aus design/lsc-app.jsx)
   Phasen: onboarding → sov → diagnose → morph → result
   PhoneStage (skaliert 390×844) · Onboarding · Souveränität · MorphView.
   Render passiert in main.jsx (hier nur die Komponenten + default export).
   =================================================================== */
import { useState, useEffect, useMemo } from 'react'
import { THEME, StatusBar, Glyph, QUESTIONS, METHODS, buildRecommendation } from './shared.jsx'
import { Constellation, DiagnoseCanvas, LSC } from './Diagnose.jsx'
import { ResultString } from './Result.jsx'
import { Button } from './ui.jsx'

// ---- PhoneStage: skaliertes Gerät auf warmem Hintergrund ----------
function PhoneStage({ children }) {
  const [scale, setScale] = useState(1);
  useEffect(() => {
    const f = () => setScale(Math.min(window.innerWidth / 408, window.innerHeight / 868, 1));
    f(); window.addEventListener('resize', f); return () => window.removeEventListener('resize', f);
  }, []);
  return (
    <div style={{ position: 'fixed', inset: 0, display: 'grid', placeItems: 'center', overflow: 'hidden',
      background: 'radial-gradient(120% 90% at 50% 0%, #F3E7D4 0%, #EAE0CE 55%, #E2D6C0 100%)' }}>
      <div style={{ width: 390, height: 844, transform: `scale(${scale})`, position: 'relative',
        borderRadius: 48, background: '#000', padding: 5, boxShadow: '0 40px 90px rgba(70,45,20,.32), 0 6px 20px rgba(70,45,20,.2)' }}>
        <div style={{ width: '100%', height: '100%', borderRadius: 43, overflow: 'hidden', position: 'relative', background: 'var(--bg)' }}>
          {children}
          <div style={{ position: 'absolute', bottom: 7, left: '50%', transform: 'translateX(-50%)', width: 130, height: 5,
            borderRadius: 3, background: 'rgba(38,34,28,.28)', zIndex: 50, pointerEvents: 'none' }} />
        </div>
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

// ---- Morph: Konstellation → 3er-String ----------------------------
function MorphView({ answers, onDone }) {
  const tension = (() => { const s = (answers.situation || '').toLowerCase(); return answers._tension || /frust|still|schweig|konflikt|spannung|streit|nicht weiter/.test(s); })();
  const seq = QUESTIONS.filter((q) => !q.adaptive || tension);
  const rec = useMemo(() => buildRecommendation(answers), [answers]);
  const [stage, setStage] = useState(0);

  useEffect(() => {
    const t1 = setTimeout(() => setStage(1), 850);
    const t2 = setTimeout(() => onDone(), 3000);
    return () => { clearTimeout(t1); clearTimeout(t2); };
  }, []);

  const { CW, CH, cx } = LSC;
  const spineY = [CH * 0.2, CH * 0.5, CH * 0.8];
  const spineX = [cx - 6, cx + 14, cx - 4];

  return (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />
      <div style={{ position: 'relative', flex: '0 0 auto' }}>
        <Constellation seq={seq} answers={answers} filled={seq.length} collapse={stage >= 1} />
        {/* String-Spine erscheint */}
        <div style={{ position: 'absolute', inset: 0, opacity: stage >= 1 ? 1 : 0, transition: 'opacity .6s .2s', pointerEvents: 'none' }}>
          <svg width={CW} height={CH} style={{ position: 'absolute', inset: 0 }}>
            <path d={`M${spineX[0]},${spineY[0]} Q${spineX[0] + 26},${(spineY[0] + spineY[1]) / 2} ${spineX[1]},${spineY[1]} Q${spineX[1] - 26},${(spineY[1] + spineY[2]) / 2} ${spineX[2]},${spineY[2]}`}
              fill="none" stroke="var(--amber)" strokeWidth="2" strokeLinecap="round" />
          </svg>
          {rec.string.map((name, i) => (
            <div key={name} style={{ position: 'absolute', left: spineX[i], top: spineY[i], transform: `translate(-50%,-50%) scale(${stage >= 1 ? 1 : .6})`,
              transition: `transform .5s ${0.25 + i * 0.13}s cubic-bezier(.5,1.5,.4,1)`, display: 'flex', alignItems: 'center', gap: 10 }}>
              <span style={{ background: 'var(--surface)', border: '1.5px solid var(--amber)', borderRadius: 14, padding: 5, boxShadow: '0 4px 14px rgba(184,88,39,.18)' }}>
                <Glyph name={name} size={38} tile={false} />
              </span>
              <span style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 9, padding: '4px 9px', whiteSpace: 'nowrap' }}>
                <span style={{ fontSize: 9.5, fontWeight: 700, textTransform: 'uppercase', letterSpacing: '.05em', color: 'var(--terra)', display: 'block' }}>{METHODS[name].role}</span>
                <span className="ls-serif" style={{ fontSize: 14, fontWeight: 500, color: 'var(--ink)' }}>{name}</span>
              </span>
            </div>
          ))}
        </div>
      </div>

      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', padding: '0 30px', textAlign: 'center' }}>
        <div style={{ display: 'flex', gap: 5, marginBottom: 14 }}>
          {[0, 1, 2].map((i) => <span key={i} style={{ width: 7, height: 7, borderRadius: 5, background: 'var(--terra)', animation: `lsPulse 1s ${i * 0.18}s infinite` }} />)}
        </div>
        <h2 className="ls-serif" style={{ margin: 0, fontSize: 22, fontWeight: 500, color: 'var(--ink)', lineHeight: 1.2 }}>
          {stage >= 1 ? 'Euer Weg: öffnen → vertiefen → schließen' : 'Ich verdichte euer Lagebild …'}</h2>
      </div>
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

export default function App() {
  const [phase, setPhase] = useState(initialPhase);
  const [sov, setSov] = useState('eu');
  const [answers, setAnswers] = useState({});

  let screen;
  if (phase === 'onboarding') screen = <Onboarding onStart={() => setPhase('sov')} />;
  else if (phase === 'sov') screen = <Sovereignty value={sov} onChange={setSov} onBack={() => setPhase('onboarding')} onContinue={() => setPhase('diagnose')} />;
  else if (phase === 'diagnose') screen = <DiagnoseCanvas sovereignty={sov} onBack={() => setPhase('sov')} onComplete={(a) => { setAnswers(a); setPhase('morph'); }} />;
  else if (phase === 'morph') screen = <MorphView answers={answers} onDone={() => setPhase('result')} />;
  else screen = (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />
      <ResultString answers={answers} accent="var(--sage)" onRestart={() => { setAnswers({}); setPhase('onboarding'); }} />
    </div>
  );

  return <PhoneStage>{screen}</PhoneStage>;
}
