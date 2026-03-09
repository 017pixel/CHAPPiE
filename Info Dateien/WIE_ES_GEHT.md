# WIE ES GEHT

Diese Datei ist jetzt eine **kurze Brücke** auf die neue, fachlich sauberere Dokumentation.

## Wenn du verstehen willst, wie CHAPPiE funktioniert

- Gehirn-Metapher und Komponenten: [`docs/architecture.md`](../docs/architecture.md)
- Anfrage-, Schlaf- und Trainingsabläufe: [`docs/workflows.md`](../docs/workflows.md)
- lokale Qwen-3.5-Strategie und API-Fallbacks: [`docs/local-models.md`](../docs/local-models.md)
- lokaler Steering-Endpoint und Layer-Editing: [`docs/vLLM-Setup.md`](../docs/vLLM-Setup.md)
- Orientierung in der Codebasis: [`docs/project-map.md`](../docs/project-map.md)

## Kurz erklärt

CHAPPiE simuliert keine Biologie 1:1, sondern bildet **Funktionen des menschlichen Gehirns** softwareseitig nach:

- Wahrnehmung
- emotionale Gewichtung
- Gedächtnisarbeit
- Planung
- Lernen über Zeit
- innere Zustände und Entwicklung

Die Hauptschichten sind:

- `brain/` für die Agenten-Orchestrierung
- `memory/` für Erinnern, Vergessen und Konsolidierung
- `life/` für Needs, Goals, Habits, Planning, Forecast und Timeline
- `web_infrastructure/` für UI und Bedienung
- `Chappies_Trainingspartner/` für den autonomen Lernmodus

## Wichtigster Modellhinweis

Die Projektdokumentation priorisiert jetzt **lokale Qwen-3.5-Modelle**. APIs sind als Fallback dokumentiert, nicht als erste Wahl. Fuer echtes Emotion-Steering laeuft CHAPPiE ueber einen steering-faehigen lokalen OpenAI-Endpoint.

In der Streamlit-UI sieht man das jetzt explizit:

- 7 Vitalzeichen als Basis fuer das Endausgabe-Steering
- Basisvektoren und Composite-Zusatzmuster getrennt
- Brain Monitor mit sichtbarer Trennung zwischen Gehirnstruktur und finaler Modellsteuerung

Details: [`docs/local-models.md`](../docs/local-models.md)

