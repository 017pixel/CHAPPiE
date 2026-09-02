# CHAPPiE Legacy-Code

Dieser Ordner bewahrt historische Implementierungen und Quellbelege. Er liegt
absichtlich außerhalb des Python-Importpfads und ist kein aktiver
Produktionscode.

Archiviert wurde der Stand von Commit `5911242475b3c510be772f3f9068aa651dff65d0`
am 2. September 2026. Die Dateien bleiben für Forschung, Vergleichbarkeit und
den unveränderten Forschungsbericht v5 lesbar. Änderungen hier verändern das
Produktionsverhalten nicht automatisch und werden nicht als unterstützte
Runtime getestet.

Der erste Architekturversuch verteilte einen Turn auf mehrere spezialisierte
Brain-Agenten. Im realen Web-, CLI- und Research-Pfad setzte sich später die
lokale Zwei-Schritt-Verarbeitung durch. Beim alten Ansatz erschwerten
konkurrierende Orchestrierung, enge Kopplung, eager Imports, unklare
Providergrenzen und schwer vergleichbare Sync-/Stream-Pfade Tests und
Präsentation. Die fachlich wertvollen Ideen, etwa Global Workspace, Memory,
Life-State und Steering, bleiben in der aktiven Architektur erhalten.

Aktive Nachfolger:

- Runtime-Fassade: [`web_infrastructure/chappie_runtime.py`](../web_infrastructure/chappie_runtime.py)
- Turn-Orchestrierung: [`web_infrastructure/turn_pipeline.py`](../web_infrastructure/turn_pipeline.py)
- Generation: [`web_infrastructure/generation.py`](../web_infrastructure/generation.py)
- Persistenz: [`web_infrastructure/persistence.py`](../web_infrastructure/persistence.py)
- Formatierung: [`web_infrastructure/formatting.py`](../web_infrastructure/formatting.py)
- Steering: [`brain/steering_manager.py`](../brain/steering_manager.py)
- Architektur: [`docs/architecture.md`](../docs/architecture.md)
- Forschungsbericht v6: [`forschung/report/CHAPPiE-Forschungsbericht-v6.html`](../forschung/report/CHAPPiE-Forschungsbericht-v6.html)

Siehe [`legacy-index.md`](legacy-index.md) für Herkunft, Status und Hashes.

