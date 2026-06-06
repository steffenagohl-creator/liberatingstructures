/* ===================================================================
   API-Client — Zugriff auf das LS-Matchmaker-Backend (Django/DRF)
   ===================================================================
   Basis-Pfad '/api' wird im Dev vom Vite-Proxy an das Django-Backend
   (web:8000) weitergeleitet → kein CORS nötig. In Produktion/Capacitor
   später über VITE_API_BASE überschreibbar.

   Endpunkte (selbstbeschreibend, vgl. OpenAPI /api/docs/):
   - fetchMatch(diagnose)      → POST /api/match/      : begründeter String
   - fetchStructure(slug,lang) → GET  /api/structures/<slug>/ : volle Details
   - fetchInterview(situation,answers) → POST /api/interview/ : adaptive Rückfragen
   =================================================================== */

const BASE = import.meta.env.VITE_API_BASE || '/api';

/** Fehler mit HTTP-Status + Backend-Detail, für sprechende Fehlermeldungen im UI. */
export class ApiError extends Error {
  constructor(message, status, detail) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
    this.detail = detail;
  }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(`${BASE}${path}`, options);
  } catch (netzfehler) {
    throw new ApiError('Keine Verbindung zum Server.', 0, String(netzfehler));
  }
  if (!res.ok) {
    let detail = '';
    try { detail = JSON.stringify(await res.json()); } catch { /* ignore */ }
    throw new ApiError(`Server-Fehler (${res.status}).`, res.status, detail);
  }
  return res.json();
}

const postJSON = (path, body) =>
  request(path, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });

/** Matchmaking: Diagnose → validierter, begründeter String (nutzt das LLM-Gehirn). */
export const fetchMatch = (diagnose) => postJSON('/match/', { diagnose });

/** Adaptive Rückfrage: Freitext-Situation → Diagnose + offene Fragen (Chat-Pfad, Stufe 4). */
export const fetchInterview = (situation, answers = {}) =>
  postJSON('/interview/', { situation, answers });

/** Volle Struktur-Details je Slug in der gewählten Sprache (Name, short_desc, guide, icon …). */
export const fetchStructure = (slug, lang = 'de') =>
  request(`/structures/${encodeURIComponent(slug)}/?lang=${lang}`);
