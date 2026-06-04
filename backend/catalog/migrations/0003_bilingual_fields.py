"""Zweisprachigkeit (DE+EN): Textfelder auf JSONField {de,en} umstellen.

Die sechs bisher einsprachigen Textspalten werden zu ``jsonb``. Bestehende
(einsprachige) Werte werden mit ``to_jsonb(...)`` verlustfrei in ein JSON-Skalar
gehoben; der anschließende ``import_structures``-Lauf überschreibt sie mit dem
vollen ``{"de": …, "en": …}``-Objekt aus ``data/structures.json``.

text/varchar -> jsonb braucht in Postgres einen expliziten ``USING``-Cast, daher
``RunSQL`` mit passenden ``state_operations`` (damit Djangos Modellzustand stimmt).
Neu hinzu kommt das Feld ``icon_alt`` (Alt-Text fürs LS-Icon, Barrierefreiheit).
"""
from django.db import migrations, models


def _to_jsonb(table, column):
    return migrations.RunSQL(
        sql=f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE jsonb USING to_jsonb("{column}");',
        reverse_sql=(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" TYPE text '
            f'USING COALESCE("{column}"->>\'de\', "{column}"#>>\'{{}}\');'
        ),
    )


TABLE = "catalog_structure"
JSON_FIELDS = ["name", "short_desc", "objective", "materials", "scrum_use", "attribution"]


class Migration(migrations.Migration):

    dependencies = [
        ("catalog", "0002_structure_embodied_principles_structure_guide_and_more"),
    ]

    operations = [
        # 1) Spaltentyp in der DB sicher casten (text/varchar -> jsonb), Modellzustand
        #    parallel über state_operations auf JSONField setzen.
        migrations.SeparateDatabaseAndState(
            database_operations=[_to_jsonb(TABLE, col) for col in JSON_FIELDS],
            state_operations=[
                migrations.AlterField(
                    model_name="structure", name="name",
                    field=models.JSONField(default=dict),
                ),
                migrations.AlterField(
                    model_name="structure", name="short_desc",
                    field=models.JSONField(default=dict),
                ),
                migrations.AlterField(
                    model_name="structure", name="objective",
                    field=models.JSONField(blank=True, default=dict),
                ),
                migrations.AlterField(
                    model_name="structure", name="materials",
                    field=models.JSONField(blank=True, default=dict),
                ),
                migrations.AlterField(
                    model_name="structure", name="scrum_use",
                    field=models.JSONField(blank=True, default=dict),
                ),
                migrations.AlterField(
                    model_name="structure", name="attribution",
                    field=models.JSONField(blank=True, default=dict),
                ),
            ],
        ),
        # 2) Neues Feld icon_alt (Alt-Text fürs Icon, zweisprachig).
        migrations.AddField(
            model_name="structure",
            name="icon_alt",
            field=models.JSONField(blank=True, default=dict),
        ),
    ]
