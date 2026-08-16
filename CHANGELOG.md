# Changelog

Alle Änderungen werden in 5 Stichpunkten dokumentiert. Keine Code-Anzeigen!

## [16.1] - 2026-08-16

### Verändert
- Berichtstitel auf den inhaltlichen Schwerpunkt Layer Editing umgestellt

---

## [16.0] - 2026-08-16

### Erstellt
- Forschungsbericht v5 mit OLED-Design und roter/gruener Befundfarbung erstellt
- GitHub Pages Deployment fuer den Forschungsbericht eingerichtet
- Sechs externe Forschungsquellen von Anthropic und OpenAI als Quellenkarten eingebunden
- Zahlenkonsistenz-Pruefung im Validator-Skript ergaenzt
- Legacy-Kennzeichnung fuer die nicht angebundene Brain-Pipeline gesetzt

### Verändert
- Quellenkarten auf 16:9-Format mit offiziellen Seiten-Screenshots umgestellt
- Färbung nach dokumentiertem Regelwerk vereinheitlicht (nur messbare Befunde)
- D1-Pipeline und D2-Emotionsdiagramm luftiger gestaltet
- Sidebar-Status als Stichpunkte ohne Pillen dargestellt
- Em- und En-Dashes im Berichtstext entfernt

### Gelöscht
- Ueberfluessige Hinweisboxen und Meta-Informationen aus dem Bericht entfernt
- Nicht angebundenen Agentenpfad aus dem Bericht entfernt

---

## [15.0] - 2026-07-04

### Erstellt
- Remote-Endpoint `/emotions/reset` fuer echte CLI-Resets erstellt
- Provider-Auswahl fuer Forschungssessions mit vLLM, Ollama und Groq erstellt
- Provider-spezifische Modell-Presets fuer den Forschungsharness erstellt
- Tests fuer providerfaehige Forschungskonfiguration ergaenzt
- API-Version 15.0 fuer den reparierten Runtime-Stand gesetzt

### Verändert
- Emotions-Fallback senkt Energy nicht mehr pauschal bei jedem Turn
- Positive und neugierige Interaktionen koennen Energy wieder leicht erhoehen
- Desktop-Sidebar ist jetzt per Header-Button ein- und ausklappbar
- Forschungssessions setzen Runtime-Provider und Modell passend zur Auswahl
- CLI `/resetemotions` nutzt remote jetzt einen schreibenden Reset statt nur Status zu lesen

### Gelöscht
- 3D-Visualizer-Route und Navigation aus dem Frontend entfernt
- React-Three-Fiber, Three.js, Drei und Postprocessing aus den Frontend-Abhaengigkeiten entfernt
- Unbenutzten `/visualizer` API-Endpunkt entfernt
- Visualizer-Komponenten und Canvas-spezifische Mobile-CSS entfernt
- Visualizer-Erwartung aus API-Contract-Test und aktueller Doku entfernt

---

## [14.0] - 2026-07-02

### Erstellt
- Gemma 4 E4B als lokale Modellalternative hinzugefuegt
- Gemma 4 26B-A4B als NF4-Option fuer komplexe Tests hinzugefuegt
- Modell-Presets in den Einstellungen erstellt
- Steering-Restart-Modal mit Fortschrittsanzeige erstellt
- `/model` Befehl fuer die Terminal-CLI erstellt

### Verändert
- vLLM-Generierung nutzt jetzt modell-spezifische Defaults
- Steering-Backend erkennt Qwen und Gemma 4 getrennt
- Steering-Server kann Modelle per Hot-Swap neu laden
- Alignment-Tests koennen das Laufzeitmodell auswaehlen
- Dokumentation beschreibt Qwen- und Gemma-4-Betrieb gemeinsam

### Gelöscht
- Qwen-only-Erkennung im Steering-Pfad entfernt
- Fest verdrahtete Qwen-Thinking-Annahme entfernt
- Manuelle Modellwechsel ohne Default-Anpassung entfernt
- Fehlende Restart-Status-Sicht im Frontend entfernt
- Veralteter Versionsstand 13.6 in der UI entfernt

---

## [0.11.1] - 2026-06-11

### Verändert
- `settings.chain_of_thought` steuert jetzt tatsaechlich das Reasoning (vLLM: `enable_thinking`, Ollama: `think`, Groq: CoT-Prompt)
- `CHAIN_OF_THOUGHT_INSTRUCTION` mit echtem deutschem CoT-Prompt befuellt (vorher leer)

### Erstellt
- `/thinking` Command in der CLI (`true`/`false`/Status)
- Thinking-Toggle-Button im Frontend-Chat-Header
- Reasoning-Option bei der Konfiguration neuer Alignment-Test-Durchlaeufe
- Dokumentation in `docs/workflows.md` (Abschnitt "Chain of Thought / Reasoning")

## [0.11.0] - 2026-05-14

### Erstellt
- Live-Timer während der Generierung unter der Denk-Animation
- Timing-Metriken im Info-Popup (TTFT, Thinking-Zeit, Antwort-Zeit, Tokens)
- Token-Budget-Steuerung für Thinking und Antwort getrennt
- Effizienteres API-Response-Handling für Cerebras

### Verändert
- Config-System auf Root-Config umgestellt für zentrale Verwaltung
- Memory-Engine Performance verbessert mit Batch-Operationen
- Short-Term Memory V2 mit optimierter Sortierung und Filterung
- vLLM-Service-Config und Deployment-Dokumentation aktualisiert

### Gelöscht
- Veraltete API-Config-Struktur (APIs/__init__.py vereinfacht)
- Redundante Config-Beispiele aus secrets_example.py entfernt

---

## [0.10.3] - 2026-05-14

### Erstellt
- Reasoning-Tokens werden live im Stream ausgegeben (vorher nur gezählt aber nie gesendet)

### Verändert
- max_tokens von 1024 auf 2048 erhöht für ausreichenden Platz bei aktivem Thinking-Modus

### Gelöscht
- (keine)

---

## [0.10.2] - 2026-05-14

### Erstellt
- Explizite CORS-Header im Streaming-Response für bessere Browser-Kompatibilität

### Verändert
- (keine)

### Gelöscht
- (keine)

---

## [0.10.1] - 2026-05-14

### Erstellt
- Info-Button (i) pro Chat-Nachricht mit Hover-Preview und Detail-Popup
- Detail-Popup zeigt LTM-Erinnerungen mit Relevanz-Prozent, Emotion-Deltas und Steering-Info
- Memory-Limit auf 12 Erinnerungen reduziert für schnellere Kontext-Verarbeitung

### Verändert
- Metadata jetzt vollständig im Frontend gespeichert für Info-Popup-Zugriff
- LTM/STM-Anhängung im Prompt geprüft und als korrekt bestätigt

### Gelöscht
- (keine)

---

## [0.10.0] - 2026-05-14

### Erstellt
- Thinking-Modus für Qwen3.5 aktiviert - Reasoning live als hellgraue Box vor der Antwort
- Provider-Anzeige in UI (vllm, ollama) neben Modellname
- Quick-Classify für triviale Eingaben (Hallo, ok, danke) ohne KI-Aufruf

### Verändert
- Emotion-Steering sanfter eingestellt - keine verstümmelten Antworten mehr
- Intent-Analyse verschlankt von 237 auf 50 Zeilen Prompt für schnellere Erkennung
- Token-Streaming mit Thinking-Trennung für flüssigere Darstellung
- Kurzzeitgedächtnis-Schreibvorgänge in Hintergrund-Thread ausgelagert

### Gelöscht
- Doppelte Query-Extraction (zweimal derselbe KI-Aufruf pro Eingabe) eliminiert
- Zweite Memory-Suche entfernt - Ergebnisse werden direkt weitergereicht
