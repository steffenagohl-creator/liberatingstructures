"""Admin-Registrierung für eine schnelle, sichtbare Kontrolle der Daten."""
from django.contrib import admin

from .i18n import localize
from .models import Structure, StringTemplate


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ("structure_id", "name_de", "slug", "edition", "difficulty", "online_capable")
    list_filter = ("edition", "type", "difficulty", "online_capable")
    # name/short_desc sind zweisprachige JSON-Felder; Slug-Suche bleibt eindeutig und schnell.
    search_fields = ("slug",)

    @admin.display(description="Name (de)", ordering="structure_id")
    def name_de(self, obj):
        """Deutscher Anzeigename (das Modellfeld ist ein {de,en}-Objekt)."""
        return localize(obj.name, "de")


@admin.register(StringTemplate)
class StringTemplateAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "total_duration", "scrum_context")
    search_fields = ("name", "slug", "purpose")
