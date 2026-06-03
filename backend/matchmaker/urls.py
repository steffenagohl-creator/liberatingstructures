"""URL-Routen der Matchmaker-App (eingebunden unter ``/api/`` in config/urls.py)."""
from django.urls import path

from .views import InterviewView, MatchView

urlpatterns = [
    path("interview/", InterviewView.as_view(), name="interview"),
    path("match/", MatchView.as_view(), name="match"),
]
