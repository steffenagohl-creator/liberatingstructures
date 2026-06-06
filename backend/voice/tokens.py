"""LiveKit-Zugangstoken — Schnittstelle + Phase-1-Stub.

Ein ``TokenSigner`` erzeugt das Token, mit dem ein Client einem LiveKit-Raum beitritt.
In **Phase 1** gibt es nur den ``StubTokenSigner`` (kein Krypto, kein echtes LiveKit) –
damit der Endpunkt schon Form und Vertrag hat und testbar ist, **ohne** neue Dependency.
Der **echte** Signer (Lib ``livekit-api`` oder PyJWT) kommt mit der LiveKit-Instanz in
**Phase 2**; ``get_token_signer()`` wird ihn dann automatisch wählen, sobald Schlüssel da sind.
"""
from __future__ import annotations

import base64
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass

from django.conf import settings

from .providers.base import VoiceError


@dataclass(frozen=True)
class TokenResult:
    """Ein ausgestelltes Token plus Transparenz, ob es echt oder ein Stub ist."""

    token: str
    is_stub: bool
    livekit_url: str


class TokenSigner(ABC):
    """Erzeugt LiveKit-Zugangstoken. Das Backend kennt nur dieses Interface."""

    name: str = "base"
    is_stub: bool = False

    @abstractmethod
    def create_token(
        self,
        *,
        room: str,
        identity: str,
        name: str | None = None,
        metadata: str | None = None,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str:
        """Gibt das Zugangstoken als String zurück.

        :param room: Raumname, dem beigetreten wird.
        :param identity: eindeutige Teilnehmer-Identität.
        :param name: Anzeigename (optional).
        :param metadata: beliebige Metadaten als String (z. B. gewählte Stufe).
        :param can_publish: darf Audio/Video senden (für späteres Video offen gehalten).
        :param can_subscribe: darf andere empfangen.
        """
        raise NotImplementedError


class StubTokenSigner(TokenSigner):
    """Nicht-kryptografischer Platzhalter (Phase 1).

    Liefert ein **klar als Stub markiertes**, base64-kodiertes JSON der Grants – inspizierbar,
    aber offensichtlich **kein** gültiges LiveKit-Token. Niemals produktiv verwenden.
    """

    name = "stub"
    is_stub = True

    def create_token(
        self,
        *,
        room: str,
        identity: str,
        name: str | None = None,
        metadata: str | None = None,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str:
        grants = {
            "stub": True,
            "room": room,
            "identity": identity,
            "name": name,
            "metadata": metadata,
            "video": {
                "roomJoin": True,
                "room": room,
                "canPublish": can_publish,
                "canSubscribe": can_subscribe,
            },
        }
        raw = json.dumps(grants, ensure_ascii=False).encode("utf-8")
        payload = base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")
        return f"stub.{payload}"


class LiveKitTokenSigner(TokenSigner):
    """Echtes LiveKit-Zugangstoken (Phase 2).

    Ein LiveKit-Token ist ein **signiertes JWT** (HS256) mit „video"-Grants. Wir nutzen
    direkt ``PyJWT`` (statt einer schweren LiveKit-Lib) – das hält das Backend schlank.
    ``canPublishData`` ist bewusst erlaubt: darüber schickt der Agent später die Diagnose-
    Updates ans Frontend (das „Spinnennetz"); ``canPublish`` deckt Audio **und Video** ab.
    """

    name = "livekit"
    is_stub = False

    def __init__(self, api_key: str, api_secret: str, ttl_seconds: int = 3600):
        if not api_key or not api_secret:
            raise VoiceError("LiveKit-Token braucht LIVEKIT_API_KEY und LIVEKIT_API_SECRET.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.ttl_seconds = ttl_seconds

    def create_token(
        self,
        *,
        room: str,
        identity: str,
        name: str | None = None,
        metadata: str | None = None,
        can_publish: bool = True,
        can_subscribe: bool = True,
    ) -> str:
        import time

        import jwt  # PyJWT

        now = int(time.time())
        claims: dict = {
            "iss": self.api_key,
            "sub": identity,
            "nbf": now,
            "exp": now + self.ttl_seconds,
            "video": {
                "room": room,
                "roomJoin": True,
                "canPublish": can_publish,
                "canSubscribe": can_subscribe,
                "canPublishData": True,
            },
        }
        if name:
            claims["name"] = name
        if metadata:
            claims["metadata"] = metadata
        return jwt.encode(claims, self.api_secret, algorithm="HS256")


def get_token_signer() -> TokenSigner:
    """Wählt den Signer rein über die Konfiguration.

    Echter LiveKit-Signer, sobald ``LIVEKIT_API_KEY``/``LIVEKIT_API_SECRET`` gesetzt sind
    **und** ``PyJWT`` vorhanden ist; sonst der netzfreie Stub (Dev/Tests ohne Infra).
    """
    api_key = getattr(settings, "LIVEKIT_API_KEY", "")
    api_secret = getattr(settings, "LIVEKIT_API_SECRET", "")
    if api_key and api_secret:
        try:
            import jwt  # noqa: F401  (nur Verfügbarkeit prüfen)
        except ImportError:
            return StubTokenSigner()
        ttl = int(getattr(settings, "LIVEKIT_TOKEN_TTL", 3600))
        return LiveKitTokenSigner(api_key, api_secret, ttl_seconds=ttl)
    return StubTokenSigner()


def issue_token(*, room: str, identity: str, tier: str) -> TokenResult:
    """Bequemer Wrapper: Signer holen, Token erzeugen, mit URL + Stub-Flag zurückgeben."""
    signer = get_token_signer()
    if not room or not identity:
        raise VoiceError("Raum und Identität dürfen nicht leer sein.")
    token = signer.create_token(
        room=room, identity=identity, metadata=json.dumps({"tier": tier}),
    )
    return TokenResult(
        token=token,
        is_stub=signer.is_stub,
        livekit_url=getattr(settings, "LIVEKIT_URL", ""),
    )
