"""App-Konfiguration der Sprachkanal-App."""
from django.apps import AppConfig


class VoiceConfig(AppConfig):
    """Registriert die Voice-App. Bewusst ohne Modelle (zustandslos, datensparsam)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "voice"
    verbose_name = "Sprachkanäle (LS-Voice)"
