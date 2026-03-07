═══════════════════════════════════════════════════════════════════
⚠️  WARNUNG - CHAPPiE GEDÄCHTNIS & LAUFZEITDATEN ⚠️
═══════════════════════════════════════════════════════════════════

Dieser Ordner enthält zentrale Laufzeit- und Gedächtnisdaten von CHAPPiE.

WICHTIG:
Wenn du Inhalte in `data/` unbedacht löschst, kann CHAPPiE Erinnerungen,
Zustände, Verlauf oder persönliche Kontextinformationen verlieren.

Typische Inhalte sind u. a.:
- Memory-/Vektordaten
- `soul.md`, `user.md`, `CHAPPiEsPreferences.md`
- `life_state.json`, `sleep_state.json`, Training-/Verlaufsdaten

NICHT EINFACH LÖSCHEN, wenn du nicht genau weißt, was du tust.

SICHERER RESET:
Verwende die dafür vorgesehenen Reset-Funktionen im Memory-/State-Code,
z. B. in `memory/memory_engine.py`, statt den Ordner manuell zu leeren.

Beispiel:
    python -c "from memory.memory_engine import MemoryEngine; engine = MemoryEngine(); engine.reset_all_memories()"

Weitere Einordnung:
- `README.md`
- `docs/project-map.md`
- `docs/testing.md`

═══════════════════════════════════════════════════════════════════
