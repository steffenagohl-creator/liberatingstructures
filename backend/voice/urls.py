"""URL-Routen der Sprachkanal-App (eingebunden unter ``/api/voice/`` in config/urls.py)."""
from django.urls import path

from .views import VoiceConfigView, VoiceSessionView

urlpatterns = [
    path("voice/config/", VoiceConfigView.as_view(), name="voice-config"),
    path("voice/session/", VoiceSessionView.as_view(), name="voice-session"),
]
