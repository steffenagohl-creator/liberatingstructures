# LS-LiveKit — eigenes WebRTC-Transport-Modul (Stufe 1D, Phase 2)

In sich geschlossener LiveKit-Server für die **Sprachkanäle** des LS-Matchmaker. Eigenständig
und ohne jede Abhängigkeit zu anderen Projekten — nur der **Transport** (Audio + später Video).
Die Sprach-Engines (Voxtral/Mistral, OpenAI) laufen separat im Voice-Agent-Worker (Phase 3+).

## Was hier liegt (öffentlich, generisch)
- `livekit-config.yaml` — Server-Konfiguration mit eigenem, kollisionsfreiem Port-Block.
- `docker-compose.yml` — der LiveKit-Container, ENV-getrieben, **ohne Secrets**.

## Port-Block (kollisionsfrei, falls ein zweiter LiveKit-Server auf demselben Host läuft)
| Zweck | Port |
|---|---|
| Signaling/HTTP | **7980** |
| RTC TCP | **7981** |
| RTC UDP-Medien (Audio + Video) | **40000–49999** |
| TURN UDP / TLS (optional, später) | **3479 / 5350** |

## Vor dem Start zu klären (NICHT im Repo, kommt in `.env` / lokal)
1. **Schlüssel erzeugen:** `LIVEKIT_API_KEY` + `LIVEKIT_API_SECRET` (zufällig) → in die `.env`.
2. **`LIVEKIT_NODE_IP`** = öffentliche IP des Servers (für WebRTC-Kandidaten) → `.env`.
3. **Firewall (root):** UDP **40000–49999** (+ TCP 7980/7981, falls nicht über Reverse-Proxy)
   öffnen. Muss Steffen/root machen.
4. **Nach außen:** entweder über den vorhandenen Reverse-Proxy (443 → 7980, eigener Pfad/Subdomain)
   oder direkt. Konkrete Wahl mit Steffen.
5. **TURN (optional, später):** eigene **Subdomain + TLS-Zertifikat** nötig; dann in
   `livekit-config.yaml` `turn.enabled: true` + Domain/Cert setzen und Certs read-only mounten.

## Start (ERST nach Steffens Freigabe — bindet öffentliche Ports)
```bash
# Voraussetzung: LIVEKIT_API_KEY/SECRET + LIVEKIT_NODE_IP in ../../.env
docker compose -f infra/livekit/docker-compose.yml up -d
docker logs lsm_livekit         # prüfen, dass der Server sauber startet
```

## Bewusst NICHT enthalten
- **Egress** (server-seitige Video-Aufzeichnung) — nur bei Bedarf nachrüsten; Live-Video braucht es nicht.
- Keine Werte oder Code aus anderen Projekten; dieses Modul steht für sich.
