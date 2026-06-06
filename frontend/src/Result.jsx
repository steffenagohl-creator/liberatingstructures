/* ===================================================================
   ERGEBNIS — der vorgeschlagene "String"  (portiert aus design/result.jsx)
   Bekommt die Antworten, baut die Empfehlung (vorerst Mock) und zeigt sie
   als gegliederte Methoden-Abfolge. In Stufe 3 kommt der echte /api/match/-Response.

   Barrierefrei/maschinenlesbar: nutzt die Design-System-Primitive (Button/Badge/
   Card/Eyebrow) aus ui.jsx; Buttons tragen aria-label, interaktive Bereiche
   aria-expanded. Trägerwörter je Aktion stehen als Docstring an der Aufrufstelle.
   =================================================================== */
import { useState, useMemo } from 'react'
import { METHODS, GUIDES, THEME, Glyph, buildRecommendation } from './shared.jsx'
import { Button, Badge, Card, Eyebrow } from './ui.jsx'

export function MethodCard({ name, idx, last, rzn, open, onToggle }) {
  const m = METHODS[name];
  const guide = GUIDES[name];
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
          <Glyph name={name} size={42} />
          <div style={{ flex: 1, minWidth: 0 }}>
            <div style={{ fontSize: 11, fontWeight: 600, letterSpacing: '.07em', textTransform: 'uppercase',
              color: 'var(--faint)' }}>{m.role}</div>
            <h3 className="ls-serif" style={{ margin: 0, fontSize: 21, fontWeight: 500, color: 'var(--ink)' }}>{name}</h3>
          </div>
        </div>
        <p style={{ margin: '0 0 11px', fontSize: 14.5, lineHeight: 1.5, color: 'var(--ink)' }}>{m.desc}</p>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 11 }}>
          <Badge primary>{m.purpose}</Badge><Badge>{m.size + ' Pers.'}</Badge><Badge>{m.time}</Badge>
          {m.online && <Badge>online-fähig</Badge>}<Badge>{m.level}</Badge>
        </div>
        <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: 'var(--muted)',
          borderTop: '1px dashed var(--line)', paddingTop: 10 }}>
          <strong style={{ color: 'var(--terra)', fontWeight: 600 }}>Warum hier: </strong>{rzn}</p>

        {/* Aufklapp-Schalter für die Anleitung. Trägerwörter: anleitung, details, aufklappen, mehr, schritte. */}
        <button onClick={onToggle} aria-expanded={open}
          aria-label={`${guide ? 'Vollständige Anleitung' : 'Anleitung'} für ${name} ${open ? 'einklappen' : 'aufklappen'}`}
          style={{ marginTop: 12, width: '100%', textAlign: 'left',
          background: 'none', border: 'none', borderTop: '1px solid var(--line)', paddingTop: 11,
          cursor: 'pointer', fontFamily: THEME.sans, fontSize: 14, fontWeight: 600,
          color: 'var(--terra)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          {guide ? 'Vollständige Anleitung' : 'Anleitung'}
          <span style={{ transition: 'transform .25s', transform: open ? 'rotate(90deg)' : 'none' }} aria-hidden="true">›</span>
        </button>

        {open && (
          <div style={{ animation: 'lsFade .3s both', marginTop: 6 }}>
            {guide ? guide.map((g, i) => (
              <div key={i} style={{ margin: '13px 0' }}>
                <h4 style={{ fontSize: 12, textTransform: 'uppercase', letterSpacing: '.06em',
                  color: 'var(--terra)', margin: '0 0 6px', fontWeight: 600 }}>{g.h}</h4>
                {g.b && <p style={{ margin: 0, fontSize: 13.5, lineHeight: 1.5, color: 'var(--ink)' }}>{g.b}</p>}
                {g.steps && g.steps.map((s, j) => (
                  <div key={j} style={{ marginBottom: 7, fontSize: 13.5, lineHeight: 1.45 }}>
                    <span style={{ fontWeight: 600 }}>{s[0]}</span>
                    <span style={{ color: 'var(--muted)' }}> ({s[1]})</span><br />
                    <span style={{ color: 'var(--ink)' }}>{s[2]}</span>
                  </div>
                ))}
                {g.list && <ul style={{ margin: 0, paddingLeft: 18, fontSize: 13.5, lineHeight: 1.5, color: 'var(--ink)' }}>
                  {g.list.map((li, j) => <li key={j} style={{ marginBottom: 3 }}>{li}</li>)}</ul>}
              </div>
            )) : (
              <p style={{ fontSize: 13.5, color: 'var(--muted)', lineHeight: 1.5, margin: '12px 0 0' }}>
                Voller Guide wie bei Schritt 1: Was wird möglich · Einladung · Schritte mit Zeiten ·
                Tipps · Online · Material &amp; Quelle.</p>
            )}
            <p style={{ fontSize: 11.5, color: 'var(--faint)', margin: '12px 0 0' }}>
              Liberating Structures · CC BY-SA 4.0 · Quelle verlinkt.</p>
          </div>
        )}
      </Card>
    </div>
  );
}

/**
 * ResultString — Ergebnis-Ansicht: zeigt den vorgeschlagenen String als Methoden-Abfolge.
 * Titel:        Vorschlag/Ergebnis.
 * Beschreibung: Listet die empfohlenen Strukturen mit Begründung, Badges und Anleitung.
 */
export function ResultString({ answers, onRestart, accent = 'var(--amber)' }) {
  const rec = useMemo(() => buildRecommendation(answers), [answers]);
  const [open, setOpen] = useState(0); // erste Karte offen

  return (
    <div style={{ flex: 1, overflowY: 'auto', WebkitOverflowScrolling: 'touch' }}>
      <div style={{ padding: '8px 20px 28px' }}>
        <Eyebrow style={{ marginBottom: 6 }}>Dein Vorschlag</Eyebrow>
        <h2 className="ls-serif" style={{ margin: '0 0 14px', fontSize: 28, fontWeight: 500,
          lineHeight: 1.1, letterSpacing: '-.01em' }}>Ein String, der zu eurer<br />Situation passt</h2>

        <div style={{ background: 'var(--sand)', border: '1px solid var(--amber)', borderRadius: 14,
          padding: '14px 16px', marginBottom: 22 }}>
          <div style={{ fontSize: 13, fontWeight: 700, color: 'var(--terra)', marginBottom: 4 }}>Warum diese Abfolge?</div>
          <p style={{ margin: 0, fontSize: 14, lineHeight: 1.55, color: 'var(--ink)' }}>{rec.arc}</p>
        </div>

        {rec.string.map((name, i) => (
          <MethodCard key={name} name={name} idx={i} last={i === rec.string.length - 1}
            rzn={rec.rzn[name]} open={open === i} onToggle={() => setOpen(open === i ? -1 : i)} />
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
