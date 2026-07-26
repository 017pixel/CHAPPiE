# Architektur- und Kausalhinweise für den Report

## Tatsächlich gemessener Laufzeitpfad

`api/routers/chat.py:101–230` führt zu `CHAPPiEBackend.process_stream()` in `web_infrastructure/backend_wrapper.py:3464–3499` und standardmäßig in die zweistufige Pipeline `_process_two_step_stream()` (`:2920–3256`). `brain/brain_pipeline.py:35–202` enthält eine konzeptionelle/alternative Agenten-Orchestrierung, ist aber nicht als aktiver Pfad der aktuellen Sessions nachgewiesen.

Der Provideroutput wird vollständig gepuffert (`backend_wrapper.py:3063–3084`), danach geparst, formatiert und sanitisiert und erst dann in 96-Zeichen-Stücken als SSE ausgegeben (`:3183–3206`). Die aktuelle TTFT-Metrik entspricht damit eher der Gesamtgenerierungszeit als echter clientseitiger First-Token-Latenz.

## Prompt- und Turnkette

1. Intent, Emotionen, STM und Retrievalbegriffe: `backend_wrapper.py:2934–3005`.
2. Semantisches und Keyword-Retrieval: `:3011–3026`, `:2793–2829`.
3. Persona-/Kontextdateien abhängig vom Intent: `:2167–2237`.
4. Systemprompt und Cloud-Emotionstatus: `config/prompts.py:13–22`, `:209–240`, `:259–319`.
5. Response-Style, Tone-Plan, Budget, STM und Memories: `backend_wrapper.py:2839–2895`.
6. Lokales `extra_body` mit Steering-Payload: `:2898–2908`.
7. Parser/Sanitizer: `brain/response_parser.py:137–275`.

Life und Workspace werden nicht als großer serialisierter Promptblock eingefügt, beeinflussen aber Tone-Plan, Steering und Traces. Das muss im Report klar von direkter Prompt-Injection getrennt werden.

## Memory und Vergessen

Memory-Provenienz umfasst ID, Rolle, Zeit, Typ, Relevanz, Label, Match-Typ/-Begriffe und Quelle (`memory/memory_engine.py:55–68`, `:1153–1201`). `memory_trace` trägt Query, Trefferzahl, Relevanz, IDs und Vorschau (`backend_wrapper.py:820–845`). Modellfehler und Prompt-/Toolkontamination werden vor Persistenz oder Retrieval gefiltert.

Die Vergessenskurve nutzt interpolierte Referenzpunkte und eine beschriebene Exponentialform `R = e^(-t/S)` mit Floor (`memory/forgetting_curve.py:31–165`). Das ist ein implementiertes Modell, kein empirischer Nachweis optimalen Agentenvergessens. Research-Runs deaktivieren automatischen Sleep.

## Life und Workspace

`life/service.py:58–114` aktualisiert Zeit, Homeostase, Aktivität, Episoden, Ziele, Beziehung, Habits, Attachment und Self-Model in `prepare_turn`/`finalize_turn`. `GlobalWorkspace` sortiert mehrere technische Salienzsignale (`brain/global_workspace.py:11–193`). Im realen Wrapper wird ein Workspace aus Intent, Life und Memory erzeugt, nicht aus sämtlichen konzeptionellen Brain-Agent-Outputs.

`causal_trace` ist ein erklärender Datenpfad für eingespeiste/verarbeitete Zustände. Er beweist weder, dass ein Modell einen Zustand in der behaupteten psychologischen Bedeutung nutzt, noch subjektives Erleben.

## Emotion und Steering

Zehn Zustände sind zentral definiert: happiness, trust, energy, curiosity, motivation, frustration, sadness, affection, anxiety und calm (`config/emotions.py:8–148`). Das nominelle Qwen-Profil besitzt 32 Schichten mit L10–26, das Gemma-E4B-Profil 42 Schichten mit L12–30 (`steering_manager.py:88–95`, `:176–186`).

Die VAD-Richtungen sind ausdrücklich synthetisch, bis echte Kontrastpaare vorliegen (`:351–380`). Der Payload listet Name, Stärke, Richtung und Layerbereich; der Backendpfad addiert normalisierte und gekappte Vektoren pro Layer. Crashout wird bei `frustration >= 72` und `trust <= 38` aktiviert, während ein Guard Beleidigungen und Drohungen untersagt.

Run 2 zeigt bereits eine wichtige Abweichung: Das Startlog meldet Gemma L12–30, aber tatsächliche aktive Vektoren reichen in Session 33 bis L40. Der Report verwendet deshalb nicht einfach das nominelle Profil als tatsächliche Injektion.

Die Ursache ist im statischen Abgleich reproduzierbar: Die Dateien unter
`data/steering_vectors/` speichern pro Emotion eigene `layer_start`/`layer_end`
und enthalten gemischte alte Bereiche L16–40, L16–31 und L12–34.
`SteeringManager._load_vectors()` übernimmt diese Metadaten unverändert
(`brain/agents/steering_manager.py:316–327`). Bei einem späteren Modellwechsel
aktualisiert sich zwar das Modellprofil, bestehende Vektoren werden aber nicht
neu gebunden. `_sanitize_vector_runtime_config()` schneidet nur auf
`total_layers - 1` (`:389–428`), nicht auf die aktuelle `emotion_range`. Damit
stammen nominelles Zielprofil und realer Basisvektor-Payload aus zwei
verschiedenen Konfigurationsquellen.

## Geeignete Codeauszüge

- sicherer `SYSTEM_PROMPT`: `config/prompts.py:13–22`;
- Promptassembly: `backend_wrapper.py:2839–2906`;
- Modellprofile: `steering_manager.py:88–95`, `:176–186`;
- Crashout und Guard: `steering_manager.py:554–569`, `steering_backend.py:285–307`;
- gepufferte Sicherheitsgrenze: `backend_wrapper.py:3081–3106`;
- Causal Trace: `backend_wrapper.py:888–940`.
