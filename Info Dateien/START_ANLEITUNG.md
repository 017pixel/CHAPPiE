# CHAPPiE Schnellstart

Diese Datei ist nur noch eine kurze Bruecke. Die aktuelle Einstiegskette ist:

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
source venv/bin/activate
pip install -r requirements.txt
cd frontend && npm install && cd ..
```

### Starten

- API: `uvicorn api.main:app --reload --port 8010`
- Frontend: `cd frontend && npm run dev`
- Brain CLI: `python chappie_brain_cli.py`
- Training: `python -m Chappies_Trainingspartner.training_daemon --neu`

## Kritischer Hinweis

Der Linux-Training-Service muss `Chappies_Trainingspartner.training_daemon` starten, nicht `training_loop.py`.

Mehr Details:

- [`docs/deployment.md`](../docs/deployment.md)
- [`docs/vLLM-Setup.md`](../docs/vLLM-Setup.md)
- [`docs/testing.md`](../docs/testing.md)
