# LS-Voice-Agent (LiveKit-Worker)

Der **konversationelle** Sprach-Agent des LS-Matchmaker — Ohren, Stimme, Transport. Die
LS-Fachlogik liegt getrennt in `brain.py` (LiveKit-unabhängig, gegen das Backend testbar).

- `agent.py` — LiveKit-Worker: Voxtral-STT → Mistral-LLM → Voxtral-TTS, **offenes Mikro** (Silero-VAD).
- `brain.py` — Gesprächs-/Diagnose-Logik: ruft `/api/interview/` (nach jeder Äußerung) und
  `/api/match/` (wenn bereit); spiegelt die Diagnose live ans Frontend (Data-Channel „diagnose"/„result").
- Nur **offizielle LiveKit-Plugins** (pip), **kein** Code aus `klara_voice`.

## ENV
- `LIVEKIT_URL`, `LIVEKIT_API_KEY`, `LIVEKIT_API_SECRET` — Verbindung zum LiveKit-Server.
- `MISTRAL_API_KEY` — für Voxtral/Mistral (Pay-per-Use).
- `VOICE_BACKEND_URL` (Default `http://web:8000`), `VOICE_STT_MODEL`, `VOICE_LLM_MODEL`, `VOICE_TTS_VOICE`.

## Start (Container) — ERST nach Freigabe + laufendem LiveKit-Server
```bash
docker compose -f infra/livekit/docker-compose.agent.yml up -d --build   # (Compose-Datei folgt bei der Integration)
```

## Status
Code gebaut; **Laufzeit-Verifikation der livekit-agents-Hook-Namen (~1.5) steht beim ersten echten
Lauf an** (markierte Stellen in `agent.py`). `brain.py` ist schon jetzt gegen das laufende Backend testbar.
