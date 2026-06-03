from django.apps import AppConfig


class MatchmakerConfig(AppConfig):
    """Konfiguration der Matchmaker-App (Interview, Matchmaking, Quality Gate)."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "matchmaker"
    verbose_name = "LS-Matchmaker (Interview & Matchmaking)"
