# Repository-Cleanup und Migrationsentscheidungen

Stand: 2. September 2026. Ausgangscommit: `5911242475b3c510be772f3f9068aa651dff65d0`.

Die rückwärtskompatible Migration erscheint als Produktversion 16.4.0. Eigenständige Steering-Service-, Payload- und Datenformatversionen bleiben unverändert. Es wurden keine localStorage- oder IndexedDB-Strukturen migriert.

## Ausgangslage

- 3.176 getrackte Dateien, davon 2.906 unter `forschung/`
- 2.253 Session-Log-Dateien, 574 Run-Artefakte und 69 Report-Dateien
- `backend_wrapper.py` mit 4.179 Zeilen und mehreren Verantwortungen
- Ruff-Baseline: 172 aktive Befunde
- Mypy-Baseline: 145 Fehler in 28 Dateien
- Forschungsbericht v5: 245.797 Byte, SHA-256 `a206bb0308f804340076ef8cb6714c07be9fe81c184a3aa6a8f40eb0fed983fa`
- lokaler API-Test zunächst durch fehlendes FastAPI blockiert; dafür existiert jetzt `requirements/ci.txt`

Forschungsdaten wurden nicht pauschal verändert. Ihre Klassifizierung steht in `forschung/research-inventory.json`.

## Technische Entscheidungen

### Runtime statt Monolith

Der aktive Wrapper wurde entlang realer Verantwortungen in Runtime, Turn-Kontext, Pipeline, Generation, Persistenz und Formatierung getrennt. Der alte Wrappername bleibt als kleine Kompatibilitätsschicht bestehen. Sync und Stream nutzen denselben Turn-Einstieg und Abschlussvertrag.

### BrainPipeline als Historie

Die BrainPipeline v1 war kein produktiver Requestpfad. Ihre Quellen sind bytegetreu unter `Legacy-Code/brain-pipeline-v1/` archiviert. Der aktive Dateiname ist nur noch ein lazy Loader für alte Tests und Forschung.

### Steering bleibt aktiv

Der SteeringManager wurde nach `brain/steering_manager.py` isoliert. Der alte Agent-Pfad re-exportiert ihn, ohne alle historischen Agenten eager zu laden.

### Providerwahrheit

Der Web-Chat bleibt fest auf vLLM. Ollama und Groq bleiben unterstützte Adapter. Ein alter Cerebras-Enum-Zugriff im Training war ein echter Fehler und wurde auf Groq korrigiert. `enable_two_step_processing` bleibt als persistierter/UI-sichtbarer Kompatibilitätswert erhalten, ändert aber nicht den festen Webpfad.

### Config

Globale Settings bleiben in `config/config.py`, Prompts in `config/prompts.py`. Der Import-Sideeffect zur Erzeugung von Datenverzeichnissen bleibt kompatibel und ist in der Architektur dokumentiert.

Trainingsconfig wird künftig nach `config/training_config.json` geschrieben. Eine alte Root-Datei wird gelesen, aber nicht automatisch verschoben oder gelöscht. Dadurch bleiben bestehende Installationen nutzbar und die neue Quelle ist eindeutig.

### Abhängigkeiten

`requirements.txt` behält die vollständige Installation durch Includes. Laufzeit, lokale Provider, Training, Entwicklung und minimale CI sind getrennt dokumentiert. Die künstliche Root-NPM-Abhängigkeit `python3` hatte keine Aufrufer und wurde entfernt.

## Archivierte oder entfernte Dateien

Archiviert:

- vollständige Wrapper-v1-Quelle
- BrainPipeline-v1 und historische Agentenquellen
- `autonomy.sh` mit veraltetem hartcodiertem Pfad

Als reproduzierbare Artefakte entfernt und in `.gitignore` aufgenommen:

- `backend-test.err`, `frontend-test.err`
- `orbit-browser-*.ts`
- `telemetry-id`
- TypeScript-Buildinfo-Dateien
- generierte Vite-/Tailwind-JavaScript- und Deklarationsdateien
- Root-`package.json` und `package-lock.json` mit ausschließlich künstlicher `python3`-Abhängigkeit

Alle entfernten getrackten Dateien sind über Git wiederherstellbar. Es wurden keine Memory-, Session-, Run- oder Forschungsdaten gelöscht.

## Qualitätsgrenzen

- Legacy und eingefrorene Runs sind aus aktivem Ruff/Mypy ausgeschlossen.
- Ruff ist für die neuen Runtime-, Router-, Steering- und Validatorgrenzen required.
- Mypy prüft einen ehrlichen öffentlichen Contract-Scope, statt den historischen Gesamtbestand global zu ignorieren.
- Deterministische erweiterte Tests sind in CI required; echte Modelltests bleiben getrennt.
- v5 wird per Hash eingefroren, v6 besitzt ein eigenes Evidence-Manifest und einen Offline-Validator.
- Der Security-Audit ist unter `docs/security-audit-2026-09-02.md` dokumentiert. Eine Session-Pfad-Traversal wurde behoben; Authentifizierung, CORS-Härtung und die noch ungepatchten ChromaDB-Advisories bleiben als explizite Betriebsrisiken sichtbar.

Der breite aktive Ruff-Lauf sank von 172 auf 144 Befunde; der verpflichtende Architektur-Scope hat null Befunde. Der öffentliche Mypy-Vertragsscope hat ebenfalls null Fehler. Außerhalb der vier dynamisch zusammengesetzten Runtime-Mixins sank der breite aktive Mypy-Bestand von 145 Fehlern in 28 Dateien auf 122 Fehler in 24 Dateien. Die Mixins selbst melden bei isolierter Prüfung 242 `attr-defined`-Befunde, weil ihre `self`-Attribute erst durch die zusammengesetzte Runtime-Fassade entstehen. Diese Befunde werden nicht global ignoriert oder als behoben ausgegeben.

## Rollback

- Alte Factory- und Importnamen bleiben verfügbar.
- Die vollständige frühere Implementierung liegt im Legacy-Snapshot.
- Alte Trainingsconfig bleibt lesbar.
- Persistierte Memory-, Life- und Chatdaten wurden nicht migriert.
- Entfernte Buildartefakte können durch Build oder Git wiederhergestellt werden.
- Ein Rückbau soll einzelne kleine Änderungen zurücknehmen, niemals Nutzer- oder Forschungsdaten löschen.

## Nicht Teil dieser Migration

- kein Modellwechsel
- keine neue Providerpriorität
- keine neue UI-Funktion oder Designänderung
- keine Memory-, Life-, Emotions- oder Datenbankmigration
- keine Änderung laufender Dienste oder Nutzer-Previews
- kein Commit oder Push ohne ausdrückliche Freigabe
