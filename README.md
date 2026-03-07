# CHAPPiE

CHAPPiE ist ein kognitischer KI-Assistent mit brain-inspirierter Multi-Agent-Architektur, episodischem Gedächtnis, autonomem Trainingsmodus und einer erweiterten Life-Simulation für Entwicklung, Gewohnheiten, Planung, Forecasting und Beziehungsdynamik.

## Überblick

CHAPPiE kombiniert mehrere Schichten zu einem zusammenhängenden System:

- **Brain Pipeline** mit spezialisierten Agenten
- **Memory System** mit ChromaDB, Kurzzeitgedächtnis und Schlafphase
- **Life Simulation** mit Needs, Goals, Habits, Development und Attachment
- **Growth Layer** mit Planning, Forecasting, Social Arc und Timeline
- **Web UI**, **CLI** und **Training Daemon** für interaktiven und autonomen Betrieb

## Kernfunktionen

### Brain-Inspired Multi-Agent Architecture

- Sensory Cortex für Input-Klassifikation und Dringlichkeit
- Amygdala für Emotionsbewertung und Vertrauensdynamik
- Hippocampus für Memory-Encoding, Retrieval und Query-Extraktion
- Prefrontal Cortex für Orchestrierung und Antwortstrategie
- Basal Ganglia für Reward-Feedback
- Neocortex für Langzeitspeicherung
- Memory Agent für Kontextdateien und Tool-Entscheidungen

### Memory System

- ChromaDB-basiertes Langzeitgedächtnis
- JSON-basiertes Kurzzeitgedächtnis
- Ebbinghaus-Vergessenskurve mit referenznahen Retentionswerten
- Schlafphase für Konsolidierung, emotionale Regeneration und Replay
- Kontextdateien in `data/soul.md`, `data/user.md`, `data/CHAPPiEsPreferences.md`

### Life Simulation

CHAPPiE verwaltet einen inneren Zustandsraum mit:

- **Homeostasis / Needs**
- **Goal Competition**
- **World Model**
- **Habit Engine** inklusive Decay und Konflikterkennung
- **Development Engine**
- **Attachment Model**
- **Autobiographical Self**

Zusätzliche Growth-Schichten:

- **Planning Engine** mit Milestones, Bottlenecks und Planungshorizont
- **Self Forecast** mit Risiko- und Schutzfaktoren
- **Social Arc Engine** für Beziehungsbogen und Episoden
- **History Engine / Timeline** für autobiografische Entwicklung über Zeit

### Interfaces

- **Web App** via Streamlit
- **Advanced Brain CLI** mit Status-, Life- und Steering-Kommandos
- **Autonomer Training Daemon** für 24/7 Training
- **Life Dashboard** und **Growth Timeline Dashboard** in der Weboberfläche

## Installation

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

## Konfiguration

- `config/secrets.py` aus dem Beispiel erzeugen und Provider/Keys setzen
- oder die Modelle später in der Web-UI konfigurieren
- lokale Provider wie Ollama oder vLLM sind optional

## Starten

### Web UI

```bash
streamlit run app.py
```

Wichtige Bereiche in der Sidebar:

- Alle Erinnerungen
- Einstellungen
- Autonomes Training
- Life Dashboard
- Growth Timeline
- Kontextdateien (`soul.md`, `user.md`, Preferences)

### CLI

```bash
python chappie_brain_cli.py
```

### Training Daemon

```bash
python -m Chappies_Trainingspartner.training_daemon --neu
python -m Chappies_Trainingspartner.training_daemon --fokus "Architektur"
```

Wichtig:

- Der systemd-Service muss auf **`Chappies_Trainingspartner.training_daemon`** zeigen
- **nicht** auf `training_loop.py`
- Für zuverlässigen Dauerbetrieb ist `Restart=always` gesetzt

## Verfügbare Commands

### Web / Chat Commands

- `/sleep`
- `/think [thema]`
- `/deep think`
- `/clear`
- `/help`
- `/stats`
- `/config`
- `/daily`
- `/personality`
- `/consolidate`
- `/reflect`
- `/functions`
- `/debug`
- `/step1`
- `/soul`
- `/user`
- `/prefs` / `/preferences`
- `/twostep`
- `/life`
- `/needs`
- `/goals`
- `/world`
- `/habits`
- `/stage`
- `/plan`
- `/forecast`
- `/arc`
- `/timeline`

### CLI Commands

- `/status`
- `/sleep`
- `/life`
- `/world`
- `/habits`
- `/stage`
- `/plan`
- `/forecast`
- `/arc`
- `/timeline`
- `/vectors`
- `/help`
- `/exit`

## Projektstruktur

```text
brain/                         Brain-Pipeline, Agenten, Workspace, Action Layer
life/                          Life Simulation, Planning, Forecast, Social Arc, History
memory/                        Memory Engine, Forgetting Curve, Sleep Phase
web_infrastructure/            Streamlit UI, Dashboards, Command Handling
Chappies_Trainingspartner/     Training Daemon, Training Loop, Daemon Manager
tests/                         Unit-Tests und manuelle Smoke-/Kompatibilitätstests
data/                          Kontextdateien und lokale Laufzeitdaten
```

## Wichtige Zustandsfelder der Life-Simulation

Der Snapshot der Life-Simulation enthält u. a.:

- `homeostasis`
- `active_goal`
- `world_model`
- `habits`
- `habit_dynamics`
- `development`
- `attachment_model`
- `planning_state`
- `forecast_state`
- `social_arc`
- `timeline_history`
- `timeline_summary`
- `replay_state`

## Testing und lokale Verifikation

Empfohlene lokale Checks ohne echte API-Calls:

```bash
python tests/test_life_simulation.py
python tests/test_quick.py
python tests/test_forgetting_curve.py
python validate_system.py
python tests/manual/test_compatibility.py
python tests/manual/test_chappie.py
```

Zusätzlich hilfreich:

```bash
python -m Chappies_Trainingspartner.training_daemon --help
```

## Deployment-Hinweise

### Linux / systemd

Die Datei `chappie-training.service` ist auf den Daemon-Modulstart ausgelegt:

```ini
ExecStart=/home/.../venv/bin/python3 -m Chappies_Trainingspartner.training_daemon
Restart=always
```

Deployment-Helfer:

- `deploy_training.sh`
- `deploy_training.bat`

## Daten & Laufzeitdateien

- Persistente Chat-/Memory-Daten liegen unter `data/`
- Laufzeit-State wie `life_state.json`, `sleep_state.json` und generierte Steering-Vektoren werden lokal erzeugt und sind für Git ignoriert
- ChromaDB-Datenbankinhalte sollten nicht versehentlich gelöscht werden

## Weitere Doku im Repository

- `Info Dateien/START_ANLEITUNG.md`
- `Info Dateien/WIE_ES_GEHT.md`
- `Info Dateien/SSH_Befehle_CHAPPiE.md`
- `validate_system.py` für schnelle Systemprüfung

## Status dieses Stands

Dieser Stand enthält:

- die integrierte Life- und Growth-Architektur
- lokale Tests für Forgetting Curve, Life Simulation und Kompatibilität
- aufgeräumte Teststruktur unter `tests/`
- konsistenten Training-Daemon-Start per Modulaufruf
