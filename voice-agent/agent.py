"""LS-Voice-Agent — der LiveKit-Worker (🇪🇺 Mistral/Voxtral-Pfad).

Ohren + Stimme + Transport; die LS-Fachlogik liegt in ``brain.py`` (LiveKit-unabhängig).
Offenes Mikro über Silero-VAD (kein Push-to-talk). Das „Hirn" bleibt unser ``/api/interview/``:
Nach jeder Nutzer-Äußerung fragt der Agent das Backend, spiegelt die Diagnose live ans Frontend
(Data-Channel → „Spinnennetz") und schlägt am Ende über ``/api/match/`` den String vor.

⚠️ Die genauen livekit-agents-Hook-Namen (Version ~1.5) beim ersten echten Lauf verifizieren;
die Stellen sind unten markiert. Bewusst defensiv programmiert (getattr/try), damit ein
API-Detail den ganzen Agenten nicht sprengt.
"""
from __future__ import annotations

import json
import logging
import os

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import mistralai, silero

from brain import LSInterviewBrain

load_dotenv()
logger = logging.getLogger("ls-voice-agent")

BACKEND_URL = os.environ.get("VOICE_BACKEND_URL", "http://web:8000")
STT_MODEL = os.environ.get("VOICE_STT_MODEL", "voxtral-mini-latest")
LLM_MODEL = os.environ.get("VOICE_LLM_MODEL", "mistral-large-latest")
TTS_VOICE = os.environ.get("VOICE_TTS_VOICE", "de_female_warm")

# Coach-Charakter: führt das adaptive LS-Interview als GESPRÄCH (kein Formular).
COACH_INSTRUCTIONS = (
    "Du bist eine warmherzige, kompetente Liberating-Structures-Coachin und sprichst Deutsch. "
    "Du führst ein lockeres Gespräch, um die Gruppensituation zu verstehen: Anlass/Zweck, "
    "Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid), psychologische Sicherheit "
    "und das Ziel. Stelle immer nur EINE kurze, natürliche Frage zur Zeit und höre zu. "
    "Erfinde keine Empfehlung selbst — das übernimmt das System, sobald genug bekannt ist."
)


async def _publish_diagnose(room, state) -> None:
    """Spiegelt den aktuellen Diagnose-Zustand an alle im Raum (Frontend „Spinnennetz")."""
    try:
        payload = json.dumps(
            {"type": "diagnose", "diagnose": state.diagnose,
             "open_questions": state.open_questions, "ready": state.ready},
            ensure_ascii=False,
        ).encode("utf-8")
        # ⚠️ API verifizieren: publish_data-Signatur (topic/reliable) je livekit-Version.
        await room.local_participant.publish_data(payload, reliable=True, topic="diagnose")
    except Exception as exc:  # pragma: no cover - reine Lauf-Robustheit
        logger.warning("Diagnose-Update konnte nicht gesendet werden: %s", exc)


class LSCoach(Agent):
    """Die Coachin: natürliche Gesprächsführung + Anbindung ans LS-Gehirn."""

    def __init__(self, room, brain: LSInterviewBrain):
        super().__init__(instructions=COACH_INSTRUCTIONS)
        self._room = room
        self._brain = brain
        self._done = False

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:  # noqa: D401
        """Nach jeder fertigen Nutzer-Äußerung: Backend fragen, Diagnose spiegeln, ggf. matchen.

        ⚠️ Signatur/Attribut ``new_message`` je livekit-agents-Version prüfen.
        """
        if self._done:
            return
        user_text = getattr(new_message, "text_content", None) or str(new_message)
        try:
            state = await self._brain.observe(user_text)
        except Exception as exc:
            logger.error("Interview-Backend nicht erreichbar: %s", exc)
            return
        await _publish_diagnose(self._room, state)

        if state.ready:
            self._done = True
            try:
                result = await self._brain.match()
                spoken = LSInterviewBrain.spoken_summary(result)
                payload = json.dumps({"type": "result", "result": result}, ensure_ascii=False)
                await self._room.local_participant.publish_data(
                    payload.encode("utf-8"), reliable=True, topic="result"
                )
                # ⚠️ session.say/generate_reply je Version; hier den Vorschlag vorlesen.
                await self.session.say(spoken)
            except Exception as exc:
                logger.error("Matchmaking fehlgeschlagen: %s", exc)


async def entrypoint(ctx: agents.JobContext) -> None:
    """Pro Raum: Session mit Voxtral-STT → Mistral-LLM → Voxtral-TTS + offenem Mikro."""
    await ctx.connect()
    brain = LSInterviewBrain(BACKEND_URL)

    session = AgentSession(
        stt=mistralai.STT(model=STT_MODEL),
        llm=mistralai.LLM(model=LLM_MODEL),
        tts=mistralai.TTS(voice=TTS_VOICE),
        vad=silero.VAD.load(),   # offenes Mikro / automatische Sprechpausen-Erkennung
    )
    await session.start(room=ctx.room, agent=LSCoach(ctx.room, brain))
    await session.generate_reply(
        instructions="Begrüße die Nutzerin kurz und frage offen nach der Gruppensituation."
    )


if __name__ == "__main__":
    # Eigener Port für den internen Worker-HTTP-Server (8081 ist auf dem Host belegt).
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            port=int(os.environ.get("AGENT_HTTP_PORT", "8099")),
        )
    )
