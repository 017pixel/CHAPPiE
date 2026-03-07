# CHAPPiE Schnellstart

Diese Datei ist jetzt eine **Legacy-Brücke**. Die aktuelle Einstiegskette ist:

1. [`README.md`](../README.md)
2. [`docs/local-models.md`](../docs/local-models.md)
3. [`docs/deployment.md`](../docs/deployment.md)
4. [`docs/testing.md`](../docs/testing.md)

## Kurzfassung

### Installation

```bash
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE
python -m venv venv
source venv/bin/activate   # Windows: .\venv\Scripts\activate
pip install -r requirements.txt
```

### Empfohlene Konfiguration

- lokale **Qwen-3.5-Modelle zuerst**
- `vLLM` bevorzugen
- APIs nur als Fallback nutzen

Vorlagen und Settings:

- [`config/secrets_example.py`](../config/secrets_example.py)
- [`config/config.py`](../config/config.py)
- [`config/brain_config.py`](../config/brain_config.py)

### Starten

- Web UI: `streamlit run app.py`
- Brain CLI: `python chappie_brain_cli.py`
- Training: `python -m Chappies_Trainingspartner.training_daemon --neu`

## Kritischer Hinweis

Der Linux-Service muss `Chappies_Trainingspartner.training_daemon` starten, **nicht** `training_loop.py`.

Mehr Details stehen jetzt in [`docs/deployment.md`](../docs/deployment.md).

