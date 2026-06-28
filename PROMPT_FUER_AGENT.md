# Prompt für nächsten KI-Agenten: CHAPPiE Timing + Effizienz-Fixes

**Repository**: CHAPPiE (`C:\Users\Benja\OneDrive\Coding\CHAPPiE`)
**Datum**: 14. Mai 2026
**Hauptdatei**: `web_infrastructure/backend_wrapper.py` (2370 Zeilen, sauberer Git-Zustand Commit `0390ee8`)

---

## ÜBERGEORDNETES ZIEL

CHAPPiE hat aktuell Performance-Probleme: Antworten dauern 2–10 Minuten, Token-Streaming funktioniert nicht zuverlässig, und es gibt keine Transparenz über die Generierungsdauer. Der gesamte End-to-End-Flow muss zuverlässig und schnell funktionieren:

**User sendet Nachricht → UI zeigt sofort User-Nachricht an → Backend verarbeitet (Intent-Analyse, Memory-Suche, Generierung) → Antwort-Tokens werden LIVE in der UI gestreamt → Finale Antwort erscheint**

Alle Optimierungen müssen bei **gleicher Business-Logik** nur die Effizienz verbessern. Keine Änderungen an der Art, WIE CHAPPiE antwortet.

---

## KONKRETE ZIELE DIESER ARBEIT

### Ziel 1: Live-Timer während Generierung
Während CHAPPiE denkt ("Habs gleich, gib mir noch einen Moment...") soll ein kleiner Live-Timer unter dem Denk-Text laufen (z.B. "3.2s"), der die bisherige Generierungsdauer anzeigt.

### Ziel 2: Timing-Metriken im Info-Popup
Im "i"-Button-Popup (neben jeder Assistant-Nachricht) detaillierte Zeitmetriken anzeigen:
- Time to First Token (TTFT)
- Thinking-Zeit (Reasoning-Dauer)
- Antwort-Zeit (Answer-Dauer)
- Gesamtdauer
- Token-Anzahl (Reasoning-Tokens vs. Answer-Tokens vs. Total)

### Ziel 3: Streaming muss zuverlässig funktionieren
Jeder generierte Token muss SOFORT in der UI erscheinen – Reasoning-Tokens in der hellgrauen Box, Antwort-Tokens in der Haupt-Box. Kein Warten auf komplette Antwort.

### Ziel 4: Effizienz bei gleicher Logik
Die gesamte Pipeline (Intent → Memory → Prompt → Generate → Post-Process) soll so schnell wie möglich laufen, ohne die Antwort-Qualität zu verändern.

---

## WAS BEREITS ERFOLGREICH UMGESETZT WURDE

### Frontend (`frontend/src/pages/chat-page.tsx`) – FERTIG, NICHT ÄNDERN
- `genStartTime` State + `elapsedMs` State
- `useEffect` aktualisiert `elapsedMs` alle 100ms während thinking/streaming
- `setGenStartTime(Date.now())` beim Message-Start, `null` im finally
- Thinking-Nachricht trägt `metadata: { timer_ms: elapsedMs }`
- Thinking-Rendering zeigt Timer unter Text (Sekunden/Minuten-Format)
- Info-Popup enthält "Timing"-Sektion, liest `meta.timing.*` (ttft_ms, total_gen_ms, reasoning_time_ms, answer_time_ms, total_tokens, reasoning_tokens, answer_tokens)

### Backend-Metadaten (`web_infrastructure/backend_wrapper.py` Zeile ~199)
- `"timing": result.get("timing", {})` in `_build_assistant_message` metadata eingefügt (1 Zeile, funktioniert)

### Bereits in früheren Commits umgesetzt (Commit `0390ee8` und davor)
- **Steering**: Alpha-Werte gesenkt (max_alpha 0.58–0.78, boost 1.05–1.15), Caps reduziert (PLAN_STRENGTH_SOFT_CAP=1.2). Keine nummerischen Artefakte mehr.
- **Thinking aktiviert**: `enable_thinking=True` in vllm_brain.py und `think=True` in ollama_brain.py
- **Reasoning-Streaming gefixt**: vllm_brain.py + ollama_brain.py yielde Reasoning-Tokens als `<think>...</think>` (vorher: wurden nur gezählt, nie ausgegeben – das war der Grund für 10-Minuten-Wartezeit)
- **Think-Tag-Parsing**: `<think>` zu response_parser.py hinzugefügt
- **IntentProcessor**: Quick-Classify (triviale Inputs → kein LLM-Call), Prompt von 237 auf ~50 Zeilen, max_tokens 512
- **Memory**: Doppelte Query-Extraction entfernt, nur eine search_memory mit top_k=12
- **STM-Writes**: In Hintergrund-Thread ausgelagert
- **max_tokens**: Von 1024 auf 2048 erhöht
- **CORS**: Explizite Header in StreamingResponse
- **Provider-Anzeige**: UI zeigt jetzt "via: vllm/ollama/groq" neben Modellname
- **Doppelte User-Nachricht**: gefixt (loadedOnce-Flag)
- **Reasoning-Box**: Hellgraue Box über der Antwort, zeigt live gestreamte Thinking-Tokens

---

## WAS NOCH NICHT UMGESETZT IST (HIER ANSETZEN)

**Nur `web_infrastructure/backend_wrapper.py` – Datei ist aktuell im sauberen Git-Zustand (Commit `0390ee8`, 2370 Zeilen, kompiliert sauber).**

### Schritt 1: Timing-Variablen + Helpers VOR dem Token-Loop einfügen
**Ort**: ca. Zeile 1792, direkt vor `for token in token_generator:` in `_process_two_step_stream`

Es müssen eingefügt werden:
```python
gen_start = time.time()
first_token_ts = None
reasoning_start_ts = None
reasoning_end_ts = None
reasoning_token_count = 0
answer_start_ts = None
answer_end_ts = None
answer_token_count = 0

# Zwei lokale Helper, die bei jedem Yield die Timing-Variablen aktualisieren
def _emit_answer(content: str): ...
def _emit_reasoning(content: str): ...
```

### Schritt 2: Alle Yields im Loop ersetzen
Jedes `yield {"event": "token", "content": X, "token_type": "answer"}` muss durch `yield _emit_answer(X)` ersetzt werden.
Jedes `yield {"event": "token", "content": X, "token_type": "reasoning"}` muss durch `yield _emit_reasoning(X)` ersetzt werden.

**ACHTUNG**: Es gibt 8 Yield-Stellen im Think-Tag-Parser-Loop (ca. Zeilen 1808–1838). Jede muss EINZELN mit KURZEM, EINDEUTIGEM `oldString` ersetzt werden.

Aktuell sehen die Yields so aus:
- `yield {"event": "token", "content": prefix, "token_type": "answer"}` (2×)
- `yield {"event": "token", "content": emit, "token_type": "reasoning"}` (1×)
- `yield {"event": "token", "content": reasoning, "token_type": "reasoning"}` (1×)
- `yield {"event": "token", "content": think_buffer, "token_type": "answer"}` (1×)
- `yield {"event": "token", "content": think_buffer, "token_type": token_type}` (1×)

### Schritt 3: Timing-Dict NACH dem Loop bauen
**Ort**: Direkt nach dem Token-Loop (nach dem letzten `yield`, vor `raw_response = "".join(raw_parts)`)

```python
gen_end = time.time()
total_token_count = reasoning_token_count + answer_token_count
timing = {
    "ttft_ms": round((first_token_ts - gen_start) * 1000) if first_token_ts else 0,
    "total_gen_ms": round((gen_end - gen_start) * 1000),
    "total_tokens": total_token_count,
    "reasoning_tokens": reasoning_token_count,
    "answer_tokens": answer_token_count,
    "reasoning_time_ms": round((reasoning_end_ts - reasoning_start_ts) * 1000) if reasoning_start_ts and reasoning_end_ts else 0,
    "answer_time_ms": round((answer_end_ts - answer_start_ts) * 1000) if answer_start_ts and answer_end_ts else 0,
}
```

### Schritt 4: Timing ins result-Dict
**Ort**: ca. Zeile 1937, nach `"model": get_active_model(),`

```python
"timing": timing,
```

---

## WICHTIGE REGELN FÜR DIE UMSETZUNG

1. **Kein `replaceAll=true`** – jeder Edit mit kurzem, eindeutigem `oldString`
2. **Nach jedem Edit prüfen**: `python -c "import py_compile; py_compile.compile('web_infrastructure/backend_wrapper.py', doraise=True); print('OK')"`
3. **Zeilenzahl prüfen**: `(Get-Content "web_infrastructure/backend_wrapper.py").Count` – darf nicht plötzlich um Hunderte Zeilen schrumpfen
4. **Falls was schiefgeht**: `git checkout -- web_infrastructure/backend_wrapper.py` und von vorne
5. **Nur `backend_wrapper.py` ändern** – Frontend (`chat-page.tsx`) ist FERTIG und KOMPILIEREND, nicht anfassen

---

## BISHERIGE FEHLVERSUCHE (Lektionen)

- **Dreimal gescheitert**: Zu große `oldString`-Blöcke (50+ Zeilen) für Token-Loop-Ersetzung. Die Blöcke matchten falsch oder löschten unbeabsichtigt Code.
- **replaceAll-Fehler**: Ein `replaceAll=true` auf `"provider"`/`"model"` matchte 11 Stellen und duplizierte Felder in falsche Dicts.
- **Lösung**: Jeder Yield einzeln mit maximal 3–5 Zeilen `oldString` ersetzen, der durch umgebende Unique-Variablen (`think_buffer`, `in_think`, etc.) eindeutig ist.

---

## END-TO-END FLOW (als Referenz)

```
User tippt Nachricht → Enter
  → Frontend: setDisplayMessages([...prev, userMsg])  ← sofort sichtbar
  → Frontend: fetch POST /chat/stream mit SSE
  → Backend: Step 1 Intent-Analyse (LLM-Call, synchron)
  → Backend: Memory-Suche (ChromaDB)
  → Backend: Step 2 Response-Generierung (streaming)
      → vLLM/Ollama erzeugt Thinking-Tokens → <think>...</think>
      → vLLM/Ollama erzeugt Answer-Tokens
      → Backend-Stream-Loop parsed <think>-Tags in Echtzeit
      → yield {"event": "token", "content": ..., "token_type": "reasoning"}
      → yield {"event": "token", "content": ..., "token_type": "answer"}
  → SSE-Event "token" → Frontend zeigt Token SOFORT
      → reasoning-Tokens: hellgraue Box über der Antwort
      → answer-Tokens: Haupt-Antwort-Box
  → SSE-Event "turn_finished" → Frontend finalisiert Nachricht
  → Frontend speichert metadata (rag_memories, emotion_delta, timing, ...)
  → User kann "i"-Button klicken → Popup mit allen Details
```
