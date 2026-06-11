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
from livekit import agents, api
from livekit.agents import Agent, AgentSession, room_io
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

# ── Kostenschutz (Steffen 2026-06-09): Eine Sprach-Sitzung wird pro Minute Verbindung abgerechnet
# (EU: Voxtral-STT läuft durchgehend; US: OpenAI Realtime ist ein teurer Dauer-Stream). Damit eine
# vergessene/offen gelassene Sitzung nicht stundenlang Kosten verursacht, schaltet sich der Agent
# selbst ab: nach dem Ergebnis (kurzes Nachfrage-Fenster), bei Inaktivität, und ein hartes Zeitlimit
# als absolute Obergrenze. Alle Werte per ENV justierbar.
INACTIVITY_TIMEOUT_S = float(os.environ.get("VOICE_INACTIVITY_TIMEOUT", "180"))  # Stille bis Abschaltung
POST_RESULT_GRACE_S = float(os.environ.get("VOICE_POST_RESULT_GRACE", "60"))      # Nachfrage-Fenster nach dem Ergebnis
MAX_SESSION_S = float(os.environ.get("VOICE_MAX_SESSION", "1200"))                # harte Obergrenze je Sitzung
# Abschied + Session-Abschluss dürfen NIE unbegrenzt blockieren (sonst wird die Raum-Löschung nie
# erreicht und die Sitzung läuft weiter — genau der Hänger im Test 2026-06-11: ``session.say`` mit
# ``allow_interruptions=False`` wartete nach dem stillen Nutzer ewig aufs Playout-Ende). Jede Stufe
# bekommt darum eine Obergrenze; danach geht es zwingend weiter zur serverseitigen Raum-Löschung.
GOODBYE_TIMEOUT_S = float(os.environ.get("VOICE_GOODBYE_TIMEOUT", "20"))           # max. Zeit für den Abschiedssatz
SHUTDOWN_STEP_TIMEOUT_S = float(os.environ.get("VOICE_SHUTDOWN_STEP_TIMEOUT", "10"))  # max. je drain/aclose

# Feste Abschiedssätze je Abschalt-Grund (deterministisch vorgelesen, nicht vom Modell generiert).
GOODBYE_TEXTS = {
    "post_result": (
        "Ich wünsche euch viel Erfolg mit eurem Vorhaben. Ich beende unser Gespräch jetzt — "
        "du kannst jederzeit ein neues starten. Bis bald!"
    ),
    "inactivity": (
        "Ich habe eine Weile nichts mehr gehört, darum beende ich das Gespräch jetzt, um Ressourcen "
        "zu schonen. Melde dich gern jederzeit wieder — bis bald!"
    ),
    "max_session": (
        "Wir sind jetzt schon eine ganze Weile zusammen, darum beende ich das Gespräch an dieser "
        "Stelle. Du kannst jederzeit ein neues starten. Bis bald!"
    ),
}

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
    # THEMEN-LEITPLANKE (Steffen 2026-06-09): hält den Sprachkanal beim Thema (auch Kostenschutz —
    # verhindert Missbrauch als allgemeiner Chatbot). Bewusst in der gemeinsamen Persona, damit sie
    # in ALLEN Phasen und BEIDEN Pfaden greift (US nur additiv ergänzt, Tag voice-vorzeigbar-…).
    "WICHTIG — bleib beim Thema: Du hilfst AUSSCHLIESSLICH bei der Gruppensituation, der Moderation "
    "und der Auswahl passender Liberating Structures (im weitesten Sinne rund um Workshops, Teams "
    "und Zusammenarbeit). Auf klar themenfremde Anliegen (z. B. Kochrezepte, Allgemeinwissen, "
    "Politik, Programmierung, private Plauderei) gehst du NICHT ein: Sag freundlich und kurz, dass "
    "du dafür nicht da bist, und lenke zurück zur Gruppensituation. Erfinde keine Inhalte außerhalb "
    "dieses Themas. "
)

# PHASE 1 — ERHEBUNG: nur zuhören & gezielt fragen, nie selbst vorschlagen.
PHASE_ERHEBUNG = COACH_PERSONA + (
    "Ihr seid am ANFANG des Gesprächs. Du führst ein lockeres Gespräch, um die Gruppensituation "
    "zu verstehen: Anlass/Situation, , Ziel, Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid), "
    "psychologische Sicherheit, Schwerpunkt. Lass die Person AUSREDEN und unterbrich NICHT — warte, "
    "bis sie wirklich fertig ist. Reagiere dann ZUERST kurz und warm auf das gerade Gesagte (ein "
    "Satz, der zeigt: du hast zugehört), und stelle ERST DANN deine nächste Frage — immer nur EINE "
    "kurze, natürliche Frage zur Zeit und leite Damit über auf den nächsten Aspekt, den du erfragen möchtest. "
    "GANZ WICHTIG — halte dich strikt daran: Du schlägst in dieser Phase NIEMALS selbst eine "
    "Methode, Übung oder Lösung vor, du nennst KEINE Liberating Structures und du moderierst "
    "NICHTS. Auch wenn du glaubst, schon genug zu wissen: präsentiere KEINE Lösung. Deine einzige "
    "Aufgabe ist jetzt ZUHÖREN und FRAGEN. Den konkreten Vorschlag erstellt allein das System — "
    "du fragst so lange ruhig weiter, bis das System dir das Signal gibt. "
    "Sage AUSSERDEM niemals Sätze wie „ich weiß genug“, „ich habe alles verstanden“ oder „ich "
    "gebe dir jetzt eine Empfehlung“. OB genug Information vorhanden ist, entscheidet allein das "
    "System — nicht du. Bis dahin fragst du einfach ruhig und freundlich weiter."
)

# Startinstruktion = Erhebung (Alias, hält bestehende Verweise gültig). PHASE_ERHEBUNG = der
# eingefrorene 🇺🇸 US-Stand.
COACH_INSTRUCTIONS = PHASE_ERHEBUNG

# 🇪🇺 EU/Mistral — eigene Erhebung: ALLE sieben Aspekte ausdrücklich erfragen, BEVOR die
# Zusammenfassung kommt (Steffen 2026-06-07: Mistral fasste zu früh zusammen, obwohl noch nicht
# alle Aspekte wirklich erfragt waren). Nichts annehmen, nur weil es sich ableiten ließe.
PHASE_ERHEBUNG_EU = PHASE_ERHEBUNG + (
    "\n\nGANZ WICHTIG für die Vollständigkeit: Du brauchst zu ALLEN SIEBEN Aspekten eine klare, "
    "ausdrücklich von der Person genannte Antwort: Anlass/Situation, Ziel, Methode/Schwerpunkt, "
    "Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid) und psychologische Sicherheit. "
    "Nimm einen Aspekt NICHT als gegeben an, nur weil er sich vielleicht aus der Schilderung "
    "ableiten ließe — frage im Zweifel kurz nach. Frage die noch offenen Aspekte gezielt ab, EINEN "
    "nach dem anderen. Fasse ERST ZUSAMMEN, wenn ALLE SIEBEN Aspekte ausdrücklich erfragt und "
    "beantwortet sind — solange auch nur EINER offen ist, fasse NICHTS zusammen. "
    "BESONDERS der Zweck/Schwerpunkt ist eine EIGENE, ausdrückliche Frage: Verwechsle ihn NICHT mit "
    "dem Ziel und setze ihn NICHT als bekannt voraus, nur weil ein Ziel genannt wurde. Frage den "
    "Schwerpunkt immer eigens (offenlegen / analysieren / entscheiden / planen), bevor du zusammenfasst."
)

# PHASE 1b — BESTÄTIGUNG: alle Punkte gehört → ZUSAMMENFASSEN und auf das ausdrückliche „Go"
# warten. Wie ein echter Berater: erst rückversichern, dann erst rechnen. Der eigentliche Start
# des Strings steuert UNSER Code (Erkennung der Bestätigung), nicht das Modell.
#
# AB 2026-06-07 PFAD-GETRENNT (Steffen): Der 🇺🇸-US-Stand ist „vorzeigbar" (Tag
# `voice-vorzeigbar-2026-06-07`) und wird EINGEFROREN — Mistral/EU bekommt eigenes Feintuning.
# Verschiedene Modelle = verschiedene Instruktionstreue (GPT-Realtime folgt dem US-Prompt brav;
# mistral-small fragte „stimmt das so" nach JEDEM Punkt → verfrühter Start). Gelerntes übertragen
# wir gezielt, aber eine EU-Änderung darf US NIE berühren. Auswahl je Stufe in LSCoach.__init__.

# 🇺🇸 US — EINGEFROREN (exakt wie im Tag voice-vorzeigbar-2026-06-07). NICHT ohne ausdrückliche
# Freigabe ändern.
PHASE_BESTAETIGUNG_US = COACH_PERSONA + (
    "Du hast jetzt zu allen wichtigen Punkten etwas gehört. BEVOR irgendein Vorschlag erstellt "
    "wird, vergewissere dich sorgfältig. Gehe dafür die SIEBEN Punkte EINZELN durch: Anlass/"
    "Situation, das Ziel (was am Ende erreicht sein soll), den Zweck/Schwerpunkt, Gruppengröße, "
    "verfügbare Zeit, Setting (Präsenz/Online/Hybrid) und psychologische Sicherheit. "
    "Sage der Person zu jedem Punkt kurz, was du verstanden "
    "hast. Ist ein Punkt unklar, vage oder wurde er NICHT ausdrücklich genannt, frage GEZIELT "
    "danach, statt zu raten — lieber einmal mehr nachfragen. "
    "Erst wenn alle fünf Punkte klar und ausdrücklich sind, stelle GENAU EINE einzige, klare "
    "Ja/Nein-Frage, ob du auf dieser Grundlage den Vorschlag erstellen sollst (z. B. „Passt das "
    "so für dich und soll ich dir jetzt einen Vorschlag zusammenstellen?“).  "
    "Schlage selbst KEINE Methode vor und nenne KEINE Liberating Structures. Wenn die Person "
    "etwas korrigiert oder ergänzt, nimm es dankbar auf und spiegel ihm was du verstanden hast. "
    "Erst wenn die Person ausdrücklich zustimmt, geht es weiter."
)

# 🇪🇺 EU/Mistral — eigenes Feintuning: EIN zusammenhängender Rückblick aller sieben, KEINE Frage
# pro Punkt, GENAU EINE Schlussfrage (mistral-small fragte sonst nach jedem Punkt → verfrühter Start).
PHASE_BESTAETIGUNG_EU = COACH_PERSONA + (
    "Du hast jetzt zu allen wichtigen Punkten etwas gehört. Leite mit einem klaren SIGNALSATZ ein, "
    "dass du JETZT zusammenfasst (z. B. „Gut, dann fasse ich einmal zusammen, was ich verstanden "
    "habe:“) — damit die Person merkt, dass die Abschluss-Zusammenfassung beginnt. Gib ihr dann in "
    "EINEM einzigen, zusammenhängenden, ruhigen Rückblick wieder, was du verstanden hast — ALLE "
    "sieben Punkte nacheinander in wenigen Sätzen: Anlass/Situation, das Ziel, den Zweck/Schwerpunkt, "
    "Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid) und psychologische Sicherheit. "
    "GANZ WICHTIG: Stelle WÄHREND dieser Aufzählung KEINE Zwischenfragen. Frage NICHT nach jedem "
    "einzelnen Punkt „stimmt das so“ — das verwirrt. Zähle erst ALLE sieben Punkte am Stück auf. "
    "ERST WENN du alle sieben genannt hast, stellst du GENAU EINE einzige Ja/Nein-Frage, die die "
    "FOLGE klar benennt — dass ein „Ja“ JETZT den Vorschlag startet (z. B. „Wenn das so passt, "
    "stelle ich dir jetzt auf dieser Grundlage den Vorschlag zusammen. Soll ich? Sag Ja zum Starten "
    "— oder sag mir, was noch fehlt oder anders ist.“). Diese eine Schlussfrage ist die EINZIGE Frage "
    "in deiner Antwort. "
    "Schlage selbst KEINE Methode vor und nenne KEINE Liberating Structures. Wenn die Person "
    "danach etwas korrigiert oder ergänzt, nimm es dankbar auf und gib anschließend wieder den "
    "ganzen Rückblick aller sieben Punkte mit einer einzigen Schlussfrage. Erst wenn die Person "
    "auf diese Schlussfrage ausdrücklich zustimmt, geht es weiter."
)

# Zusammenfassungs-Auftrag (für das aktive Vorlesen in _enter_confirmation) — ebenfalls pfad-getrennt.
SUMMARY_INSTR_US = (
    "Gehe jetzt ruhig die sieben Punkte EINZELN durch und sage zu jedem kurz, was du "
    "verstanden hast: Anlass/Situation, das Ziel, den Zweck/Schwerpunkt, Gruppengröße, "
    "verfügbare Zeit, Setting (Präsenz/Online/Hybrid) und psychologische Sicherheit. "
    "Wurde ein Punkt nicht ausdrücklich genannt oder ist er unklar, frage gezielt danach, "
    "statt zu raten. "
    "Erst wenn alle sieben klar sind, stelle GENAU EINE einzige, klare Ja/Nein-Frage, ob du "
    "auf dieser Grundlage einen Vorschlag erstellen sollst. Schlage selbst noch nichts vor."
)
SUMMARY_INSTR_EU = (
    "Leite jetzt DEUTLICH ein, dass du zusammenfasst — beginne mit einem klaren Signalsatz wie "
    "„Gut, dann fasse ich einmal zusammen, was ich verstanden habe:“, damit die Person merkt, dass "
    "jetzt die ABSCHLUSS-Zusammenfassung kommt. Gib dann in EINEM zusammenhängenden, ruhigen "
    "Rückblick ALLE sieben Punkte nacheinander in wenigen Sätzen wieder: Anlass/Situation, das Ziel, "
    "den Zweck/Schwerpunkt, Gruppengröße, verfügbare Zeit, Setting (Präsenz/Online/Hybrid) und "
    "psychologische Sicherheit. Stelle WÄHREND der Aufzählung KEINE Zwischenfragen. "
    "Schließe mit GENAU EINER unmissverständlichen Ja/Nein-Frage, die die FOLGE klar benennt: dass "
    "du bei „Ja“ JETZT den Vorschlag erstellst — z. B. „Wenn das so passt, stelle ich dir auf dieser "
    "Grundlage jetzt den Vorschlag zusammen. Soll ich? Sag Ja zum Starten — oder sag mir, was noch "
    "fehlt oder anders ist.“ Schlage selbst noch nichts vor."
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
SPINNE_KEYS = ("ziel_text", "zweck", "gruppengroesse", "zeitbudget", "setting", "psychologische_sicherheit")
# KERN-Dimensionen = die zuverlässig erkannten. ``psychologische_sicherheit`` wird vom Backend
# chronisch NICHT sauber erkannt (Test 2026-06-06: über eine ganze Sitzung nie gefüllt, ready
# blieb False). Daher darf sie den Match NICHT blockieren: sind die Kern-4 da, fragt der Coach
# noch kurz nach Sicherheit und löst dann auch ohne sie aus (s. Trigger in process_user_text).
CORE_KEYS = ("zweck", "gruppengroesse", "zeitbudget", "setting")
# 🇪🇺 EU — „weiche" Dimensionen: Schwerpunkt und psychologische Sicherheit leitet das Backend gern
# aus dem Kontext ab, statt sie zu erfragen. Wurde so eine Dimension nur INTERPRETIERT (nie aktiv
# erfragt), lässt der Coach sie vor der Zusammenfassung einzeln rückversichern (Steffen 2026-06-07:
# „habe ich richtig verstanden, dass …?"). Die „harten" Fakten (Größe/Zeit/Setting) bleiben unberührt.
EU_SOFT_DIMS = ("zweck", "psychologische_sicherheit")
SPINNE_LABELS = {
    "ziel_text": "das Ziel — was am Ende konkret anders oder erreicht sein soll",
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

    def __init__(self, ctx, room, brain: LSInterviewBrain, tier: str = "eu"):
        # Erhebungs-Instruktion pfad-getrennt: US eingefroren, EU erfragt alle 7 ausdrücklich.
        erhebung_instr = PHASE_ERHEBUNG if tier == "us" else PHASE_ERHEBUNG_EU
        super().__init__(instructions=erhebung_instr)
        self._ctx = ctx   # JobContext: für die serverseitige Raum-Löschung beim Abschalten (Kostenschutz)
        self._room = room
        self._brain = brain
        self._tier = tier
        self._erhebung_instr = erhebung_instr
        self._done = False
        self._last_guidance = None  # zuletzt gesetzte Coach-Guidance (vermeidet unnötige Updates)
        self._ready_turns = 0       # wie oft das Backend „ready" meldete (Anti-Hänger)
        self._seen: set[str] = set()  # je erkannte Dimensionen — KLEBRIG (gegen Backend-Flackern)
        self._diag: dict = {}         # gemergte Diagnose-WERTE (klebrig; neue Werte überschreiben)
        self._core_turns = 0        # Äußerungen, seit die Kern-4 vollständig sind (Diagnose)
        self._phase = "ERHEBUNG"    # aktuelle Verhaltensphase (verhindert doppelte Instruktions-Updates)
        self._awaiting_confirmation = False  # True = zusammengefasst, wartet auf das ausdrückliche „Go"
        self._erfragt: set[str] = set()  # 🇪🇺 EU: Dimensionen, die der Coach AKTIV erfragt hat (vs. nur interpretiert)
        self._suppress_turn_hook = False  # im US/Realtime-Pfad True (Transkript kommt übers Event)
        # Kostenschutz-Timer (s. Konstanten oben): Inaktivitäts-/Nachfrage-Wächter + harter Backstop.
        self._inactivity_task: asyncio.Task | None = None
        self._maxsession_task: asyncio.Task | None = None
        self._shutting_down = False  # idempotenter Abschalt-Guard
        # PFAD-GETRENNTE Bestätigungs-Prompts (ab 2026-06-07): US eingefroren, EU eigenes Feintuning.
        if tier == "us":
            self._bestaetigung_instr = PHASE_BESTAETIGUNG_US
            self._summary_instr = SUMMARY_INSTR_US
        else:  # eu / sov
            self._bestaetigung_instr = PHASE_BESTAETIGUNG_EU
            self._summary_instr = SUMMARY_INSTR_EU

    async def on_enter(self) -> None:  # noqa: D401
        """Wird vom Framework aufgerufen, sobald der Agent in der Sitzung AKTIV ist — der richtige
        Zeitpunkt für die Begrüßung. (Früher direkt nach ``session.start`` aufgerufen → Race:
        die Sitzung war noch nicht bereit, die erste Antwort wurde abgeschnitten und neu
        ausgelöst → Start-Loop. ``on_enter`` vermeidet das.)"""
        logger.info("on_enter: Begrüßung wird gesendet")
        # Kostenschutz scharf schalten: harter Backstop (einmalig) + Inaktivitäts-Wächter.
        self._arm_max_session()
        self._bump_activity()
        await self._request_reply(
            "Begrüße die Nutzerin kurz und herzlich und frage offen nach der Gruppensituation. "
            "Sage genau EINE Begrüßung und EINE offene Frage — danach hörst du zu."
        )

    async def on_user_turn_completed(self, turn_ctx, new_message) -> None:  # noqa: D401
        """Pipeline-Pfad (eu/sov): nach jeder fertigen Nutzer-Äußerung das Gehirn füttern.

        Im US/Realtime-Pfad ist dieser Hook ABGESCHALTET (``_suppress_turn_hook``) — dort kommt
        die Transkription über das ``user_input_transcribed``-Event. Sonst würde dieser Hook
        zusätzlich feuern und, weil ``text_content`` im Realtime oft leer ist, früher auf
        ``str(new_message)`` zurückfallen — das schrieb die Objekt-Repr (``id='item_…'``) als
        „Situation" ins Gehirn (Bug 2026-06-06)."""
        if self._suppress_turn_hook:
            return
        user_text = getattr(new_message, "text_content", None)
        if not user_text:  # NIE auf str(new_message) zurückfallen (das ist die Objekt-Repr).
            return
        await self.process_user_text(user_text)

    async def process_user_text(self, user_text: str) -> None:
        """Gemeinsame Gehirn-Logik **beider** Pfade: Backend fragen, Diagnose spiegeln (Spinne),
        und sobald genug bekannt ist den ECHTEN Match holen + vorlesen.

        Aufgerufen aus ``on_user_turn_completed`` (EU-Pipeline) **und** aus dem
        ``user_input_transcribed``-Event (US-Realtime) — denn im Realtime-Modus liefert
        livekit die Nutzer-Transkription über dieses Event, nicht über den Turn-Hook.
        """
        # Kostenschutz: JEDE Nutzer-Äußerung setzt den Inaktivitäts-/Nachfrage-Wächter zurück —
        # bewusst VOR dem ``_done``-Check, damit auch Rückfragen im Nachfrage-Fenster (Phase
        # ABSCHLUSS, wo ``_done`` True ist) das Fenster verlängern. Während der VERDICHTUNG ist der
        # Wächter pausiert (``_bump_activity`` ignoriert diese Phase).
        self._bump_activity()
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
        # DIAGNOSE-PROTOKOLL (temporär): exakt zeigen, WAS gesagt wurde und WAS das Backend daraus
        # extrahiert hat — so sehen wir, an welcher Dimension die Identifikation hakt (z. B. fehlende
        # Gruppengröße), statt zu raten.
        logger.info("EU-Input: text=%r → backend_diagnose=%s ready=%s",
                    user_text[:160], state.diagnose, state.ready)
        # KLEBRIG + KORREKTUR-FEST mergen: einmal erkannte Werte bleiben (das Backend lässt Felder
        # zwischendurch wegfallen → sonst flackert die Spinne, v. a. die psychologische Sicherheit).
        # NEUE, nicht-leere Werte ÜBERSCHREIBEN den alten — so gewinnen echte Korrekturen weiterhin.
        prev_diag = dict(self._diag)
        for k, v in (state.diagnose or {}).items():
            if v not in (None, "", [], {}):
                self._diag[k] = v
        diag_changed = self._diag != prev_diag  # kam durch diese Äußerung ein neuer/geänderter Wert?
        diagnose = self._diag
        # Anzeige (Spinne) UND Gehirn-Gate aus dem gemergten Stand speisen (keine Flacker-Verluste).
        # state ist brain.state → so nutzt auch der spätere Match denselben gemergten Stand.
        state.diagnose = dict(self._diag)
        # Mittelpunkt-Beschriftung: bevorzugt die SEMANTISCHE Anlass-Benennung des Backends
        # (EU-Prompt liefert ``anlass``); fehlt sie (z. B. US-Pfad oder noch früh), erster Satz.
        anlass_label = self._diag.get("anlass") or self._brain.opening
        await _publish_diagnose(self._room, state, anlass_label)
        self._seen = set(k for k in SPINNE_KEYS if self._diag.get(k))
        core_voll = all(k in self._seen for k in CORE_KEYS)
        spinne_voll = all(k in self._seen for k in SPINNE_KEYS)
        if state.ready:
            self._ready_turns += 1
        if core_voll:
            self._core_turns += 1
        logger.info(
            "Brain: seen=%s spinne_voll=%s ready=%s awaiting_confirmation=%s | situation=%r ziel=%r",
            sorted(self._seen), spinne_voll, state.ready, self._awaiting_confirmation,
            self._brain.opening[:50], (diagnose.get("ziel_text") or "")[:50],
        )

        # ── Bestätigungs-Schleife: wir haben zusammengefasst und warten auf das ausdrückliche „Go".
        # Die Person antwortet auf eine Ja/Nein-Frage. Die Spracherkennung verstümmelt kurze
        # Bestätigungen oft („Ja" → „Yeah"/„On va"/„Hello"). Darum: Antwort gilt als GO, ES SEI
        # DENN sie sieht nach einer KORREKTUR aus (Verneinung, ein Dimensions-Wert wie „online",
        # oder eine Zahl). So zählt jedes „irgendwie ja", echte Korrekturen aber nicht.
        if self._awaiting_confirmation:
            if self._tier == "us":
                # 🇺🇸 US — EINGEFROREN: unveränderte Bestätigungs-Logik (nicht anfassen).
                if self._is_correction(user_text):
                    logger.info("Korrektur erkannt (%r) → erneut zusammenfassen", user_text[:60])
                    await self._enter_confirmation()
                elif self._is_affirmation(user_text):
                    logger.info("Go erkannt (%r) → Match wird gestartet", user_text[:60])
                    self._awaiting_confirmation = False
                    await self._run_match()
                else:
                    # Unklare/verstümmelte Antwort (die Spracherkennung macht aus „okay" schon mal
                    # „добре"): NIEMALS einfach starten. Lieber um ein klares Ja/Nein bitten.
                    logger.info("Unklar (%r) → klares Ja/Nein erbitten", user_text[:60])
                    await self._ask_confirm_again()
                return
            # 🇪🇺 EU — Endlosschleife vermeiden: Bei „Nein"/unklar OHNE neuen Wert NICHT stur dieselbe
            # Zusammenfassung wiederholen, sondern offen nach der gewünschten Änderung fragen.
            if self._is_affirmation(user_text):
                logger.info("Go erkannt (%r) → Match wird gestartet", user_text[:60])
                self._awaiting_confirmation = False
                await self._run_match()
            elif self._is_correction(user_text) and diag_changed:
                # Echte Korrektur MIT neuem/geändertem Wert → aktualisierte Zusammenfassung.
                logger.info("Korrektur mit neuem Wert (%r) → erneut zusammenfassen", user_text[:60])
                await self._enter_confirmation()
            else:
                # Verneinung/unklar OHNE neuen Wert (oder reine Meta-Aussage wie „du hast X nicht
                # gefragt"): offen fragen, WAS geändert/ergänzt werden soll (statt zu wiederholen).
                logger.info("Kein Go, kein neuer Wert (%r) → offen nach Änderung fragen", user_text[:60])
                await self._ask_what_to_change()
            return

        # ── Genug erhoben? Dann NICHT automatisch matchen, sondern Zusammenfassung + GO einholen.
        # Expliziter Startpunkt (Steffen-Wunsch): erst nach Rückversicherung im Dialog rechnen.
        # 🇺🇸 US (eingefroren): volle Spinne ODER Backend-„ready"-Fallback.
        # 🇪🇺 EU: STRENGER — erst zusammenfassen, wenn wirklich alle sieben Aspekte da sind
        # (Anlass/Situation + die sechs Dimensionen); KEIN ready-Fallback (bei Mistral unzuverlässig
        # → führte zu verfrühten Zusammenfassungen, obwohl noch nicht alles erfragt war).
        if self._tier == "us":
            # 🇺🇸 US (eingefroren): volle Spinne ODER ready-Fallback → zusammenfassen.
            if spinne_voll or (state.ready and self._ready_turns >= 2):
                await self._enter_confirmation()
                return
        else:
            # 🇪🇺 EU: alle sechs Dimensionen + Anlass da. BEVOR zusammengefasst wird, jede „weiche"
            # Dimension (Schwerpunkt, psychologische Sicherheit), die das Backend nur INTERPRETIERT
            # hat (= nie aktiv erfragt → nicht in ``self._erfragt``), einzeln rückversichern
            # („Habe ich richtig verstanden, dass …?"). So wird nichts still unterstellt (Steffen).
            if spinne_voll and bool(self._brain.opening):
                interpretiert = [k for k in EU_SOFT_DIMS
                                 if k in self._seen and k not in self._erfragt]
                if interpretiert:
                    key = interpretiert[0]
                    self._erfragt.add(key)  # gilt nach der Rückversicherung als geklärt
                    await self._bestaetige_dimension(key)
                    return
                await self._enter_confirmation()
                return

        # ── Sonst ruhig weiter erheben (gezielt nach dem Fehlenden fragen).
        await self._guide_coach()

    async def _enter_confirmation(self) -> None:
        """Wechselt in die BESTÄTIGUNG: fasst das Verstandene zusammen und bittet um das
        ausdrückliche „Go", bevor gerechnet wird. Kein automatischer Match mehr."""
        self._awaiting_confirmation = True
        # Pfad-getrennt: US nutzt den eingefrorenen Prompt, EU/sov das eigene Feintuning.
        await self._set_phase("BESTÄTIGUNG", self._bestaetigung_instr)
        # Das Modell JETZT zusammenfassen + nachfragen lassen — es hat den Gesprächskontext, fasst
        # also natürlicher zusammen, als wir es aus (teils kodierten) Diagnose-Feldern könnten.
        await self._request_reply(self._summary_instr)

    async def _ask_confirm_again(self) -> None:
        """Bei unklarer/verstümmelter Antwort kurz um ein klares Ja oder Nein bitten — OHNE die
        ganze Zusammenfassung zu wiederholen. Bleibt in der Bestätigungsphase (startet nie von
        selbst)."""
        await self._request_reply(
            "Du hast die Antwort gerade nicht eindeutig verstanden. Frage kurz und freundlich "
            "nach, ob du auf der eben besprochenen Grundlage einen Vorschlag erstellen sollst, "
            "und bitte um ein klares Ja oder Nein. Fasse NICHT erneut alles zusammen — stelle nur "
            "diese eine kurze Frage."
        )

    async def _bestaetige_dimension(self, key: str) -> None:
        """🇪🇺 EU: Versichert sich EINZELN bei einer „weichen" Dimension, die das Backend nur aus dem
        Kontext ABGELEITET hat (statt sie zu erfragen) — als freundliche Rückfrage „Habe ich richtig
        verstanden, dass …?" (Steffen 2026-06-07: Interpretiertes nicht still unterstellen, sondern
        je einzeln bestätigen lassen). Genau EINE Frage; bleibt in der Erhebung (kein Auto-Start).
        Korrigiert die Person, fließt der neue Wert über ``observe`` zurück in die Diagnose."""
        label = SPINNE_LABELS.get(key, key)
        wert = self._diag.get(key)
        await self._request_reply(
            f"Du hast {label} bisher nur aus der Schilderung ABGELEITET, aber nicht ausdrücklich "
            "erfragt. Vergewissere dich jetzt mit GENAU EINER kurzen, freundlichen Rückfrage, ob du "
            "es richtig verstanden hast — formuliere sie als Rückfrage „Habe ich richtig verstanden, dass …?“ "
            f"und gib dein bisheriges Verständnis in eigenen, natürlichen Worten wieder (intern: {wert!r}). "
            "Schlage KEINE Methode vor und fasse NICHT alles zusammen — stelle nur diese eine Rückfrage."
        )

    async def _ask_what_to_change(self) -> None:
        """🇪🇺 EU: Die Person hat in der Bestätigung NICHT klar zugestimmt (Verneinung, unklare
        Antwort oder reine Meta-Aussage wie „du hast X nicht gefragt") und es kam KEIN neuer
        Diagnose-Wert. Statt stur dieselbe Zusammenfassung zu wiederholen (das war die Endlos-
        schleife) fragen wir offen, was geändert/ergänzt werden soll. Bleibt in der Bestätigungs-
        phase (kein Auto-Start); die nächste inhaltliche Antwort aktualisiert dann die Diagnose."""
        await self._request_reply(
            "Die Person hat NICHT klar zugestimmt — sie ist nicht einverstanden oder möchte etwas "
            "ergänzen oder ändern. Wiederhole NICHT die ganze Zusammenfassung und erstelle KEINEN "
            "Vorschlag. Frage stattdessen freundlich und konkret nach, WAS sie ändern oder ergänzen "
            "möchte. Hat sie einen bestimmten Punkt genannt (z. B. die psychologische Sicherheit "
            "oder den Schwerpunkt), frage gezielt zu genau diesem Punkt nach. Stelle GENAU EINE "
            "kurze, klare Frage."
        )

    async def _run_match(self) -> None:
        """Holt nach dem „Go" den echten String aus ``/api/match/``, spiegelt ihn ans Frontend
        und liest ihn vor. Phasenführung: VERDICHTUNG (überbrücken) → ABSCHLUSS (vorlesen, fertig)."""
        self._done = True
        # PHASE 2 — Verdichtung: Verhalten umschalten (keine Fragen mehr), dann ~60 s überbrücken.
        await self._set_phase("VERDICHTUNG", PHASE_VERDICHTUNG)
        # Kostenschutz: Inaktivitäts-Wächter PAUSIEREN — während das System rechnet, schweigt der
        # Nutzer bewusst (Wartespiel/Musik); das darf nicht fälschlich als Inaktivität auslösen.
        self._pause_inactivity()
        # Frontend-Signal „ich rechne jetzt" → dort startet das Wartespiel und überbrückt die
        # 1–2 Min Verdichtung (ohne dieses Signal blitzte es nur beim Ergebnis kurz auf).
        try:
            await self._room.local_participant.publish_data(
                json.dumps({"type": "status", "status": "matching"}).encode("utf-8"),
                reliable=True, topic="status",
            )
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("Status matching konnte nicht gesendet werden: %s", exc)
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
            await self._set_phase("ERHEBUNG", self._erhebung_instr)
            # Wir sind zurück in der Erhebung → den normalen Inaktivitäts-Wächter wieder armen.
            self._bump_activity()
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
        # Kostenschutz: Nachfrage-Fenster starten. Ab jetzt gilt die kürzere POST_RESULT_GRACE_S —
        # kommt keine Rückfrage mehr, verabschiedet sich der Coach und die Sitzung wird beendet.
        # (``_bump_activity`` liest Phase ABSCHLUSS und armt automatisch das kurze Fenster.)
        self._bump_activity()

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
        # Nur EINDEUTIGE Bestätigungs-Wörter. Bewusst NICHT dabei: beschreibende Adjektive wie
        # „gut/super/sicher" oder Verben wie „machen/los" — die kommen oft in INHALTLICHEN
        # Antworten vor („das Vertrauen ist gut", „die machen das alte") und lösten fälschlich
        # ein GO aus.
        zustimmung = {"ja", "jo", "joa", "joah", "jaa", "jaja", "jau", "jawohl", "jawoll",
                      "yeah", "yea", "yep", "yes", "jup", "jupp", "jepp", "klar", "genau",
                      "stimmt", "passt", "richtig", "korrekt", "perfekt", "gerne", "gern",
                      "okay", "ok", "mhm", "mhmm"}
        if words & zustimmung:
            return True
        phrasen = ("auf jeden fall", "leg los", "los geht", "passt so", "stimmt so", "mach mal",
                   "machen wir", "alles richtig", "alles korrekt", "ist richtig", "ist korrekt",
                   "kannst loslegen", "leg gern los")
        return any(p in low for p in phrasen)

    @staticmethod
    def _is_correction(text: str) -> bool:
        """Sieht eine Antwort in der Bestätigungsphase nach einer KORREKTUR/Ergänzung aus (statt
        nach Zustimmung)? Signale: Verneinung, ein konkreter Dimensions-Wert (z. B. „online",
        „hybrid", „niedrig") oder eine Zahl (korrigiert Größe/Zeit). Dann NICHT matchen, sondern
        neu zusammenfassen."""
        low = text.lower()
        for ch in ".,!?;:\"'„“”-—…":
            low = low.replace(ch, " ")
        words = set(low.split())
        verneinung = {"nein", "nicht", "falsch", "ne", "nee", "quatsch", "stopp", "stop",
                      "warte", "moment", "aber", "doch", "eigentlich", "noch", "kein", "keine"}
        if words & verneinung:
            return True
        dimwerte = {"online", "remote", "digital", "präsenz", "praesenz", "vorort", "hybrid",
                    "niedrig", "mittel", "hoch"}
        if words & dimwerte:
            return True
        if any(ch.isdigit() for ch in text):  # eine Zahl → korrigiert meist Größe/Zeit
            return True
        if "vor ort" in low or "lieber" in low:
            return True
        return False

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

    # ── Kostenschutz: Selbst-Abschaltung (Abschied + Sitzung sauber trennen) ────────────────────
    def _bump_activity(self) -> None:
        """(Re)startet den Inaktivitäts-Wächter — von JEDER Nutzer-Äußerung aufgerufen. Die Frist
        hängt von der Phase ab: in ``ABSCHLUSS`` gilt das kurze Nachfrage-Fenster
        (``POST_RESULT_GRACE_S``), sonst die normale Inaktivitäts-Frist (``INACTIVITY_TIMEOUT_S``).
        Während der ``VERDICHTUNG`` (das System rechnet, der Nutzer schweigt bewusst) bleibt der
        Wächter PAUSIERT."""
        if self._shutting_down or self._phase == "VERDICHTUNG":
            return
        if self._phase == "ABSCHLUSS":
            timeout, reason = POST_RESULT_GRACE_S, "post_result"
        else:
            timeout, reason = INACTIVITY_TIMEOUT_S, "inactivity"
        if self._inactivity_task is not None:
            self._inactivity_task.cancel()
        self._inactivity_task = asyncio.create_task(self._inactivity_countdown(timeout, reason))

    def _pause_inactivity(self) -> None:
        """Stoppt den Inaktivitäts-Wächter (z. B. solange das System rechnet)."""
        if self._inactivity_task is not None:
            self._inactivity_task.cancel()
            self._inactivity_task = None

    async def _inactivity_countdown(self, seconds: float, reason: str) -> None:
        """Wartet ``seconds`` und schaltet dann ab. Ein ``cancel()`` (neue Aktivität) bricht ab."""
        try:
            await asyncio.sleep(seconds)
        except asyncio.CancelledError:
            return
        logger.info("Wächter (%s) nach %.0fs ausgelöst → Abschaltung", reason, seconds)
        await self._graceful_shutdown(reason)

    def _arm_max_session(self) -> None:
        """Startet den harten Maximal-Backstop EINMALIG (wird nie zurückgesetzt) — absolute Obergrenze."""
        if self._maxsession_task is not None:
            return
        self._maxsession_task = asyncio.create_task(self._max_session_countdown())

    async def _max_session_countdown(self) -> None:
        try:
            await asyncio.sleep(MAX_SESSION_S)
        except asyncio.CancelledError:
            return
        logger.info("Hartes Zeitlimit (%.0fs) erreicht → Abschaltung", MAX_SESSION_S)
        await self._graceful_shutdown("max_session")

    async def _graceful_shutdown(self, reason: str) -> None:
        """Verabschiedet sich freundlich und beendet die Sitzung SAUBER, damit keine Minuten
        weiterlaufen (Kostenschutz). Idempotent.

        Reihenfolge: Abschiedssatz AUSREDEN lassen → Frontend „ended" → **Raum serverseitig löschen**
        (Kern-Trennung, s. u.) → Session lokal schließen (``drain`` + ``aclose``).

        WARUM die serverseitige Raum-Löschung der eigentliche Hebel ist (quelltext-belegt gegen
        livekit-agents 1.5.17): ``session.shutdown``/``aclose`` durchläuft ``_aclose_impl``, das den
        Raum erst GANZ AM ENDE über ``room_io.aclose`` (= ``delete_room_on_close``) löscht. Davor wartet
        es — selbst bei ``drain=False`` — noch auf ``activity.drain()``, laufende ``current_speech`` und
        ``commit_user_turn``. Redet der Gast nach dem Abschied weiter, hängt diese Kette und der Raum
        wird NIE erreicht → Verbindung blieb minutenlang offen (Test 2026-06-11: 5–8 Min). Deshalb löschen
        wir den Raum ZUERST direkt über die LiveKit-Server-API: das trennt alle sofort, unabhängig von der
        Session-Schließkette. Der anschließende ``drain``/``aclose`` ist dann nur noch lokales Aufräumen
        (läuft schnell durch, weil die Verbindung bereits weg ist); ``delete_room_on_close=True`` bleibt
        als zusätzliches Sicherheitsnetz beim ``session.start``."""
        if self._shutting_down:
            return
        self._shutting_down = True
        self._done = True
        for task in (self._inactivity_task, self._maxsession_task):
            if task is not None:
                task.cancel()
        self._inactivity_task = None
        self._maxsession_task = None
        logger.info("Graceful Shutdown — Grund: %s", reason)
        # Abschiedssatz ausreden lassen — aber MIT HARTEM TIMEOUT. ``session.say`` mit
        # ``allow_interruptions=False`` kann nach einem stillen/abgewandten Nutzer ewig aufs
        # Playout-Ende warten (Test 2026-06-11: Sitzung hing genau hier, die Raum-Löschung
        # darunter wurde nie erreicht). Nach ``GOODBYE_TIMEOUT_S`` geht es ZWINGEND weiter —
        # der Kostenschutz (Raum-Löschung) darf nicht vom Gelingen der Sprachausgabe abhängen.
        try:
            await asyncio.wait_for(
                self._speak(GOODBYE_TEXTS.get(reason, GOODBYE_TEXTS["post_result"]),
                            allow_interruptions=False),
                timeout=GOODBYE_TIMEOUT_S,
            )
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("Abschiedssatz nicht (rechtzeitig) ausgeredet (%r) — fahre mit Trennung fort", exc)
        # Frontend für eine freundliche „Sitzung beendet"-Ansicht informieren (dann erst trennen).
        try:
            await self._room.local_participant.publish_data(
                json.dumps({"type": "status", "status": "ended", "reason": reason}).encode("utf-8"),
                reliable=True, topic="status",
            )
        except Exception as exc:  # pragma: no cover - reine Robustheit
            logger.warning("Ende-Status konnte nicht gesendet werden: %s", exc)
        # KERN-TRENNUNG (Kostenschutz): Den Raum SERVERSEITIG löschen — das wirft ALLE Teilnehmer
        # (auch den Gast) sofort raus, unabhängig von der Session-Schließkette. Nötig, weil sich der
        # interne ``_aclose_impl`` (selbst mit drain=False) noch an ``activity.drain()`` /
        # ``commit_user_turn`` aufhängen kann, solange der Gast weiterredet — dann wird die
        # eingebaute ``delete_room_on_close``-Löschung (ganz am Ende der Kette) NIE erreicht und die
        # Verbindung bleibt minutenlang offen (Test 2026-06-11). Raum weg ⇒ Minuten stoppen.
        try:
            await self._ctx.api.room.delete_room(api.DeleteRoomRequest(room=self._ctx.room.name))
            logger.info("Kostenschutz: Raum %s gelöscht — alle Teilnehmer getrennt", self._ctx.room.name)
        except Exception as exc:
            logger.error("Raum-Löschung fehlgeschlagen: %r — Fallback auf Session-Abschluss", exc)
        # Session lokal schließen — jede Stufe AWAITED, mit Timeout und geloggt (kein stilles Versagen,
        # kein Hänger mehr). Nach der Raum-Löschung oben ist die Verbindung bereits weg, das läuft also
        # zügig durch; der Timeout ist nur das Sicherheitsnetz gegen ein erneutes Aufhängen.
        try:
            await asyncio.wait_for(self.session.drain(), timeout=SHUTDOWN_STEP_TIMEOUT_S)
            logger.info("Session gedraint")
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("drain fehlgeschlagen/Timeout: %r", exc)
        try:
            await asyncio.wait_for(self.session.aclose(), timeout=SHUTDOWN_STEP_TIMEOUT_S)
            logger.info("Session geschlossen")
        except (asyncio.TimeoutError, Exception) as exc:
            logger.warning("aclose fehlgeschlagen/Timeout: %r → Fallback room.disconnect", exc)
            try:
                await asyncio.wait_for(self._room.disconnect(), timeout=SHUTDOWN_STEP_TIMEOUT_S)
            except (asyncio.TimeoutError, Exception) as exc2:  # pragma: no cover - reine Robustheit
                logger.error("Auch Fallback-Trennung fehlgeschlagen/Timeout: %r", exc2)

    # Reihenfolge + lesbare Namen der 7 Stränge fürs „gemeinsame Bild" (Anlass = Mittelpunkt zuerst).
    _STATUS_ORDER = (
        ("anlass", "Anlass/Thema"), ("ziel_text", "Ziel"), ("zweck", "Schwerpunkt"),
        ("gruppengroesse", "Gruppengröße"), ("zeitbudget", "Zeit (Minuten)"),
        ("setting", "Setting"), ("psychologische_sicherheit", "Sicherheit"),
    )

    def _spinne_status_text(self) -> str:
        """🇪🇺 EU: Das VOLLSTÄNDIGE gemeinsame Bild der Spinne (alle 7 Stränge mit aktuellem Wert
        bzw. „noch offen"). Kern des Coachings: Coachin und Person teilen jederzeit DENSELBEN Stand.
        Das Backend extrahiert nur „dumm"; die Intelligenz/Führung liegt bei der Coachin."""
        zeilen = []
        for key, label in self._STATUS_ORDER:
            wert = self._diag.get(key)
            if isinstance(wert, list):
                wert = ", ".join(str(x) for x in wert) if wert else None
            zeilen.append(f"- {label}: {wert}" if wert not in (None, "", []) else f"- {label}: — noch offen")
        return (
            "GEMEINSAMES BILD — so steht die Spinne gerade (du und die Person müsst dasselbe "
            "Verständnis davon haben, worüber ihr sprecht):\n" + "\n".join(zeilen) + "\n\n"
            "Deine Aufgabe: Fülle gemeinsam mit der Person ALLE noch offenen Stränge — EINEN nach "
            "dem anderen, je eine ruhige, klare Frage. Die Spinne muss am Ende VOLLSTÄNDIG und "
            "STIMMIG sein. Solange noch ein Strang offen ist, fasse NICHTS zusammen und stelle "
            "KEINE Ja/Nein-Bestätigungsfrage — frage stattdessen den nächsten offenen Punkt ab."
        )

    async def _guide_coach(self) -> None:
        """Spielt dem Sprachmodell den VOLLEN Erhebungsstand zurück — das „gemeinsame Bild", also
        genau das, was im Frontend in der Spinne steht — damit es gezielt + ruhig führt statt blind
        zu raten (gemessen am KLEBRIGEN ``self._seen``).

        BEIDE Pfade erhalten dieses Bild (Steffen 2026-06-07: US bewusst „aufgetaut", per Git-Tag
        ``voice-vorzeigbar-2026-06-07`` reversibel). VORSICHTIG umgesetzt: der eingefrorene US-Prompt
        (``self._erhebung_instr``) bleibt unverändert — das Live-Bild wird nur ANGEHÄNGT. Und es wird
        NUR bei echter Änderung neu gesetzt (Cache) → schützt v. a. den US-Realtime-Stream vor „Stocken"."""
        fehlende_keys = [k for k in SPINNE_KEYS if k not in self._seen]
        if not fehlende_keys:
            return  # alles erfasst → das Gate übernimmt (Zusammenfassung)
        # 🇪🇺 EU merkt sich aktiv erfragte Stränge (für die Rückversicherung interpretierter Werte).
        if self._tier != "us":
            self._erfragt |= set(fehlende_keys)
        status = self._spinne_status_text()
        if status == self._last_guidance:  # nur bei echter Änderung neu setzen (Anti-Stocken)
            return
        self._last_guidance = status
        try:
            await self.update_instructions(self._erhebung_instr + "\n\n" + status)
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
        # Server-seitige Sprechpausen-Erkennung ABSCHALTEN (turn_detection=None) und stattdessen
        # eine eigene Silero-VAD an die Sitzung hängen. Grund (Test 2026-06-06, Log-Hinweis): mit
        # Server-Turn-Detection ignoriert das Realtime-Modell ``allow_interruptions`` und
        # unterbricht den Agenten selbst — das zerschoss das vollständige Vorlesen des Vorschlags
        # und führte am Anfang zu abgehacktem „Zickzack". Mit eigener VAD haben WIR die Kontrolle.
        rt_kwargs["turn_detection"] = None
        # GEDULD beim Zuhören: Die Default-VAD endet schon nach 0,55 s Stille → der Agent grätscht
        # in normale Sprechpausen rein (Test 2026-06-06). Wir verlangen eine längere Pause, bis die
        # Äußerung als beendet gilt, plus eine Endpointing-Mindestverzögerung. Per ENV justierbar.
        vad_silence = float(os.environ.get("VOICE_VAD_SILENCE", "1.2"))
        min_endpoint = float(os.environ.get("VOICE_MIN_ENDPOINT", "0.8"))
        max_endpoint = float(os.environ.get("VOICE_MAX_ENDPOINT", "6.0"))
        return AgentSession(
            llm=openai.realtime.RealtimeModel(**rt_kwargs),
            vad=silero.VAD.load(min_silence_duration=vad_silence),
            min_endpointing_delay=min_endpoint,
            max_endpointing_delay=max_endpoint,
        )

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
        # Vorab-Generierung AUS: Sonst erzeugt LiveKit die Antwort der Coachin schon, BEVOR unser
        # ``on_user_turn_completed``-Hook die Diagnose vom Backend geholt und die nächste Frage
        # gesetzt hat (Warnung „chat context changed after on_user_turn_completed"). Folge: die
        # Coachin fragt die fehlenden Punkte NICHT gezielt ab und das Gespräch mäandert. Mit AUS
        # wartet die Antwort, bis unsere Steuerung steht — etwas mehr Latenz, aber korrekt geführt.
        preemptive_generation=False,
    )


async def entrypoint(ctx: agents.JobContext) -> None:
    """Pro Raum: Sitzung je Souveränitätsstufe. Die gewählte Stufe steht in den
    Teilnehmer-Metadaten des LiveKit-Tokens (``{"tier": "us"|"eu"|"sov"}``)."""
    await ctx.connect()
    # Build-Nachweis: stempelt jede Sitzung mit dem laufenden Code-Stand (s. Dockerfile BUILD_ID).
    # So ist nie unklar, welcher Stand aktiv ist. „?" = ohne --build-arg gebaut (z. B. nur restart).
    logger.info("voice-agent BUILD_ID=%s", os.environ.get("BUILD_ID", "?"))

    # Stufe aus den Teilnehmer-Metadaten lesen (Token trägt {"tier": ...}); Default eu.
    tier = "eu"
    try:
        participant = await ctx.wait_for_participant()
        if participant and participant.metadata:
            tier = json.loads(participant.metadata).get("tier", "eu")
    except Exception as exc:  # pragma: no cover - reine Robustheit
        logger.warning("Stufe nicht lesbar (%r) — nutze eu.", exc)
    logger.info("Sprach-Sitzung: Stufe %s", tier)

    # Brain mit dem Tier bauen, damit /api/interview/ den pfad-getrennten Erhebungs-Prompt
    # bekommt (EU = vorsichtig, US = eingefroren). Daher erst NACH der Tier-Erkennung.
    brain = LSInterviewBrain(BACKEND_URL, tier=tier)
    session = _build_session(tier)
    coach = LSCoach(ctx, ctx.room, brain, tier=tier)

    # Realtime (us) liefert die Nutzer-Transkription NICHT über on_user_turn_completed,
    # sondern über das Session-Event „user_input_transcribed" — daran hängen wir das Gehirn,
    # damit sich die Spinne füllt und am Ende der echte Match kommt.
    if tier == "us":
        # Im US-Pfad liefert das „user_input_transcribed"-Event die Transkription — daher den
        # zusätzlichen on_user_turn_completed-Hook abschalten (sonst doppelt + Objekt-Repr-Müll).
        coach._suppress_turn_hook = True
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
    # ``delete_room_on_close=True`` (Kostenschutz): Wenn der Agent die Sitzung beendet
    # (``_graceful_shutdown`` → ``session.shutdown``), löscht LiveKit den ganzen Raum und trennt
    # AUCH den Nutzer — sonst bliebe dessen Verbindung offen und würde weiter Minuten verursachen.
    await session.start(
        room=ctx.room,
        agent=coach,
        room_options=room_io.RoomOptions(delete_room_on_close=True),
    )


if __name__ == "__main__":
    # Eigener Port für den internen Worker-HTTP-Server (8081 ist auf dem Host belegt).
    agents.cli.run_app(
        agents.WorkerOptions(
            entrypoint_fnc=entrypoint,
            port=int(os.environ.get("AGENT_HTTP_PORT", "8099")),
        )
    )
