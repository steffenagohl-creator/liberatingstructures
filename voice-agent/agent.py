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

import asyncio
import base64
import json
import logging
import os

from dotenv import load_dotenv
from livekit import agents
from livekit.agents import Agent, AgentSession
from livekit.plugins import mistralai, openai, silero

from brain import LSInterviewBrain

load_dotenv()
logger = logging.getLogger("ls-voice-agent")

BACKEND_URL = os.environ.get("VOICE_BACKEND_URL", "http://web:8000")
# Realtime-Streaming-STT (Voxtral): liefert laufende Zwischen-Transkripte (<200 ms) statt
# erst nach kompletter Äußerung — fühlbar flüssigeres Gespräch. Hat KEIN server-seitiges
# Endpointing, braucht daher eine VAD (unten geteilt), um Sprechpausen zu erkennen/flushen.
STT_MODEL = os.environ.get("VOICE_STT_MODEL", "voxtral-mini-transcribe-realtime-2602")
# Gesprächs-LLM: mistral-small ist deutlich schneller als -large und reicht hier völlig —
# die eigentliche Diagnose-Intelligenz liegt im Backend (/api/interview/); der Agent formuliert
# nur natürlich aus. Schnelleres Modell = weniger Stille zwischen den Fragen.
LLM_MODEL = os.environ.get("VOICE_LLM_MODEL", "mistral-small-latest")
TTS_VOICE = os.environ.get("VOICE_TTS_VOICE", "de_female_warm")

# Coach-Charakter & Verhaltens-Leitplanken — PHASEN-MODELL.
# Hintergrund (verifiziert im Test 2026-06-06): Im Realtime-Pfad (us) führt das Sprachmodell
# das Gespräch SELBST. Ein einziger, statischer Prompt („frage immer weiter, präsentiere nie")
# lässt das Modell auch nach dem fertigen Match WEITER fragen („und wie geht es dir damit?") —
# es bekommt den Phasenwechsel nicht mit. Lösung: Persönlichkeit bleibt konstant, aber die
# VERHALTENSREGEL wird je Phase umgeschaltet (``update_instructions`` ist im Realtime-Modell das
# Lenkrad fürs Verhalten). Vier Phasen: ERHEBUNG → BESTÄTIGUNG (Go einholen) → VERDICHTUNG → ABSCHLUSS.

# Persönlichkeit (in ALLEN Phasen gleich): warmherzig, ruhig, geduldig, Deutsch, langsam.
COACH_PERSONA = (
    "Du bist eine warmherzige, ruhige und geduldige Liberating-Structures-Coachin und sprichst "
    "Deutsch. Sprich LANGSAM, ruhig und freundlich; schaffe eine angenehme, sichere Atmosphäre "
    "und lass der Person Zeit zum Nachdenken — keine Hektik, kein Drängen. "
)

# PHASE 1 — ERHEBUNG: nur zuhören & gezielt fragen, nie selbst vorschlagen.
PHASE_ERHEBUNG = COACH_PERSONA + (
    "Ihr seid am ANFANG des Gesprächs. Du führst ein lockeres Gespräch, um die Gruppensituation "
    "zu verstehen: Anlass/Zweck, Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid), "
    "psychologische Sicherheit und das Ziel. Stelle immer nur EINE kurze, natürliche Frage zur "
    "Zeit und höre aufmerksam zu. "
    "GANZ WICHTIG — halte dich strikt daran: Du schlägst in dieser Phase NIEMALS selbst eine "
    "Methode, Übung oder Lösung vor, du nennst KEINE Liberating Structures und du moderierst "
    "NICHTS. Auch wenn du glaubst, schon genug zu wissen: präsentiere KEINE Lösung. Deine einzige "
    "Aufgabe ist jetzt ZUHÖREN und FRAGEN. Den konkreten Vorschlag erstellt allein das System — "
    "du fragst so lange ruhig weiter, bis das System dir das Signal gibt. "
    "Sage AUSSERDEM niemals Sätze wie „ich weiß genug“, „ich habe alles verstanden“ oder „ich "
    "gebe dir jetzt eine Empfehlung“. OB genug Information vorhanden ist, entscheidet allein das "
    "System — nicht du. Bis dahin fragst du einfach ruhig und freundlich weiter."
)

# Startinstruktion = Erhebung (Alias, hält bestehende Verweise gültig).
COACH_INSTRUCTIONS = PHASE_ERHEBUNG

# PHASE 1b — BESTÄTIGUNG: alle Punkte gehört → ZUSAMMENFASSEN und auf das ausdrückliche „Go"
# warten. Wie ein echter Berater: erst rückversichern, dann erst rechnen. Der eigentliche Start
# des Strings steuert UNSER Code (Erkennung der Bestätigung), nicht das Modell.
PHASE_BESTAETIGUNG = COACH_PERSONA + (
    "Du hast jetzt zu allen wichtigen Punkten etwas gehört. BEVOR irgendein Vorschlag erstellt "
    "wird, fasse der Person in zwei, drei ruhigen Sätzen zusammen, was du verstanden hast — und "
    "zwar zu: Zweck/Anlass, Gruppengröße, verfügbarer Zeit, Setting (Präsenz/Online/Hybrid) und "
    "psychologischer Sicherheit. Stelle danach GENAU EINE einzige, klare Ja/Nein-Frage, ob du auf "
    "dieser Grundlage den Vorschlag erstellen sollst (z. B. „Passt das so für dich — soll ich dir "
    "jetzt einen Vorschlag zusammenstellen?“). Stelle NICHT zwei Fragen auf einmal und frage NICHT "
    "getrennt, ob du richtig zusammengefasst hast — eine einzige Frage genügt. "
    "Schlage selbst KEINE Methode vor und nenne KEINE Liberating Structures. Wenn die Person "
    "etwas korrigiert oder ergänzt, nimm es dankbar auf und fasse danach erneut kurz zusammen. "
    "Erst wenn die Person ausdrücklich zustimmt, geht es weiter."
)

# PHASE 2 — VERDICHTUNG: genug erhoben, das System rechnet. Keine Fragen mehr, ruhig warten.
PHASE_VERDICHTUNG = COACH_PERSONA + (
    "Die Erhebung ist ABGESCHLOSSEN — das System hat genug Informationen und stellt JETZT im "
    "Hintergrund einen passenden Vorschlag zusammen (das dauert einen kleinen Moment). "
    "Deine Aufgabe in dieser Phase: Sage der Person EINMAL ruhig, dass du genug verstanden hast "
    "und gerade einen Vorschlag zusammenstellst, und bitte sie um einen kurzen Moment Geduld. "
    "Danach stellst du KEINE weiteren Fragen mehr und beginnst KEIN neues Thema — du wartest "
    "ruhig. Falls die Person noch etwas sagt, antworte nur kurz und freundlich, dass der "
    "Vorschlag gleich da ist."
)

# PHASE 3 — ABSCHLUSS: Vorschlag ist da und wird vorgelesen. Danach ist der Job erledigt.
PHASE_ABSCHLUSS = COACH_PERSONA + (
    "Der Vorschlag des Systems ist FERTIG und wird der Person gerade vorgelesen. Damit ist deine "
    "Hauptaufgabe ERLEDIGT. "
    "GANZ WICHTIG: Starte das Interview NICHT neu. Stelle KEINE neuen Diagnose-Fragen mehr "
    "(weder nach Zweck, Gruppengröße, Zeit, Setting noch nach psychologischer Sicherheit) und "
    "frage NICHT „und wie geht es dir jetzt damit“. Das Gespräch zur Situationsaufnahme ist "
    "vorbei. Wenn die Person eine konkrete RÜCKFRAGE ZUM VORSCHLAG stellt, beantworte sie kurz "
    "und hilfreich. Ansonsten wünsche der Person warm viel Erfolg und lass das Gespräch ruhig "
    "ausklingen."
)

# Dimensionen, die für eine „volle Spinne" erfasst sein müssen, bevor der Agent den Match
# auslöst (Steffen-Wunsch). Wir prüfen die ERKANNTE Diagnose direkt — nicht ``open_questions``,
# denn das Backend lässt ``psychologische_sicherheit`` dort auch dann stehen, wenn sie längst
# erkannt ist (dadurch würde der Match nie starten). ``ziel_text``/``scrum_kontext`` sind
# bewusst NICHT Pflicht (oft diffus) — sie füllen die Spinne, blockieren sie aber nicht.
SPINNE_KEYS = ("zweck", "gruppengroesse", "zeitbudget", "setting", "psychologische_sicherheit")
# KERN-Dimensionen = die zuverlässig erkannten. ``psychologische_sicherheit`` wird vom Backend
# chronisch NICHT sauber erkannt (Test 2026-06-06: über eine ganze Sitzung nie gefüllt, ready
# blieb False). Daher darf sie den Match NICHT blockieren: sind die Kern-4 da, fragt der Coach
# noch kurz nach Sicherheit und löst dann auch ohne sie aus (s. Trigger in process_user_text).
CORE_KEYS = ("zweck", "gruppengroesse", "zeitbudget", "setting")
SPINNE_LABELS = {
    "zweck": "den Schwerpunkt/Zweck des Treffens (z. B. offenlegen, analysieren, entscheiden, planen)",
    "gruppengroesse": "die Gruppengröße (wie viele Personen dabei sind)",
    "zeitbudget": "die verfügbare Zeit (ungefähr in Minuten)",
    "setting": "das Setting — Präsenz, online oder hybrid",
    "psychologische_sicherheit": "wie offen und sicher sich die Gruppe fühlt, frei zu sprechen",
}


def _build_tts():
    """Baut das TTS. Voxtral hat KEINE deutsche Preset-Stimme (nur EN/GB/FR), die Deutsch
    daher mit Akzent sprechen. Klares Deutsch entsteht per **Zero-Shot-Voice-Cloning**:
    Ist ``VOICE_TTS_REF_AUDIO`` (Pfad zu einer sauberen, akzentfrei-deutschen Sprachprobe,
    ~10–25 s) gesetzt, wird die Stimme daraus geklont. Ohne Referenz Fallback auf die
    Default-Stimme, damit der Agent weiterläuft (dann mit Akzent).
    """
    ref_path = os.environ.get("VOICE_TTS_REF_AUDIO", "").strip()
    if ref_path and os.path.isfile(ref_path):
        with open(ref_path, "rb") as fh:
            ref_b64 = base64.b64encode(fh.read()).decode("ascii")
        logger.info("TTS: deutsche Stimme per Voice-Cloning aus %s", ref_path)
        return mistralai.TTS(ref_audio=ref_b64)
    logger.warning("TTS: kein VOICE_TTS_REF_AUDIO — Default-Stimme (ausländischer Akzent möglich).")
    return mistralai.TTS()


async def _publish_diagnose(room, state, situation: str = "") -> None:
    """Spiegelt den aktuellen Diagnose-Zustand an alle im Raum (Frontend „Spinnennetz").
    ``situation`` (erste Äußerung) beschriftet den Mittelpunkt, wenn das Backend keinen
    ``scrum_kontext`` erkennt."""
    try:
        payload = json.dumps(
            {"type": "diagnose", "diagnose": state.diagnose,
             "open_questions": state.open_questions, "ready": state.ready,
             "situation": situation},
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
        self._last_guidance = None  # zuletzt gesetzte Coach-Guidance (vermeidet unnötige Updates)
        self._ready_turns = 0       # wie oft das Backend „ready" meldete (Anti-Hänger)
        self._seen: set[str] = set()  # je erkannte Dimensionen — KLEBRIG (gegen Backend-Flackern)
        self._core_turns = 0        # Äußerungen, seit die Kern-4 vollständig sind (Diagnose)
        self._phase = "ERHEBUNG"    # aktuelle Verhaltensphase (verhindert doppelte Instruktions-Updates)
        self._awaiting_confirmation = False  # True = zusammengefasst, wartet auf das ausdrückliche „Go"

    async def on_enter(self) -> None:  # noqa: D401
        """Wird vom Framework aufgerufen, sobald der Agent in der Sitzung AKTIV ist — der richtige
        Zeitpunkt für die Begrüßung. (Früher direkt nach ``session.start`` aufgerufen → Race:
        die Sitzung war noch nicht bereit, die erste Antwort wurde abgeschnitten und neu
        ausgelöst → Start-Loop. ``on_enter`` vermeidet das.)"""
        logger.info("on_enter: Begrüßung wird gesendet")
        await self._request_reply(
            "Begrüße die Nutzerin kurz und herzlich und frage offen nach der Gruppensituation. "
            "Sage genau EINE Begrüßung und EINE offene Frage — danach hörst du zu."
        )

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:  # noqa: D401
        """Pipeline-Pfad (eu/sov): nach jeder fertigen Nutzer-Äußerung das Gehirn füttern."""
        user_text = getattr(new_message, "text_content", None) or str(new_message)
        await self.process_user_text(user_text)

    async def process_user_text(self, user_text: str) -> None:
        """Gemeinsame Gehirn-Logik **beider** Pfade: Backend fragen, Diagnose spiegeln (Spinne),
        und sobald genug bekannt ist den ECHTEN Match holen + vorlesen.

        Aufgerufen aus ``on_user_turn_completed`` (EU-Pipeline) **und** aus dem
        ``user_input_transcribed``-Event (US-Realtime) — denn im Realtime-Modus liefert
        livekit die Nutzer-Transkription über dieses Event, nicht über den Turn-Hook.
        """
        if self._done:
            return
        user_text = (user_text or "").strip()
        if not user_text:
            return
        try:
            state = await self._brain.observe(user_text)
        except Exception as exc:
            logger.error("Interview-Backend nicht erreichbar: %s", exc)
            return
        await _publish_diagnose(self._room, state, self._brain.opening)

        # KLEBRIG aufsammeln: einmal erkannt bleibt erkannt (das Backend lässt Felder — v. a.
        # ``zweck`` — zwischendurch wieder wegfallen; ohne dies würde die Spinne nie voll). Das
        # betrifft NUR das Timing (ist genug da?), NIE die Werte — die kommen stets aus dem
        # aktuellen Backend-Stand, Korrekturen gewinnen also immer.
        diagnose = state.diagnose or {}
        self._seen.update(k for k in SPINNE_KEYS if diagnose.get(k))
        core_voll = all(k in self._seen for k in CORE_KEYS)
        spinne_voll = all(k in self._seen for k in SPINNE_KEYS)
        if state.ready:
            self._ready_turns += 1
        if core_voll:
            self._core_turns += 1
        logger.info(
            "Brain: seen=%s spinne_voll=%s ready=%s awaiting_confirmation=%s",
            sorted(self._seen), spinne_voll, state.ready, self._awaiting_confirmation,
        )

        # ── Bestätigungs-Schleife: wir haben zusammengefasst und warten auf das ausdrückliche „Go".
        if self._awaiting_confirmation:
            if self._is_affirmation(user_text):
                logger.info("Bestätigung erhalten → Match wird gestartet")
                self._awaiting_confirmation = False
                await self._run_match()
            else:
                # Korrektur/Ergänzung (z. B. „nein, online"): ist über observe() schon im Backend.
                # Erneut zusammenfassen und wieder um Bestätigung bitten — Schleife bis zum „Go".
                logger.info("Noch kein Go (Korrektur/Ergaenzung) - erneut zusammenfassen")
                await self._enter_confirmation()
            return

        # ── Genug erhoben? Dann NICHT automatisch matchen, sondern Zusammenfassung + GO einholen.
        # Expliziter Startpunkt (Steffen-Wunsch): erst nach Rückversicherung im Dialog rechnen.
        if spinne_voll or (state.ready and self._ready_turns >= 2):
            await self._enter_confirmation()
            return

        # ── Sonst ruhig weiter erheben (gezielt nach dem Fehlenden fragen).
        await self._guide_coach()

    async def _enter_confirmation(self) -> None:
        """Wechselt in die BESTÄTIGUNG: fasst das Verstandene zusammen und bittet um das
        ausdrückliche „Go", bevor gerechnet wird. Kein automatischer Match mehr."""
        self._awaiting_confirmation = True
        await self._set_phase("BESTÄTIGUNG", PHASE_BESTAETIGUNG)
        # Das Modell JETZT zusammenfassen + nachfragen lassen — es hat den Gesprächskontext, fasst
        # also natürlicher zusammen, als wir es aus (teils kodierten) Diagnose-Feldern könnten.
        await self._request_reply(
            "Fasse jetzt in zwei, drei ruhigen Sätzen zusammen, was du über die Situation "
            "verstanden hast — zu Zweck, Gruppengröße, verfügbarer Zeit, Setting "
            "(Präsenz/Online/Hybrid) und psychologischer Sicherheit. Stelle danach GENAU EINE "
            "einzige, klare Ja/Nein-Frage, ob du auf dieser Grundlage einen Vorschlag erstellen "
            "sollst — nicht zwei Fragen. Schlage selbst noch nichts vor."
        )

    async def _run_match(self) -> None:
        """Holt nach dem „Go" den echten String aus ``/api/match/``, spiegelt ihn ans Frontend
        und liest ihn vor. Phasenführung: VERDICHTUNG (überbrücken) → ABSCHLUSS (vorlesen, fertig)."""
        self._done = True
        # PHASE 2 — Verdichtung: Verhalten umschalten (keine Fragen mehr), dann ~60 s überbrücken.
        await self._set_phase("VERDICHTUNG", PHASE_VERDICHTUNG)
        await self._speak(
            "Wunderbar, danke dir — einen kleinen Moment, "
            "ich stelle euch jetzt einen passenden Vorschlag zusammen."
        )
        try:
            result = await self._brain.match()
        except Exception as exc:
            logger.error("Matchmaking fehlgeschlagen: %r", exc)
            # Nicht im Wartemodus einfrieren: zurück in die Erhebung, damit das Gespräch weitergeht.
            self._done = False
            self._awaiting_confirmation = False
            await self._set_phase("ERHEBUNG", PHASE_ERHEBUNG)
            await self._speak(
                "Entschuldige, beim Zusammenstellen ist gerade etwas schiefgegangen. "
                "Lass uns kurz weitermachen — magst du mir noch etwas zur Situation erzählen?"
            )
            return
        # Den grafischen String ZUERST ans Frontend spiegeln (das Kernergebnis) — unabhängig
        # davon, ob das Vorlesen klappt (so verhindert ein Sprach-Fehler nie den String).
        try:
            payload = json.dumps({"type": "result", "result": result}, ensure_ascii=False)
            await self._room.local_participant.publish_data(
                payload.encode("utf-8"), reliable=True, topic="result"
            )
        except Exception as exc:
            logger.warning("Ergebnis-Spiegelung ans Frontend fehlgeschlagen: %s", exc)
        # PHASE 3 — Abschluss: Verhalten auf „Job erledigt" umschalten, DANN den Vorschlag vorlesen.
        # allow_interruptions=False → der Agent liest den Begründungssatz KOMPLETT vor und wird von
        # der Server-VAD nicht mittendrin unterbrochen („Wagen fährt"). Test 2026-06-06: ohne dies
        # zerschoss ein VAD-Zucken das lange Vorlesen.
        await self._set_phase("ABSCHLUSS", PHASE_ABSCHLUSS)
        await self._speak(LSInterviewBrain.spoken_summary(result), allow_interruptions=False)

    @staticmethod
    def _is_affirmation(text: str) -> bool:
        """Erkennt ein ausdrückliches „Go". WORT-basiert (nicht Teilstring) — robust gegen
        STT-Varianten (die Spracherkennung machte aus „Ja" schon „Yeah"). Eine
        Verneinung/Einschränkung schlägt jede Zustimmung; im Zweifel FALSE (lieber kurz
        nachfragen als verfrüht rechnen)."""
        low = text.lower()
        for ch in ".,!?;:\"'„“”-—…":
            low = low.replace(ch, " ")
        words = set(low.split())
        if not words:
            return False
        verneinung = {"nein", "nicht", "falsch", "ne", "nee", "quatsch", "stopp", "stop",
                      "warte", "moment", "aber", "doch", "eigentlich", "noch"}
        if words & verneinung:
            return False
        zustimmung = {"ja", "jo", "joa", "joah", "jaa", "jaja", "jau", "jawohl", "jawoll",
                      "yeah", "yea", "yep", "yes", "jup", "jupp", "jepp", "klar", "genau",
                      "stimmt", "passt", "richtig", "korrekt", "perfekt", "gerne", "gern",
                      "okay", "ok", "mhm", "mhmm", "definitiv", "absolut", "exakt", "sicher",
                      "los", "mach", "machen", "gut", "super", "prima"}
        if words & zustimmung:
            return True
        phrasen = ("auf jeden", "leg los", "los geht", "passt so", "stimmt so", "mach mal",
                   "machen wir", "kannst du", "können wir", "sehr gut", "alles richtig",
                   "alles korrekt", "ist richtig", "ist korrekt")
        return any(p in low for p in phrasen)

    async def _set_phase(self, name: str, instructions: str) -> None:
        """Schaltet die Verhaltens-Leitplanken des Modells auf eine neue Phase um (ERHEBUNG →
        BESTÄTIGUNG → VERDICHTUNG → ABSCHLUSS). Im Realtime-Pfad ist die Instruktion das Lenkrad
        fürs Verhalten — ohne Umschalten bliebe das Modell im „immer weiter fragen"-Modus.
        Idempotent: ist die Phase schon aktiv, kein erneutes Update (sonst stockt der Stream).
        Wirft nie."""
        if name == self._phase:
            return
        try:
            await self.update_instructions(instructions)
            self._phase = name
            logger.info("Phase → %s", name)
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("Phasen-Instruktion (%s) konnte nicht gesetzt werden: %s", name, exc)

    @staticmethod
    async def _maybe(coro_fn, *args, **kwargs):
        """Ruft eine Coroutine mit optionalen kwargs auf; kennt die Version ein kwarg nicht
        (TypeError), wird es entfernt und erneut versucht. So können wir ``allow_interruptions``
        durchreichen, ohne bei älteren/abweichenden APIs zu brechen."""
        try:
            return await coro_fn(*args, **kwargs)
        except TypeError:
            kwargs.pop("allow_interruptions", None)
            return await coro_fn(*args, **kwargs)

    async def _request_reply(self, instructions: str, allow_interruptions: bool = True) -> None:
        """Lässt das Modell eine Antwort GENERIEREN (nicht festen Text vorlesen) — z. B. die
        Zusammenfassung in der Bestätigungs-Phase. Pfad-übergreifend über ``generate_reply``.
        Wirft nie."""
        try:
            await self._maybe(self.session.generate_reply, instructions=instructions,
                              allow_interruptions=allow_interruptions)
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("generate_reply (Zusammenfassung) nicht möglich: %s", exc)

    async def _speak(self, text: str, allow_interruptions: bool = True) -> None:
        """Sprachausgabe **pfad-sicher**: die Mistral-Pipeline nutzt ``session.say`` (TTS);
        die OpenAI-RealtimeSession unterstützt kein ``say()`` → dort über ``generate_reply``
        vorlesen. ``allow_interruptions=False`` lässt den Agenten AUSREDEN (Server-VAD unterbricht
        ihn dann nicht) — wichtig fürs vollständige Vorlesen des Vorschlags. Wirft NIE — die
        Stimme ist nie kritischer als das (separat gespiegelte) Ergebnis."""
        try:
            await self._maybe(self.session.say, text, allow_interruptions=allow_interruptions)
            return
        except Exception:
            pass
        try:
            await self._maybe(
                self.session.generate_reply,
                instructions="Sprich den folgenden Text auf Deutsch ruhig und vollständig aus, "
                f"ohne etwas hinzuzufügen oder zu verändern:\n{text}",
                allow_interruptions=allow_interruptions,
            )
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("Sprachausgabe nicht möglich: %s", exc)

    async def _guide_coach(self) -> None:
        """Spielt dem Sprachmodell zurück, welche Spinnen-Angaben noch fehlen (gemessen am
        KLEBRIGEN ``self._seen`` — nicht am flackernden Snapshot), damit es **gezielt + ruhig**
        danach fragt statt blind zu raten. Aktualisiert laufend die Instruktionen."""
        fehlend = [SPINNE_LABELS[k] for k in SPINNE_KEYS if k not in self._seen]
        if not fehlend:
            return
        # Nur aktualisieren, wenn sich die fehlenden Felder geändert haben — sonst würde jedes
        # Instruktions-Update den Realtime-Stream kurz unterbrechen (das „Stocken").
        key = ",".join(k for k in SPINNE_KEYS if k not in self._seen)
        if key == self._last_guidance:
            return
        self._last_guidance = key
        try:
            await self.update_instructions(
                COACH_INSTRUCTIONS
                + "\n\nDem System fehlen für die Empfehlung noch diese Angaben. Frage natürlich, "
                "freundlich und nacheinander gezielt danach — immer nur EINE Frage zur Zeit: "
                + "; ".join(fehlend)
            )
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("Coach-Guidance konnte nicht gesetzt werden: %s", exc)


def _build_session(tier: str) -> AgentSession:
    """Baut die Sitzung passend zur Souveränitätsstufe.

    * ``us`` 🇺🇸 — **OpenAI Realtime**: ein Sprache↔Sprache-Modell mit server-seitiger
      Sprechpausen-Erkennung → niedrigste Latenz, glattes Unterbrechen (keine getrennten
      STT/TTS-Glieder). Das Gehirn (``/api/interview/``) bleibt über ``on_user_turn_completed``
      angebunden (die Transkription liefert das Realtime-Modell selbst mit).
    * ``eu`` 🇪🇺 (Default) — **Mistral-Pipeline**: Voxtral-STT → Mistral-LLM → Voxtral-TTS.
    """
    if tier == "us":
        logger.info("US-Pfad: OpenAI Realtime (Sprache↔Sprache)")
        rt_kwargs: dict = {
            # Nutzer-Transkription AKTIVIEREN (Default ist aus): nur so kommt der Text ans
            # Gehirn (/api/interview/) → Spinne füllt sich + echter Match (kein Halluzinieren).
            "input_audio_transcription": {
                "model": os.environ.get("VOICE_REALTIME_STT", "gpt-4o-mini-transcribe"),
                "language": "de",
            },
        }
        # Sprechtempo nur ändern, wenn ausdrücklich per ENV gewünscht — sonst normal (1.0).
        # Ruhe kommt über die Prompt-Anweisung; speed 0.9 + Prompt zusammen war zu langsam.
        rt_speed = os.environ.get("VOICE_REALTIME_SPEED", "").strip()
        if rt_speed:
            rt_kwargs["speed"] = float(rt_speed)
        rt_voice = os.environ.get("VOICE_REALTIME_VOICE", "").strip()
        if rt_voice:
            rt_kwargs["voice"] = rt_voice
        rt_model = os.environ.get("VOICE_REALTIME_MODEL", "").strip()
        if rt_model:
            rt_kwargs["model"] = rt_model
        return AgentSession(llm=openai.realtime.RealtimeModel(**rt_kwargs))

    logger.info("EU-Pfad: Mistral-Pipeline (Voxtral-STT → Mistral-LLM → Voxtral-TTS)")
    # Eine VAD-Instanz für Session UND Realtime-STT (das Voxtral-Realtime-STT hat kein
    # server-seitiges Endpointing und nutzt die VAD, um die Audio-Pakete zu flushen).
    vad = silero.VAD.load()
    return AgentSession(
        stt=mistralai.STT(model=STT_MODEL, vad=vad),
        # LLM über Mistrals OpenAI-kompatiblen Endpunkt (zuverlässige Standard-Chat-API).
        # Der native mistralai-LLM nutzt die „conversations"-Beta-API und schlug fehl
        # (HTTPValidationError: inputs is required) — verifiziert 2026-06-06.
        llm=openai.LLM(
            model=LLM_MODEL,
            base_url="https://api.mistral.ai/v1",
            api_key=os.environ.get("MISTRAL_API_KEY", ""),
        ),
        tts=_build_tts(),        # deutsche Stimme via Voice-Cloning (ref_audio), s. _build_tts
        vad=vad,                 # offenes Mikro / automatische Sprechpausen-Erkennung
    )


async def entrypoint(ctx: agents.JobContext) -> None:
    """Pro Raum: Sitzung je Souveränitätsstufe. Die gewählte Stufe steht in den
    Teilnehmer-Metadaten des LiveKit-Tokens (``{"tier": "us"|"eu"|"sov"}``)."""
    await ctx.connect()
    brain = LSInterviewBrain(BACKEND_URL)

    # Stufe aus den Teilnehmer-Metadaten lesen (Token trägt {"tier": ...}); Default eu.
    tier = "eu"
    try:
        participant = await ctx.wait_for_participant()
        if participant and participant.metadata:
            tier = json.loads(participant.metadata).get("tier", "eu")
    except Exception as exc:  # pragma: no cover - reine Robustheit
        logger.warning("Stufe nicht lesbar (%r) — nutze eu.", exc)
    logger.info("Sprach-Sitzung: Stufe %s", tier)

    session = _build_session(tier)
    coach = LSCoach(ctx.room, brain)

    # Realtime (us) liefert die Nutzer-Transkription NICHT über on_user_turn_completed,
    # sondern über das Session-Event „user_input_transcribed" — daran hängen wir das Gehirn,
    # damit sich die Spinne füllt und am Ende der echte Match kommt.
    if tier == "us":
        def _on_user_transcript(ev) -> None:
            transcript = getattr(ev, "transcript", "") or ""
            is_final = getattr(ev, "is_final", False)
            # Diagnose-Logging: Taucht hier die EIGENE Begrüßung als „Nutzer"-Text auf, ist es
            # Echo (Lautsprecher → Mikro) — dann brauchen wir Echo-Unterdrückung, nicht Code.
            logger.info("Transkript (final=%s): %r", is_final, transcript[:120])
            if is_final and transcript.strip():
                asyncio.create_task(coach.process_user_text(transcript))
        session.on("user_input_transcribed", _on_user_transcript)

    # Begrüßung erfolgt in ``LSCoach.on_enter`` (kein Race nach session.start mehr).
    await session.start(room=ctx.room, agent=coach)


if __name__ == "__main__":
    # Eigener Port für den internen Worker-HTTP-Server (8081 ist auf dem Host belegt).
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            port=int(os.environ.get("AGENT_HTTP_PORT", "8099")),
        )
    )
