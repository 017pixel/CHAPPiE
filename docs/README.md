# CHAPPiE Dokumentation

Diese Dokumentation ist der zentrale Einstieg für Menschen und KI-Agents, die das Projekt verstehen, starten, testen oder weiterentwickeln wollen.

## Schnellnavigation

- [Projektüberblick](../README.md)
- [Agent-Arbeitsanweisung](../AGENTS.md)
- [Architektur & Gehirn-Metapher](architecture.md)
- [Laufzeitverträge](runtime-contracts.md)
- [Workflows](workflows.md)
- [Lokale Modelle & Fallbacks](local-models.md)
- [vLLM-Setup Schritt für Schritt](vLLM-Setup.md)
- [Projektkarte / Ordnerstruktur](project-map.md)
- [Testing](testing.md)
- [Deployment & Serverbetrieb](deployment.md)
- [Security-Audit vom 2. September 2026](security-audit-2026-09-02.md)
- [Repository-Cleanup und Migration](repository-cleanup.md)
- [Legacy-Code](../Legacy-Code/README.md)

## Empfohlene Lesereihenfolge

### Für neue Entwickler:innen
1. [README.md](../README.md)
2. [Architektur & Gehirn-Metapher](architecture.md)
3. [Workflows](workflows.md)
4. [Projektkarte](project-map.md)
5. [Testing](testing.md)

### Für KI-Agents
1. [AGENTS.md](../AGENTS.md)
2. [README.md](../README.md)
3. [Projektkarte](project-map.md)
4. [Architektur](architecture.md)
5. Relevante Detailseiten je nach Aufgabe

### Für Betrieb / Server
1. [README.md](../README.md)
2. [Lokale Modelle & Fallbacks](local-models.md)
3. [Deployment & Serverbetrieb](deployment.md)
4. [Testing](testing.md)

## Wofür welche Datei gedacht ist

| Datei | Zweck |
|---|---|
| `README.md` | Produkt- und Projektüberblick, Einstieg, Links |
| `AGENTS.md` | Arbeitsregeln für Agents vor Änderungen oder Pushes |
| `docs/architecture.md` | Gehirn-Metapher, Systemschichten, Quellpfade |
| `docs/runtime-contracts.md` | öffentliche API-, SSE-, CLI-, Provider- und Persistenzverträge |
| `docs/workflows.md` | Ablauf einer Anfrage, Schlafphase, Training, UI-Flows |
| `docs/local-models.md` | Qwen-3.5-Strategie, vLLM/Ollama/API-Rollen |
| `docs/vLLM-Setup.md` | konkretes Setup fuer vLLM + Qwen 3.5 + Layer Editing |
| `docs/project-map.md` | Orientierung in der Codebasis |
| `docs/testing.md` | Teststrategie, sichere Checks, manuelle Smoke-Tests |
| `docs/deployment.md` | systemd, Services, Deploy-Skripte, Serverbetrieb |
| `docs/security-audit-2026-09-02.md` | Findings, Korrekturen und offene Deployment-Risiken |
| `docs/repository-cleanup.md` | Baseline, Entscheidungen, Migration und Rollback |
| `tests/README.md` | Konkrete Testdateien nach Typ eingeordnet |

## Doku-Prinzipien in diesem Repository

- **Ein Einstieg, viele Deep Dives:** Die Root-README bleibt kompakt und verweist auf Details.
- **Lokale Modelle zuerst:** Qwen-3.5 lokal ist die bevorzugte Ausrichtung.
- **Webpfad eindeutig:** vLLM ist produktiv fest; Ollama und Groq bleiben unterstützte Nebenpfade.
- **Docs vor Push prüfen:** Jede strukturelle oder funktionale Änderung muss auf Doku-Relevanz geprüft werden.
- **Pfadgenaue Links:** Wichtige Aussagen sollen auf konkrete Dateien verweisen.

## Legacy-Hinweis

Einige ältere Dateien in `Info Dateien/` bleiben als kurze Brücken erhalten. Die inhaltliche Hauptquelle ist jetzt jedoch `docs/` plus `README.md` und `AGENTS.md`.
## Trace-Hinweis

Die Debug-Doku soll die Ursache-Wirkung-Kette klar lesbar machen: Input, Memory, Emotion, Steering und Ton gehoeren gemeinsam beschrieben, nicht getrennt als Rohdatenliste.
