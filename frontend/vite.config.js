import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev-Server läuft im Container (node:20), am Host erreichbar unter 127.0.0.1:5173.
// `/api` wird an das Django-Backend weitergeleitet (Proxy) — so entwickelt das Frontend
// ohne CORS gegen das echte Backend. Ziel über ENV überschreibbar: Compose setzt
// VITE_PROXY_TARGET=http://web:8000 (Container-Name im selben Docker-Netz).
export default defineConfig({
  plugins: [react()],
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
