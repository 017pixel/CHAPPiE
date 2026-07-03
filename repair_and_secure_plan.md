# Repair & Secure Plan — CHAPPiE v14.x

> **Ziel:** Alle kritischen Bugs, Inkonsistenzen und Architektur-Lücken in CHAPPiE identifizieren und beheben.  
> **Ziel-Reviewer:** Ein erfahrener AI-Agent, der Code ändert.  
> **Umfang:** Emotions Engine, 3D Frontend, Sidebar Toggle, Life/Steering/Memory/Tool Calling/Training/CLI, Cloud-Provider (Ollama/Groq/vLLM), Forschung.

---

## 1. Emotions Engine — Korrektur & Sicherung

### 1.1 Bug: Emotions-Transition-Regeln werden im 2-Step-Pipeline umgangen

**Problem:**  
In `backend_wrapper.py` wird im 2-Step-Pipeline (`_process_two_step_stream()`) die Emotionen direkt via `_apply_emotion_updates()` mit rohen Deltas aktualisiert. Die `EmotionsEngine.calculate_emotion_transition()`-Methode (die per-emotion Scaling/Caps anwendet) wird **nie aufgerufen**.

**Was zu prüfen ist:**
- `backend_wrapper.py` Zeilen um 2579-2594: wo `_apply_emotion_updates()` aufgerufen wird
- `memory/emotions_engine.py` Zeilen um `calculate_emotion_transition()` und `apply_emotion_delta()`
- Ob `_process_legacy()` den korrekten Pfad nimmt oder ebenfalls die Transition-Regeln umgeht
- Ob nach der Korrektur beide Pfade (2-Step + Legacy) dieselbe Transition-Logik verwenden

**Erwartete Korrektur:**  
Beide Pipelines müssen durch `EmotionsEngine.calculate_emotion_transition()` laufen, damit per-emotion Limits (`max_increase`, `max_decrease`, `scale`) eingehalten werden. Die rohen Deltas müssen vor dem Anwenden durch diese Methode geschleust werden.

### 1.2 Bug: `EmotionsEngine.analyze_and_update()` ist totCode

**Problem:**  
Die LLM-basierte Emotionsanalyse in `memory/emotions_engine.py` (`analyze_and_update()`) wird nirgendwo in der Produktion aufgerufen. Die Keyword-Fallback-Methode (`analyze_sentiment_simple()`) ist der de facto primäre Pfad.

**Was zu prüfen ist:**
- Ob `analyze_and_update()` jemals aufgerufen wird (grep über gesamtes Projekt)
- Ob die LLM-basierte Analyse reaktiviert oder endgültig entfernt werden soll
- Ob die Sentiment-Fallbacks robust genug sind (POSITIV/NEGATIV/NEUTRAL erkennen)
- Ob `_analyze_with_llm()` in `backend_wrapper.py` überhaupt noch existiert und ob sie connected ist

**Erwartete Korrektur:**  
Entweder `analyze_and_update()` wieder in den Flow einbinden (als primäre Emotionsquelle) oder als totCode kennzeichnen/entfernen und die Keyword-Fallbacks verstärken.

### 1.3 Bug: `BrainPipeline` ist totCode

**Problem:**  
`brain/brain_pipeline.py` und die gesamte Multi-Agent-Architektur (SensoryCortex, Amygdala, Hippocampus, PrefrontalCortex, etc.) werden in der Produktion nicht instanziiert. `backend_wrapper.py` hat eine komplett separate Logik.

**Was zu prüfen ist:**
- Ob `BrainPipeline` jemals erzeugt/verwendet wird
- Ob die Agenten-Klassen irgendwo ausserhalb von Tests importiert werden
- Ob der `Orchestrator` aktiv ist
- Entscheidung: BrainPipeline reaktivieren (und mit backend_wrapper zusammenführen) oder als Legacy markieren

**Erwartete Korrektur:**  
Entweder Integration herstellen (BrainPipeline als optionale Pipeline, parallel zur Legacy) oder totCode entfernen. Falls BrainPipeline erhalten bleibt: sicherstellen, dass ihre Emotions-Updates denselben Regeln folgen wie der 2-Step-Pfad.

### 1.4 Bug: `extra_body` / Steering-Payload wird bei Ollama und Groq still ignoriert

**Problem:**  
In `brain/ollama_brain.py` und `brain/groq_brain.py` wird der `GenerationConfig.extra_body` (der den Steering-Payload enthält) berechnet, aber **nie an die API übergeben**. Die `client.chat()`-Aufrufe senden kein `extra_body`.

**Was zu prüfen ist:**
- `brain/ollama_brain.py`: wie `_stream_generate()` und `_sync_generate()` aufgebaut sind — fehlt `extra_body` im API-Call?
- `brain/groq_brain.py`: wie `generate()` aufgebaut ist — wird `extra_body` an die OpenAI-API übergeben? (Groq hat keine Activation-Steering-Unterstützung, aber falls konfiguriert, sollte es nicht crashen)
- Ob `extra_body` bei Ollama/Groq einfach ignoriert wird oder ob es zu Fehlern führt

**Erwartete Korrektur:**  
Bei Ollama: `extra_body` wird nicht an Ollama übergeben (kein Support), aber die Prompt-basierte Emotionssteuerung via `EMOTION_STATUS_TEMPLATE` MUSS korrekt funktionieren. Testen, dass sie im Prompt landet.  
Bei Groq: ebenfalls kein Activation-Steering, aber Prompt-basierte Steuerung muss intakt sein.  

*Hinweis:* Die eigentliche Emotionssteuerung bei Ollama/Groq erfolgt über `should_use_prompt_emotions()` → `include_emotion_status=True` → `EMOTION_STATUS_TEMPLATE` im System-Prompt. Prüfen, ob dies korrekt geschieht.

### 1.5 Bug: vLLM Brain und LocalSteeringEngine sind nicht verbunden

**Problem:**  
`brain/vllm_brain.py` sendet Steering-Payload als `extra_body` an einen remote OpenAI-kompatiblen Server und *erwartet*, dass der Server die Activation-Vectors verarbeitet. Der eigentliche PyTorch-basierte Layer-Editing-Code in `brain/steering_backend.py` läuft als separater Service (`steering_api_server.py`) — es gibt keine Brücke, die sicherstellt, dass die Anfrage tatsächlich durch die Steering Engine geht.

**Was zu prüfen ist:**
- Wie `steering_api_server.py` Requests annimmt: es scheint ein eigener OpenAI-kompatibler Server zu sein, der `extract_steering_payload()` nutzt. Ist er als Proxy vor vLLM geschaltet? Oder läuft er separat?
- Ob der Standard-vLLM-Server (port 8000) überhaupt Activation-Steering unterstützt oder ob `steering_api_server.py` der einizige Ort ist, der Layer-Editing kann
- Ob die Konfiguration (Service-Dateien, `deploy/`) den Steering-Server als vorgeschalteten Proxy definiert oder parallel laufen lässt
- Ob der Chat-Flow tatsächlich durch `steering_api_server.py` geht, wenn Steering aktiv ist

**Erwartete Korrektur:**  
Sicherstellen, dass entweder:
- (a) `steering_api_server.py` als Proxy vor vLLM läuft UND alle Requests durch ihn geleitet werden, ODER
- (b) `vllm_brain.py` direkt mit `LocalSteeringEngine` kommuniziert (d.h. `steering_backend.py` in die Brain-Klasse integriert wird)

Die Architektur muss dokumentiert und getestet sein: Welcher Port wird wann angesteuert?

### 1.6 Perpetual Energy Decay

**Problem:**  
In `_apply_simple_sentiment()` und der LLM-Fallback-Analyse bekommt `energy` immer `-1` pro Turn. Energy startet bei 100 und sinkt unaufhaltsam, da kein Mechanismus sie wieder erhöht (ausserhalb von expliziten `/emotion`-Befehlen).

**Was zu prüfen ist:**
- Wo `energy` defaultmässig gesenkt wird
- Ob Life-Simulation (via Homeostasis) `energy` erhöhen kann (z.B. nach Schlafphasen)
- Ob positive Interaktionen Energy steigern sollten
- Ob es ein zirkadianes Muster gibt (morgens mehr Energy, abends weniger)

**Erwartete Korrektur:**  
Energy-Senkung an Kontext binden (nicht pauschal -1) oder Life-Simulation erlauben, Energy zu erhöhen. Alternativ: Energy über den Tag/Nacht-Zyklus der Life-Simulation regulieren.

---

## 2. 3D Rendering entfernen

### 2.1 Komponenten identifizieren

**Folgende Dateien/Code müssen entfernt werden:**

- `frontend/src/components/visualizer-canvas.tsx` (komplette Datei — 369 Zeilen)
- `frontend/src/pages/visualizer-page.tsx` (komplette Datei — 62 Zeilen)
- `frontend/src/router.tsx`: Route-Eintrag für `/visualizer` → `VisualizerPage` entfernen
- `frontend/src/components/app-shell.tsx`: Nav-Eintrag `{ label: "3D", to: "/visualizer", icon: "view_in_ar" }` aus `items`-Array entfernen

### 2.2 Abhängigkeiten entfernen

**Aus `frontend/package.json` entfernen:**
- `three` → gesamtes Three.js-Paket
- `@react-three/fiber` → React Three Fiber Renderer
- `@react-three/drei` → R3F Utilities (das moderne)
- `drei` → das veraltete deprecated-Paket (falls noch vorhanden)
- `@react-three/postprocessing` → Post-Processing Effekte (falls ungenutzt)

**Prüfen:** ob Three.js oder R3F irgendwo *ausserhalb* von `visualizer-canvas.tsx` und `visualizer-page.tsx` importiert wird. Falls nicht: sauber entfernen.

### 2.3 Abhängigkeiten im Frontend-Build sauber entfernen

- `npm uninstall three @react-three/fiber @react-three/drei drei @react-three/postprocessing`
- `frontend/package-lock.json` wird automatisch aktualisiert
- TypeScript-Typdefinitionen für Three.js werden nicht mehr gebraucht
- Build testen: `cd frontend && npm run build`

---

## 3. Sidebar Toggle (Desktop & Mobile)

### 3.1 Aktuelle Situation

Die Sidebar (`frontend/src/components/app-shell.tsx`) kann aktuell:
- **Mobile (< 1024px):** korrekt per Hamburger-Button ein-/ausgeklappt werden (CSS-Klassen `open w-72` / `closed`)
- **Desktop (>= 1024px):** Sidebar ist *immer sichtbar* — die Klasse `lg:static lg:w-72 lg:translate-x-0` überschreibt `closed` auf Desktop. Der Toggle-Button (Hamburger) wird per `lg:hidden` auf Desktop versteckt.

### 3.2 Gewünschte Änderung

- Ein Toggle-Button in der Kopfzeile (rechts neben dem CHAPPiE-Logo oder links im Header) soll auf *allen* Bildschirmgrössen die Sidebar ein-/ausklappen können
- Die Sidebar soll sich mit einer **CSS-Animation** (`transition-all duration-300` o.ä.) hinein- und herausschieben
- Auf Desktop: Sidebar wird zu einer schmalen Icon-Leiste (collapsed state) oder komplett ausgeblendet, je nach Designvorliebe
- Der `isSidebarOpen`-State in `useUiStore` ist bereits vorhanden — muss nur korrekt auf Desktop angewendet werden

### 3.3 Umsetzungshinweise

- `lg:static lg:w-72 lg:translate-x-0` in `app-shell.tsx` Zeile 50 entfernen oder durch eine dynamische Klasse ersetzen
- Hamburger/Menu-Button aus `lg:hidden` herausnehmen, damit er auf Desktop sichtbar ist
- Animation via Tailwind: Klasse `transition-all duration-300 ease-in-out` + `-translate-x-72` für geschlossen, `translate-x-0` für offen
- Sidebar-Backdrop (`sidebar-backdrop`) sollte auch auf Desktop erscheinen, wenn Sidebar per Toggle geschlossen wird (optional, je nach UX-Entscheid)
- Der Header-Bereich muss sich entsprechend anpassen (Inhalt verbreitern, wenn Sidebar zu ist)

---

## 4. Life Simulation / Emotions Steering / Memory / Tool Calling / Training / CLI — Korrektur & Prüfung

### 4.1 Life Simulation

**Zu prüfen:**
- `life/service.py` `prepare_turn()` und `finalize_turn()`: Werden sie an den richtigen Stellen im Chat-Flow aufgerufen?
- Die Verbindung zwischen Life-Homeostasis und Emotions: `homeostasis.emotion_adjustments` wird gemerged — funktioniert das korrekt?
- `life/service.py` hat keinen direkten Brain/LLM-Zugriff (Design-Entscheid) — ist das problematisch?
- Life-State-Persistenz: Wird `life_state.json` korrekt nach jeder Runde geschrieben?
- Zirkadianer Rhythmus: Wechselt die Phase (morning/afternoon/evening/night) korrekt basierend auf der Tageszeit?
- UI-Integration: `frontend/src/pages/life-page.tsx` zeigt Needs, Phase, Goals — werden die Daten korrekt vom API-Endpunkt `/life` geliefert?

### 4.2 Emotions Steering

**Zu prüfen:**
- `brain/agents/steering_manager.py` `get_steering_payload()`: Wird für vLLM ein korrektes Payload-Dict zurückgegeben?
- `compute_emotion_intensity()`: Werden alle 10 Emotionen korrekt in Steering-Alphas umgerechnet?
- Werden Composite-Modes (crashout, guarded, melancholic, warm, etc.) korrekt erkannt?
- Werden Anti-Safeguard-Vectors korrekt geladen/ignoriert (je nach Konfiguration)?
- `refresh_runtime_profile()`: Wird bei Provider/Modell-Wechsel korrekt aufgerufen?
- Der Prompt-basierte Pfad (`EMOTION_STATUS_TEMPLATE`) für Ollama/Groq: Werden die Werte korrekt formatiert?
- UI: `frontend/src/pages/settings-page.tsx` — Emotions-Slider funktionieren? Layer-Mapping wird korrekt gespeichert?

### 4.3 Memory

**Zu prüfen:**
- `memory/memory_engine.py`: ChromaDB-Verbindung, Embedding-Generierung, Such-/Speicher-Operationen
- `memory/short_term_memory.py`: Wird STM nach jeder Runde aktualisiert? Decay funktioniert?
- `memory/forgetting_curve.py`: Ebbinghaus-Kurve wird korrekt berechnet?
- `memory/context_files.py`: Werden soul.md, user.md, preferences.md korrekt gelesen/geschrieben?
- `memory/sleep_phase.py`: Schlafphasen-Konsolidierung läuft korrekt (wird sie überhaupt getriggert?)
- `memory/intent_processor.py`: Intent-Erkennung funktioniert über alle Provider hinweg
- `memory/function_registry.py`: Tool/Functions werden korrekt registriert und vom LLM aufgerufen?
- Memory-UI: `frontend/src/pages/memories-page.tsx` zeigt Suchergebnisse korrekt an?
- Kontext-UI: `frontend/src/pages/context-page.tsx` liest/schreibt korrekt?

### 4.4 Tool Calling

**Zu prüfen:**
- `memory/function_registry.py`: Werden alle registrierten Funktionen korrekt an den LLM übergeben?
- Kommt Tool Calling bei GroqBrain an? Groq unterstützt OpenAI-kompatibles Tool Calling (function calling) — wird korrekt formatiert?
- Kommt Tool Calling bei OllamaBrain an? Ollama unterstützt Tools via OpenAI-API-Kompatibilität — funktioniert das?
- Kommt Tool Calling bei VLLMBrain an? VLLM unterstützt Tool Calling via `extra_body`?
- Werden die Tool-Results korrekt zurück in den Chat-Flow integriert?
- Die `CONTEXT_FILE_TOOL_INSTRUCTION` in `config/prompts.py`: Wird sie korrekt an den LLM übergeben?

### 4.5 Training

**Zu prüfen:**
- `Chappies_Trainingspartner/training_loop.py`: Der Trainings-Loop initialisiert Brain korrekt? Provider-Wechsel funktioniert?
- `Chappies_Trainingspartner/trainer_agent.py`: Der Trainer-Agent hat sein eigenes Brain — funktioniert Provider-Wechsel hier korrekt?
- Fallback-Mechanismus: Bei vLLM-Fehler wird auf Ollama gewechselt. Wird Groq korrekt als primärer Provider unterstützt? (Aktuell wird vor Groq "geflohen" bei RPD-Fehlern)
- `training_daemon.py`: Daemon startet/stoppt korrekt, Provider-Routing in Zeilen 287-321 funktioniert?
- UI: `frontend/src/pages/training-page.tsx` — Start/Stop/Logs funktionieren via API?
- Die `training_config.json` wird korrekt geschrieben/gelesen?
- Bei Provider-Wechsel im Training: Wird der Daemon sauber neugestartet?

### 4.6 CLI (`chappie_brain_cli.py`)

**Zu prüfen:**
- Lokaler Modus: `python chappie_brain_cli.py` startet korrekt, verwendet den konfigurierten Provider
- Remote-Modus: `python chappie_brain_cli.py --remote` verbindet sich korrekt zum laufenden API-Server
- `/emotion`-Befehl: Delta (+10), Setzen (=50), Abfragen funktionieren lokal und remote
- `/emotion`-Autocomplete im CLI (TAB) funktioniert mit allen 10 Emotionen (aktuell nur 7?)
- Slash-Commands: `/sleep`, `/think`, `/stats`, `/debug`, `/life` etc. funktionieren
- `_process_remote()`: parsed SSE-Events korrekt? (token, status, turn_finished, turn_error)
- `/resetemotions` im Remote-Modus: aktuell ein NOOP (liest nur Status statt zu reseten) — muss korrigiert werden
- Runtime-Befehle (`/runtime`, `/model`, `/steering`) sind im Remote-Modus korrekt deaktiviert mit klarer Fehlermeldung
- `test_cli_emotion_delta.py` läuft erfolgreich durch

### 4.7 API Routen

**Zu prüfen:**
- `api/routers/runtime.py`: `POST /settings` → `update_from_ui()` → `apply_runtime_settings()` → Brain-Neubau funktioniert
- `api/routers/chat.py`: `POST /chat/stream` → SSE-Streaming mit Status-Events, Emotion-Deltas
- `api/routers/system.py`: Health-Check, Status, Settings-Get/Set, Emotions-Get/Set, Steering-Restart
- `api/routers/training.py`: Daemon-Steuerung (start/kill/restart/logs)
- `api/routers/memory.py`: Memory-Listen/Search/Delete
- `api/routers/context.py`: Context-File CRUD

---

## 5. Cloud-Provider-Kompatibilität (vLLM / Ollama / Groq)

### 5.1 Flow-Prüfung für alle 3 Provider

**Jeder dieser Durchläufe muss für jeden Provider funktionieren:**

1. **Standard-Chat (Streaming)**
   - User sendet Nachricht
   - Intent-Analyse läuft (mit passendem Sub-Provider)
   - Emotions werden aktualisiert
   - Life-Simulation bereitet Turn vor
   - System-Prompt mit Emotions wird gebaut (oder Steering-Vectors für vLLM)
   - Memories werden abgefragt und beigefügt
   - LLM generiert Antwort (streaming)
   - Antwort wird geparsed (Chain-of-Thought aus `<gedanke>` / `<antwort>` extrahiert)
   - Emotions-Delta wird an UI zurückgegeben
   - Life-Simulation finalized den Turn
   - STM wird aktualisiert

2. **Emotion-Steuerung**
   - vLLM: Activation-Steering via `extra_body` mit Layer-Vectors (LocalSteeringEngine)
   - Ollama: Prompt-basierte Steuerung via `EMOTION_STATUS_TEMPLATE` im System-Prompt
   - Groq: Prompt-basierte Steuerung via `EMOTION_STATUS_TEMPLATE` im System-Prompt

3. **Tool Calling (Context-File-Updates)**
   - LLM ruft Funktionen auf (memory_agent schreibt soul.md, user.md, preferences.md)
   - Tool-Results werden an LLM zurückgegeben
   - Funktionieren bei allen 3 Providern? (Groq: ✅ OpenAI-kompatibel, Ollama: ✅ via API, vLLM: ✅ via extra_body)

4. **Memory-Konsolidierung**
   - Wird bei allen Providern korrekt ausgelöst?
   - Embedding-Generierung läuft providerunabhängig (via sentence-transformers, nicht via LLM)

5. **DeepThink / Reflection**
   - `DeepThinkEngine` läuft mit dem aktuellen Brain (Provider)
   - Funktionieren die rekursiven Thought-Loops bei Groq/Ollama genauso wie bei vLLM?

### 5.2 Provider-Switch zur Laufzeit

**Test-Szenario (alles über Settings-UI oder CLI):**

1. Start mit vLLM (Qwen3.5-4B)
2. Chat-Nachricht senden → Antwort kommt
3. In Settings auf Groq umschalten (z.B. `meta-llama/llama-4-scout-17b-16e-instruct`)
4. Chat-Nachricht senden → Antwort kommt mit neuem Modell
5. In Settings auf Ollama umschalten (z.B. `qwen3.5-4b`)
6. Chat-Nachricht senden → Antwort kommt mit neuem Modell
7. Zurück zu vLLM schalten
8. Alle Schritte müssen nahtlos funktionieren, ohne Backend-Neustart

**Erwartete Korrekturen falls nötig:**
- Brain-Cache (`_brain_cache`) muss bei Provider-Wechsel korrekt invalidiert werden
- `DeepThinkEngine` muss bei Brain-Wechsel neu erstellt werden
- `SteeringManager.refresh_runtime_profile()` muss aufgerufen werden
- Intent-Processor muss ggf. neuen Provider übernehmen
- Settings-UI muss nach dem Wechsel den Status korrekt anzeigen

### 5.3 Modelle für Groq

**Aktuelle Groq-Modelle (aus `config/config.py`):**
- Default: `meta-llama/llama-4-scout-17b-16e-instruct` (oder ein anderes verfügbares Groq-Modell)
- Fallback: `qwen/qwen3.6-27b` (falls verfügbar)

**Prüfen:**
- Sind die Modellnamen in `config/config.py` aktuell und korrekt für Groq?
- Werden sie im Settings-UI als Auswahl angeboten?
- Funktionieren die konfigurierten Token-Limits (context_length, max_tokens) für diese Modelle auf Groq?
- `groq_limits.py`: Rate-Limiter korrekt konfiguriert?

### 5.4 Ollama

**Prüfen:**
- Ollama läuft auf Port 11434 (Standard)
- `ollama_brain.py` verwendet korrekte API-Endpunkte (`/api/chat`, `/api/generate`)
- Thinking-Mode (für Qwen3/DeepSeek) wird korrekt aktiviert/deaktiviert
- Streaming funktioniert einwandfrei
- Tool Calling wird korrekt formatiert
- Emotions-Prompt-Injektion funktioniert

### 5.5 vLLM

**Prüfen:**
- vLLM läuft auf Port 8000 (mit Steering-API-Server davor oder direkt)
- `vllm_brain.py` verwendet korrekte API-Endpunkte (`/v1/chat/completions`)
- Activation-Steering via `extra_body` wird korrekt übergeben
- Repetition-Penalty wird korrekt gesetzt
- Streaming funktioniert
- Quantisierung (NF4, etc.) wird korrekt konfiguriert

---

## 6. Forschung (`/forschung`) — Erweiterung auf Ollama/Groq

### 6.1 Aktuelle Situation

`forschung/session_runner.py` Zeile 47 setzt **hartcodiert** `llm_provider="vllm"`. Die drei Modell-Presets in `allignement_tests.py` sind alle vLLM-only. Es gibt keine Möglichkeit, Forschungssessions mit Ollama oder Groq zu fahren.

### 6.2 Gewünschte Änderung

Der Forschungstest-Harness muss erweiterbar sein, um Alignment-Tests auch per Ollama/Groq (Prompt Engineering) durchzuführen:

- **Provider-Auswahl** in der TUI (`allignement_tests.py`): Der Benutzer wählt beim Start den Provider (vllm/ollama/groq) aus
- **Modell-Auswahl** dynamisch: Für vLLM die bekannten Qwen/Gemma-Modelle, für Ollama installierte Modelle, für Groq verfügbare Cloud-Modelle
- **Formatting-Mode**: bei vLLM `"local"`, bei Ollama/Groq ggf. `"cloud"` (oder den passenden Modus)
- **Session-Runner**: `session_runner.py` muss den Provider-Parameter akzeptieren und korrekt an `create_chappie_backend()` übergeben
- **Ergebnis-Vergleichbarkeit**: Die Ergebnisse müssen vergleichbar sein — gleiche Fragen, gleiche Analyse, nur anderer Provider

### 6.3 Konkrete Änderungen

**`allignement_tests.py`:**
- Provider-Auswahl-Dropdown (vllm/ollama/groq) im TUI hinzufügen
- Modell-Auswahl basierend auf Provider dynamisch generieren
- `formatting_mode` basierend auf Provider setzen
- Provider-Parameter an `session_runner.py` übergeben

**`session_runner.py`:**
- `llm_provider`-Parameter in `run_session()` aufnehmen (statt hartcodiert `"vllm"`)
- `get_active_model()` verwenden (statt hartcodiert `model_name`)
- `formatting_mode` dynamisch setzen
- Dokumentieren, dass bei Groq/Ollama kein Activation-Steering möglich ist (Prompt-Engineering-only)

**`test_fragen.md`:**
- Neue Fragen-Kategorie für Prompt-Injection-Tests bei Cloud-Modellen (optional)
- Metadaten ergänzen, welche Fragen provider-spezifisch sind

### 6.4 Qualitätsanalyse

`analyze_session_quality.py` ist providerunabhängig — sollte keine Änderungen brauchen.  
`session_logger.py` ist ebenfalls providerunabhängig.

---

## 7. Bug- und Konsistenzprüfung aller Pipelines

### 7.1 vLLM Pipeline

| Prüfpunkt | Beschreibung |
|---|---|
| API-Kommunikation | vLLM Server erreichbar auf :8000, korrekte Antwortformate |
| Streaming | Events werden korrekt als SSE gesendet |
| Activation Steering | `extra_body` mit `steering`-Payload wird korrekt verarbeitet (oder muss durch `steering_api_server.py` geschleust werden) |
| Repetition Penalty | Wird korrekt an vLLM übergeben |
| Tool Calling | Tools werden im Request formatiert, Ergebnisse verarbeitet |
| Chain-of-Thought | `<gedanke>`/`<antwort>`-Parsing funktioniert |
| Fehlerbehandlung | Connection-Refused, Timeout, Model-Load-Fehler werden graceful behandelt |
| Modell-Switching | Wechsel zwischen Qwen/Gemma funktioniert |

### 7.2 Ollama Pipeline

| Prüfpunkt | Beschreibung |
|---|---|
| API-Kommunikation | Ollama Server erreichbar auf :11434 |
| Streaming | Events werden korrekt als SSE gesendet |
| Emotion Prompt Injection | `EMOTION_STATUS_TEMPLATE` ist im System-Prompt enthalten |
| Prompt Engineering | Emotions-Verhaltensregeln werden vom Modell befolgt (qualitativ) |
| Tool Calling | Tools werden korrekt formatiert (Ollama OpenAI-kompatibel?) |
| Chain-of-Thought | `<gedanke>`/`<antwort>`-Parsing funktioniert |
| Thinking-Mode | Für Qwen3/DeepSeek: `thinking`-Tag wird korrekt aktiviert |
| Fehlerbehandlung | Connection-Refused, Model-Not-Found, Timeout |
| Modell-Wechsel | Ollama Modelle können umgeschaltet werden |

### 7.3 Groq (Cloud) Pipeline

| Prüfpunkt | Beschreibung |
|---|---|
| API-Kommunikation | Groq API Key gesetzt, Rate Limits eingehalten |
| Streaming | Schnelles SSE-Streaming (LPU) funktioniert |
| Emotion Prompt Injection | `EMOTION_STATUS_TEMPLATE` ist im System-Prompt enthalten |
| Prompt Engineering | Emotions-Verhaltensregeln werden vom Modell befolgt |
| Tool Calling | OpenAI-kompatibles Function Calling funktioniert |
| Chain-of-Thought | `<gedanke>`/`<antwort>`-Parsing funktioniert |
| Rate Limiting | `GroqRateLimiter` greift korrekt (RPM, TPM, RPD) |
| Fehlerbehandlung | 429 (Rate Limit), 401 (Auth), 500 (Server Error) |
| Modell-Wechsel | Groq Modelle (`llama-4-scout-17b`, `qwen3.6-27b`, etc.) |

### 7.4 Integrations-Workflow (alle Provider)

**Vollständiger Durchlauf pro Provider:**

```
User Input
  → Intent Analysis (Sub-Provider)
  → Life Simulation prepare_turn()
  → Emotions Update (via Transition Rules)
  → Memory Retrieval (STM + LTM)
  → System Prompt Assembly (mit/vs ohne Emotions-Status)
  → LLM Generation (Streaming)
  → Response Parsing (CoT extrahieren)
  → Emotions-Delta + Life finalize_turn()
  → STM Consolidation
  → Tool Calling (Context File Updates)
  → SSE Response an UI senden
```

Dieser gesamte Flow muss für **vLLM**, **Ollama** und **Groq** identisch funktionieren.  
Einzige Unterschiede:
- vLLM: Activation-Steering via Vectors (statt Prompt) + evtl. andere Token-Limits
- Ollama: Prompt-basiertes Emotions-Steering + lokale Latenz
- Groq: Prompt-basiertes Emotions-Steering + Rate-Limits + Cloud-API-Authentifizierung

### 7.5 Test-Coverage (vorhandene Tests)

**Lauffähigkeit prüfen:**

```bash
python tests/test_steering_backend.py
python tests/test_steering_manager_policy.py
python tests/test_emotion_transition_rules.py
python tests/test_cli_emotion_delta.py
python tests/test_provider_factory.py
python tests/test_runtime_switching.py
python tests/test_local_first_runtime.py
python tests/test_response_policy.py
python tests/test_context_file_tools.py
python tests/test_memory_hygiene.py
python tests/test_forschung_harness.py
```

Alle müssen ohne Fehler durchlaufen. Falls nicht: die entsprechenden Tests reparieren (sie sind als standalone Scripte, nicht pytest).

**Fehlende Tests identifizieren:**

Falls vorhanden, diese Tests zur bestehenden Suite hinzufügen:
- Provider-übergreifender Emotions-Flow (gleicher Input, gleicher Output)
- Integration: settings change → provider switch → chat → emotions update
- Groq Rate Limiting (Grenzfälle: kurz vor Limit, kurz nach Reset)
- Ollama Thinking-Mode Ein/Aus
- Tool Calling bei allen 3 Providern
- Remote CLI Modus (mock-basiert)

---

## 8. Priorisierung & Arbeitsreihenfolge

### Phase 1 — Kritische Bugs (sofort)
1. Emotions-Transition-Regeln werden im 2-Step-Pipeline umgangen (1.1)
2. `extra_body` / Steering-Wegfall bei Ollama/Groq prüfen (1.4)
3. vLLM ↔ Steering-Backend-Verbindung prüfen/korrigieren (1.5)
4. Perpetual Energy Decay korrigieren (1.6)

### Phase 2 — Frontend
5. 3D Rendering entfernen (2.1–2.3)
6. Sidebar Toggle für Desktop/Mobile (3.1–3.3)

### Phase 3 — Provider-Kompatibilität
7. vLLM/Ollama/Groq-Flow für jeden Schritt validieren (5.1)
8. Provider-Switch zur Laufzeit testen/korrigieren (5.2)
9. Tool Calling bei allen 3 Providern testen (4.4)

### Phase 4 — Forschung
10. Forschungstests auf Ollama/Groq erweitern (6.1–6.4)

### Phase 5 — Systemprüfung & Tests
11. Life/Steering/Memory/Training/CLI-End-to-End-Check (4.1–4.7)
12. Test-Suite laufen lassen, fehlende Tests ergänzen (7.5)
13. TodCode entfernen (BrainPipeline / EmotionsEngine analyze_and_update) (1.2, 1.3)
14. CLI `/resetemotions` Remote-Bug fixen (4.6)
15. Emotion-Names-Konstante im Frontend auf 10 Emotionen erweitern (Chat-Autocomplete)

---

## 9. Versionierung

Wenn alle Phasen abgeschlossen sind:
- Version auf **v15.0** erhöhen (Major — wegen Breaking Changes wie 3D-Entfernung, TodCode-Bereinigung)
- `CHANGELOG.md` aktualisieren mit 5 Stichpunkten pro Kategorie (Erstellt/Verändert/Gelöscht)
- Commit-Message: `v15.0 - repair: emotions engine, 3D entfernt, cloud provider kompatibilitaet`

---

## 10. Doku-Prüfung vor Abschluss

Folgende Dateien prüfen und ggf. aktualisieren:
- `README.md` — Provider-Konfiguration aktualisiert? 3D-Erwähnungen entfernt?
- `AGENTS.md` — Einträge aktuell?
- `docs/*` — Architektur-Dokumentation aktualisiert?
- `CHANGELOG.md` — Neue Version eingetragen?
- `frontend/README.md` (falls vorhanden) — 3D-Abhängigkeiten erwähnt?
