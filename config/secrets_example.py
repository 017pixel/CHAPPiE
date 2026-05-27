"""
Legacy-Hinweis.

Neue Installationen nutzen nicht mehr config/secrets.py als Hauptkonfiguration.
Kopiere stattdessen im Projekt-Root:

    CHAPPIE_CONFIG.example.json -> CHAPPIE_CONFIG.json

    Trage dort mindestens api.groq_api_key ein.
Diese Datei bleibt nur als Kompatibilitaetshinweis fuer alte Setups bestehen.
"""

