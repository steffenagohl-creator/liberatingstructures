"""
Django-Einstellungen für das LS-Matchmaker-Backend.

Konfiguration ausschließlich über ENV-Variablen (provider-agnostisch, keine Secrets im Code).
Werte werden aus der Umgebung gelesen; lokal optional aus einer .env-Datei.
"""
import os
from pathlib import Path

import dj_database_url
from dotenv import load_dotenv

# Verzeichnisse
BASE_DIR = Path(__file__).resolve().parent.parent          # .../backend
load_dotenv(BASE_DIR.parent / ".env")                      # lädt .env (lokal); in Docker via env_file

# Verzeichnis mit den kuratierten Daten (structures.json, diagnosis_schema.json, ...)
DATA_DIR = Path(os.environ.get("LSM_DATA_DIR", BASE_DIR.parent / "data"))

# Sicherheit / Betrieb (aus ENV)
SECRET_KEY = os.environ.get("DJANGO_SECRET_KEY", "dev-unsafe-change-me")
DEBUG = os.environ.get("DJANGO_DEBUG", "true").lower() == "true"
ALLOWED_HOSTS = os.environ.get("DJANGO_ALLOWED_HOSTS", "*").split(",")

INSTALLED_APPS = [
    "django.contrib.admin",
    "django.contrib.auth",
    "django.contrib.contenttypes",
    "django.contrib.sessions",
    "django.contrib.messages",
    "django.contrib.staticfiles",
    "rest_framework",
    "drf_spectacular",
    "catalog",
    "matchmaker",
    "voice",
]

MIDDLEWARE = [
    "django.middleware.security.SecurityMiddleware",
    "django.contrib.sessions.middleware.SessionMiddleware",
    "django.middleware.common.CommonMiddleware",
    "django.middleware.csrf.CsrfViewMiddleware",
    "django.contrib.auth.middleware.AuthenticationMiddleware",
    "django.contrib.messages.middleware.MessageMiddleware",
    "django.middleware.clickjacking.XFrameOptionsMiddleware",
]

ROOT_URLCONF = "config.urls"

TEMPLATES = [
    {
        "BACKEND": "django.template.backends.django.DjangoTemplates",
        "DIRS": [],
        "APP_DIRS": True,
        "OPTIONS": {
            "context_processors": [
                "django.template.context_processors.debug",
                "django.template.context_processors.request",
                "django.contrib.auth.context_processors.auth",
                "django.contrib.messages.context_processors.messages",
            ],
        },
    },
]

WSGI_APPLICATION = "config.wsgi.application"

# Datenbank: PostgreSQL über DATABASE_URL (Standard zeigt auf den Compose-Dienst "db")
DATABASES = {
    "default": dj_database_url.config(
        default="postgres://lsm:lsm@db:5432/lsm",
        conn_max_age=600,
    )
}

AUTH_PASSWORD_VALIDATORS = [
    {"NAME": "django.contrib.auth.password_validation.UserAttributeSimilarityValidator"},
    {"NAME": "django.contrib.auth.password_validation.MinimumLengthValidator"},
    {"NAME": "django.contrib.auth.password_validation.CommonPasswordValidator"},
    {"NAME": "django.contrib.auth.password_validation.NumericPasswordValidator"},
]

# Sprache/Zeit: Deutsch
LANGUAGE_CODE = "de"
TIME_ZONE = "Europe/Berlin"
USE_I18N = True
USE_TZ = True

STATIC_URL = "static/"
DEFAULT_AUTO_FIELD = "django.db.models.BigAutoField"

REST_FRAMEWORK = {
    "DEFAULT_SCHEMA_CLASS": "drf_spectacular.openapi.AutoSchema",
}

# OpenAPI-Doku (Leitprinzip: dokumentierte, maschinenlesbare Endpunkte)
SPECTACULAR_SETTINGS = {
    "TITLE": "LS-Matchmaker API",
    "DESCRIPTION": "API des LS-Matchmaker: schlägt passende Liberating-Structures-Strings vor.",
    "VERSION": "0.3.0",
    "SERVE_INCLUDE_SCHEMA": False,
}

# --------------------------------------------------------------------------- #
# LLM-Schicht (AP3) – provider-agnostisch, ausschließlich über ENV.
# Ohne Schlüssel/Provider läuft alles über den Stub (LLM_PROVIDER=stub).
# --------------------------------------------------------------------------- #
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "mistral")
LLM_MODEL = os.environ.get("LLM_MODEL", "mistral-medium-latest")
# Schlüssel: bevorzugt MISTRAL_API_KEY, ersatzweise das generische LLM_API_KEY.
LLM_API_KEY = os.environ.get("MISTRAL_API_KEY") or os.environ.get("LLM_API_KEY", "")
LLM_TIMEOUT = float(os.environ.get("LLM_TIMEOUT", "60"))
# Wie oft die Sequenzierung nach einem Quality-Gate-Verstoß nachbessern darf.
MATCHMAKER_MAX_ITERATIONS = int(os.environ.get("MATCHMAKER_MAX_ITERATIONS", "3"))
# Zwei-Agenten-Konsolidierung (Agent A & B + prüfender Konsolidierer). Zum Sparen abschaltbar.
MATCHMAKER_CONSOLIDATE = os.environ.get("MATCHMAKER_CONSOLIDATE", "true").lower() == "true"

# --------------------------------------------------------------------------- #
# Sprachkanäle (Stufe 1D) – provider-agnostisch, ausschließlich über ENV.
# Fundament (Phase 1): keine Infrastruktur nötig. LiveKit-Transport + echte Provider
# kommen in Phase 2+ (eigene LS-LiveKit-Instanz, Ports 7980/7981, UDP 40000–49999).
# --------------------------------------------------------------------------- #
# Vorausgewählte Souveränitätsstufe (sov | eu | us). Default: EU (empfohlen).
VOICE_DEFAULT_TIER = os.environ.get("VOICE_DEFAULT_TIER", "eu")
# 🔒 sov erst nutzbar, wenn der lokale Sprach-Stack (Voxtral/Piper/LLM) aktiviert ist (Phase 4).
VOICE_SELFHOSTED_ENABLED = os.environ.get("VOICE_SELFHOSTED_ENABLED", "false").lower() == "true"
# Erzwingt offline nutzbare Stub-Bausteine (Dev/Tests ohne Netz/Schlüssel).
VOICE_FORCE_STUB = os.environ.get("VOICE_FORCE_STUB", "false").lower() == "true"
# LiveKit-Transport (leer bis Phase 2 – dann eigene LS-Instanz).
LIVEKIT_URL = os.environ.get("LIVEKIT_URL", "")
LIVEKIT_API_KEY = os.environ.get("LIVEKIT_API_KEY", "")
LIVEKIT_API_SECRET = os.environ.get("LIVEKIT_API_SECRET", "")
# 🇺🇸 us-Pfad (OpenAI Realtime) – Schlüssel wird erst in Phase 5 wirklich genutzt.
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY", "")
