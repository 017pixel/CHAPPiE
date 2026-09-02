# Security-Audit vom 2. September 2026

Scope: API, Streaming, Session- und Memory-Zugriff, Konfiguration, Deployment, Abhängigkeiten, Forschungsartefakte und lokale Git-Historie. Der Audit bewertet den Repository-Stand dieser Cleanup-Migration. Er ist kein Penetrationstest einer laufenden Installation.

## Zusammenfassung

| Schwere | Befund | Stand |
|---|---|---|
| Kritisch | ChromaDB-Advisories ohne verfügbare Fix-Version | offen, lokal eingegrenzt |
| Hoch | Unauthentifizierte Steuer- und Datenendpunkte bei extern bindendem Deployment | offen, Deployment-Entscheidung nötig |
| Hoch | Pfad-Traversal über Chat-Session-IDs | behoben und getestet |
| Mittel | Wildcard-CORS in Web- und Steering-API | offen, kompatibel dokumentiert |
| Mittel | Keine zentrale Rate- und Größenbegrenzung | offen |
| Mittel | Schreibende Modell-Tools ohne wirksame Freigabegrenze | offen |
| Niedrig | Forschungslogs können Gesprächs- und Bewertungsinhalte enthalten | organisatorische Prüfung nötig |

## Kritisch: bekannte ChromaDB-Schwachstellen

**Ort:** `requirements/runtime.txt`, `memory/memory_engine.py`

**Szenario:** `pip-audit` löst die aktuelle erlaubte ChromaDB-Version 1.5.9 auf und meldet `CVE-2026-45829`, `CVE-2026-45830`, `CVE-2026-45831` und `CVE-2026-45833`. Für keine Meldung ist am Audit-Tag eine korrigierte Version angegeben. Die Schwachstellen betreffen vor allem Chroma-Serverendpunkte, Autorisierung und dynamisch ladbare Embedding-Modelle.

**Lokale Eingrenzung:** CHAPPiE startet keinen Chroma-HTTP-Server. Die Memory Engine verwendet `PersistentClient` beziehungsweise einen In-Process-Client, eigene lokal erzeugte Embeddings und kein `trust_remote_code`. Das reduziert die direkte Angriffsfläche, beseitigt aber nicht das Abhängigkeitsrisiko.

**Empfehlung:** Chroma niemals separat ins Netz binden. Keine fremden Modell-Repositories oder Collection-Konfigurationen annehmen. Upstream-Advisories beobachten und auf die erste korrigierte Version aktualisieren. Ein ungeprüfter Downgrade unter die bestehende Mindestversion ist wegen Daten- und API-Kompatibilität keine sichere automatische Reparatur.

```text
uvx pip-audit -r requirements/runtime.txt --progress-spinner=off
```

Referenzen: [CVE-2026-45829](https://nvd.nist.gov/vuln/detail/CVE-2026-45829), [CVE-2026-45830](https://nvd.nist.gov/vuln/detail/CVE-2026-45830), [CVE-2026-45831](https://nvd.nist.gov/vuln/detail/CVE-2026-45831), [CVE-2026-45833](https://nvd.nist.gov/vuln/detail/CVE-2026-45833)

## Hoch: API ohne Authentifizierung

**Ort:** `api/main.py`, `api/routers/`, `deploy/chappie-web.service`

**Szenario:** Der Deployment-Service bindet die API an `0.0.0.0:8010`. Ohne vorgeschaltete Zugriffskontrolle kann ein erreichbarer Client Chats, Sessions, Memory, Kontextdateien, Settings, Emotionen, Steering-Neustarts und Training lesen oder verändern. Die Settings-Antwort liefert den Groq-Key nicht aus, aber der Settings-Endpunkt akzeptiert einen neuen Key.

**Empfehlung:** Bis zur Implementierung einer stabilen Authentifizierung nur an Loopback oder ein geschütztes privates Netz binden. Bei externer Freigabe einen authentifizierenden Reverse Proxy einsetzen. Langfristig eine zentrale FastAPI-Dependency für Bearer- oder Session-Authentifizierung und eine Autorisierungsprüfung für jede schreibende Route ergänzen.

```python
def require_operator(credentials = Depends(bearer_scheme)):
    if not secrets.compare_digest(credentials.credentials, configured_token):
        raise HTTPException(status_code=401, detail="Nicht autorisiert")
```

Diese Migration ändert die Authentifizierung nicht still, weil das ein externer Vertrags- und Deploymentwechsel wäre.

## Hoch: Pfad-Traversal bei Chat-Sessions

**Ort:** `memory/chat_manager.py`, Symbol `ChatManager._get_file_path`

**Szenario vor der Korrektur:** Eine Session-ID wie `../outside` wurde direkt in einen Dateipfad eingesetzt. Dadurch konnten JSON-Dateien außerhalb von `data/chat_sessions/` gelesen, überschrieben oder gelöscht werden.

**Korrektur:** Session-IDs erlauben nur noch 1 bis 128 ASCII-Zeichen aus Buchstaben, Ziffern, Unterstrich und Bindestrich, beginnend mit einem alphanumerischen Zeichen. Die zentrale Pfadfunktion lehnt ungültige IDs zusätzlich ab. Löschen verweigert ungültige IDs. UUID-basierte bestehende Sessions bleiben kompatibel.

```python
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,127}$")
```

**Nachweis:** `tests/test_chat_manager_persistence.py` prüft, dass eine manipulierte ID weder eine äußere Datei liest noch löscht.

## Mittel: permissives CORS

**Ort:** `api/main.py`, `brain/steering_api_server.py`

**Szenario:** Beide APIs erlauben jede Origin. Browser können dadurch aus beliebigen Webseiten Anfragen an erreichbare lokale oder private CHAPPiE-Dienste senden. `allow_credentials=False` begrenzt Cookie-Risiken, ersetzt aber keine Origin- oder API-Zugriffskontrolle.

**Empfehlung:** Erlaubte Origins zentral in `config/` konfigurieren und im Deployment auf die konkrete Frontend-Origin begrenzen. Steering sollte im Normalbetrieb ausschließlich auf Loopback erreichbar sein.

```python
allow_origins=["http://127.0.0.1:4173", "http://localhost:4173"]
```

Die Wildcard bleibt in diesem Cleanup kompatibel erhalten, bis die tatsächlich benötigten Deployment-Origins feststehen.

## Mittel: keine zentrale Rate- und Größenbegrenzung

**Ort:** `api/routers/chat.py`, `api/routers/training.py`, `api/routers/runtime.py`, `api/schemas/__init__.py`

**Szenario:** Teure Chat-, Streaming-, Restart- und Trainingsoperationen besitzen keine zentrale Request-Rate. Chat- und Kontexttexte haben Mindest-, aber keine angemessenen Höchstgrenzen. Ein erreichbarer Client kann CPU, GPU, Speicher oder Dateisystem belasten.

**Empfehlung:** Limits am Reverse Proxy und zusätzlich pro Identität in der API durchsetzen. Textfelder und Override-Dictionaries erhalten fachlich begründete Maximalgrößen. Streaming-Verbindungen brauchen ein gleichzeitiges Verbindungs- und Zeitlimit.

```text
Beispielgrenzen: Request-Body, Requests pro Minute, parallele Streams, Laufzeit pro Generation
```

## Mittel: schreibende Modell-Tools ohne Freigabegrenze

**Ort:** `memory/function_registry.py`

**Szenario:** Modellgenerierte Toolaufrufe können Daily Info sowie Soul-, User- und Preference-Kontext verändern. Das Feld `requires_approval` existiert, wird für diese Schreibaktionen aber nicht als wirksame Laufzeitgrenze eingesetzt. Prompt-Injection kann dadurch persistente Inhalte beeinflussen.

**Empfehlung:** Schreibende Funktionen mit `requires_approval=True` markieren und vor dem Handler-Aufruf eine zentrale Freigabe oder eine eng begrenzte Policy prüfen. Nutzereingaben, Toolargumente und gespeicherte Modelltexte bleiben als nicht vertrauenswürdige Daten behandelt.

```python
if function.requires_approval and not approval_context.allows(function.name):
    raise PermissionError("Freigabe erforderlich")
```

## Niedrig: Forschungs- und Sessiondaten

**Ort:** `forschung/sessions/`, `forschung/runs/`, `forschung/report/workspace/`

Die Dateien sind laut Migrationsplan Forschungsbelege und wurden nicht pauschal gelöscht. Ein Muster-Scan fand keine aktiven API-Key- oder Private-Key-Signaturen. Inhaltliche Gesprächsdaten können trotzdem personenbezogen oder vertraulich sein. Vor öffentlicher Weitergabe ist eine separate fachliche Anonymisierungs- und Einwilligungsprüfung notwendig. Blind-Review-`key`-Dateien enthalten Versuchszuordnungen, keine API-Schlüssel.

## Positive Kontrollen

- Aktive Konfigurations- und Secret-Dateien sind gitignored; getrackt ist in `config/APIs/` nur der Paketmarker.
- Der lokale Arbeitsstand und die lokale Git-Historie zeigten keine Muster für OpenAI-/Groq-Keys oder private Schlüssel.
- Settings-Antworten enthalten keinen Groq-API-Key.
- Kein `shell=True`, kein `eval` auf Nutzdaten und kein `dangerouslySetInnerHTML` im aktiven Scope gefunden.
- Kontextdatei-Routen verwenden eine feste Namens-Whitelist.
- Steering bindet im direkten Python-Entrypoint standardmäßig an Loopback.
- `npm audit` meldet für Produktions- und Entwicklungsabhängigkeiten null bekannte Schwachstellen.
- `pip-audit` meldet für `requirements/ci.txt` null bekannte Schwachstellen.

## Verifikation

```bash
python3 tests/test_chat_manager_persistence.py
python3 tests/test_api_contract.py
uvx pip-audit -r requirements/ci.txt --progress-spinner=off
uvx pip-audit -r requirements/runtime.txt --progress-spinner=off
cd frontend && npm audit
```

Der ChromaDB-Scan bleibt erwartbar rot, solange Upstream keine korrigierte Version veröffentlicht und der betroffene Dependency-Vertrag nicht sicher migriert werden kann.
