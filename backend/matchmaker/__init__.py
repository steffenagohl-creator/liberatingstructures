"""App ``matchmaker`` – das „Gehirn" des LS-Matchmaker (AP3).

Enthält die provider-agnostische LLM-Schicht (``llm/``), den deterministischen
Kern (Vorfilterung + Quality Gate in ``services.py``, Katalog-Abfragen in
``tools.py``) und die dokumentierten DRF-Endpunkte (``/api/interview/``,
``/api/match/``).
"""
