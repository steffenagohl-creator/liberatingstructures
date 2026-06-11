/* LS-MATCHMAKER — Sprach-Client (Stufe 1D / Phase 6)
   Verbindet das Frontend mit dem LiveKit-Sprachkanal:
   1) holt eine Sitzung beim Backend  (POST /api/voice/session/  → Token + URL + Stufe),
   2) tritt dem LiveKit-Raum bei und schaltet das Mikrofon ein (offenes Mikro),
   3) empfängt die Live-Updates des Agenten über den Data-Channel
      (Topic 'diagnose' → „Spinnennetz", Topic 'result' → fertiger String).

   Bewusst klein & rein technisch: die Optik bleibt im VoicePanel. Mikrofon braucht HTTPS
   (sicherer Kontext) — lokal über localhost, in Produktion über ls.klara.services.
*/
import { Room, RoomEvent, Track } from 'livekit-client';

const API_BASE = import.meta.env.VITE_API_BASE || '/api';

/**
 * Startet eine Sprach-Sitzung.
 * @param {object} opts
 * @param {string} opts.sovereignty       gewählte Stufe ('eu' | 'us' | 'sov')
 * @param {(d:object)=>void} [opts.onDiagnose]  Diagnose-Update vom Agenten
 * @param {(r:object)=>void} [opts.onResult]    fertiger Match-String vom Agenten
 * @param {(s:string)=>void} [opts.onStatus]    Status: 'connecting'|'live'|'closed'|'error'
 * @param {(m:object)=>void} [opts.onThinking]  Agent rechnet den Vorschlag (Wartespiel anzeigen)
 * @param {(reason:string)=>void} [opts.onEnded] Agent hat die Sitzung selbst beendet (Kostenschutz)
 * @returns {Promise<{room: Room, stop: ()=>Promise<void>, session: object}>}
 */
export async function startVoiceSession({ sovereignty, onDiagnose, onResult, onStatus, onThinking, onEnded } = {}) {
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

  // Stimme des Agenten hörbar machen: eingehende Audio-Tracks an ein (verstecktes)
  // <audio>-Element hängen. Ohne attach() bleibt der Agent stumm — sein Ton käme zwar
  // im Browser an, würde aber nie abgespielt.
  const audioEls = new Set();
  const cleanupAudio = () => { audioEls.forEach((el) => el.remove()); audioEls.clear(); };
  room.on(RoomEvent.TrackSubscribed, (track) => {
    if (track.kind !== Track.Kind.Audio) return;
    const el = track.attach();
    el.setAttribute('data-ls-voice', 'agent');
    el.style.display = 'none';
    document.body.appendChild(el);
    audioEls.add(el);
  });
  room.on(RoomEvent.TrackUnsubscribed, (track) => {
    track.detach().forEach((el) => { el.remove(); audioEls.delete(el); });
  });

  room.on(RoomEvent.DataReceived, (payload, _participant, _kind, topic) => {
    let msg;
    try { msg = JSON.parse(new TextDecoder().decode(payload)); } catch { return; }
    if (topic === 'diagnose' || msg?.type === 'diagnose') onDiagnose && onDiagnose(msg);
    else if (topic === 'status' || msg?.type === 'status') {
      onThinking && onThinking(msg);
      // Kostenschutz-Sicherheitsnetz: Hat der Agent die Sitzung selbst beendet ('ended'), trennen
      // wir uns nach kurzer Verzoegerung selbst — falls die serverseitige Raum-Loeschung den Client
      // ausnahmsweise nicht erreicht, bleibt so kein offenes Mikro stehen. Die Verzoegerung (~12s)
      // laesst den vollstaendigen Abschiedssatz ausklingen, bevor wir trennen — der harte
      // Kostenschutz (serverseitige Loeschung am Ende des 20s-Abschiedsfensters) bleibt unberuehrt.
      // (Normalfall: der Server loescht den Raum -> Disconnected feuert.)
      if (msg?.status === 'ended') {
        try { onEnded && onEnded(msg.reason); } catch { /* ignore */ }
        setTimeout(() => { room.disconnect().catch(() => { /* ignore */ }); }, 12000);
      }
    }
    else if (topic === 'result' || msg?.type === 'result') onResult && onResult(msg.result || msg);
  });
  room.on(RoomEvent.Disconnected, () => { cleanupAudio(); setStatus('closed'); });

  try {
    await room.connect(session.livekit_url, session.token);
    await room.localParticipant.setMicrophoneEnabled(true); // offenes Mikro
    // Autoplay-Sperre der Browser lösen (der Klick aufs Mikro zählt als Nutzergeste).
    try { await room.startAudio(); } catch { /* ignore */ }
    setStatus('live');
  } catch (err) {
    setStatus('error');
    try { await room.disconnect(); } catch { /* ignore */ }
    throw err;
  }

  return {
    room,
    session,
    // Mikro stumm/laut schalten OHNE die Sitzung zu beenden — das Gespräch (Kontext beim
    // Agenten) bleibt erhalten, man kann nahtlos weitersprechen.
    setMuted: async (m) => { try { await room.localParticipant.setMicrophoneEnabled(!m); } catch { /* ignore */ } },
    stop: async () => { try { await room.disconnect(); } finally { cleanupAudio(); setStatus('closed'); } },
  };
}
