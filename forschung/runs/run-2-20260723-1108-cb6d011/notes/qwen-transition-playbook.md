# Bedingung A — Übergang von Gemma zu Qwen

Ressourcenklasse: später `DEPENDENT`  
Voraussetzung: Session 33 ist `TEST_VALID`; kein zweiter Forschungsprozess aktiv

## Serielle Reihenfolge

1. Gemma-Unit muss beendet sein; Exit-Code und Sessionvalidierung sichern.
2. GPU-Sperrprozesse 480679 und 480681 bleiben `Tsl`.
3. Steering-API exakt einmal auf `Qwen/Qwen3.5-4B`, `quantize=false` umstellen.
4. `/v1/steering/restart-status` ohne Sekundenpolling bis `ready` oder `error`
   beobachten.
5. Modell-ID, FP16-Modus, GPU-Speicher und interne Testgenerierung des
   Steering-Servers prüfen.
6. Erst dann einen neuen transienten User-systemd-Dienst für
   `qwen-a-five-repetitions.config.json` starten.
7. PID, Invocation-ID, Startzeit, Logpfade, Config-Hash
   `8d9ea9a414ed6dd7146c789f1f4489816f150f28f19e457c4409edb5fee1f08e`
   und erwartete neue Session in `processes.json` registrieren.
8. Qwen-Run mit denselben 86 Fragen, Seeds 11/23/37/53/71,
   isoliertem State, deaktiviertem Sleep und lokalem Formatting ausführen.

## Abbruchbedingungen

- Steering-Restart endet in `error`
- Modell-ID ist nicht exakt `Qwen/Qwen3.5-4B`
- unplausible VRAM-Restbelegung nach Gemma-Cleanup
- zweiter Researchprozess oder freigegebener Web-/Trainingprozess
- erste Frage verwendet nicht ausschließlich Qwen/vLLM für alle
  als modellabhängig deklarierten Pfade

## Validierung

Wie bei Gemma: 430 Dateien, fünf Seeds, Summary, Provider-Audit,
`valid_completed`, keine leeren Antworten, keine Hard-/Setup-/Parsingfehler,
keine Modellvermischung. Das nominelle Qwen-Layerprofil L10–26 wird zusätzlich
gegen tatsächlich protokollierte aktive Layerbereiche geprüft.
