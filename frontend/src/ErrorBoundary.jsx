import { Component } from 'react'

/**
 * ErrorBoundary — Schutz gegen die „weiße Seite".
 *
 * Ohne diesen Schutz führt JEDER unbehandelte Render-Fehler in React dazu, dass der
 * gesamte Baum ausgehängt wird und der Bildschirm leer/weiß bleibt — ohne jede sichtbare
 * Spur, woran es lag (genau das Symptom beim Sprach-Ergebnis, Untersuchung 2026-06-08).
 *
 * Stattdessen fangen wir den Fehler hier ab und zeigen eine ruhige, VORLESBARE Meldung
 * mit der konkreten Ursache. ``role="alert"`` macht sie auch für Screenreader sofort
 * hörbar (Leitprinzip Barrierefreiheit). Der Fehler wird zusätzlich in die Browser-Konsole
 * geschrieben, damit wir bei der Fehlersuche den vollen Stack haben.
 */
export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { error: null }
  }

  static getDerivedStateFromError(error) {
    return { error }
  }

  componentDidCatch(error, info) {
    // Voller Kontext für die Fehlersuche (Browser-Konsole), schadet im Betrieb nicht.
    // eslint-disable-next-line no-console
    console.error('[LS] Render-Fehler abgefangen:', error, info)
  }

  handleReload = () => {
    this.setState({ error: null })
    try { window.location.reload() } catch { /* ignore */ }
  }

  render() {
    const { error } = this.state
    if (!error) return this.props.children

    return (
      <div role="alert" style={{ minHeight: '100vh', display: 'flex', flexDirection: 'column',
        alignItems: 'center', justifyContent: 'center', gap: 14, padding: '32px',
        textAlign: 'center', background: 'var(--bg, #faf6f0)', color: 'var(--ink, #2b2320)',
        fontFamily: 'system-ui, sans-serif' }}>
        <div style={{ fontSize: 34 }} aria-hidden="true">🛠️</div>
        <h1 style={{ margin: 0, fontSize: 22, fontWeight: 600 }}>Da ist im Bildschirm etwas abgestürzt</h1>
        <p style={{ margin: 0, fontSize: 14, lineHeight: 1.5, maxWidth: 420, color: 'var(--muted, #6b5d52)' }}>
          Die Anzeige konnte nicht aufgebaut werden. Die genaue Ursache steht unten — bitte beim
          Melden mitgeben.</p>
        <pre style={{ margin: 0, maxWidth: 460, maxHeight: 200, overflow: 'auto', textAlign: 'left',
          fontSize: 12, lineHeight: 1.45, background: 'var(--surface, #fff)',
          border: '1px solid var(--line, #e6ddd2)', borderRadius: 10, padding: '12px 14px',
          whiteSpace: 'pre-wrap', wordBreak: 'break-word' }}>
          {String(error?.message || error)}
        </pre>
        <button onClick={this.handleReload} aria-label="Seite neu laden"
          style={{ marginTop: 6, padding: '12px 22px', borderRadius: 12, border: 'none',
            background: 'var(--amber, #b85827)', color: '#fff', fontSize: 15, cursor: 'pointer' }}>
          Neu laden
        </button>
      </div>
    )
  }
}
