# Changelog

Alle Änderungen werden in 5 Stichpunkten dokumentiert. Keine Code-Anzeigen!

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
- Provider-Anzeige in UI (vllm, ollama, groq) neben Modellname
- Quick-Classify für triviale Eingaben (Hallo, ok, danke) ohne KI-Aufruf

### Verändert
- Emotion-Steering sanfter eingestellt - keine verstümmelten Antworten mehr
- Intent-Analyse verschlankt von 237 auf 50 Zeilen Prompt für schnellere Erkennung
- Token-Streaming mit Thinking-Trennung für flüssigere Darstellung
- Kurzzeitgedächtnis-Schreibvorgänge in Hintergrund-Thread ausgelagert

### Gelöscht
- Doppelte Query-Extraction (zweimal derselbe KI-Aufruf pro Eingabe) eliminiert
- Zweite Memory-Suche entfernt - Ergebnisse werden direkt weitergereicht
