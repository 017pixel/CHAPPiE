# 🚀 CHAPPiE Schnellstart

## Voraussetzungen

- Python 3.11+
- Git
- optional: konfigurierte LLM-Provider oder lokale Modelle

## 1. Installation

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

## 2. Konfiguration

Option A:

1. `config/secrets_example.py` nach `config/secrets.py` kopieren
2. gewünschten Provider und API-Keys eintragen

Option B:

- CHAPPiE starten und Modelle später in der Web-Oberfläche konfigurieren

## 3. CHAPPiE starten

### Web UI

```bash
streamlit run app.py
```

### CLI

```bash
python chappie_brain_cli.py
```

### Training Daemon

```bash
python -m Chappies_Trainingspartner.training_daemon --neu
python -m Chappies_Trainingspartner.training_daemon --fokus "Architektur"
```

Optionaler Setup-Wizard:

```bash
python Chappies_Trainingspartner/setup_training.py
```

## 4. Updates holen

```bash
git pull
pip install -r requirements.txt
```

## 5. Wichtige Hinweise

- Der Linux-Service muss `Chappies_Trainingspartner.training_daemon` starten
- `training_loop.py` ist kein Service-Entry-Point
- Laufzeitdateien in `data/` werden lokal erzeugt und gehören nicht ins Repository

Viel Spaß mit CHAPPiE 🤖