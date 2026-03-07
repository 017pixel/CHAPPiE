# CHAPPiE Dokumentation

Diese Dokumentation ist der zentrale Einstieg für Menschen und KI-Agents, die das Projekt verstehen, starten, testen oder weiterentwickeln wollen.

## Schnellnavigation

- [Projektüberblick](../README.md)
- [Agent-Arbeitsanweisung](../agent.md)
- [Architektur & Gehirn-Metapher](architecture.md)
- [Workflows](workflows.md)
- [Lokale Modelle & Fallbacks](local-models.md)
- [Projektkarte / Ordnerstruktur](project-map.md)
- [Testing](testing.md)
- [Deployment & Serverbetrieb](deployment.md)

## Empfohlene Lesereihenfolge

### Für neue Entwickler:innen
1. [README.md](../README.md)
2. [Architektur & Gehirn-Metapher](architecture.md)
3. [Workflows](workflows.md)
4. [Projektkarte](project-map.md)
5. [Testing](testing.md)

### Für KI-Agents
1. [agent.md](../agent.md)
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
| `agent.md` | Arbeitsregeln für Agents vor Änderungen oder Pushes |
| `docs/architecture.md` | Gehirn-Metapher, Systemschichten, Quellpfade |
| `docs/workflows.md` | Ablauf einer Anfrage, Schlafphase, Training, UI-Flows |
| `docs/local-models.md` | Qwen-3.5-Strategie, vLLM/Ollama/API-Rollen |
| `docs/project-map.md` | Orientierung in der Codebasis |
| `docs/testing.md` | Teststrategie, sichere Checks, manuelle Smoke-Tests |
| `docs/deployment.md` | systemd, Services, Deploy-Skripte, Serverbetrieb |
| `tests/README.md` | Konkrete Testdateien nach Typ eingeordnet |

## Doku-Prinzipien in diesem Repository

- **Ein Einstieg, viele Deep Dives:** Die Root-README bleibt kompakt und verweist auf Details.
- **Lokale Modelle zuerst:** Qwen-3.5 lokal ist die bevorzugte Ausrichtung.
- **API nur als Fallback:** Cloud-Provider sind sekundär.
- **Docs vor Push prüfen:** Jede strukturelle oder funktionale Änderung muss auf Doku-Relevanz geprüft werden.
- **Pfadgenaue Links:** Wichtige Aussagen sollen auf konkrete Dateien verweisen.

## Legacy-Hinweis

Einige ältere Dateien in `Info Dateien/` bleiben als kurze Brücken erhalten. Die inhaltliche Hauptquelle ist jetzt jedoch `docs/` plus `README.md` und `agent.md`.

