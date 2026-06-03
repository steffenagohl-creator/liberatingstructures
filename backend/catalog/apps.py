"""App-Konfiguration für den LS-Katalog (Strukturen + String-Templates)."""
from django.apps import AppConfig


class CatalogConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "catalog"
    verbose_name = "Liberating-Structures-Katalog"
