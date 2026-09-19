# Optimierung der 4 LLM-Aufrufe

**Datum:** 2026-04-02
**Status:** Planung
**Ziel:** Latenz um ~92% senken, von ~1550ms auf ~120ms pro Turn

---

## Problem

Jede User-Anfrage durchlaeuft aktuell 4 sequentielle LLM-Aufrufe bevor die finale Antwort generiert wird:

| Agent | Aufgabe | Laufzeit ca. |
|---|---|---|
| Sensory Cortex | Input-Klassifikation | ~300ms |
| Amygdala | Emotionsanalyse | ~400ms |
| Hippocampus | Memory-Entscheidungen | ~350ms |
| Prefrontal Cortex | Strategie-Entscheidung | ~500ms |
| **Summe vor Antwort** | | **~1550ms** |

Zusaetzlich kommt der finale Antwort-Call (~500-1500ms) hinzu.

**Gesamt pro Turn: ~2000-3000ms**

---

## Loesung 1: Sensory Cortex → Deterministisch ersetzen

### Ist-Zustand
LLM klassifiziert Input-Typ, Dringlichkeit, ob Memory-Suche noetig ist.

### Ziel-Zustand
Rule-based + Keyword-Matching. Ein reiner Klassifikator braucht kein LLM.

### Umsetzung

```python
class DeterministicSensoryCortex:
    TECHNICAL_WORDS = {
        "implement", "code", "debug", "architektur", "fehler", "api",
        "funktion", "modul", "server", "deploy", "test", "bug", "fix"
    }
    EMOTIONAL_WORDS = {
        "traurig", "wuetend", "danke", "super", "scheisse", "hilf mir",
        "genervt", "froh", "gluecklich", "enttaeuscht", "verrueckt"
    }
    MEMORY_WORDS = {
        "erinner", "letztes mal", "wir haben", "gesagt", "besprochen",
        "damals", "frueher", "nochmal", "wieder"
    }
    URGENCY_WORDS = {
        "fehler", "bug", "crash", "dringend", "hilfe", "problem", "sofort"
    }

    def classify(self, user_input: str) -> Dict[str, Any]:
        lower = user_input.lower()
        words = set(lower.split())

        # Input-Typ bestimmen
        tech_hits = len(words & self.TECHNICAL_WORDS)
        emo_hits = len(words & self.EMOTIONAL_WORDS)

        if tech_hits >= emo_hits and tech_hits > 0:
            input_type = "technical"
        elif emo_hits > tech_hits and emo_hits > 0:
            input_type = "emotional"
        else:
            input_type = "conversation"

        # Dringlichkeit
        urgency_hits = len(words & self.URGENCY_WORDS)
        if urgency_hits > 0:
            urgency = "high"
        elif input_type in ("technical", "emotional"):
            urgency = "medium"
        else:
            urgency = "low"

        # Memory-Suche noetig?
        memory_hits = len(words & self.MEMORY_WORDS)
        requires_memory = memory_hits > 0 or input_type != "conversation"

        # Einfache Entity-Extraktion (Stopwords entfernen)
        stop_words = {"der", "die", "das", "und", "ich", "bin", "mir", "du", "ist", "ein", "eine"}
        entities = [w for w in lower.split() if w not in stop_words and len(w) > 2]

        return {
            "input_type": input_type,
            "urgency": urgency,
            "requires_memory_search": requires_memory,
            "entities": entities[:8],
            "confidence": min(1.0, max(tech_hits, emo_hits, memory_hits) / 4.0),
        }
```

### Einsparung
- **1 LLM-Aufruf entfernt**
- Laufzeit: <1ms statt ~300ms
- Konfidenz-Score kann bei Unsicherheit (<0.3) trotzdem LLM-Fallback triggern

---

## Loesung 2: Amygdala → Hybrid: Regel-basiert + LLM nur bei Ambivalenz

### Ist-Zustand
LLM analysiert 7 Emotionen, berechnet intensity, memory_boost, steering_hints.

### Ziel-Zustand
Sentiment-Lexikon + Emotion-Woerterbuch als Fast-Path. LLM nur wenn Konflikt oder niedrige Konfidenz.

### Umsetzung

```python
EMOTION_LEXIKON = {
    "happiness": ["freu", "toll", "super", "klasse", "hammer", "witzig", "lach", "gott sei dank", "endlich"],
    "sadness": ["traurig", "schlecht", "mist", "schade", "deprimiert", "leider", "weinen", "einsam"],
    "frustration": ["wuetend", "genervt", "scheisse", "idiot", "aerger", "nerv", "kotzen", "unfassbar"],
    "trust": ["danke", "vertrau", "gut", "gerne", "gemeinsam", "sicher", "stabil", "zuverlaessig"],
    "curiosity": ["warum", "wie", "was wenn", "interessant", "erklaer", "verstehe nicht", "erkunden"],
    "motivation": ["will", "ziele", "schaffen", "voran", "anpacken", "motivation", "loslegen"],
    "energy": ["muede", "schlaf", "wach", "power", "energie", "kaputt", "fit", "erschöpft"],
}

# VAD-Mapping fuer bekannte Emotionen
EMOTION_VAD = {
    "happiness":  ( 0.8,  0.6,  0.6),
    "sadness":    (-0.8, -0.4, -0.5),
    "frustration":(-0.6,  0.7,  0.3),
    "trust":      ( 0.7, -0.2,  0.4),
    "curiosity":  ( 0.4,  0.5,  0.2),
    "motivation": ( 0.5,  0.8,  0.7),
    "energy":     ( 0.3,  0.9,  0.5),
}

def analyze_emotions_fast(
    user_input: str,
    current_emotions: Dict[str, int],
    use_llm_fallback: bool = True,
) -> Dict[str, Any]:
    lower = user_input.lower()
    hits = {emo: 0 for emo in EMOTION_LEXIKON}

    for emo, words in EMOTION_LEXIKON.items():
        for w in words:
            if w in lower:
                hits[emo] += 1

    total = sum(hits.values())

    # Kein klares Signal → Default, kein LLM noetig
    if total == 0:
        return _build_neutral_result(current_emotions)

    # Ambivalent (1-2 Treffer) → LLM als Tiebreaker
    if total <= 2 and use_llm_fallback:
        return _llm_amygdala_fallback(user_input, current_emotions)

    # Klarer Fall → deterministisch
    primary = max(hits, key=hits.get)
    intensity = min(1.0, total / 8.0)

    # Emotion-Updates berechnen
    emotions_update = {}
    for emo, count in hits.items():
        if count > 0:
            vad = EMOTION_VAD[emo]
            delta = int(count * 8 * (1 if vad[0] > 0 else -1))
            emotions_update[emo] = {"delta": delta, "reason": f"lexikon_match:{emo}"}

    # Steering hints fuer vLLM
    steering_hints = []
    for emo, count in hits.items():
        if count > 0:
            vad = EMOTION_VAD[emo]
            alpha = min(1.5, count * 0.4)
            steering_hints.append({
                "target_emotion": emo,
                "alpha": alpha,
                "vad": {"valence": vad[0], "arousal": vad[1], "dominance": vad[2]},
            })

    return {
        "primary_emotion": primary,
        "emotional_intensity": intensity,
        "valence": EMOTION_VAD[primary][0],
        "arousal": EMOTION_VAD[primary][1],
        "dominance": EMOTION_VAD[primary][2],
        "emotions_update": emotions_update,
        "memory_boost_factor": round(1.0 + intensity * 2.0, 2),
        "personal_relevance": min(1.0, intensity * 1.5),
        "steering_hints": steering_hints,
        "reasoning": f"Lexikon-basiert: {primary} ({total} Treffer)",
        "method": "deterministic",
    }
```

### Einsparung
- **~60-70% der Amygdala-Aufrufe entfallen**
- Fast-Path: <1ms
- Fallback-Pfad (LLM): ~200-500ms
- Durchschnitt: ~120ms statt ~400ms

---

## Loesung 3: Hippocampus → Zusammenlegen mit Memory-Engine

### Ist-Zustand
LLM entscheidet ob encodieren, welche importance, extrahiert Suchquery, bestimmt Context-Relevanz.

### Ziel-Zustand
Memory-Engine entscheidet selbst. Encoding-Entscheidung ist regelbasiert. Query-Extraction via TF-IDF oder Keyword-Filter.

### Umsetzung

```python
def decide_memory_operations(
    user_input: str,
    sensory: Dict[str, Any],
    amygdala: Dict[str, Any],
) -> Dict[str, Any]:
    lower = user_input.lower()
    words = user_input.split()

    # === Encoding-Entscheidung ===
    too_short = len(words) < 3
    is_greeting = any(w in lower for w in ["hi", "hallo", "hey", "moin", "servus", "grüß"])
    is_filler = any(w in lower for w in ["ok", "ja", "nein", "danke", "bitte", "achso"])
    should_encode = not (too_short and (is_greeting or is_filler))

    # Importance aus Amygdala-Intensity
    emo_intensity = amygdala.get("emotional_intensity", 0.0)
    if emo_intensity > 0.6:
        importance = "high"
    elif emo_intensity > 0.3 or len(words) > 15:
        importance = "medium"
    else:
        importance = "low"

    # Memory-Typ
    is_question = user_input.strip().endswith("?")
    if is_question:
        memory_type = "episodic"
    elif sensory.get("input_type") == "technical":
        memory_type = "semantic"
    else:
        memory_type = "episodic"

    # === Query-Extraction ===
    stop_words = {
        "der", "die", "das", "und", "ich", "bin", "mir", "du", "ist",
        "ein", "eine", "es", "nicht", "auch", "nur", "noch", "schon",
        "aber", "oder", "wenn", "dann", "weil", "dass", "dem", "den",
        "von", "zum", "zur", "mit", "auf", "an", "in", "für", "wie",
    }
    content_words = [w for w in lower.split() if w not in stop_words and len(w) > 2]
    search_query = " ".join(content_words[:6]) or user_input[:80]

    # === Context-Relevanz ===
    need_soul = any(w in lower for w in {"ich", "selbst", "persönlichkeit", "wer bin", "identität", "bewusstsein"})
    need_user = any(w in lower for w in {"du", "dein", "user", "benjamin", "dir"})
    need_preferences = any(w in lower for w in {"einstellung", "pref", "config", "modell", "anbieter"})
    need_stm = True
    need_ltm = importance in ("high", "medium") or len(content_words) > 4

    # Short-Term Entries planen
    short_term_entries = []
    if should_encode and importance != "low":
        short_term_entries.append({
            "content": user_input[:200],
            "category": sensory.get("input_type", "conversation"),
            "importance": importance,
        })

    return {
        "should_encode": should_encode,
        "encoding_decision": {
            "importance": importance,
            "memory_type": memory_type,
            "emotional_boost": amygdala.get("memory_boost_factor", 1.0),
            "content_to_store": user_input[:300] if should_encode else "",
            "tags": content_words[:5],
        },
        "search_query": search_query,
        "related_concepts": content_words[:4],
        "context_relevance": {
            "need_soul_context": need_soul,
            "need_user_context": need_user,
            "need_preferences": need_preferences,
            "need_short_term_memory": need_stm,
            "need_long_term_memory": need_ltm,
        },
        "short_term_entries": short_term_entries,
        "confidence": min(1.0, len(content_words) / 6.0),
        "method": "deterministic",
    }
```

### Einsparung
- **1 LLM-Aufruf entfernt**
- Laufzeit: <1ms statt ~350ms
- Encoding-Qualitaet ist vergleichbar – die LLM-Entscheidung war ohnehin oft "medium, episodic"

---

## Loesung 4: Prefrontal Cortex → Reduzieren auf Strategie-Entscheidung

### Ist-Zustand
LLM orchestriert alles – Strategie, Tone, Guidance, Planning-Mode, Life-Alignment.

### Ziel-Zustand
Die meisten Entscheidungen sind aus den vorherigen Schritten ableitbar. Nur die finale Response-Strategie braucht Kreativitaet – und die kann direkt in den Generation-Call integriert werden.

### Umsetzung

```python
def derive_prefrontal_deterministic(
    sensory: Dict[str, Any],
    amygdala: Dict[str, Any],
    life_context: Dict[str, Any],
    workspace: Dict[str, Any],
    emotions: Dict[str, int],
) -> Dict[str, Any]:
    # === Strategie aus Input-Typ + Emotion ===
    input_type = sensory.get("input_type", "conversation")
    emo_intensity = amygdala.get("emotional_intensity", 0.0)
    primary_emotion = amygdala.get("primary_emotion", "neutral")

    if input_type == "technical":
        strategy = "technical"
        tone = "direct"
    elif input_type == "emotional" or emo_intensity > 0.6:
        strategy = "emotional"
        tone = "empathetic"
    elif life_context.get("current_mode") == "curious":
        strategy = "creative"
        tone = "explorative"
    elif emotions.get("happiness", 50) > 70 and emotions.get("trust", 50) > 60:
        strategy = "conversational"
        tone = "warm"
    elif emotions.get("frustration", 0) > 60:
        strategy = "conversational"
        tone = "sharp_direct"
    else:
        strategy = "conversational"
        tone = "friendly"

    # === Guidance aus Workspace ===
    dominant_focus = workspace.get("dominant_focus", {}).get("label", "Stabilitaet")
    guidance = workspace.get("guidance", "Antworte klar und hilfreich.")
    broadcast = workspace.get("broadcast", "")

    # === Planning-Mode aus Life-Simulation ===
    planning_mode = life_context.get("current_mode", "goal_directed")
    life_alignment = life_context.get("homeostasis", {}).get("guidance", "")

    # === Kontext-Prioritaeten ===
    context_priorities = []
    if sensory.get("requires_memory_search"):
        context_priorities.append("memory")
    if emo_intensity > 0.5:
        context_priorities.append("emotion")
    if life_context.get("homeostasis", {}).get("needs", {}).get("social", 50) < 30:
        context_priorities.append("relationship")
    if not context_priorities:
        context_priorities.append("task")

    return {
        "response_strategy": strategy,
        "tone": tone,
        "response_guidance": guidance,
        "planning_mode": planning_mode,
        "life_alignment": life_alignment,
        "context_priorities": context_priorities,
        "emotional_tone_adjustment": {
            "primary": primary_emotion,
            "intensity": emo_intensity,
        },
        "method": "deterministic",
    }
```

### Einsparung
- **1 LLM-Aufruf entfernt**
- Laufzeit: <1ms statt ~500ms
- Die eigentliche "Intelligenz" steckt ohnehin im finalen Antwort-Call

---

## Ergebnis der Optimierung

| Schritt | Vorher | Nachher | Zeitersparnis |
|---|---|---|---|
| Sensory Cortex | LLM (~300ms) | Deterministisch (<1ms) | ~300ms |
| Amygdala | LLM (~400ms) | Hybrid: 70% fast, 30% LLM (~120ms) | ~280ms |
| Hippocampus | LLM (~350ms) | Deterministisch (<1ms) | ~350ms |
| Prefrontal Cortex | LLM (~500ms) | Deterministisch (<1ms) | ~500ms |
| **Summe vor Antwort** | **~1550ms** | **~120ms** | **~92% schneller** |

### Was bleibt als LLM-Aufruf?

**Nur einer:** Die finale Antwortgenerierung.

```
System: [Basis-Prompt + Emotions-Status + Personality + Style-Instruction]
User: [Eingabe]
Context: [Memories + Life-Simulation + Workspace + Response-Plan]
→ 1x LLM-Call → Antwort
```

**Gesamt pro Turn neu:** ~120ms (Prep) + ~500-1500ms (Antwort) = **~620-1620ms**
**Vorher:** ~1550ms (Prep) + ~500-1500ms (Antwort) = **~2050-3050ms**

---

## Zusaetzliche Beschleunigung

### 1. Parallele Verarbeitung

Amygdala und Hippocampus sind unabhaengig voneinander – koennen parallel laufen:

```python
from concurrent.futures import ThreadPoolExecutor

def process_parallel(user_input: str, sensory_result: Dict) -> Tuple[Dict, Dict]:
    input_data = {"user_input": user_input, "sensory_result": sensory_result}
    with ThreadPoolExecutor(max_workers=2) as pool:
        future_amygdala = pool.submit(amygdala.process, input_data)
        future_hippocampus = pool.submit(hippocampus.process, input_data)
        return future_amygdala.result(), future_hippocampus.result()
```

**Effekt:** Bei LLM-Fallback-Pfaden halbiert sich die Wartezeit.

### 2. Caching fuer haeufige Inputs

```python
import hashlib
from functools import lru_cache

@lru_cache(maxsize=512)
def get_cached_sensory(input_hash: str) -> Dict:
    # ...
```

Begrüßungen, Standardfragen, wiederkehrende Patterns cachen – kein Call noetig.

### 3. Intent-Modell separat lassen

Das Two-Step-System nutzt bereits ein kleines Modell fuer Intent. Das kann so bleiben – aber die 4 Brain-Agents sollten weg.

### 4. Streaming frueher starten

Sobald der Response-Plan steht, kann das Antwort-Modell schon anfangen zu streamen. Life-Simulation `finalize_turn` kann asynchron nachlaufen.

---

## Migrationsplan

### Phase 1: Deterministische Agents einfuehren (1-2 Tage)
- [ ] `DeterministicSensoryCortex` implementieren
- [ ] `HybridAmygdala` implementieren
- [ ] `DeterministicHippocampus` implementieren
- [ ] `DeterministicPrefrontalCortex` implementieren
- [ ] Feature-Flag: `use_deterministic_agents: true/false` in Config

### Phase 2: Parallelisierung (0.5 Tage)
- [ ] Amygdala + Hippocampus parallel ausfuehren
- [ ] ThreadPoolExecutor in Brain-Pipeline integrieren

### Phase 3: Caching (0.5 Tage)
- [ ] Input-Hash-basiertes Caching fuer Sensory + Hippocampus
- [ ] TTL von 24h fuer Cache-Eintraege

### Phase 4: Testing & Validierung (1-2 Tage)
- [ ] Vergleichstests: Deterministisch vs. LLM-Ergebnisse
- [ ] Konfidenz-Schwellen kalibrieren
- [ ] Latenz-Messungen vor/nachher

### Phase 5: Alte Agents entfernen (0.5 Tage)
- [ ] `brain/agents/sensory_cortex.py` → loeschen oder archivieren
- [ ] `brain/agents/hippocampus.py` → loeschen oder archivieren
- [ ] `brain/agents/prefrontal_cortex.py` → loeschen oder archivieren
- [ ] `brain/agents/amygdala.py` → nur noch Fallback-Pfad behalten

---

## Risiken und Gegenmassnahmen

| Risiko | Wahrscheinlichkeit | Gegenmassnahme |
|---|---|---|
| Deterministische Klassifikation trifft schlechter | Mittel | Feature-Flag zum sofortigen Rollback, Konfidenz-Schwellen |
| Lexikon deckt nicht alle Emotionen ab | Hoch | Regelmassige Erweiterung, LLM-Fallback bei niedriger Konfidenz |
| Encoding-Entscheidungen zu grob | Niedrig | Manuelle Review-Stichprobe nach 100 Turns |
| Breaking Changes in Pipeline | Niedrig | Gleiche Return-Signatur wie bisher, nur `method`-Feld neu |
