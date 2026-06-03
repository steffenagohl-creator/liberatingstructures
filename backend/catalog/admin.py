"""Admin-Registrierung für eine schnelle, sichtbare Kontrolle der Daten."""
from django.contrib import admin

from .models import Structure, StringTemplate


@admin.register(Structure)
class StructureAdmin(admin.ModelAdmin):
    list_display = ("structure_id", "name", "slug", "edition", "difficulty", "online_capable")
    list_filter = ("edition", "type", "difficulty", "online_capable")
    search_fields = ("name", "slug", "short_desc")


@admin.register(StringTemplate)
class StringTemplateAdmin(admin.ModelAdmin):
    list_display = ("slug", "name", "total_duration", "scrum_context")
    search_fields = ("name", "slug", "purpose")
