# Brain-Pipeline v1

Dieser Snapshot dokumentiert CHAPPiEs ersten Brain-orientierten
Orchestrierungsversuch mit spezialisierten Agenten. Er ist kein aktiver
Requestpfad und wird nicht als produktive Runtime unterstützt.

- Herkunft: `brain/brain_pipeline.py` und `brain/agents/`
- Stand: Commit `5911242475b3c510be772f3f9068aa651dff65d0`
- Aktiver Nachfolger: `web_infrastructure/turn_pipeline.py`
- Weiter aktive Konzepte: `brain/global_workspace.py`,
  `brain/action_response.py`, `brain/deep_think.py`, Memory und Life
- Aktives Steering: `brain/steering_manager.py`

Der Steering-Snapshot unter `agents/` belegt nur die damalige Ordnerstruktur.
Die aktive Implementierung wurde nicht archiviert, sondern in
`brain/steering_manager.py` isoliert. Der alte Importpfad ist ein dünner
Kompatibilitäts-Re-Export.

