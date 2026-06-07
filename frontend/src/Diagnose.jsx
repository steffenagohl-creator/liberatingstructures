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
import { QUESTIONS, THEME, StatusBar, ZWECK_LABEL_COLOR } from './shared.jsx'
import { Chip } from './ui.jsx'

export const LSC = { CW: 390, CH: 376, cx: 195, cy: 178, rx: 128, ry: 122 };

function nodePos(i, n) {
  const ang = -Math.PI / 2 + (i * 2 * Math.PI) / n;
  return { x: LSC.cx + LSC.rx * Math.cos(ang), y: LSC.cy + LSC.ry * Math.sin(ang) };
}
// Etwas mehr Text in den Knoten zeigen (Wunsch: „Situation"/„Ziel" wirken auf großem Screen
// zu knapp). Bewusst maßvoll, damit das feste Konstellations-Layout nicht überläuft.
function shortVal(v) { return v && v.length > 30 ? v.slice(0, 28).trimEnd() + '…' : v; }

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
    <div style={{ position: 'relative', width: CW, height: CH, flex: '0 0 auto', alignSelf: 'center',
      background: 'radial-gradient(circle at 50% 47%, #FFFDF8 0%, var(--bg) 70%)', overflow: 'hidden' }}>
      <div style={{ position: 'absolute', inset: 0, opacity: .5,
        backgroundImage: 'radial-gradient(var(--line) 1px, transparent 1px)', backgroundSize: '22px 22px' }} />

      <svg width={CW} height={CH} style={{ position: 'absolute', inset: 0, pointerEvents: 'none',
        opacity: collapse ? 0 : 1, transition: 'opacity .5s' }}>
        {seq.map((q, i) => {
          const p = nodePos(i, seq.length);
          // Faden „aktiv", sobald der zugehörige Wert erkannt ist (wie die Knoten) — sonst
          // würden im Sprach-Modus (nicht-lineare Füllung) die falschen Linien gezogen.
          const active = answers[q.id] != null;
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
        // „Erkannt", sobald ein Wert vorliegt — füllt die Spinne im Sprach-Modus auch
        // nicht-linear (das Gespräch nennt die Dimensionen in beliebiger Reihenfolge).
        // Im Tipp-Modus identisch zum bisherigen Verhalten (Antworten kommen der Reihe nach).
        const done = answers[q.id] != null;
        const isNew = busyStep === i;
        const tx = collapse ? cx - p.x : 0, ty = collapse ? cy - p.y : 0;
        return (
          <div key={q.id} style={{ position: 'absolute', left: p.x, top: p.y, width: 116, textAlign: 'center', zIndex: 1,
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
// Sprach-Sitzung lebt auf App-Ebene (überlebt Phasen-/Schrittwechsel) und wird über Props
// hereingereicht: voiceStatus + live erkannte voiceAnswers (für die Spinne), onVoiceStart/Stop.
export function DiagnoseCanvas({ sovereignty, onComplete, onBack,
  voiceStatus = 'idle', voiceAnswers = {}, voiceMuted = false,
  onVoiceStart, onVoiceStop, onVoiceToggleMute }) {
  const [answers, setAnswers] = useState({});
  const [step, setStep] = useState(0);
  const [busy, setBusy] = useState(false);
  const [draft, setDraft] = useState('');
  const voiceAllowed = sovereignty !== 'sov';
  const [mode, setMode] = useState(voiceAllowed ? 'voice' : 'type');

  const tension = useMemo(() => {
    const s = (answers.situation || '').toLowerCase();
    return answers._tension || /frust|still|schweig|konflikt|spannung|streit|nicht weiter/.test(s);
  }, [answers]);
  // Adaptive Knoten (z. B. „offen sprechen" = psychologische Sicherheit) werden im Tipp-Modus
  // nur bei erkannter Spannung gezeigt (Prototyp-Verhalten, bewusst erhalten). Im SPRACH-Modus
  // erhebt das Backend diese Dimension aber IMMER → dann auch immer als Strang visualisieren.
  const seq = useMemo(
    () => QUESTIONS.filter((q) => !q.adaptive || tension || mode === 'voice'),
    [tension, mode],
  );
  const current = seq[step];
  const filled = step + (busy ? 1 : 0);

  const isVoice = mode === 'voice';
  // Im Sprach-Modus speist die live aus dem Gespräch erkannte Diagnose (voiceAnswers) die
  // Spinne; im Tipp-Modus die selbst gewählten Antworten. Fortschritt = Anzahl erkannter Knoten.
  const shownAnswers = isVoice ? voiceAnswers : answers;
  const filledCount = isVoice ? seq.filter((q) => shownAnswers[q.id] != null).length : filled;

  const answer = (val, extra) => {
    if (busy) return;
    setAnswers((a) => ({ ...a, [current.id]: val, ...extra }));
    setDraft(''); setBusy(true);
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

      <Constellation seq={seq} answers={shownAnswers} filled={filledCount} busyStep={busy ? step : -1} />

      {/* Frage-/Eingabepanel */}
      <div key={isVoice ? 'voice' : step} style={{ flex: 1, overflowY: 'auto', padding: '14px 22px 18px', animation: 'lsRise .4s both' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 7 }}>
          <span style={{ fontSize: 11, fontWeight: 700, letterSpacing: '.06em', textTransform: 'uppercase', color: 'var(--sage)' }}>{isVoice ? 'Gespräch' : current.label}</span>
          <span style={{ fontSize: 12, fontWeight: 600, color: 'var(--faint)', fontVariantNumeric: 'tabular-nums' }}>{filledCount} von {seq.length}</span>
        </div>
        <h2 className="ls-serif" style={{ margin: '0 0 5px', fontSize: 23, lineHeight: 1.15, fontWeight: 500,
          letterSpacing: '-.01em', color: 'var(--ink)', textWrap: 'balance' }}>{isVoice ? 'Erzähl frei — ich höre zu' : current.q}</h2>
        {isVoice
          ? <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.45, color: 'var(--muted)' }}>{sovereignty === 'eu'
              ? 'Sprich einfach über eure Situation. Oben im Bild siehst du, was ich schon verstanden habe. Bitte beachte, dass zwischen den Fragen und deinen Antworten Pausen entstehen können, da die KI einen Moment braucht, um deine Antworten zu verarbeiten.'
              : 'Sprich einfach über eure Situation. Oben im Bild siehst du, was ich schon verstanden habe — du musst keine Fragen abarbeiten.'}</p>
          : (current.adaptive && current.why
            ? <p style={{ margin: 0, fontSize: 13, lineHeight: 1.45, color: 'var(--terra)' }}><span style={{ fontWeight: 600 }}>✦ </span>{current.why}</p>
            : <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.45, color: 'var(--muted)' }}>{current.hint}</p>)}

        {/* Eingabe-Umschalter */}
        {voiceAllowed && (
          <div style={{ display: 'flex', gap: 6, margin: '14px 0 4px' }}>
            {[['voice', '🎤 Sprechen'], ['type', '⌨️ Tippen']].map(([m, lbl]) => (
              <button key={m} onClick={() => { if (m !== 'voice') onVoiceStop && onVoiceStop(); setMode(m); }}
                aria-pressed={mode === m} aria-label={m === 'voice' ? 'Eingabe per Sprache' : 'Eingabe per Tastatur'}
                style={{ flex: 1, padding: '8px',
                borderRadius: 10, cursor: 'pointer', fontFamily: THEME.sans, fontSize: 13, fontWeight: 600,
                border: `1px solid ${mode === m ? 'var(--sage)' : 'var(--line)'}`,
                background: mode === m ? '#EAF1ED' : 'var(--surface)', color: mode === m ? 'var(--sage)' : 'var(--muted)' }}>{lbl}</button>
            ))}
          </div>
        )}

        {isVoice && voiceAllowed ? (
          <VoicePanel status={voiceStatus} muted={voiceMuted} diagCount={filledCount}
            onStart={onVoiceStart} onStop={onVoiceStop} onToggleMute={onVoiceToggleMute} />
        ) : (
          <div style={{ marginTop: 14 }}>
            <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
              {current.kind === 'text'
                ? current.presets.map((p) => (
                    <Chip key={p.v} onClick={() => answer(p.v, { _tension: !!p.tension })} style={{ width: '100%', textAlign: 'left' }}>{p.v}</Chip>
                  ))
                : current.options.map((opt) => {
                    // Schwerpunkt-Chips in der offiziellen Kategorie-Farbe (volle Fläche +
                    // Umrandung, wie das Ergebnis-Badge) → „Farbe = Kategorie" prägt sich ein.
                    const tint = current.id === 'zweck' ? ZWECK_LABEL_COLOR[opt] : null;
                    return (
                      <Chip key={opt} onClick={() => answer(opt)}
                        style={tint ? { background: tint, borderColor: 'rgba(60,40,30,.22)' } : undefined}>
                        {opt}
                        {current.sub && current.sub[opt] && <span style={{ display: 'block', fontSize: 11.5, color: 'var(--muted)', fontWeight: 400, marginTop: 1 }}>{current.sub[opt]}</span>}
                      </Chip>
                    );
                  })}
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

// ---- Sprach-Panel: reines „freies Gespräch" ----------------------------------
// Die LiveKit-Sitzung lebt auf APP-Ebene (überlebt Phasen-/Schrittwechsel) und wird hier
// nur gesteuert (Mikro an/aus) + der Status gespiegelt. Im Sprach-Modus führt die Coachin
// das Gespräch (Steffen 2026-06-06) — daher KEINE Antwort-Chips; die Rückmeldung ist das
// „Spinnennetz" oben. Der Tipp-Modus mit Chips bleibt davon unberührt erhalten.
function VoicePanel({ status, muted = false, diagCount = 0, onStart, onStop, onToggleMute }) {
  const active = status === 'live' || status === 'connecting';   // Sitzung läuft
  const live = status === 'live';
  // Mikro-Knopf: ohne Sitzung → starten; mit Sitzung → stumm/laut schalten (Sitzung bleibt).
  const onMic = () => (active ? onToggleMute && onToggleMute() : onStart && onStart());
  const statusText = {
    idle: 'Tippe aufs Mikro und erzähl frei.',
    connecting: 'Verbinde …',
    live: muted ? 'Mikro stumm — tippe aufs Mikro zum Weitersprechen.'
                : (diagCount ? `Ich höre zu … (${diagCount} erkannt)` : 'Ich höre zu … sprich frei.'),
    closed: 'Gespräch beendet — tippe aufs Mikro für ein neues.',
    error: 'Sprachverbindung nicht möglich — wechsle oben zu „Tippen".',
  }[status] || 'Tippe aufs Mikro und erzähl frei.';

  const micBg = !active ? 'var(--sage)' : (muted ? 'var(--faint)' : 'var(--terra)');
  const ring = !active ? '#EAF1ED' : (muted ? 'rgba(0,0,0,.06)' : 'rgba(184,88,39,.15)');
  const waving = live && !muted;

  return (
    <div style={{ marginTop: 14 }}>
      <div style={{ background: 'var(--surface)', border: '1px solid var(--line)', borderRadius: 16, padding: '16px', textAlign: 'center' }}>
        <button onClick={onMic} aria-pressed={active && !muted}
          aria-label={!active ? 'Sprachaufnahme starten' : (muted ? 'Mikrofon wieder einschalten' : 'Mikrofon stummschalten')}
          style={{ width: 60, height: 60, borderRadius: 32, border: 'none', cursor: 'pointer', fontSize: 24,
            background: micBg, color: '#fff',
            boxShadow: `0 0 0 ${active && !muted ? 8 : 5}px ${ring}`, transition: 'box-shadow .3s, background .3s' }}>
          {muted ? '🔇' : '🎤'}</button>
        <div aria-hidden="true" style={{ display: 'flex', gap: 3, alignItems: 'center', justifyContent: 'center', height: 22, marginTop: 12 }}>
          {[10, 18, 26, 16, 22, 12, 24, 14, 8].map((h, i) => (
            <span key={i} style={{ width: 3.5, height: h, borderRadius: 2, background: waving ? 'var(--sage)' : 'var(--line)',
              transformOrigin: 'center', animation: waving ? `lsWave ${0.7 + (i % 4) * 0.12}s ${i * 0.05}s infinite` : 'none' }} />
          ))}
        </div>
        <p style={{ margin: '8px 0 0', fontSize: 13, color: 'var(--muted)' }} aria-live="polite">
          {statusText}</p>
      </div>
      {active && (
        <button onClick={() => onStop && onStop()} aria-label="Gespräch beenden und Sitzung schließen"
          style={{ display: 'block', margin: '12px auto 0', border: 'none', background: 'none', cursor: 'pointer',
            fontSize: 13, fontWeight: 600, color: 'var(--muted)', textDecoration: 'underline', padding: 6 }}>
          Gespräch beenden</button>
      )}
    </div>
  );
}

