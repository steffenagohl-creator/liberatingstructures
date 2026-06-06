/* LS-MATCHMAKER — Sprach-Client (Stufe 1D / Phase 6)
   Verbindet das Frontend mit dem LiveKit-Sprachkanal:
   1) holt eine Sitzung beim Backend  (POST /api/voice/session/  → Token + URL + Stufe),
   2) tritt dem LiveKit-Raum bei und schaltet das Mikrofon ein (offenes Mikro),
   3) empfängt die Live-Updates des Agenten über den Data-Channel
      (Topic 'diagnose' → „Spinnennetz", Topic 'result' → fertiger String).

   Bewusst klein & rein technisch: die Optik bleibt im VoicePanel. Mikrofon braucht HTTPS
   (sicherer Kontext) — lokal über localhost, in Produktion über ls.klara.services.
*/
import { Room, RoomEvent } from 'livekit-client';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

/**
 * Startet eine Sprach-Sitzung.
 * @param {object} opts
 * @param {string} opts.sovereignty       gewählte Stufe ('eu' | 'us' | 'sov')
 * @param {(d:object)=>void} [opts.onDiagnose]  Diagnose-Update vom Agenten
 * @param {(r:object)=>void} [opts.onResult]    fertiger Match-String vom Agenten
 * @param {(s:string)=>void} [opts.onStatus]    Status: 'connecting'|'live'|'closed'|'error'
 * @returns {Promise<{room: Room, stop: ()=>Promise<void>, session: object}>}
 */
export async function startVoiceSession({ sovereignty, onDiagnose, onResult, onStatus } = {}) {
  const setStatus = (s) => { try { onStatus && onStatus(s); } catch { /* ignore */ } };
  setStatus('connecting');

  const res = await fetch(`${API_BASE}/voice/session/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ sovereignty }),
  });
  if (!res.ok) { setStatus('error'); throw new Error(`Sitzung fehlgeschlagen (HTTP ${res.status})`); }
  const session = await res.json();

  const room = new Room({ adaptiveStream: true, dynacast: true });

  room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
    let msg;
    try { msg = JSON.parse(new TextDecoder().decode(payload)); } catch { return; }
    if (topic === 'diagnose' || msg?.type === 'diagnose') onDiagnose && onDiagnose(msg);
    else if (topic === 'result' || msg?.type === 'result') onResult && onResult(msg.result || msg);
  });
  room.on(RoomEvent.Disconnected, () => setStatus('closed'));

  try {
    await room.connect(session.livekit_url, session.token);
    await room.localParticipant.setMicrophoneEnabled(true); // offenes Mikro
    setStatus('live');
  } catch (err) {
    setStatus('error');
    try { await room.disconnect(); } catch { /* ignore */ }
    throw err;
  }

  return {
    room,
    session,
    stop: async () => { try { await room.disconnect(); } finally { setStatus('closed'); } },
  };
}
