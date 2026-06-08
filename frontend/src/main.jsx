import { createRoot } from 'react-dom/client'
// Fonts lokal gebündelt (DSGVO — kein Google-Fonts-CDN). Ersetzt den <link> aus injectTheme().
import '@fontsource-variable/newsreader/opsz.css'
import '@fontsource-variable/newsreader/opsz-italic.css'
import '@fontsource-variable/hanken-grotesk/wght.css'
import './index.css'
import App from './App.jsx'
import ErrorBoundary from './ErrorBoundary.jsx'
import { injectTheme } from './shared.jsx'

// Einmaliges Einspielen von CSS-Variablen + Keyframes (Fonts kommen jetzt lokal, s. o.).
injectTheme()

// Bewusst ohne <StrictMode>: der Prototyp lief ohne; die Morph-Animation nutzt setTimeout,
// das unter StrictMode im Dev doppelt anliefe. So bleibt das Verhalten 1:1 zum Original.
// In eine ErrorBoundary gehüllt: ein Render-Crash zeigt jetzt eine lesbare Meldung mit
// Ursache, statt den ganzen Bildschirm leer/weiß werden zu lassen.
createRoot(document.getElementById('root')).render(
  <ErrorBoundary><App /></ErrorBoundary>
)
