/* ===================================================================
   ERGEBNIS — der echte vorgeschlagene "String"  (Stufe 3: echtes Backend)
   ===================================================================
   Zeigt den /api/match/-Response (match) + die je Slug geladenen
   Struktur-Details (details). Ersetzt die Prototyp-Schein-Logik.
   Optik 1:1 zum Prototyp; Inhalte sind jetzt echt (Name, Beschreibung,
   Badges, „Warum hier", echte Anleitung, echtes LS-Icon).

   Barrierefrei/maschinenlesbar: Primitive aus ui.jsx, aria-labels,
   aria-expanded; Icon mit icon_alt für Screenreader.
   =================================================================== */
import { useState } from 'react'
import { THEME, Glyph, PURPOSE_COLORS } from './shared.jsx'
import { Button, Badge, Card, Eyebrow } from './ui.jsx'

// Lesbare Labels für die purpose_tags (Backend-Keys → deutsche Kurzform).
const PURPOSE_LABEL = {
  offenlegen: 'Offenlegen', teilen: 'Teilen', analysieren: 'Analysieren',
  strategie: 'Strategie', helfen: 'Helfen', planen: 'Planen', solo: 'Solo',
};

// Kategorie-Farben kommen aus shared.jsx (PURPOSE_COLORS), das wiederum den Backend-Wert
// catalog/constants.py spiegelt — so nutzen Ergebnis & Schwerpunkt-Chips dieselbe Quelle.

const sizeLabel = (s) => `${s.group_size_min ?? '?'}–${s.group_size_max ?? '∞'} Pers.`;
const timeLabel = (s) => (s.duration_max && s.duration_max !== s.duration_min)
  ? `${s.duration_min}–${s.duration_max} Min` : `${s.duration_min} Min`;

/** Guide — rendert die echte Backend-Anleitung in der Prototyp-Optik. */
function Guide({ guide }) {
  if (!guide) return (
    <p style={{ fontSize: 13.5, color: 'var(--muted)', lineHeight: 1.5, margin: '12px 0 0' }}>
      Für diese Struktur liegt noch keine ausführliche Anleitung vor.</p>
  );
  const sections = [];
  if (guide.was_wird_moeglich) sections.push({ h: 'Was wird möglich', b: guide.was_wird_moeglich });
  if (guide.einladung) sections.push({ h: 'Einladung', b: guide.einladung });
  if (guide.schritte?.length) sections.push({ h: 'Ablauf & Timing', steps: guide.schritte });
  if (guide.tipps?.length) sections.push({ h: 'Tipps & Fallstricke', list: guide.tipps });
  if (guide.online_durchfuehrung) sections.push({ h: 'Online durchführen', b: guide.online_durchfuehrung });
  return (
    <>
      {sections.map((g, i) => (
        <div key={i} style={{ margin: '13px 0' }}>
          <h4 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '.06em',
            color: 'var(--terra)', margin: '0 0 6px', fontWeight: 600 }}>{g.h}</h4>
          {g.b && <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: 'var(--ink)' }}>{g.b}</p>}
          {g.steps && g.steps.map((s, j) => (
            <div key={j} style={{ marginBottom: 7, fontSize: 13.5, lineHeight: 1.45 }}>
              <span style={{ fontWeight: 600 }}>{s.phase}</span>
              <span style={{ color: 'var(--muted)' }}> ({s.dauer_min} Min)</span><br />
              <span style={{ color: 'var(--ink)' }}>{s.beschreibung}</span>
            </div>
          ))}
          {g.list && <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, lineHeight: 1.5, color: 'var(--ink)' }}>
            {g.list.map((li, j) => <li key={j} style={{ marginBottom: 3 }}>{li}</li>)}</ul>}
        </div>
      ))}
      <p style={{ fontSize: 11.5, color: 'var(--faint)', margin: '12px 0 0' }}>
        Liberating Structures · CC BY-SA 4.0 · Quelle verlinkt.</p>
    </>
  );
}

/** MethodCard — eine Struktur im String: echte Details + Begründung aus dem Match. */
export function MethodCard({ step, struct, idx, last, open, onToggle }) {
  const name = struct?.name || step.slug;
  return (
    <div style={{ display: 'flex', gap: 14, animation: `lsRise .5s ${idx * 0.12}s both` }}>
      {/* Zeitstrahl */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', flex: '0 0 auto' }}>
        <div className="ls-serif" style={{ width: 34, height: 34, borderRadius: 20, flex: '0 0 auto',
          background: 'var(--terra)', color: '#fff', display: 'grid', placeItems: 'center',
          fontSize: 17, fontWeight: 500 }} aria-hidden="true">{idx + 1}</div>
        {!last && <div style={{ width: 2, flex: 1, background: 'var(--line)', margin: '6px 0', borderRadius: 2 }} />}
      </div>
      {/* Karte */}
      <Card style={{ flex: 1, marginBottom: last ? 0 : 14 }}>
        <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12, marginBottom: 9 }}>
          <Glyph iconFile={struct?.icon} iconAlt={struct?.icon_alt} size={42} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase',
              color: 'var(--faint)' }}>{step.role}{step.duration ? ` · ${step.duration} Min` : ''}</div>
            <h3 className="ls-serif" style={{ margin: 0, fontSize: 21, fontWeight: 500, color: 'var(--ink)' }}>{name}</h3>
          </div>
        </div>
        {struct?.short_desc && <p style={{ margin: '0 0 11px', fontSize: 14.5, lineHeight: 1.5, color: 'var(--ink)' }}>{struct.short_desc}</p>}
        {struct && (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 11 }}>
            {struct.purpose_tags?.[0] && (
              <Badge style={{ background: PURPOSE_COLOR[struct.purpose_tags[0]] || 'var(--sand)',
                border: '1px solid rgba(60,40,30,.18)', color: 'var(--ink)', fontWeight: 600 }}>
                {PURPOSE_LABEL[struct.purpose_tags[0]] || struct.purpose_tags[0]}</Badge>
            )}
            <Badge>{sizeLabel(struct)}</Badge>
            <Badge>{timeLabel(struct)}</Badge>
            {struct.online_capable && <Badge>online-fähig</Badge>}
            {struct.difficulty && <Badge>{struct.difficulty}</Badge>}
          </div>
        )}
        {step.rationale && (
          <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: 'var(--muted)',
            borderTop: '1px dashed var(--line)', paddingTop: 10 }}>
            <strong style={{ color: 'var(--terra)', fontWeight: 600 }}>Warum hier: </strong>{step.rationale}</p>
        )}

        {/* Aufklapp-Schalter. Trägerwörter: anleitung, details, aufklappen, mehr, schritte. */}
        <button onClick={onToggle} aria-expanded={open}
          aria-label={`Anleitung für ${name} ${open ? 'einklappen' : 'aufklappen'}`}
          style={{ marginTop: 12, width: '100%', textAlign: 'left',
          background: 'none', border: 'none', borderTop: '1px solid var(--line)', paddingTop: 11,
          cursor: 'pointer', fontFamily: THEME.sans, fontSize: 14, fontWeight: 600,
          color: 'var(--terra)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          Vollständige Anleitung
          <span style={{ transition: 'transform .25s', transform: open ? 'rotate(90deg)' : 'none' }} aria-hidden="true">›</span>
        </button>

        {open && <div style={{ animation: 'lsFade .3s both', marginTop: 6 }}><Guide guide={struct?.guide} /></div>}
      </Card>
    </div>
  );
}

/**
 * ResultString — Ergebnis-Ansicht mit dem echten Backend-String.
 * @param {object} match    /api/match/-Response (string[], summary, …)
 * @param {object} details  slug → Struktur-Details (/api/structures/)
 */
export function ResultString({ match, details = {}, onRestart }) {
  const [open, setOpen] = useState(0); // erste Karte offen
  const steps = match?.string || [];

  return (
    <div style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>
      <div style={{ padding: '8px 20px 28px' }}>
        <Eyebrow style={{ marginBottom: 6 }}>Dein Vorschlag</Eyebrow>
        <h2 className="ls-serif" style={{ margin: '0 0 14px', fontSize: 28, fontWeight: 500,
          lineHeight: 1.1, letterSpacing: '-.01em' }}>Ein String, der zu eurer<br />Situation passt</h2>

        {match?.summary && (
          <div style={{ background: 'var(--sand)', border: '1px solid var(--amber)', borderRadius: 14,
            padding: '14px 16px', marginBottom: 22 }}>
            <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--terra)', marginBottom: 4 }}>Warum diese Abfolge?</div>
            <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--ink)' }}>{match.summary}</p>
            {match.total_duration ? <p style={{ margin: '8px 0 0', fontSize: 12.5, color: 'var(--muted)' }}>Gesamtdauer ca. {match.total_duration} Min</p> : null}
          </div>
        )}

        {steps.map((step, i) => (
          <MethodCard key={step.slug + i} step={step} struct={details[step.slug]} idx={i}
            last={i === steps.length - 1} open={open === i} onToggle={() => setOpen(open === i ? -1 : i)} />
        ))}

        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 9, marginTop: 24 }}>
          {/* Trägerwörter: speichern, merken, sichern, behalten. */}
          <Button variant="primary" ariaLabel="Diesen String speichern" style={{ flex: 1, minWidth: 130 }}>String speichern</Button>
          {/* Trägerwörter: anpassen, ändern, umsortieren, bearbeiten. */}
          <Button variant="ghost" ariaLabel="Reihenfolge der Methoden anpassen" style={{ flex: 1, minWidth: 130 }}>Reihenfolge anpassen</Button>
        </div>
        {/* Trägerwörter: neu, zurücksetzen, von vorne, neue Situation. */}
        <Button variant="ghost" ariaLabel="Neue Situation beginnen" onClick={onRestart}
          style={{ flex: 1, minWidth: 130, width: '100%', marginTop: 9 }}>Neue Situation</Button>
      </div>
    </div>
  );
}
