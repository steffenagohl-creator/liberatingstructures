/* ===================================================================
   LS-MATCHMAKER APP — Diagnose-Leinwand  (portiert aus design/lsc-diagnose.jsx)
   Geschwungene, organische Verbindungen · Eingabe per Tippen ODER Sprechen.
   Exportiert Constellation (für die Morph-Animation), DiagnoseCanvas, LSC.

   MODUS-KONZEPT (Steffen 2026-06-06): Optik leicht modusabhängig.
   - Chat/Tippen: Chips + Freitext (wie hier).
   - Sprache (später, 1D/Stufe 4): KEINE Chips — die KI leitet die Dimensionen aus
     dem freien Gespräch ab und füllt das „Spinnennetz" (Constellation) live.
   Die Modus-Struktur (mode 'voice'/'type', voiceAllowed) ist hier bereits angelegt.
   =================================================================== */
import { useState, useMemo } from 'react'
import { QUESTIONS, THEME, StatusBar } from './shared.jsx'
import { Chip } from './ui.jsx'

export const LSC = { CW: 390, CH: 376, cx: 195, cy: 178, rx: 128, ry: 122 };

function nodePos(i, n) {
  const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
  return { x: LSC.cx + LSC.rx * Math.cos(ang), y: LSC.cy + LSC.ry * Math.sin(ang) };
}
function shortVal(v) { return v && v.length > 16 ? v.slice(0, 14).trimEnd() + '…' : v; }

// geschwungener Pfad Kern -> Knoten (Bezier mit seitlichem Bauch)
function curve(x, y, bend) {
  const { cx, cy } = LSC;
  const mx = (cx + x) / 2, my = (cy + y) / 2;
  const dx = x - cx, dy = y - cy, len = Math.hypot(dx, dy) || 1;
  const nx = -dy / len, ny = dx / len, off = bend * len * 0.16;
  return `M${cx},${cy} Q${(mx + nx * off).toFixed(1)},${(my + ny * off).toFixed(1)} ${x.toFixed(1)},${y.toFixed(1)}`;
}

// ---- Konstellation (geteilt mit Morph) ---------------------------
export function Constellation({ seq, answers, filled, busyStep = -1, collapse = false }) {
  const { CW, CH, cx, cy } = LSC;
  return (
    <div style={{ position: 'relative', width: CW, height: CH, flex: '0 0 auto',
      background: 'radial-gradient(circle at 50% 47%, #FFFDF8 0%, var(--bg) 70%)', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, opacity: .5,
        backgroundImage: 'radial-gradient(var(--line) 1px, transparent 1px)', backgroundSize: '22px 22px' }} />

      <svg width={CW} height={CH} style={{ position: 'absolute', inset: 0, pointerEvents: 'none',
        opacity: collapse ? 0 : 1, transition: 'opacity .5s' }}>
        {seq.map((q, i) => {
          const p = nodePos(i, seq.length);
          const active = i < filled;
          return (
            <path key={q.id} d={curve(p.x, p.y, i % 2 ? 1 : -1)} fill="none"
              stroke={active ? 'var(--sage)' : 'var(--line)'} strokeWidth={active ? 1.7 : 1}
              strokeDasharray={active ? 'none' : '3 5'} strokeLinecap="round"
              style={{ opacity: active ? 1 : .7 }} />
          );
        })}
      </svg>

      {/* Kern */}
      <div style={{ position: 'absolute', left: cx, top: cy, transform: `translate(-50%,-50%) scale(${collapse ? 1.15 : 1})`,
        width: 74, height: 74, borderRadius: 42, background: 'var(--terra)', color: '#fff',
        display: 'grid', placeItems: 'center', textAlign: 'center', lineHeight: 1.15,
        boxShadow: '0 8px 24px rgba(184,88,39,.32)', transition: 'transform .6s cubic-bezier(.5,1.4,.4,1)', zIndex: 2 }}>
        <span className="ls-serif" style={{ fontSize: 14.5, fontWeight: 500 }}>Euer<br />Thema</span>
      </div>

      {/* Knoten */}
      {seq.map((q, i) => {
        const p = nodePos(i, seq.length);
        const done = i < filled;
        const isNew = busyStep === i;
        const tx = collapse ? cx - p.x : 0, ty = collapse ? cy - p.y : 0;
        return (
          <div key={q.id} style={{ position: 'absolute', left: p.x, top: p.y, width: 96, textAlign: 'center', zIndex: 1,
            transform: `translate(-50%,-50%) translate(${tx}px,${ty}px) scale(${collapse ? .25 : 1})`,
            opacity: collapse ? 0 : 1, transition: 'transform .6s cubic-bezier(.5,0,.3,1), opacity .5s',
            animation: isNew && !collapse ? 'lsPop .5s both' : 'none' }}>
            {done ? (
              <div style={{ background: 'var(--surface)', border: '1.5px solid var(--sage)', borderRadius: 12,
                padding: '6px 9px', boxShadow: '0 3px 10px rgba(94,138,120,.18)' }}>
                <div style={{ fontSize: 9.5, fontWeight: 700, letterSpacing: '.05em', textTransform: 'uppercase', color: 'var(--sage)' }}>{q.label}</div>
                <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--ink)', lineHeight: 1.2, marginTop: 1 }}>{shortVal(answers[q.id])}</div>
              </div>
            ) : (
              <div style={{ display: 'inline-flex', flexDirection: 'column', alignItems: 'center', gap: 4, opacity: i === filled ? 1 : .5 }}>
                <span style={{ width: 14, height: 14, borderRadius: 9, border: '1.5px dashed var(--faint)',
                  background: i === filled ? 'var(--sand)' : 'transparent',
                  animation: i === filled ? 'lsPulse 1.6s infinite' : 'none' }} />
                <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--faint)' }}>{q.label}</span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}

// ---- Diagnose-Bildschirm -----------------------------------------
export function DiagnoseCanvas({ sovereignty, onComplete, onBack }) {
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const voiceAllowed = sovereignty !== 'sov';
  const [mode, setMode] = useState(voiceAllowed ? 'voice' : 'type');
  const [listening, setListening] = useState(false);

  const tension = useMemo(() => {
    const s = (answers.situation || '').toLowerCase();
    return answers._tension || /frust|still|schweig|konflikt|spannung|streit|nicht weiter/.test(s);
  }, [answers]);
  const seq = useMemo(() => QUESTIONS.filter((q) => !q.adaptive || tension), [tension]);
  const current = seq[step];
  const filled = step + (busy ? 1 : 0);

  const answer = (val, extra) => {
    if (busy) return;
    setAnswers((a) => ({ ...a, [current.id]: val, ...extra }));
    setDraft(''); setListening(false); setBusy(true);
    const next = step + 1;
    setTimeout(() => {
      setBusy(false);
      if (next >= seq.length) onComplete({ ...answers, [current.id]: val, ...extra }); else setStep(next);
    }, 640);
  };

  const sovBadge = { sov: '🔒 Souverän', eu: '🇪🇺 EU', us: '🇺🇸 Komfort' }[sovereignty] || '🇪🇺 EU';

  return (
    <div className="ls-app" style={{ height: '100%', display: 'flex', flexDirection: 'column', background: 'var(--bg)' }}>
      <StatusBar />

      {/* Topbar */}
      <div style={{ flex: '0 0 auto', display: 'flex', alignItems: 'center', gap: 10, padding: '2px 16px 10px' }}>
        <button onClick={onBack} aria-label="Zurück zur Datenschutz-Auswahl" style={{ border: 'none', background: 'none', cursor: 'pointer', fontSize: 22,
          color: 'var(--muted)', padding: 0, width: 18, flex: '0 0 auto' }}>‹</button>
        <div style={{ flex: 1 }} role="progressbar" aria-label="Fortschritt der Diagnose"
          aria-valuenow={filled} aria-valuemin={0} aria-valuemax={seq.length}>
          <div style={{ height: 5, background: 'var(--line)', borderRadius: 5, overflow: 'hidden' }}>
            <div style={{ height: '100%', width: `${(filled / seq.length) * 100}%`, background: 'var(--sage)',
              borderRadius: 5, transition: 'width .5s' }} />
          </div>
        </div>
        <span style={{ fontSize: 11.5, fontWeight: 600, color: 'var(--muted)', flex: '0 0 auto' }}>{sovBadge}</span>
      </div>

      <Constellation seq={seq} answers={answers} filled={filled} busyStep={busy ? step : -1} />

      {/* Frage-/Eingabepanel */}
      <div key={step} style={{ flex: 1, overflowY: 'auto', padding: '14px 22px 18px', animation: 'lsRise .4s both' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--sage)' }}>{current.label}</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--faint)', fontVariantNumeric: 'tabular-nums' }}>{filled} von {seq.length}</span>
        </div>
        <h2 className="ls-serif" style={{ margin: '0 0 5px', fontSize: 23, lineHeight: 1.15, fontWeight: 500,
          letterSpacing: '-.01em', color: 'var(--ink)', textWrap: 'balance' }}>{current.q}</h2>
        {current.adaptive && current.why
          ? <p style={{ margin: 0, fontSize: 13, lineHeight: 1.45, color: 'var(--terra)' }}><span style={{ fontWeight: 600 }}>✦ </span>{current.why}</p>
          : <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.45, color: 'var(--muted)' }}>{current.hint}</p>}

        {/* Eingabe-Umschalter */}
        {voiceAllowed && (
          <div style={{ display: 'flex', gap: 6, margin: '14px 0 4px' }}>
            {[['voice', '🎤 Sprechen'], ['type', '⌨️ Tippen']].map(([m, lbl]) => (
              <button key={m} onClick={() => { setMode(m); setListening(false); }}
                aria-pressed={mode === m} aria-label={m === 'voice' ? 'Eingabe per Sprache' : 'Eingabe per Tastatur'}
                style={{ flex: 1, padding: '8px',
                borderRadius: 10, cursor: 'pointer', fontFamily: THEME.sans, fontSize: 13, fontWeight: 600,
                border: `1px solid ${mode === m ? 'var(--sage)' : 'var(--line)'}`,
                background: mode === m ? '#EAF1ED' : 'var(--surface)', color: mode === m ? 'var(--sage)' : 'var(--muted)' }}>{lbl}</button>
            ))}
          </div>
        )}

        {mode === 'voice' && voiceAllowed ? (
          <VoicePanel current={current} listening={listening} setListening={setListening} onPick={answer} />
        ) : (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {current.kind === 'text'
                ? current.presets.map((p) => (
                    <Chip key={p.v} onClick={() => answer(p.v, { _tension: !!p.tension })} style={{ width: '100%', textAlign: 'left' }}>{p.v}</Chip>
                  ))
                : current.options.map((opt) => (
                    <Chip key={opt} onClick={() => answer(opt)}>
                      {opt}
                      {current.sub && current.sub[opt] && <span style={{ display: 'block', fontSize: 11.5, color: 'var(--muted)', fontWeight: 400, marginTop: 1 }}>{current.sub[opt]}</span>}
                    </Chip>
                  ))}
            </div>
            {current.kind === 'text' && (
              <div style={{ display: 'flex', gap: 8, marginTop: 10 }}>
                <input value={draft} onChange={(e) => setDraft(e.target.value)}
                  onKeyDown={(e) => { if (e.key === 'Enter' && draft.trim()) answer(draft.trim()); }}
                  placeholder="… oder frei beschreiben"
                  aria-label={`Freie Antwort zu: ${current.q}`}
                  style={{ flex: 1, border: '1px solid var(--line)', borderRadius: 12, padding: '12px 14px',
                    fontFamily: THEME.sans, fontSize: 14.5, background: 'var(--surface)', color: 'var(--ink)', outline: 'none' }} />
                <button onClick={() => draft.trim() && answer(draft.trim())} aria-label="Antwort senden"
                  style={{ width: 46, borderRadius: 12, border: 'none', background: 'var(--sage)', color: '#fff', fontSize: 18, cursor: 'pointer', flex: '0 0 auto' }}>↑</button>
              </div>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

// ---- Sprach-Panel (Mikrofon-Ästhetik; Chips bleiben echte Eingabe)
// (In Stufe 1D/4 wird hieraus das echte Gespräch — Chips entfallen dann im Sprach-Modus.)
function VoicePanel({ current, listening, setListening, onPick }) {
  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 16, padding: '16px', textAlign: 'center' }}>
        <button onClick={() => setListening((v) => !v)} aria-pressed={listening}
          aria-label={listening ? 'Sprachaufnahme stoppen' : 'Sprachaufnahme starten'}
          style={{ width: 60, height: 60, borderRadius: 32, border: 'none', cursor: 'pointer', fontSize: 24,
            background: listening ? 'var(--terra)' : 'var(--sage)', color: '#fff',
            boxShadow: `0 0 0 ${listening ? 8 : 5}px ${listening ? 'rgba(184,88,39,.15)' : '#EAF1ED'}`, transition: 'box-shadow .3s, background .3s' }}>🎤</button>
        <div aria-hidden="true" style={{ display: 'flex', gap: 3, alignItems: 'center', justifyContent: 'center', height: 22, marginTop: 12 }}>
          {[10, 18, 26, 16, 22, 12, 24, 14, 8].map((h, i) => (
            <span key={i} style={{ width: 3.5, height: h, borderRadius: 2, background: listening ? 'var(--sage)' : 'var(--line)',
              transformOrigin: 'center', animation: listening ? `lsWave ${0.7 + (i % 4) * 0.12}s ${i * 0.05}s infinite` : 'none' }} />
          ))}
        </div>
        <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--muted)' }}>
          {listening ? 'Ich höre zu … sprich frei.' : 'Tippe aufs Mikro und erzähl — oder wähle unten.'}</p>
      </div>
      <p style={{ fontSize: 11.5, color: 'var(--faint)', margin: '12px 0 8px', textAlign: 'center', letterSpacing: '.04em' }}>SCHNELLE ANTWORTEN</p>
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
        {(current.kind === 'text' ? current.presets.map((p) => p.v) : current.options).map((opt, i) => {
          const tension = current.kind === 'text' ? current.presets[i].tension : false;
          return <Chip key={opt} onClick={() => onPick(opt, { _tension: !!tension })} style={current.kind === 'text' ? { width: '100%', textAlign: 'left' } : undefined}>{opt}</Chip>;
        })}
      </div>
    </div>
  );
}

