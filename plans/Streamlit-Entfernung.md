# CHAPPiE Streamlit Entfernung und Frontend-Neuaufbau

Stand: 29.03.2026

Dieses Dokument ist die Arbeitsgrundlage fuer den kompletten Umbau der Weboberflaeche von CHAPPiE weg von Streamlit hin zu einem separaten React-Frontend mit FastAPI-Backend.

## Ziel

CHAPPiE soll frontend-seitig komplett neu gebaut werden.

Das bedeutet:

- kein Streamlit mehr
- keine UI-Logik mehr im Python-Code
- klares Backend-Frontend-Splitting
- gleiche Fachfunktionalitaet wie heute
- bessere Performance, bessere Struktur, bessere Erweiterbarkeit
- Vorbereitung fuer Animationen, Audio, spaeter 3D und komplexeres State-Management

Das Backend bleibt fachlich gleich und wird nur sauber hinter eine API gesetzt.

## Warum wir das machen

Streamlit ist fuer CHAPPiE zu eng und zu träge geworden.

Die aktuellen Probleme sind:

- jede Interaktion ist zu stark an Request-Response und Re-Render gekoppelt
- UI und Fachlogik sind in Python vermischt
- feingranulares State-Management ist schwer
- Animationen und echte Echtzeit-Interaktion sind unnatuerlich
- spaetere 3D- oder Audio-Features sind in Streamlit technisch unpassend
- die Frontend-Schicht ist schwer sauber zu erweitern

Das Ziel ist eine echte Web-App:

- React fuer UI und State
- React Three Fiber und Three.js fuer visuelle/3D-Komponenten
- FastAPI als API-Schicht zum bestehenden Backend
- Tailwind CSS fuer Styling
- klare Trennung zwischen Darstellung und Logik

## Aktueller Zustand

### Was heute die UI traegt

Die komplette Streamlit-Schicht sitzt im Wesentlichen hier:

- `app.py`
- `web_infrastructure/backend_wrapper.py`
- `web_infrastructure/chat_ui.py`
- `web_infrastructure/command_handler.py`
- `web_infrastructure/components.py`
- `web_infrastructure/context_ui.py`
- `web_infrastructure/growth_dashboard_ui.py`
- `web_infrastructure/life_dashboard_ui.py`
- `web_infrastructure/memories_ui.py`
- `web_infrastructure/settings_ui.py`
- `web_infrastructure/sidebar_ui.py`
- `web_infrastructure/state_manager.py`
- `web_infrastructure/styles.py`
- `web_infrastructure/training_ui.py`
- `web_infrastructure/ui_utils.py`

Diese Schicht ist stark mit Streamlit verheiratet.

### Was bereits sauberes Backend ist

Diese Bereiche sollen erhalten bleiben:

- `brain/`
- `memory/`
- `life/`
- `Chappies_Trainingspartner/`
- `config/`
- `data/`
- `chappie_brain_cli.py`
- `main.py`

Wichtig:

- `brain/steering_api_server.py` ist bereits FastAPI und bleibt als Modell-/Steering-Server bestehen
- das ist nicht die neue App-API
- die neue App-API ist ein eigener Layer

### Wichtige bestehende Backend-Funktionen

Die heutige UI ruft bereits Funktionen auf, die sich gut in eine API ueberfuehren lassen:

- `get_status()`
- `_get_emotions_snapshot()`
- `process()`
- `handle_command()`
- `get_emotion_layer_config()`
- `update_emotion_layer_config()`
- Chat-Session-Persistenz ueber `memory/chat_manager.py`
- Life-Snapshot ueber `life/service.py`
- Debug-Daten ueber `memory/debug_logger.py`
- Steering-Daten ueber `brain/agents/steering_manager.py`
- Training-Daten ueber `Chappies_Trainingspartner/daemon_manager.py`

## Zielarchitektur

### 1. Python Backend

Das Backend bekommt eine eigene FastAPI-App.

Empfohlene neue Struktur:

- `api/main.py`
- `api/routers/`
- `api/schemas.py`
- `api/services/`
- `api/dependencies.py`

Diese Schicht:

- importiert keine Streamlit-Module
- enthaelt keine UI-Renderlogik
- liefert nur JSON, Streams und Statusdaten
- ruft die bestehende CHAPPiE-Fachlogik auf

### 2. React Frontend

Das neue Frontend liegt getrennt im eigenen Ordner.

Empfohlene neue Struktur:

- `frontend/`
- `frontend/src/pages/`
- `frontend/src/components/`
- `frontend/src/features/`
- `frontend/src/hooks/`
- `frontend/src/store/`
- `frontend/src/services/`
- `frontend/src/lib/`
- `frontend/src/assets/`

Technische Basis:

- Vite
- React
- TypeScript
- Tailwind CSS
- Zustand fuer UI-State
- TanStack Query fuer Server-State
- React Router fuer Seiten
- React Three Fiber / Three.js fuer 3D-Panel

### 3. Laufzeit-Aufteilung

Die neue Laufzeit ist getrennt:

- Backend: FastAPI auf eigenem Port
- Frontend: React Dev Server oder statische Build-Auslieferung
- Modellserver: bestehender Steering-Server bleibt separat auf seinem Port

Wichtig:

- Port-Konflikte vermeiden
- Frontend darf nie direkt auf den Modellserver zeigen
- Frontend spricht nur die App-API
- App-API spricht intern mit Brain, Memory, Life und Training

## Entscheidungsstand

Diese Entscheidungen sind fuer den Umbau bereits festgelegt:

- Frontend-Basis: Vite + React + TypeScript
- 3D-Scope: erst als eigenes Panel, nicht als komplette 3D-App
- API-Transport: REST + SSE
- Styling: Tailwind CSS
- Icons: Google Material Icons
- State-Management: Zustand + Query-basierte Serverdaten
- Python-Backend bleibt fachlich gleich, wird aber von der UI entkoppelt

## Soll-Zustand der App

Die neue Web-App soll dieselben Informationen anzeigen und dieselben Aktionen ausfuehren koennen wie die alte Streamlit-Oberflaeche.

Pflichtfunktionen:

- Chat
- Session-Verlauf
- Slash-Commands
- Memory-Ansicht
- Context-Ansicht
- Settings
- Life Dashboard
- Growth Dashboard
- Training Control
- Debug Monitor
- Emotion Steering / Layer Editing
- 3D-Panel

Zusatznutzen:

- bessere Performance
- echtes State-Management
- fluessigere Interaktionen
- bessere Animationen
- zukunftssichere Struktur fuer neue Features

## API-Vertrag

Die neue FastAPI-Schicht muss die bisherige UI in saubere Endpunkte zerlegen.

### Kernendpunkte

| Bereich | Route | Zweck |
|---|---|---|
| Health | `GET /health` | Basis-Check fuer Backend und Modellverfuegbarkeit |
| Status | `GET /status` | Modell, Emotionen, Life-Snapshot, Tagesstatus |
| Chat | `POST /chat` | Normale Chat-Anfrage als JSON |
| Chat-Stream | `POST /chat/stream` | SSE fuer flüssige Antwort- und Statusupdates |
| Command | `POST /command` | Slash-Commands und UI-Aktionen |
| Sessions | `GET /sessions` | Liste aller Chat-Sessions |
| Session | `GET /sessions/{id}` | Einzelne Session laden |
| Session anlegen | `POST /sessions` | Neue Session erstellen |
| Session aktualisieren | `PATCH /sessions/{id}` | Nachricht oder Metadata nachziehen |
| Session loeschen | `DELETE /sessions/{id}` | Session entfernen |
| Memories | `GET /memories` | Erinnerungen und Suchergebnisse |
| Life | `GET /life` | Life-Snapshot |
| Growth | `GET /growth` | Growth- und Timeline-Snapshot |
| Settings | `GET /settings` | Aktuelle Laufzeit-Konfiguration |
| Settings speichern | `POST /settings` | Modell-, Provider- und Runtime-Settings speichern |
| Emotionen | `GET /emotion-layer-config` | Aktuelle Layer-/Vektor-Konfiguration |
| Emotionen speichern | `POST /emotion-layer-config` | Layer Editing speichern |
| Training | `GET /training/status` | Trainigsstatus abrufen |
| Training steuern | `POST /training/action` | Start, Stop, Restart, Reload |
| Debug | `GET /debug` | Debug-Trace abrufen |

### Chat-Request

Der Chat-Request muss mindestens diese Felder koennen:

- `session_id`
- `message`
- `stream`
- `debug_mode`
- `command_mode`

Optional spaeter:

- `client_context`
- `attachments`
- `selected_tool`
- `override_settings`

### Chat-Response

Der Chat-Response muss mindestens diese Felder koennen:

- `session_id`
- `message_id`
- `user_message`
- `assistant_message`
- `metadata`
- `life_snapshot`
- `emotion_snapshot`
- `debug_entries`
- `sleep_status`
- `retry_history`

### SSE-Events

Wenn Streaming aktiv ist, sollte die API klare Event-Typen senden:

- `turn_started`
- `status`
- `delta`
- `message_part`
- `turn_finished`
- `turn_error`

Das Frontend darf niemals auf unklare Rohstrings angewiesen sein.

## Backend-Umbau

### 1. Streamlit komplett aus dem Backend entfernen

Im Python-Backend darf nach dem Umbau kein Streamlit mehr vorkommen.

Das heisst:

- alle `import streamlit` entfernen
- alle `st.*` Aufrufe entfernen
- keine Streamlit-Session-State-Nutzung mehr
- keine UI-Renderlogik im Python-App-Pfad

### 2. Backend-Logik aus `web_infrastructure/` herausziehen

Die heutige Datei `web_infrastructure/backend_wrapper.py` ist die groesste Schnittstelle zwischen UI und Fachlogik.

Diese Logik muss in einen echten Backend-Service umziehen.

Empfohlene Aufteilung:

- Session- und Chat-Verwaltung
- Chat-Verarbeitung
- Command-Verarbeitung
- Status/Ausgabe-Mapping
- Emotion-/Steering-Mapping
- Debug-Payload-Erzeugung
- Trainingsstatus-Mapping

### 3. UI-nahe Python-Dateien loeschen oder ersetzen

Diese Dateien sind Streamlit-spezifisch und sollen nach der Migration nicht mehr gebraucht werden:

- `app.py`
- `web_infrastructure/chat_ui.py`
- `web_infrastructure/command_handler.py`
- `web_infrastructure/components.py`
- `web_infrastructure/context_ui.py`
- `web_infrastructure/growth_dashboard_ui.py`
- `web_infrastructure/life_dashboard_ui.py`
- `web_infrastructure/memories_ui.py`
- `web_infrastructure/settings_ui.py`
- `web_infrastructure/sidebar_ui.py`
- `web_infrastructure/state_manager.py`
- `web_infrastructure/styles.py`
- `web_infrastructure/training_ui.py`

`web_infrastructure/ui_utils.py` kann nur dann noch gebraucht werden, wenn dort wirklich backend-agnostische Konstanten oder Transformer bleiben. Sonst ebenfalls entfernen oder in neue Backend-/Frontend-Orte aufteilen.

### 4. FastAPI statt Streamlit

Die neue App-API soll mit FastAPI gebaut werden.

Pflicht:

- `fastapi`
- `uvicorn`
- Pydantic-Models fuer alle Requests und Responses
- CORS von Anfang an korrekt setzen
- klare Validierung statt stiller Fehler

Wichtig:

- der bestehende Modellserver in `brain/steering_api_server.py` bleibt unberuehrt
- die neue App-API ist eine eigene FastAPI-App
- Port-Konflikt vermeiden

### 5. Bestehende Persistenz weiterverwenden

Die neue API soll vorhandene Persistenz weiter nutzen statt neu erfinden:

- Chat-Sessions ueber `memory/chat_manager.py`
- Emotionen ueber `memory/emotions_engine.py`
- Kontextdateien ueber `memory/context_files.py`
- Life-State ueber `life/service.py`
- Training ueber `Chappies_Trainingspartner/daemon_manager.py`

So bleibt die Fachlogik stabil.

## Frontend-Umbau

### 1. React-App als echte Weboberflaeche

Die neue React-App ist die einzige UI.

Sie soll:

- responsive sein
- modular sein
- keine Logik im UI doppelt erfinden
- alle Daten nur ueber die API holen
- kein direkter Zugriff auf Python-Interna

### 2. Seitenstruktur

Empfohlene Seiten:

- Chat
- Life
- Growth
- Memories
- Settings
- Training
- Debug
- 3D

### 3. Layout

Empfohlene Grundstruktur:

- linke Sidebar fuer Navigation und Status
- Hauptbereich fuer aktuelle Ansicht
- unten Chat-Komposer
- rechte bzw. aufklappbare Inspektor-Flächen fuer Debug, Memory und Settings
- 3D-Panel als eingebetteter Bereich, nicht als eigene Kernnavigation

### 4. Chat-Ansicht

Die Chat-Ansicht muss koennen:

- Nachrichten senden
- laufende Antwort anzeigen
- Commands als Buttons und als Text verarbeiten
- Reasoning und Debug sauber einklappen
- pending/processing sichtbar machen
- Session wechseln
- Session wiederherstellen

### 5. Life- und Growth-Ansicht

Diese Ansichten sollen dieselben Daten anzeigen wie die alte UI.

Wichtige Daten:

- Phase
- Aktivitaet
- Need-Fokus
- Stage
- Goals
- World Model
- Planning
- Forecast
- Social Arc
- Timeline
- Habit Dynamics
- Attachment Model
- Selbstmodell

### 6. Settings-Ansicht

Die Settings muessen folgende Bereiche abbilden:

- Hauptprovider
- Chat-Modell
- Intent-Analyse
- Query Extraction
- Emotionsanalyse
- Embeddings
- Trainingsmodelle
- Temperature
- Max Tokens
- Chain of Thought
- Memory Top-K
- Steering-Aktivierung
- emotion layer editing

### 7. Debug-Ansicht

Die Debug-Ansicht muss die alte Brain-Monitor-Tiefe erhalten.

Pflichtdaten:

- Input und Intent
- Step-1-Roh-JSON
- Tool-Orchestrierung
- Memory-Trace
- Emotionen vor/nachher
- raw delta
- applied delta
- softening
- Homeostasis
- Layer-Pipeline
- Global Workspace
- Action Plan
- Tone Decision
- Event-Log

### 8. 3D-Panel

Das 3D-Panel ist zuerst nur ein Visualizer.

Es soll:

- Emotionen als visuelles Objekt zeigen
- Life- und Statusdaten spiegeln
- Ladezustand und Aktivitaet sichtbar machen
- spaeter ausbaubar bleiben

Nicht-Ziel in der ersten Version:

- kein vollständiges 3D-Interface
- keine komplizierte Spiel- oder Metaverse-Logik
- kein Ersatz fuer die normalen Seiten

## Was bleibt

Diese Teile bleiben fachlich unveraendert:

- `brain/`
- `memory/`
- `life/`
- `Chappies_Trainingspartner/`
- `config/`
- `data/`
- `chappie_brain_cli.py`
- `main.py`
- `brain/steering_api_server.py`

Zusatz:

- die aktuelle Modellstrategie bleibt gleich
- lokale Qwen-3.5-Modelle bleiben zuerst
- vLLM bleibt bevorzugt
- APIs bleiben Fallback

## Was geloescht wird

Nach erfolgreicher Migration sollen diese Dinge verschwinden oder ersetzt sein:

- Streamlit-Abhaengigkeit aus `requirements.txt`
- `.streamlit/`
- `app.py`
- Streamlit-UI-Dateien in `web_infrastructure/`
- alte Streamlit-Referenzen in Doku, Tests und Setup-Skripten
- Streamlit-bezogene CI-Schritte
- `chappie-web.service` in der bisherigen Form

Wichtig:

- nichts loeschen, bevor React-Frontend und FastAPI-API Feature-Paritaet erreicht haben
- erst testen, dann entfernen
- vorher keine Backups oder Daten in `data/` anruehren

## Deployment-Ziel

Die bisherige Web-Startlogik ist zu ersetzen.

### Entwicklung

- Backend mit `uvicorn`
- Frontend mit `npm install` und `npm run dev`
- Backend-API und Frontend laufen getrennt

### Produktion

- Backend als eigener Service
- Frontend als eigener Build/Serve-Pfad
- Modellserver bleibt separat
- keine Streamlit-Startanweisung mehr

### Port-Plan

- Modellserver bleibt auf seinem Port
- App-API bekommt eigenen Port
- React-Frontend bekommt eigenen Port im Dev-Setup
- keine Port-Konflikte zulassen

## Typische Fehler, die vermieden werden muessen

### 1. CORS vergessen

Wenn CORS nicht korrekt gesetzt ist, kann das Frontend nichts laden.

Absicherung:

- CORS explizit konfigurieren
- lokale Dev-Origin erlauben
- spaeter Produktions-Origin sauber pflegen

### 2. Falsche Fetch-URL

Wenn das Frontend auf die falsche URL zeigt, sieht die App tot aus.

Absicherung:

- `VITE_API_BASE_URL` nutzen
- keine hardcodierten URLs im Code
- lokale und Produktions-URLs sauber trennen

### 3. Backend laeuft nicht

Wenn das Frontend startet, aber das Backend nicht, muss der Zustand klar angezeigt werden.

Absicherung:

- Health-Check beim Laden
- klare Fehlermeldung
- Retry-Logik
- Offline-Status in der UI

### 4. JSON-Format falsch

Wenn Request oder Response nicht zum Vertrag passt, brechen Chat und Settings.

Absicherung:

- Pydantic-Modelle
- API-Contract-Tests
- Frontend-Types
- SSE-Event-Definitionen

### 5. Port-Konflikte

Der Modellserver laeuft bereits separat.

Absicherung:

- App-API nicht auf denselben Port legen
- Frontend-Ports eindeutig halten
- Dokumentation mitziehen

### 6. Streamlit-Reste bleiben irgendwo haengen

Absicherung:

- volle Repo-Suche nach `streamlit`
- keine `st.`-Aufrufe im finalen Pfad
- keine Streamlit-Startkommandos in Docs oder Services

## Migrationsplan

### Phase 0: Bestand einfrieren

Ziel:

- aktuelle Funktionalitaet verstehen
- API-Vertraege festhalten
- Screens und Features inventarisieren

Arbeiten:

- alle heutigen Views erfassen
- alle Command-Pfade erfassen
- alle Status-Keys erfassen
- Debug-Payloads erfassen
- Life-/Growth-Datenfelder erfassen
- Chat-Session-Flow erfassen

Ergebnis:

- ein eindeutiger Plan fuer die API
- kein Feature geht verloren

### Phase 1: Backend-Service aus der UI loesen

Ziel:

- Python-Backend ohne Streamlit lauffaehig machen

Arbeiten:

- Streamlit aus Backend-Code entfernen
- Backend-Wrapper in pure Service-Logik ueberfuehren
- FastAPI-App anlegen
- Pydantic-Schemas anlegen
- CORS einrichten
- Status-, Chat- und Command-Routen bauen
- Session-Persistenz ueber API zugreifbar machen

Ergebnis:

- Backend laeuft alleine
- Frontend ist noch nicht fertig, aber die API existiert

### Phase 2: React-App aufsetzen

Ziel:

- neue UI parallel aufbauen

Arbeiten:

- Vite-Projekt anlegen
- Tailwind konfigurieren
- TypeScript-Basis einrichten
- App-Shell, Navigation und Layout bauen
- API-Service-Layer bauen
- Zustand fuer UI-State einfuehren
- Query-Layer fuer Serverdaten einfuehren

Ergebnis:

- neue Oberfläche laeuft
- erste Daten aus der API werden angezeigt

### Phase 3: Feature-Paritaet herstellen

Ziel:

- alle bisherigen UIs in React nachbauen

Arbeiten:

- Chat
- Memory
- Settings
- Life Dashboard
- Growth Dashboard
- Training
- Debug Monitor
- Emotion Steering
- Context Views
- Sessions

Ergebnis:

- neue UI kann fachlich alles, was die alte UI konnte

### Phase 4: 3D-Panel integrieren

Ziel:

- React Three Fiber / Three.js als echten Zusatz einfuehren

Arbeiten:

- 3D-Komponente bauen
- Datenbindung an Emotions- und Life-State
- Lade- und Fehlerzustand
- dezente Animationen
- keine Ueberladung

Ergebnis:

- visuelles Zusatzpanel funktioniert und ist wartbar

### Phase 5: Cutover

Ziel:

- Streamlit abschalten

Arbeiten:

- alte Web-Startpfade entfernen
- Streamlit-Dependencies entfernen
- Streamlit-Services ersetzen
- UI-Docs anpassen
- CI anpassen
- Restverweise entfernen

Ergebnis:

- nur noch React-Frontend + FastAPI-Backend

### Phase 6: Aufraeumen

Ziel:

- Altlasten beseitigen

Arbeiten:

- `app.py` loeschen
- `web_infrastructure/` loeschen oder nur dort erhalten, wo wirklich noch pure Helpers gebraucht werden
- `.streamlit/` loeschen
- Streamlit-Tests ersetzen
- veraltete Doku bereinigen

Ergebnis:

- sauber getrennte Architektur ohne Streamlit

## Testplan

### Backend-Tests

- Health-Endpoint pruefen
- Status-Endpoint pruefen
- Chat-Endpoint pruefen
- Streaming pruefen
- CORS pruefen
- Session-Restore pruefen
- Command-Verarbeitung pruefen
- Settings-Update pruefen
- Emotion-Layer-Update pruefen
- Life-/Growth-Daten pruefen

### Frontend-Tests

- Chat-Rendering pruefen
- Loading-States pruefen
- Session-Switch pruefen
- Settings-Formular pruefen
- Dashboard-Daten pruefen
- 3D-Panel-Ladeverhalten pruefen
- API-Fehleranzeigen pruefen

### Integrations-Checks

- Backend laeuft allein
- Frontend laeuft allein
- Frontend spricht richtige API-URL
- Chat-Request liefert erwartete Antwort
- Streaming funktioniert
- Debug-Daten kommen vollstaendig an

### Bestehende Tests, die besonders wichtig bleiben

- `tests/test_chat_manager_persistence.py`
- `tests/test_debug_monitor_data.py`
- `tests/test_web_ui_consistency.py`
- `tests/test_training_config_ui.py`
- `tests/test_config_package_import.py`
- `tests/test_local_first_runtime.py`
- `tests/test_brain_pipeline_steering_integration.py`

Diese Tests muessen teilweise umgebaut oder ersetzt werden, wenn die UI aus Streamlit herausgeloest ist.

## Doku, die mitziehen muss

Wegen der Strukturanderung muessen diese Bereiche angepasst werden:

- `README.md`
- `agent.md`
- `docs/architecture.md`
- `docs/workflows.md`
- `docs/local-models.md`
- `docs/project-map.md`
- `docs/testing.md`
- `docs/deployment.md`
- `tests/README.md`
- Legacy-Hinweise in `Info Dateien/`

Zusatz:

- neue Frontend-Startanleitung
- neue API-Startanleitung
- neue Port- und Service-Beschreibung
- neue Teststrategie fuer API und Frontend

## Was im Code besonders zu beachten ist

- keine UI-Logik in Python
- keine Streamlit-Imports in finalen Laufzeitpfaden
- keine doppelte Wahrheitsquelle fuer Sessions
- keine doppelten Statusobjekte ohne klare Zuständigkeit
- keine Hardcodes fuer Ports oder Base-URLs
- keine unkontrollierten JSON-Strukturen
- keine Abhaengigkeit des Frontends von internen Python-Objekten
- keine Ueberfrachtung des 3D-Panels
- keine Vermischung von Modellserver und App-API

## Abnahmekriterien

Der Umbau ist erst fertig, wenn folgende Punkte alle erfuellt sind:

- kein Streamlit mehr im produktiven Webpfad
- React-Frontend startet und zeigt die wichtigsten Ansichten
- FastAPI-Backend liefert alle benoetigten Daten
- Chat funktioniert wie vorher
- Sessions bleiben erhalten
- Commands funktionieren wie vorher
- Life- und Growth-Daten sind sichtbar
- Debug-Monitor zeigt die gleiche Tiefe wie vorher
- Emotion Steering ist bearbeitbar
- Training ist steuerbar
- 3D-Panel ist integriert
- CORS funktioniert
- Fetch-Ziele sind korrekt
- Backend-API und Frontend sind getrennt
- Dokumentation ist aktualisiert
- Tests sind gruen

## Explizite Annahmen

- Frontend-Basis ist Vite + React + TypeScript
- 3D ist zuerst nur ein Panel
- Transport ist REST + SSE
- Tailwind bleibt die einzige Styling-Basis
- Google Material Icons bleiben die Icon-Quelle
- Der bestehende Modellserver in `brain/steering_api_server.py` bleibt bestehen
- Der bestehende Brain-/Memory-/Life-Kern bleibt fachlich unveraendert
- Der erste Umbau fokussiert auf Paritaet und Stabilitaet, nicht auf neue Features

## Ergebnis

Nach diesem Umbau ist CHAPPiE nicht mehr an Streamlit gebunden.

Die App hat dann:

- ein echtes Frontend
- ein klares API-Backend
- bessere Performance
- bessere Erweiterbarkeit
- eine saubere Basis fuer React Three Fiber, Animationen, Audio und spaetere UI-Features
