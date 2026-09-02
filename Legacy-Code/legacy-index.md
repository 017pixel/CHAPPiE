# Legacy-Index

| Bereich | Herkunft | Archiv | Status | Aktiver Nachfolger |
|---|---|---|---|---|
| Backend-Wrapper v1 | `web_infrastructure/backend_wrapper.py` | `backend-wrapper-v1/source/backend_wrapper.py` | eingefrorener Quellstand | `web_infrastructure/chappie_runtime.py` und Runtime-Module |
| Brain-Pipeline v1 | `brain/brain_pipeline.py` | `brain-pipeline-v1/brain_pipeline.py` | historischer Architekturversuch | `web_infrastructure/turn_pipeline.py` |
| Spezialisierte Agents | `brain/agents/*.py` | `brain-pipeline-v1/agents/` | historische Komponenten, aktive Runtime lädt sie nicht | Brain-, Memory- und Life-Module |
| Steering im alten Namespace | `brain/agents/steering_manager.py` | `brain-pipeline-v1/agents/steering_manager.py` | nur Snapshot des damaligen Pfads | `brain/steering_manager.py` |
| Bericht-v5-Quellen | mehrere damalige Quellpfade | `report-v5-source/` | Provenienzmanifest | aktuelle v6-Evidenz |

Die Referenzprüfung am Archivierungsstand fand keine produktiven Aufrufer der
entfernten Runtime-Methoden `_process_legacy`, `_process_legacy_stream`,
`_extract_legacy_generation`, `start_async_chat`, `_run_chat_job`,
`_shrink_message_to_fit` und `_estimate_msg_tokens`. Ihre vollständige letzte
Implementierung bleibt im Wrapper-v1-Snapshot erhalten.

