import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-Server läuft im Container (node:20), am Host erreichbar unter 127.0.0.1:5173.
// `/api` wird an das Django-Backend weitergeleitet (Proxy) — so entwickelt das Frontend
// ohne CORS gegen das echte Backend. Ziel über ENV überschreibbar: Compose setzt
// VITE_PROXY_TARGET=http://web:8000 (Container-Name im selben Docker-Netz).
export default defineConfig({
  plugins: [react()],
  // Die Landing-Page (frontend/public/index.html) ist die echte Startseite und wird
  // von Vite 1:1 ausgeliefert. Die React-App ist eine eigene Seite: ihr Einstieg heißt
  // bewusst app.html (NICHT index.html), damit es nur EINE index.html gibt. Vite muss
  // diesen Einstieg explizit kennen, sonst sucht der Build vergeblich nach index.html.
  build: {
    rollupOptions: {
      input: 'app.html',
    },
  },
  server: {
    host: true,
    port: 5173,
    strictPort: true,
    proxy: {
      '/api': {
        target: process.env.VITE_PROXY_TARGET || 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
})
