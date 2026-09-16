# Laufzeitverträge

## Öffentliche Oberflächen

| Oberfläche | Einstieg | Stabiler Vertrag |
|---|---|---|
| FastAPI Chat | `api/routers/chat.py` | Request-Schema, Statuscodes und Antwortfelder |
| FastAPI Streaming | `POST /chat/stream` | SSE-Eventnamen, Datenfelder und Abschlussereignis |
| Session-Export | `GET /sessions/{session_id}/export?mode=standard` oder `debug` | versioniertes JSON, Emotionstimeline und optionales Debug-Archiv |
| lokale CLI | `chappie_brain_cli.py` | Argumente, Commands, Ausgabe und Exitcode |
| Remote-CLI | `chappie_brain_cli.py --remote` | API-URL und Fehlerdarstellung |
| Research | `forschung/session_runner.py` | isolierte Runtime-Optionen, Session- und Evidence-Dateien |
| Training | `Chappies_Trainingspartner/training_daemon.py` | Modul-Entrypoint, Config, PID, State und Stopverhalten |
| Frontend | `frontend/src/services/api.ts` | JSON-/SSE-Parsing und Nachrichtentypen |
| Brain-Factory | `brain.get_brain` | vLLM-, Ollama- und Groq-Adapter |

## Runtime-Kompatibilität

Folgende Namen bleiben unterstützt:

- `web_infrastructure.backend_wrapper.create_chappie_backend`
- `web_infrastructure.backend_wrapper.init_chappie`
- `web_infrastructure.backend_wrapper.CHAPPiEBackend`
- `web_infrastructure.backend_wrapper.CHAPPiERuntime`
- reine Wrapper-Helfer, die vor der schweren Runtime importierbar waren
- `brain.agents.steering_manager` als Re-Export
- `brain.brain_pipeline.BrainPipeline` und `get_brain_pipeline` für historische Tests

Neue interne Aufrufer verwenden `web_infrastructure.chappie_runtime`. Router greifen nur auf öffentliche Message-Builder zu.

## Interne Turn-Verträge

`TurnContext` enthält die normalisierte Eingabe, kopierte History, Session-ID, Streammodus, Zeitkontext und Runtime-Optionen. Sync und Stream erstellen diesen Vertrag über dieselbe Funktion.

`ResponseEnvelope` und `StreamEvent` typisieren interne Übergaben. Sie sind keine neue externe API-Version; die Runtime erzeugt weiterhin die bisherigen Dicts am Rand.

`GenerationGateway` hält keinen veralteten Brain-Verweis. Er löst den aktuellen Providerclient bei jedem Aufruf über die Runtime auf, damit Settings-Reloads auch nach der Modularisierung wirksam bleiben.

## Sideeffects und Fehlergrenzen

| Phase | Mögliche Sideeffects |
|---|---|
| Vorbereitung | Life- und Zeitkontext lesen/aktualisieren, Intent und Memories lesen |
| Tools | bestehende Kontextdatei- oder Memory-Aktionen |
| Generation | lokaler Provideraufruf, kein persistierter Chatwrite |
| Formatierung | Parser/Sanitizer, keine Persistenz |
| Abschluss | Life finalisieren, Chat und STM persistieren, Sleep triggern |

Ein Providerfehler wird in die bestehende nutzerseitige Fehlerform überführt. Ein erfolgreicher Stream persistiert denselben fachlichen Abschluss wie der synchrone Pfad. Der vorhandene Hintergrundpfad für STM bleibt zeitlich asynchron.

## Providervertrag

Die Web-Runtime meldet und verwendet vLLM. Ollama und Groq bleiben in der allgemeinen Brain-Factory und in nicht-webbasierten Subsystemen verfügbar. Eine Änderung dieser Rollen oder der Fallback-Reihenfolge ist ein eigener Funktionsentscheid.

## Persistenz

Memory-, Life-, Chat- und Sessionformate wurden nicht geändert. `training_config.json` ist die einzige Pfadmigration: Der zentrale Zielpfad ist `config/training_config.json`; die alte Root-Datei bleibt lesbar.

## Session-Export

Der Export liest die vorhandenen Chat-Nachrichten und das dauerhafte Ereignisarchiv. `standard` enthält die sichtbaren Nachrichten, UI-Metadaten, den aktuellen Runtime-Zustand und die Emotionsänderungen. `debug` ergänzt die vollständigen gespeicherten Nachrichten-Metadaten, den aktuellen Debug-Logger und dekodierte Event-Store-Zeilen.

Der API-Endpunkt schreibt parallel eine private Fallback-Datei unter `data/session_exports/` und liefert deren Serverpfad zurück. Der API-Endpunkt sendet selbst keine Clipboard-Steuersequenz. Die Remote-CLI serialisiert die Exportantwort und sendet sie über OSC 52 an das Terminal. Zugangsdaten und Secret-Felder werden in beiden Exportstufen entfernt.
