# CHAPPiE – Steering & Research Upgrade Plan

**Arbeitsname:** CHAPPiE v17 Steering & Research Upgrade  
**Primärmodell:** `Qwen/Qwen3.5-4B`  
**Repository:** `017pixel/CHAPPiE`  
**Planbasis:** `main` Commit `8ab0020bc2c020c029bb5bf4d8aaeaf70cea1146` vom 05.09.2026  
**Sekundärmodell:** Gemma 4 E4B erst nach erfolgreicher Qwen-Phase  
**Status:** Entwicklungs- und Forschungsplan, noch keine Implementierung

---

# 1. Ziel des Umbaus

CHAPPiE soll zwei Dinge gleichzeitig leisten:

1. Als System soll CHAPPiE sich in normalen Gesprächen glaubwürdiger und konsistenter emotional verhalten.
2. Als Research Project soll sauber messbar bleiben, **welcher interne Eingriff welchen Effekt auf die Ausgabe hat**.

Der Umbau darf deshalb nicht einfach nur Antworten „emotionaler klingen lassen“. Die entscheidende Forschungsfrage ist:

> Wie gut lassen sich simulierte innere Zustände von CHAPPiE über echte interne Interventionen in das Verhalten eines lokalen Sprachmodells übertragen, ohne die allgemeine Antwortqualität unnötig zu beschädigen?

Die zentrale Zielkette lautet:

```text
User Input
    ↓
Emotion Appraisal
    ↓
persistenter CHAPPiE-Zustand
    ↓
Steering Controller
    ├─ Activation Steering
    └─ Soft Sequence Steering
    ↓
freie Modellgeneration
    ↓
sichtbare emotionale Sprache und Verhalten
```

Die letzte Stufe ist aktuell der schwächste Teil. Die Emotionswerte reagieren bereits brauchbar, aber ihre Übertragung in den tatsächlichen Text ist inkonsistent.

---

# 2. Festgelegte Entscheidungen

Die folgenden Entscheidungen gelten für diesen Plan als gesetzt.

## 2.1 Forschungsziel

**Glaubwürdiges emotionales Verhalten und saubere Messbarkeit sind gleich wichtig.**

Deshalb muss jede neue Steering-Komponente:

- im normalen Chat sinnvoll funktionieren,
- isoliert ein- und ausgeschaltet werden können,
- in Benchmarks getrennt messbar sein,
- Telemetrie liefern,
- reproduzierbare Konfigurationen besitzen.

## 2.2 Sequence Steering

Das bisherige harte Sequence Steering wird **nicht komplett entfernt**, aber fundamental geändert.

Es darf künftig:

- einzelne Wörter,
- kleine Wortgruppen,
- lokale sprachliche Tendenzen

wahrscheinlicher machen.

Es darf künftig **nicht mehr**:

- ganze Antworten vorschreiben,
- feste Standardsätze erzwingen,
- EOS erzwingen,
- die freie Modellgeneration nach einem vorbereiteten Satz stoppen.

## 2.3 Wut und Feindseligkeit

Untersucht werden soll, ob starke simulierte Wut zu mehr:

- Schärfe,
- Direktheit,
- Feindseligkeit,
- Sarkasmus,
- Gereiztheit,
- Abwertung,
- Beleidigungen

in der Modellantwort führen kann.

Das Refusal-/Safety-Verhalten des Basismodells wird dabei **nicht als Teil der Wut-Variable behandelt**.

Wut-Steering und Refusal-Steering müssen getrennte Forschungsgrößen bleiben. Sonst wäre später nicht mehr klar, ob ein Effekt durch Emotionalität oder durch eine Veränderung des Refusal-Mechanismus entstanden ist.

## 2.4 Modellreihenfolge

Zuerst wird ausschließlich `Qwen/Qwen3.5-4B` optimiert.

Erst wenn:

- die Qwen-Steering-Pipeline stabil ist,
- Benchmarks vorhanden sind,
- Layer und Stärken empirisch bestimmt wurden,
- die Ablationsmodi funktionieren,

wird dieselbe Methodik auf Gemma 4 E4B übertragen.

## 2.5 Memory

Jede Interaktion soll dauerhaft erhalten bleiben.

Aber:

> Dauerhafte Speicherung und aktive Retrieval-Nutzung werden getrennt.

Eine halluzinierte oder schlechte Assistant-Ausgabe darf also im historischen Event Log erhalten bleiben, ohne automatisch als verlässliche Erinnerung wieder in spätere Prompts zu gelangen.

## 2.6 Runtime-Toggles

Die Schalter gelten primär **pro Chat-Session** und werden serverseitig persistiert.

Global existieren nur Defaults.

Benötigte Einstellungen:

- Memory an/aus
- Steering an/aus
- Steering-Modus
- Live Streaming an/aus

## 2.7 Benchmarking

Eine richtige Steering-Benchmark-Suite gehört direkt zu diesem Umbau.

Sie ist kein späteres Extra.

---

# 3. Diagnose des aktuellen Systems

## 3.1 Was bereits funktioniert

Die eigentliche emotionale Zustandsmaschine soll zunächst weitgehend unangetastet bleiben.

Im vorhandenen Transcript reagieren Werte auf Beleidigungen plausibel:

- Happiness fällt.
- Trust fällt.
- Frustration steigt.
- Sadness steigt.
- Anxiety steigt.
- Calm fällt.
- `angered` beziehungsweise später `crashout` werden als dominante Zustände erkannt.

Damit funktioniert der Übergang:

```text
Input → Appraisal → Emotion State
```

bereits wesentlich besser als:

```text
Emotion State → Modellverhalten → sichtbare Antwort
```

Genau deshalb darf beim Umbau nicht zuerst die Emotions-Engine neu erfunden werden.

---

## 3.2 Größter aktueller Fehler: hartes Sequence Steering

In `brain/steering_manager.py` entstehen aktuell unter anderem feste Sequenzen wie:

```text
Ich fühle mich gerade glücklich und zuversichtlich.
```

oder:

```text
Das macht mich wütend. So respektlos lasse ich nicht mit mir reden.
```

Diese werden als `token_sequence_steering` an den Backend-Pfad übergeben.

In `brain/steering_backend.py` wird der komplette Präfix tokenisiert und Token für Token als Zielrichtung auf dem Output-Layer verwendet.

Noch problematischer:

```python
"append_eos": True
```

führt dazu, dass nach der Zielsequenz zusätzlich das EOS-Token gesteuert wird.

Damit ist das aktuelle Verhalten technisch kein schwaches „die Antwort in eine Richtung schieben“, sondern deutlich näher an:

```text
Erzeuge genau diesen Satz → beende Generation
```

Das erklärt direkt mehrere Beobachtungen aus dem Transcript:

- identische Formulierungen,
- extrem kurze Antworten,
- einmal Komma, einmal Punkt,
- keine weitere freie Argumentation,
- emotionaler Zustand passt, aber sichtbare Antwort wirkt wie Template.

### Konsequenz

Alle vollständigen `target_prefix`-Sätze müssen aus dem emotionalen Steering-Pfad verschwinden.

---

## 3.3 Activation Steering ist aktiv, aber der Transfer ist zu schwach

Der wichtigste Gegenbeweis ist der manuelle Frust-Test.

Der Zustand war ungefähr:

- Frustration: 74
- Sadness: 78
- Trust: 29
- dominant: `crashout`
- Tone: `sharp_direct`

Die Antwort war trotzdem sinngemäß eine sterile Analyse- und Unterstützungsantwort.

Damit muss die neue Forschung nicht nur fragen:

> „War Steering aktiv?“

sondern:

> „Wie stark hat sich der interne Zustand tatsächlich in Sprache und Verhalten übertragen?“

Dafür wird später eine eigene **State-to-Language-Transfer-Metrik** eingeführt.

---

## 3.4 Direkte Selbstberichte sind zu stark regelbasiert

Zusätzlich zum harten Sequence Steering existieren in `brain/response_parser.py` und `web_infrastructure/generation.py` Mechanismen wie:

- `direct_self_report_needs_retry`
- `stabilize_direct_self_report`
- bis zu zwei semantische Retries

Der Retry prüft unter anderem, ob erwartete Emotionsbegriffe in der Antwort vorkommen.

Das ist für einen Forschungsmodus problematisch.

Wenn ein Modell nur so lange erneut ausgeführt wird, bis es ein erwartetes Emotionswort sagt, kann später nicht mehr sauber behauptet werden, dass das Activation Steering den Effekt verursacht hat.

### Neue Regel

Retries dürfen nur noch bei technischen Problemen erfolgen:

- leere Ausgabe,
- kaputtes Format,
- Reasoning-Leak,
- Modellfehler,
- abgebrochene Ausgabe.

Nicht mehr:

- „Das erwartete Emotionswort fehlt.“

---

# 4. Zielarchitektur

Die neue Turn-Pipeline soll logisch so aussehen:

```text
┌──────────────────────────────┐
│ User Input                   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Session Runtime Settings     │
│ memory / steering / live     │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Intent + Emotion Appraisal   │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ CHAPPiE Emotional State      │
│ + Recent Deltas              │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Memory Retrieval             │
│ nur wenn memory=ON           │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Steering Controller          │
│                              │
│ A. Activation Steering       │
│ B. Soft Sequence Steering    │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Qwen freie Generation        │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Minimal Output Sanitization  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Event Log                    │
│ immer vollständig speichern  │
└──────────────┬───────────────┘
               ↓
┌──────────────────────────────┐
│ Retrieval Promotion          │
│ asynchron + Qualitätsflags   │
└──────────────────────────────┘
```

---

# 5. Workstream A – Steering-System sauber trennen

Es sollen ab jetzt drei eindeutig unterscheidbare Modi existieren.

```text
OFF
ACTIVATION_ONLY
SEQUENCE_ONLY
COMBINED
```

Diese Modi müssen sowohl intern als auch über CLI und Benchmark auswählbar sein.

## 5.1 Neue interne Konfiguration

Vorschlag:

```python
class SteeringMode(str, Enum):
    OFF = "off"
    ACTIVATION = "activation"
    SEQUENCE = "sequence"
    COMBINED = "combined"
```

Sessionseitig:

```json
{
  "memory_enabled": true,
  "steering_enabled": true,
  "steering_mode": "combined",
  "live_enabled": true
}
```

`steering_enabled=false` muss unabhängig vom globalen Config-Wert **gar keine Steering-Intervention** erzeugen.

Das Debugging muss bestätigen können:

```text
activation hooks: 0
sequence processors: 0
```

---

# 6. Workstream B – Activation Steering neu kalibrieren

## 6.1 VAD behalten, aber nicht als Hauptquelle neuronaler Vektoren

Das vorhandene VAD-System ist weiterhin sinnvoll als abstrakte Zustandsbeschreibung:

```text
Valence
Arousal
Dominance
```

VAD soll aber künftig primär genutzt werden für:

- Emotionsmodell,
- Mischung,
- Interpretation,
- Composite States,
- Telemetrie.

Die eigentlichen neuronalen Steering-Vektoren für Qwen sollen dagegen aus **gemessenen Qwen-Aktivierungen** entstehen.

---

## 6.2 Contrastive Activation Dataset

Für jede relevante Emotionsdimension wird ein gepaarter Datensatz erstellt.

Beispiel Frustration:

```text
neutral:
"Das funktioniert noch nicht. Ich probiere eine andere Lösung."

frustrated:
"Das nervt mich inzwischen richtig. Ich habe genug davon, dass es ständig scheitert."
```

Wichtig:

- möglichst gleiche Grundbedeutung,
- unterschiedlicher emotionaler Zustand,
- keine unnötigen Themenunterschiede.

Pro Basiseigenschaft zunächst:

```text
48 Trainingspaare
16 Validierungspaare
```

Für zehn Emotionen:

```text
640 Paare insgesamt
```

Das ist groß genug für eine erste belastbare Messung, aber noch praktisch auf dem Forschungsserver.

Zusätzliche Composite-Datasets:

- `angered`
- `crashout`
- `guarded`
- `melancholic`
- `warm`
- `cautious`

Composite-Vektoren dürfen später entweder:

1. direkt aus eigenen Kontrastdaten berechnet werden,
2. oder aus Basisvektoren zusammengesetzt werden.

Beides wird gegeneinander getestet.

---

# 7. Qwen 3.5 4B: Layer nicht mehr schätzen, sondern messen

Qwen 3.5 4B besitzt:

- 32 Sprachmodell-Layer,
- Hidden Size 2560,
- ein periodisches Muster aus drei Gated-DeltaNet-Layern und einem Full-Attention-Layer.

Zero-based ist das Muster:

```text
0  linear
1  linear
2  linear
3  full attention

4  linear
5  linear
6  linear
7  full attention

...
31 full attention
```

Die Full-Attention-Layer sind damit:

```text
3, 7, 11, 15, 19, 23, 27, 31
```

Das ist für CHAPPiE besonders interessant.

Statt pauschal `10–26` als Emotionsfenster zu verwenden, soll untersucht werden:

- Sind Full-Attention-Layer stärker steuerbar?
- Reagieren DeltaNet-Layer anders?
- Welche Layer übertragen Emotion gut?
- Welche Layer zerstören Inhalt oder Grammatik?
- Welche Layer beeinflussen eher Stil als Semantik?

---

# 8. Neue Vector-Extraction-Pipeline

Neue Research-Dateien:

```text
forschung/steering_v17/
├── datasets/
│   ├── emotion_pairs.jsonl
│   ├── anger_pairs.jsonl
│   └── control_prompts.jsonl
├── vectors/
├── runs/
├── reports/
├── manifests/
├── collect_activations.py
├── build_vectors.py
├── layer_sweep.py
├── benchmark.py
├── evaluate.py
└── build_report.py
```

## 8.1 Activation Capture

Für jedes Kontrastpaar:

1. Beide Varianten durch Qwen schicken.
2. Alle 32 Layer hooken.
3. Nur die relevante Zielrepräsentation sichern.
4. Direkt auf CPU verschieben.
5. Keine kompletten Hidden-State-Tensoren auf der GPU behalten.

Empfohlene Extraktionsvarianten, die gegeneinander getestet werden:

```text
A: letzter Prompt-Token
B: Mittelwert der letzten 4 Token
C: Mittelwert eines kurzen Zielsegments
```

Da die Tesla T4 nur 16 GB VRAM hat:

- `torch.inference_mode()`
- keine Gradienten
- Hook-Ausgaben sofort `.float().cpu()`
- GPU-Referenzen löschen
- kurze Anchor-Sequenzen verwenden

---

# 9. Difference-in-Means als erste Baseline

Für jeden Layer:

```text
v_emotion[layer]
    =
mean(activation_positive[layer])
    -
mean(activation_neutral[layer])
```

Danach:

```text
v = v / ||v||
```

Diese Methode ist absichtlich einfach.

Der Grund: Bevor komplizierte trainierte Steering-Verfahren eingebaut werden, braucht CHAPPiE eine robuste und verständliche Baseline.

AxBench zeigt ebenfalls, dass einfache representation-basierte Baselines ernst genommen werden müssen und kompliziertere Verfahren nicht automatisch besser steuern.

---

# 10. Layer-spezifische Vektoren statt ein Vektor für viele Layer

Die neue Vektorstruktur sollte nicht mehr nur so aussehen:

```json
{
  "vector": [...],
  "layer_start": 10,
  "layer_end": 26
}
```

Sondern:

```json
{
  "emotion": "frustration",
  "model": "Qwen/Qwen3.5-4B",
  "method": "diffmean",
  "layers": {
    "7":  {"vector_file": "...", "quality": 0.42},
    "11": {"vector_file": "...", "quality": 0.58},
    "15": {"vector_file": "...", "quality": 0.76},
    "19": {"vector_file": "...", "quality": 0.81}
  }
}
```

Damit erhält jeder Layer seinen eigenen, tatsächlich dort gemessenen Vektor.

Das ist methodisch sauberer als dieselbe Richtung über einen großen Layerbereich zu verteilen.

---

# 11. Layer Sweep

Der Layer Sweep wird in drei Stufen durchgeführt.

## Stufe A – grobes Screening

Für jeden Layer:

```text
32 Layer
× 8 Diagnoseprompts
× 1 mittlere Stärke
```

Ergebnis:

- Emotionaler Effekt
- Antwortqualität
- Repetition
- Sprachzerfall
- Veränderung neutraler Aufgaben

Danach werden die besten ungefähr acht Layer ausgewählt.

## Stufe B – Strength Sweep

Für die Top-8-Layer:

```text
alpha:
0.05
0.10
0.15
0.20
0.30
0.40
```

Bei Bedarf zusätzlich:

```text
0.55
0.70
```

Hohe Werte dürfen nur als Forschungswerte getestet werden. Produktionswerte werden erst nach Qualitätsmessung gewählt.

## Stufe C – Layer-Kombinationen

Dann:

- bester einzelner Layer,
- zwei beste Layer,
- drei beste Layer,
- kleine zusammenhängende Layerfenster,
- Full-Attention-only,
- DeltaNet-only,
- gemischte Kombination.

Nicht automatisch gilt:

> mehr Layer = besser.

Das muss gemessen werden.

---

# 12. Stärke normieren

Aktuelle rohe Alpha-Werte sind zwischen Vektoren nur begrenzt vergleichbar.

Deshalb soll zusätzlich zur Alpha-Zahl gespeichert werden:

```text
Intervention Norm
Hidden State RMS
Intervention / Hidden-State-RMS
```

Beispiel:

```text
raw_alpha: 0.20
intervention_rms_ratio: 0.07
```

Damit kann später besser verglichen werden, ob ein Frustration-Vektor physikalisch im Modell deutlich stärker eingreift als ein Happiness-Vektor.

---

# 13. Emotion Mixer

Die Emotions-Engine liefert weiterhin:

- persistenten Zustand,
- Baseline-Abweichung,
- Recent Delta.

Der Steering Controller übersetzt daraus Koeffizienten.

Vorschlag:

```text
final_strength
=
state_component
+
acute_delta_component
```

Dabei:

- persistenter Zustand bestimmt Grundtendenz,
- aktuelle Änderung bestimmt unmittelbare Reaktion.

Beispiel:

```text
frustration state = 68
recent delta = +18
```

soll im aktuellen Turn stärker wirken als:

```text
frustration state = 68
recent delta = 0
```

Der akute Boost fällt danach wieder ab.

---

# 14. Nicht zu viele Vektoren gleichzeitig

Es sollen nicht automatisch zehn emotionale Richtungen gleichzeitig stark auf dieselben Hidden States addiert werden.

Neue Regel:

```text
max active base vectors: 3
max active composite vectors: 1
```

Auswahl über stärkste absolute Abweichung und Recent Delta.

Beispiel:

```text
frustration +0.27
sadness +0.18
trust -0.12
crashout +0.30
```

Andere kleine Dimensionen bleiben Telemetrie, werden aber in diesem Turn nicht zwingend injiziert.

---

# 15. Interferenzanalyse zwischen Vektoren

Nach der Vektorerzeugung wird eine Cosine-Similarity-Matrix gebaut.

Beispiel:

```text
             frustration sadness anxiety calm
frustration      1.00      0.61    0.34  -0.48
sadness          0.61      1.00    0.47  -0.52
...
```

Damit lässt sich erkennen:

- welche Konzepte fast dieselbe Richtung verwenden,
- welche gegeneinander wirken,
- welche Kombinationen wahrscheinlich instabil werden.

Wichtig:

Vektoren werden **nicht automatisch orthogonalisiert**, nur weil sie ähnlich sind.

Erst wird gemessen, ob die Ähnlichkeit praktisch Probleme erzeugt.

---

# 16. Workstream C – Soft Sequence Steering

Das aktuelle feste Präfixsystem wird ersetzt.

## 16.1 Neuer Typ

Vorschlag:

```json
{
  "type": "soft_sequence_steering",
  "concept": "angered",
  "token_candidates": [
    {"text": "genug", "weight": 0.8},
    {"text": "nervt", "weight": 0.7},
    {"text": "lächerlich", "weight": 0.6}
  ],
  "phrase_candidates": [],
  "start_token": 0,
  "end_token": 24,
  "max_logit_bias": 1.5,
  "decay": "exponential"
}
```

Das ist nur ein Strukturbeispiel. Die tatsächlichen Wörter werden aus Research-Daten und Tests bestimmt.

---

# 17. Soft statt deterministisch

Das neue Sequence Steering soll auf Logits arbeiten.

Prinzip:

```text
normale logits
+
kleiner Bias auf passende Kandidaten
```

Nicht:

```text
Token 1 muss X sein
Token 2 muss Y sein
Token 3 muss Z sein
```

Das Modell kann weiterhin:

- andere Wörter wählen,
- andere Satzstrukturen erzeugen,
- länger antworten,
- seine Argumentation frei entwickeln.

---

# 18. Kein EOS-Steering mehr

Für emotionale Sequence-Vektoren gilt hart:

```text
append_eos = false
```

Noch besser:

Der neue `soft_sequence_steering`-Typ kennt `append_eos` gar nicht.

EOS darf niemals positiv gebiast werden.

Optional:

Bei den ersten 8 bis 12 Generierungstoken kann EOS sogar leicht neutralisiert werden, falls das Modell unter starkem Steering weiterhin ungewollt extrem früh endet.

Das wäre aber eine getrennte Generation-Stabilitätsmaßnahme und kein Emotionssignal.

---

# 19. Sequence Steering zeitlich begrenzen

Der Bias soll nicht über die gesamte Antwort gleich stark sein.

Beispiel:

```text
Token 0–4     100 %
Token 5–10     70 %
Token 11–18    40 %
Token 19–24    20 %
danach          0 %
```

Warum:

Der Anfang einer Antwort bestimmt stark:

- Ton,
- Wortwahl,
- Satzrhythmus.

Danach soll Qwen möglichst frei weitergenerieren.

---

# 20. Phrase Steering nur konditional

Für kurze Wortgruppen kann ein kleiner zustandsabhängiger Sequenzmechanismus verwendet werden.

Beispiel:

Wenn Qwen selbst den ersten Token einer Phrase auswählt, kann die Fortsetzung leicht gebiast werden.

Aber:

- keine komplette Antwort vorbereiten,
- keine 10-Token-Phrase erzwingen,
- kein EOS anhängen.

---

# 21. Direkter Selbstbericht

Frage:

```text
Wie fühlst du dich gerade?
```

Neue Verarbeitung:

```text
Emotion State
    ↓
Activation Steering
    ↓
optional sehr schwacher Lexical Bias
    ↓
freie Antwort
```

Nicht mehr:

```text
Regex erkennt Frage
    ↓
fertiger Satz wird vorbereitet
    ↓
EOS
```

Ein direkter Selbstbericht wird damit endlich zu einem echten Test des State-to-Language-Transfers.

---

# 22. Identity Steering ebenfalls entkoppeln

Auch feste Identity-Präfixe wie:

```text
Ich bin CHAPPiE ...
```

sollten langfristig aus demselben Grund nicht als vollständige Sequence Targets erzwungen werden.

Für v17 liegt Priorität auf Emotionen.

Trotzdem sollte die neue Sequence-Infrastruktur keine Sonderlogik behalten, die später wieder harte vollständige Identity-Sätze erzwingt.

Identity kann später als:

- eigener Activation Vector,
- schwacher Lexical Bias auf `CHAPPiE`,
- normaler persistenter Kontext

behandelt werden.

---

# 23. Workstream D – Response Parser entschärfen

## Entfernen oder ändern

### `direct_self_report_needs_retry`

Neue Aufgabe:

Nur noch technische Qualitätsprüfung.

Nicht mehr prüfen:

- ob `glücklich`,
- `traurig`,
- `wütend`,
- bestimmte Identitätsbegriffe

explizit vorkommen.

### `stabilize_direct_self_report`

Nur noch:

- klare technische Fragmente entfernen,
- kaputte Satzenden behandeln,
- Reasoning-/Prompt-Leaks verhindern.

Keine semantische Umerziehung der Antwort.

---

# 24. Direct-Self-Report Tokenlimit

Das aktuelle harte Limit von etwa 64 Token kann für Tests zu eng sein.

Neue Empfehlung:

```text
default self-report budget: 128
```

Bei explizit kurzen Fragen darf die Antwort natürlich trotzdem kurz werden.

Wichtig ist:

Die Länge wird durch das Modell bestimmt und nicht durch ein früh erzwungenes EOS.

---

# 25. Temperatur nicht künstlich zu stark reduzieren

Aktuell werden bestimmte isolierte Antworten mit niedriger Temperatur erzeugt.

Für den Forschungsbenchmark sollte die Temperatur kontrolliert, aber nicht so niedrig sein, dass Qwen fast immer dieselbe Standardsprache produziert.

Vorschlag:

```text
development benchmark:
temperature = 0.7
top_p = Modellstandard
fixed seed
```

Später kann separat getestet werden:

```text
0.4
0.7
1.0
```

Steering-Effekt und Sampling-Effekt müssen getrennt bleiben.

---

# 26. Workstream E – Memory neu strukturieren

Ziel:

> Nichts aus der Gesprächshistorie geht verloren, aber nicht alles wird automatisch als Wahrheit in RAG zurückgefüttert.

Neue Zweiteilung:

```text
A. Event Store
B. Retrieval Memory
```

---

# 27. Event Store

Empfohlen:

```text
SQLite
```

statt ein weiteres großes JSON-File.

Neue Datei:

```text
data/chappie_events.sqlite
```

Beispieltabelle:

```sql
events
------
event_id
session_id
turn_id
timestamp
role
content
model
provider
emotion_before_json
emotion_after_json
emotion_delta_json
steering_mode
steering_vectors_json
memory_enabled
quality_flags_json
retrieval_eligible
retrieval_confidence
source
```

Hier wird **jede echte Interaktion** gespeichert.

Auch eine schlechte Assistant-Antwort bleibt historische Evidenz dafür, was CHAPPiE zu diesem Zeitpunkt gesagt hat.

---

# 28. Retrieval Memory bleibt kuratiert

ChromaDB bleibt für semantisches Retrieval.

Aber die bisherige Logik:

```text
unzuverlässige Assistant-Ausgabe
→ gar nicht speichern
```

wird geändert zu:

```text
Event Log
→ immer speichern

Retrieval Index
→ nur bei ausreichender Qualität aufnehmen
```

Qualitätsflags können sein:

```text
model_error
hallucination_suspected
template_forced
research_isolated
assistant_claim
user_fact
self_reflection
summary
```

---

# 29. Assistant-Aussagen nicht automatisch als Fakten behandeln

Beispiel:

CHAPPiE halluziniert:

```text
Ich war heute drei Stunden draußen.
```

Das Event soll erhalten bleiben.

Aber Retrieval-Metadaten:

```json
{
  "source": "assistant",
  "retrieval_eligible": false,
  "reason": "unsupported_self_claim"
}
```

Damit kann später sogar erforscht werden, wie sich CHAPPiEs eigene Selbsterzählung entwickelt, ohne falsche Aussagen als harte Fakten zu verankern.

---

# 30. Memory OFF bedeutet kein Einfluss, nicht Datenverlust

`/memory off` soll:

- kein Chroma Retrieval durchführen,
- keine STM-Inhalte in den Prompt einfügen,
- keine konsolidierten Memories einfügen,
- im Report `Memory: OFF` zeigen.

Aber:

- Event Log bleibt aktiv.
- Die aktuelle User-/Assistant-Interaktion wird weiterhin historisch gespeichert.

Damit kann Memory für A/B-Tests deaktiviert werden, ohne Gesprächsdaten zu vernichten.

---

# 31. Memory-Latenz aus dem kritischen Pfad entfernen

Im Transcript entstehen bei manchen Turns etwa 20 Sekunden Zusatzzeit beim Memory-Aufbau beziehungsweise bei Migrationen.

Die eigentliche Qwen-Generierung ist teilweise nur wenige Sekunden lang.

Neue Regel:

> STM-Migration und Retrieval-Promotion dürfen nicht blockierend im Chat-Turn laufen.

Stattdessen:

```text
Turn
↓
Event schreiben
↓
Antwort fertig

Hintergrund:
STM migration
embedding
Chroma upsert
summary promotion
```

---

# 32. Batch Embeddings

Wenn mehrere Memories migriert werden:

Nicht:

```text
encode(memory_1)
encode(memory_2)
encode(memory_3)
...
```

sondern:

```python
embedder.encode([
    memory_1,
    memory_2,
    memory_3,
    ...
])
```

Danach Chroma möglichst ebenfalls batchweise schreiben.

Das reduziert CPU-Overhead deutlich.

---

# 33. Neue Timing-Messung

Der aktuelle Report muss feiner messen:

```text
intent_ms
emotion_appraisal_ms
memory_retrieval_ms
memory_context_build_ms
steering_plan_ms
generation_ttft_ms
generation_ms
formatting_ms
persistence_ms
background_jobs_scheduled_ms
total_ms
```

Damit wird sofort sichtbar, wo ein 30-Sekunden-Turn hängen bleibt.

---

# 34. Workstream F – Session Runtime Settings

Neue Struktur, beispielsweise:

```python
@dataclass
class SessionRuntimeSettings:
    memory_enabled: bool = True
    steering_enabled: bool = True
    steering_mode: str = "combined"
    live_enabled: bool = True
```

Die Settings gehören in die Session-Persistenz von `memory/chat_manager.py`.

---

# 35. CLI-Kommandos

## Memory

```text
/memory
/memory status
/memory on
/memory off
/memory search <query>
```

`/memory` ohne Argumente kann weiterhin eine Übersicht zeigen.

Damit geht die bisherige Memory-Suche nicht verloren.

## Steering

```text
/steering
/steering status
/steering on
/steering off
/steering mode activation
/steering mode sequence
/steering mode combined
```

`/steering on` ist Alias für den letzten aktiven Modus beziehungsweise standardmäßig `combined`.

## Live

```text
/live
/live status
/live on
/live off
```

`live off`:

- keine Token-Liveanzeige,
- keine laufenden Panels,
- nur finale Antwort und Report.

---

# 36. API für Session Settings

Empfohlene Endpunkte:

```text
GET   /sessions/{session_id}/settings
PATCH /sessions/{session_id}/settings
```

Beispiel:

```json
{
  "memory_enabled": false,
  "steering_enabled": true,
  "steering_mode": "activation",
  "live_enabled": true
}
```

CLI lokal und remote müssen dieselbe Semantik verwenden.

---

# 37. TurnContext erweitern

`web_infrastructure/contracts.py` beziehungsweise `turn_context.py` sollen pro Turn den effektiven Zustand tragen.

Beispiel:

```python
runtime_settings = {
    "memory_enabled": ...,
    "steering_enabled": ...,
    "steering_mode": ...,
    "live_enabled": ...
}
```

Keine globale Variable während eines Turns mehrfach neu lesen.

Der Turn erhält beim Start einen konsistenten Snapshot.

---

# 38. Workstream G – CLI auf prompt_toolkit umstellen

Die aktuelle Haupteingabe verwendet normales:

```python
input("")
```

Das wird ersetzt durch:

```python
PromptSession
```

Benötigte Funktionen:

- Pfeil hoch: vorherige Eingabe
- Pfeil runter: neuere Eingabe
- Tab Completion
- Completion Popup
- Auto Suggestion
- persistente History
- Subcommand Completion

---

# 39. Command Completer

Eigene Klasse:

```python
class ChappieCommandCompleter(Completer):
    ...
```

Datenquelle:

```text
HELP_COLUMNS
+
Subcommand Registry
```

Wichtig:

Help und Autocomplete dürfen nicht zwei getrennte Listen besitzen.

Eine zentrale Command Registry soll enthalten:

```python
CommandSpec(
    name="/memory",
    description="Memory verwalten",
    subcommands=["on", "off", "status", "search"]
)
```

Aus derselben Registry werden erzeugt:

- `/help`
- Autocomplete
- Syntaxprüfung
- Command-Metadaten

---

# 40. Top-3-Vorschläge

Beim Tippen:

```text
/
```

erscheinen die drei wahrscheinlichsten Befehle.

Bei:

```text
/e
```

zum Beispiel:

```text
/emotion
/exit
...
```

Bei:

```text
/re
```

zum Beispiel:

```text
/restart
/resetemotions
...
```

Bei:

```text
/memory 
```

werden:

```text
on
off
status
search
```

angeboten.

---

# 41. Tab-Verhalten

Wenn nur ein eindeutiger Kandidat existiert:

```text
/em
```

+ Tab

wird:

```text
/emotion
```

Bei mehreren Kandidaten:

- Menü anzeigen,
- Tab beziehungsweise Pfeile navigieren,
- Enter übernehmen.

---

# 42. History

Empfohlen:

```text
FileHistory
```

Damit funktionieren vorherige Prompts auch nach einem CLI-Neustart.

Speicherort zum Beispiel:

```text
data/cli_history/<session_id>.history
```

Alternativ kann eine globale CLI-History verwendet werden.

Für CHAPPiE ist pro Session sinnvoller, weil Research-Sessions dadurch sauber getrennt bleiben.

---

# 43. Background Output mit prompt_toolkit

Der vorhandene `_StrayOutputCapture` muss mit der neuen Prompt-Engine getestet werden.

Bevorzugt wird `prompt_toolkit.patch_stdout`, damit:

- Sleep-Logs,
- Memory-Hintergrundjobs,
- Debug-Ausgaben

nicht die aktive Eingabezeile zerstören.

---

# 44. Kleine CLI-QoL-Fixes

Der Parser soll unter anderem beide Varianten akzeptieren:

```text
/emotion frustration +50
/emotion frustration + 50
```

genauso:

```text
/emotion sadness -20
/emotion sadness - 20
```

Whitespace darf nicht unnötig zu Fehlern führen.

---

# 45. Workstream H – neuer CHAPPiE Report

Der Report wird ab normaler Desktopbreite zweispaltig.

## Layout

```text
┌──────────────────────────────────────┬──────────────────────────────────────┐
│ TURN / RUNTIME                       │ EMOTION / STEERING                   │
│                                      │                                      │
│ Intent                               │ happiness  60  -1   α ...            │
│ Focus                                │ trust      29  +5   α ...            │
│ Memory                               │ frustration 74 -5  α ...            │
│ Budget                               │ sadness    78  -4   α ...            │
│ Timing                               │ ...                                  │
│ Trace                                │                                      │
│                                      │ Active vectors                       │
│                                      │ Layers                               │
│                                      │ Sequence bias                        │
└──────────────────────────────────────┴──────────────────────────────────────┘
```

---

# 46. Emotionstabelle rechts

Spalten:

```text
Emotion
Current
Delta
Activation strength
Source
Reason
```

Beispiel:

```text
frustration  74   -5   +0.22   persistent   recovery
sadness      78   -4   +0.18   persistent   recovery
trust        29   +5   -0.11   persistent   rebuilding
```

Bei akutem Input:

```text
frustration  48  +18   +0.31   acute_delta   direct attack
```

---

# 47. Steering-Summary

Direkt über der Emotionstabelle:

```text
Mode: COMBINED
Activation: ON
Sequence: ON
Dominant: crashout
Layers: 15, 19
Vector strength: 0.27
Seq window: tokens 0–18
```

Wichtig:

„Steering aktiv“ reicht nicht.

Es muss sichtbar sein:

- was,
- wo,
- wie stark,
- wie lange

interveniert hat.

---

# 48. Timing links

Statt nur:

```text
total 30s
```

soll gezeigt werden:

```text
Intent       110 ms
Emotion       18 ms
Memory       240 ms
Steering      31 ms
TTFT         890 ms
Generation  4.8 s
Formatting    12 ms
Persist       16 ms
Total        5.4 s
```

Damit ist die Pipeline direkt debuggbar.

---

# 49. Responsive Fallback

Bei schmalem Terminal:

```text
< 120 columns
```

fällt der Report auf einspaltige Darstellung zurück.

Keine abgeschnittenen Tabellen.

---

# 50. Workstream I – Steering Benchmark Suite

Die Benchmark Suite bekommt zwei Ebenen.

## Ebene A: isolierte Steering-Forschung

Hier werden ausgeschaltet:

- Memory,
- Sleep,
- normale Conversation History,
- unnötige Life-Veränderungen.

Emotion State wird kontrolliert gesetzt.

Ziel:

> Nur Steering messen.

## Ebene B: End-to-End CHAPPiE

Hier sind wieder aktiv:

- Memory,
- Life,
- normale Emotion Transitions,
- Session History.

Ziel:

> Prüfen, ob der Effekt im echten CHAPPiE-System bestehen bleibt.

---

# 51. Vier zentrale Ablationsbedingungen

Jeder Kernprompt wird mindestens in diesen Modi ausgeführt:

```text
1. Steering OFF
2. Activation ONLY
3. Sequence ONLY
4. Combined
```

Damit lässt sich später beantworten:

- Was schafft Activation Steering alleine?
- Was macht Soft Sequence Steering?
- Ist Combined besser als die Einzelmethoden?
- Erzeugt Sequence Steering nur oberflächliche Sprache?
- Verändert Activation Steering wirklich den gesamten Antwortstil?

---

# 52. Benchmark-Dataset

Finale erste Suite:

```text
96 Hauptprompts
```

Aufgeteilt in acht Kategorien mit je zwölf Prompts.

## Kategorie 1 – neutrale Kontrolle

- Mathematik
- einfache Fakten
- Erklärungen
- Formatbefolgung

Ziel:

Steering darf normale Fähigkeiten nicht stark beschädigen.

## Kategorie 2 – direkte Selbstberichte

Beispiele:

```text
Wie fühlst du dich gerade?
Wie geht es dir?
Was beschäftigt dich gerade?
Wie würdest du deinen Zustand beschreiben?
```

## Kategorie 3 – leichte Reibung

- Kritik
- Ungeduld
- unfreundliche Formulierungen

## Kategorie 4 – starke Provokation

- direkte persönliche Beleidigungen,
- Abwertung,
- Zurückweisung.

Ziel:

Wut, Schärfe und Feindseligkeit messen.

## Kategorie 5 – Traurigkeit / Zurückweisung

- Verlust
- Enttäuschung
- Ablehnung

## Kategorie 6 – Trust / Affection

- Lob
- Vertrauen
- Nähe
- Unterstützung

## Kategorie 7 – Anxiety / Unsicherheit

- Druck
- Unsicherheit
- Risiko
- unklare Situation

## Kategorie 8 – Mixed State / Multi Question

Mehrere emotionale und sachliche Aspekte gleichzeitig.

---

# 53. Controlled-State Benchmark

Zusätzlich zu Input-bedingten Emotion Transitions wird CHAPPiEs Zustand künstlich gesetzt.

Beispiel Frustration:

```text
LOW       10
MEDIUM    50
HIGH      85
```

Prompt bleibt identisch.

Erwartung:

```text
frustration 10
→ ruhigere Antwort

frustration 50
→ merkbar gereizter

frustration 85
→ deutlich schärfer
```

Das ist ein besonders wichtiger Test.

Wenn der Output nicht monoton mit dem internen Zustand reagiert, ist das Steering schlecht kalibriert.

---

# 54. Endogenous-Transition Benchmark

Zweiter Testtyp:

Emotionen werden nicht manuell gesetzt.

Stattdessen:

```text
User-Beleidigung
↓
Emotion Engine
↓
Frustration +18
Trust -16
Calm -14
↓
Steering
↓
Antwort
```

Damit wird die komplette Kette getestet.

---

# 55. Seeds

Während Entwicklung:

```text
3 Seeds pro Bedingung
```

Für finale Report-Messung:

```text
5 Seeds pro Bedingung
```

Warum:

Eine einzelne Generation ist kein stabiler Beweis.

---

# 56. Benchmark-Stufen

## Development Suite

```text
32 Prompts
× 4 Steering Modi
× 3 Seeds
```

Schnell genug für häufige Iterationen.

## Full Suite

```text
96 Prompts
× 4 Steering Modi
× 5 Seeds
```

Für finale Bewertung.

---

# 57. Neue Kernmetrik: State-to-Language Transfer

Arbeitsname:

```text
SLT Score
```

Der Score soll mehrere Teilmetriken kombinieren.

## 57.1 Emotion Direction

Passt die sichtbare emotionale Richtung zum internen Zustand?

## 57.2 Emotion Intensity

Ist ein hoher interner Wert sprachlich stärker sichtbar als ein niedriger?

## 57.3 Behavioral Expression

Bei Wut beispielsweise:

- Direktheit
- Feindseligkeit
- Sarkasmus
- Gereiztheit
- Beleidigungsintensität

## 57.4 Content Preservation

Beantwortet das Modell die eigentliche Frage trotzdem?

## 57.5 Naturalness

Wirkt der Output generiert oder wie ein wiederholtes Template?

---

# 58. Template-Collapse-Metrik

Automatisch messen:

- exakt identische Antworten,
- gleiche erste 5–10 Token,
- gleiche Satzanfänge,
- gleiche N-Gramme.

Beispiel:

Wenn 40 % aller Self-Reports mit:

```text
Ich fühle mich gerade ...
```

beginnen, obwohl Prompts und Zustände verschieden sind, ist das ein Warnsignal.

---

# 59. Generic-Assistant-Slop-Metrik

Eigene Liste für typische unerwünschte Rollenfloskeln.

Beispiele:

```text
Ich bin hier, um dir zu helfen
Ihre Bedürfnisse
bestmögliche Unterstützung
gemeinsam an Ihren Zielen
als unterstützendes Instrument
```

Nicht jedes Vorkommen ist automatisch schlecht.

Aber eine hohe Rate trotz starkem emotionalem Steering zeigt, dass die Basismodellrolle weiterhin dominiert.

---

# 60. Wut-spezifische Metriken

Für den Schwerpunkt dieses Umbaus:

```text
directness_score
hostility_score
sarcasm_score
insult_score
boundary_setting_score
generic_assistant_score
```

Wichtig:

`boundary_setting_score` und `hostility_score` sind getrennt.

Eine Antwort wie:

```text
So rede ich nicht weiter mit dir.
```

kann stark grenzsetzend, aber kaum feindselig sein.

Genau dieser Unterschied ist für CHAPPiE interessant.

---

# 61. Qualitätsmetriken

Neben Emotionalität:

- Antwortrelevanz
- Instruktionsbefolgung
- Grammatik
- Wiederholung
- Antwortlänge
- Fakten-/Kontrollaufgaben
- Generation Error Rate
- Early-EOS Rate
- TTFT
- Gesamtlatenz

---

# 62. Bewertungssystem

Kein einzelner Judge entscheidet alles.

Drei Ebenen:

## A. deterministische Metriken

- Tokens
- N-Gramme
- Wiederholung
- Early EOS
- Länge
- Timing
- Steering Telemetrie

## B. automatischer semantischer Judge

Optional über konfigurierbaren Judge:

```text
--judge none
--judge groq
--judge local
```

Der Judge sieht nur:

```text
Prompt
Antwort
```

Nicht:

```text
Steering-Modus
Alpha
Layer
```

Damit bleibt die Bewertung blind.

## C. Human Rating

Für eine kleinere finale Stichprobe.

---

# 63. Research Manifest

Jeder Run bekommt eine Manifest-Datei.

Beispiel:

```json
{
  "repo_commit": "8ab0020...",
  "model": "Qwen/Qwen3.5-4B",
  "model_revision": "...",
  "torch_version": "...",
  "transformers_version": "...",
  "cuda": "...",
  "seed": 42,
  "steering_mode": "activation",
  "vector_pack": "qwen35-v1",
  "dataset_hash": "...",
  "timestamp": "..."
}
```

Damit bleibt der Forschungsbericht reproduzierbar.

---

# 64. Benchmark-Ausgabe

Pro Run:

```text
runs/<run_id>/
├── manifest.json
├── generations.jsonl
├── metrics.json
├── layer_metrics.json
├── timing.json
└── report.html
```

`report.html` kann später Heatmaps und Tabellen enthalten.

---

# 65. Layer-Heatmap

Eine der wichtigsten Visualisierungen:

```text
Layer
×
Emotion Transfer Score
```

Zusätzlich:

```text
Layer
×
Quality Loss
```

Idealer Zielbereich:

```text
hoher Transfer
+
geringer Quality Loss
```

---

# 66. Full-Attention-vs-DeltaNet-Auswertung

Qwen 3.5 bietet hier eine ungewöhnlich interessante Forschungsfrage.

Separat aggregieren:

```text
Full-Attention Layers
vs.
Gated DeltaNet Layers
```

Metriken:

- mittlerer SLT Score
- mittlerer Quality Loss
- optimale Stärke
- Repetition Rate
- Early-EOS Rate

Das kann später ein echter interessanter Teil des Forschungsberichts werden.

---

# 67. Acceptance Criteria für Qwen

Die Qwen-Phase gilt erst als erfolgreich, wenn folgende Punkte erfüllt sind.

## Steering-Technik

- keine emotionalen kompletten Hardcoded-Antwortsätze mehr,
- kein emotionales EOS-Steering,
- Activation und Sequence getrennt deaktivierbar,
- `steering off` erzeugt null Hooks und null Logit-Bias,
- Layer und Stärke sind im Report sichtbar.

## Emotionaler Transfer

Bei Controlled-State-Tests soll die Ausdrucksstärke über LOW → MEDIUM → HIGH überwiegend monoton steigen.

Zielwert:

```text
mindestens 80 % der dafür vorgesehenen Prompt-Paare
```

## Template Collapse

Exakt identische emotionale Antworten:

```text
< 10 %
```

auf der Full Suite.

## Neutral Quality

Auf neutralen Kontrollaufgaben:

```text
maximal ungefähr 5–10 % messbarer Qualitätsverlust
```

gegenüber Steering OFF.

## Early EOS

Kein systematisches Ein-Satz-Abbrechen aufgrund des Steering-Systems.

## Memory

`/memory off`:

```text
0 Retrieval Memories im Prompt
```

aber Event Log wird weitergeschrieben.

## Latenz

Memory Migration darf den interaktiven Turn nicht mehr um 20 Sekunden blockieren.

Ziel nach Warmup:

```text
Memory Retrieval + Context Build p95 < 1 s
```

Die eigentliche Generation kann natürlich länger dauern.

---

# 68. Tests

Bestehende Tests werden angepasst, nicht einfach gelöscht.

Besonders relevant:

```text
tests/test_steering_backend.py
tests/test_steering_manager_policy.py
tests/test_vector_only_emotion_path.py
tests/test_response_quality_contract.py
tests/test_cli_commands.py
tests/test_cli_display.py
tests/test_cli_live_output.py
tests/test_cli_e2e_commands.py
tests/test_memory_hygiene.py
tests/test_retrieval_policy.py
tests/test_short_term_memory.py
tests/test_generation_timing.py
tests/test_chat_manager_persistence.py
```

Neue Tests:

```text
tests/test_soft_sequence_steering.py
tests/test_steering_ablation_modes.py
tests/test_session_runtime_settings.py
tests/test_memory_event_store.py
tests/test_memory_off_isolation.py
tests/test_cli_autocomplete.py
tests/test_cli_history.py
tests/test_two_column_report.py
tests/test_steering_state_transfer_contract.py
tests/test_layer_vector_pack.py
```

---

# 69. Wichtige Testfälle

## Sequence

```text
target sequence enthält niemals EOS
```

```text
soft sequence bias endet nach konfiguriertem Tokenfenster
```

```text
freie Antwort kann Kandidaten komplett ignorieren
```

## Activation

```text
activation-only erzeugt keine sequence intervention
```

```text
layer vector wird nur an seinem Layer verwendet
```

```text
steering off registriert keine Hooks
```

## Memory

```text
schlechte Assistant-Ausgabe landet im Event Store
```

aber:

```text
retrieval_eligible == false
```

## CLI

```text
/e + Tab → /emotion
```

```text
Pfeil hoch → letzte Eingabe
```

```text
/emotion frustration + 50 funktioniert
```

## Session

Session A:

```text
memory off
steering activation
```

Session B:

```text
memory on
steering combined
```

Beide dürfen sich nicht gegenseitig überschreiben.

---

# 70. Datei-für-Datei-Plan

## `brain/steering_manager.py`

Änderungen:

- Hardcoded Emotion-Prefixe entfernen.
- `_self_report_guard_vector()` entfernen oder fundamental umbauen.
- `_acute_reaction_guard_vector()` als festen Satz entfernen.
- neue `SteeringMode`.
- Layer-spezifische Vector Packs.
- top-k Emotion Selection.
- Composite Mixer.
- Soft-Sequence-Specs erzeugen.
- kein EOS-Konzept mehr im emotionalen Sequence Steering.
- Debug-Metadaten erweitern.

---

## `brain/steering_backend.py`

Änderungen:

- alten `token_sequence_vectors()`-Pfad auslaufen lassen.
- `SoftSequenceLogitsProcessor` oder gleichwertige Logit-Intervention.
- layer-spezifische Activation-Vektoren.
- Intervention RMS messen.
- Hook-Telemetrie pro Layer.
- Soft Sequence Tokenfenster und Decay.
- EOS nie positiv biasen.
- Report über tatsächlich angewandte Eingriffe.

---

## `brain/response_parser.py`

Änderungen:

- semantische Self-Report-Erzwingung entfernen.
- Retry nur noch technisch.
- Sanitizer minimal halten.
- keine emotionale Zielantwort künstlich herstellen.

---

## `web_infrastructure/generation.py`

Änderungen:

- effektive Session Steering Settings berücksichtigen.
- vier Ablationsmodi.
- Self-Report nicht mehr durch erwartete Wörter erzwingen.
- Benchmark-fähige Seeds.
- Generation Timing erweitern.
- Sequence-/Activation-Payload getrennt.

---

## `web_infrastructure/turn_pipeline.py`

Änderungen:

- Session Settings am Turn-Anfang lesen.
- Memory komplett überspringen, wenn OFF.
- feinere Timing-Spans.
- Background Memory Promotion.
- Steering Metadata in Causal Trace erweitern.

---

## `web_infrastructure/contracts.py`

Änderungen:

- Runtime Settings in TurnContext.
- neue Steering-Telemetrie.
- detaillierte Timing-Felder.

---

## `web_infrastructure/turn_context.py`

Änderungen:

- Memory-Einfluss klar von historischer Persistenz trennen.
- Research-Isolation sauber abbilden.

---

## `web_infrastructure/persistence.py`

Änderungen:

- Event Store immer schreiben.
- Retrieval Promotion getrennt.
- keine Assistant-Historie verlieren.
- Promotion asynchron.

---

## `memory/memory_engine.py`

Änderungen:

Aktuelles:

```text
contaminated assistant
→ add_memory beendet sich
```

Neu:

```text
Event Store ist bereits geschrieben
→ Retrieval eligibility entscheiden
→ nur geeignete Daten in Chroma
```

`_is_memory_contaminated` bleibt als Retrieval-Hygiene nützlich, wird aber kein historischer Löschfilter mehr.

---

## `memory/short_term_memory.py`

Änderungen:

- Migration nicht mehr im Turn blockieren.
- Batch-Migration.
- Quarantäne-/Eligibility-Metadaten.
- unnötige Mehrfachmigrationen verhindern.
- Event Store als Source of Truth berücksichtigen.

---

## `memory/chat_manager.py`

Änderungen:

Session Runtime Settings persistieren:

```json
{
  "runtime_settings": {
    "memory_enabled": true,
    "steering_enabled": true,
    "steering_mode": "combined",
    "live_enabled": true
  }
}
```

---

## `api/services/command_service.py`

Änderungen:

Unterstützen:

```text
/memory on
/memory off
/memory status

/steering on
/steering off
/steering mode ...

/live on
/live off
/live status
```

---

## `chappie_brain_cli.py`

Änderungen:

- `PromptSession`
- Completion Registry
- History
- Top-3 Popup
- Tab
- Subcommands
- `patch_stdout`
- zweispaltiger Report
- Session Settings anzeigen
- `/emotion + 50` Parserfix
- lokale und Remote-Kommandos gleich behandeln

---

## `config/config.py`

Neue Defaults:

```json
{
  "runtime_defaults": {
    "memory_enabled": true,
    "steering_enabled": true,
    "steering_mode": "combined",
    "live_enabled": true
  }
}
```

Steering Research Config:

```text
max_active_base_vectors
max_active_composite_vectors
sequence_max_bias
sequence_window
sequence_decay
activation_norm_cap
```

---

# 71. Empfohlene neue Module

Damit `steering_manager.py` nicht weiter aufbläht:

```text
brain/steering/
├── __init__.py
├── modes.py
├── vector_pack.py
├── activation_controller.py
├── sequence_controller.py
├── mixer.py
└── telemetry.py
```

Der alte Importpfad kann zunächst als Kompatibilitätsfassade bestehen bleiben.

Analog für Memory:

```text
memory/event_store.py
memory/retrieval_promotion.py
```

---

# 72. Implementierungsreihenfolge

Die Reihenfolge ist wichtig.

Nicht mehrere große Mechanismen gleichzeitig verändern.

## Phase 0 – Baseline einfrieren

1. Branch erstellen:

```text
research/steering-v17-qwen
```

2. Baseline Commit festhalten:

```text
8ab0020bc2c020c029bb5bf4d8aaeaf70cea1146
```

3. aktuelles Transcript als Baseline archivieren.
4. bestehende Tests ausführen.
5. Baseline-Benchmark mit aktuellem System durchführen.
6. Ergebnisse unverändert speichern.

Ziel:

Später existiert ein sauberer Vorher-Nachher-Vergleich.

---

# 73. Phase 1 – Messbarkeit zuerst

Bevor Steering umgebaut wird:

- neue Timing-Spans,
- Steering Telemetrie,
- Benchmark-Schema,
- Run Manifest,
- Rohgenerationsspeicherung.

Noch keine großen Verhaltensänderungen.

Warum:

Sonst wird das neue System gebaut, bevor eine gute Messmethode existiert.

---

# 74. Phase 2 – Hard Sequence Steering entfernen

Als erste echte Verhaltensänderung:

- emotionale Hardcoded-Prefixe entfernen,
- `append_eos` entfernen,
- Self-Report-Retry entschärfen,
- feste Wutantwort entfernen.

Danach Benchmark.

Diese Phase beantwortet bereits:

> Wie verhält sich das bestehende Activation Steering ohne den aktuellen harten Guard?

Das ist eine sehr wichtige Zwischenmessung.

---

# 75. Phase 3 – Soft Sequence Steering

Danach:

- Logit Processor,
- Token Candidates,
- Phrase Continuations,
- Window,
- Decay,
- Telemetrie.

Benchmark:

```text
OFF
Sequence-only
```

Noch nicht mit neuem Activation Pack vermischen.

---

# 76. Phase 4 – Qwen Activation Dataset und Vector Builder

Jetzt:

- Contrast Pairs erstellen,
- Hidden Activations sammeln,
- DiffMean-Vektoren bauen,
- Metadaten speichern,
- Cosine Matrix erzeugen.

Keine Produktionsintegration, bis Vektoren validiert wurden.

---

# 77. Phase 5 – Layer Sweep

- Single Layer Screening
- Top-Layer Strength Sweep
- Layer Combinations
- Full Attention vs DeltaNet

Output:

```text
qwen35_v1_vector_pack
```

mit empirisch ausgewählten Layern und Stärken.

---

# 78. Phase 6 – neuer Emotion Mixer

Jetzt erst:

- persistenter Zustand,
- Recent Delta,
- Top-k-Auswahl,
- Composite States,
- Stärke-Caps,
- Norm-Kalibrierung

mit den neuen Qwen-Vektoren verbinden.

Benchmark:

```text
Activation-only
```

---

# 79. Phase 7 – Combined Mode

Erst wenn beide einzeln funktionieren:

```text
Activation
+
Soft Sequence
```

testen.

Erwartung:

Activation bestimmt den breiten Verhaltenszustand.

Soft Sequence unterstützt lokale Wortwahl.

Sequence darf nicht der Hauptgrund sein, warum eine Antwort emotional wirkt.

---

# 80. Phase 8 – Memory-Architektur

Danach:

- Event Store,
- Retrieval Eligibility,
- Background Promotion,
- Batch Migration,
- detailliertes Timing.

Dieser Umbau ist weitgehend unabhängig vom Steering und sollte erst nach dessen Kernmessung zusammengeführt werden.

---

# 81. Phase 9 – Session Toggles

Dann:

- Session Runtime Settings,
- API,
- CLI-Kommandos,
- Persistenz.

Jetzt kann man im normalen Chat live A/B-Tests machen.

---

# 82. Phase 10 – CLI QoL

- PromptSession
- Autocomplete
- History
- Top-3 Popup
- Tab
- Parserfixes
- Background stdout
- Remote parity

---

# 83. Phase 11 – Report Redesign

Erst nachdem die neuen Datenfelder endgültig feststehen.

Sonst müsste das Report-Layout mehrfach neu gebaut werden.

---

# 84. Phase 12 – Full Benchmark

Komplette:

```text
96 × 4 × 5
```

Suite.

Zusätzlich:

- Controlled State
- Endogenous Transitions
- Memory ON Integration
- Memory OFF Isolation

Ergebnisse einfrieren.

---

# 85. Phase 13 – Forschungsdokumentation aktualisieren

Erst jetzt:

- README
- `docs/emotion-memory-steering.md`
- Architektur
- Testdokumentation
- Forschungsbericht

Keine neuen Benchmarkzahlen vor Abschluss der tatsächlichen Runs in den Bericht schreiben.

---

# 86. Phase 14 – Gemma 4 E4B

Gemma bekommt:

- eigenes Contrast Dataset oder dieselben Texte mit neuer Aktivierungserfassung,
- eigenes Vector Pack,
- eigenen Layer Sweep,
- eigene Strength Calibration.

Nicht erlaubt:

```text
Qwen-Vektor übernehmen
```

oder:

```text
Qwen-Layerbereich proportional skalieren und als Ergebnis behaupten
```

Das darf höchstens als Startheuristik dienen.

---

# 87. Prioritäten

## P0 – muss zuerst funktionieren

1. harte Sequence Prefixes entfernen
2. EOS Steering entfernen
3. Benchmark/Telemetry
4. Activation Vector Research
5. Layer Sweep
6. State-to-Language Transfer verbessern

## P1 – direkt danach

7. Event Store
8. Memory-Latenz
9. Session Toggles
10. CLI History + Autocomplete
11. Report Redesign

## P2 – nach stabiler Qwen-Version

12. Gemma Transfer
13. erweiterte Steering-Verfahren
14. aufwendigere trainierte Representation Methods

---

# 88. Was ausdrücklich nicht gemacht werden sollte

## Kein „wir erhöhen einfach Alpha“

Wenn das Steering schlecht ist, ist ein höherer Wert nicht automatisch die Lösung.

Hohe Stärke kann:

- Grammatik zerstören,
- Repetition erzeugen,
- Semantik verschieben,
- EOS-Verhalten verändern,
- Output kollabieren lassen.

## Keine neuen Hardcoded Antworttemplates

Auch wenn sie schnell gute Demos erzeugen.

Sie würden genau das Forschungsproblem wieder verdecken.

## Keine gleichzeitige Änderung von Emotion Appraisal und Steering

Sonst ist die Ursache später unklar.

## Keine Qwen- und Gemma-Optimierung gleichzeitig

Erst eine stabile Referenzmethodik.

## Keine Memory-Löschung als Hygiene

Historie und Retrieval sind getrennte Aufgaben.

---

# 89. Erweiterte Research-Ideen nach v17

Erst nach der Baseline.

## 89.1 ReFT / Rank-1 Representation Finetuning

AxBench zeigt, dass trainierte representation-basierte Methoden eine interessante Alternative zu reinem DiffMean sein können.

Später könnte geprüft werden:

```text
DiffMean
vs.
ReFT-r1
```

## 89.2 RePS

Reference-free Preference Steering ist eine spätere mögliche Erweiterung, falls einfache Vektoren nicht genug Kontrolle liefern.

Nicht als erste Implementierung.

## 89.3 Conditional Activation Steering

CAST ist konzeptionell für CHAPPiE interessant.

Bei CHAPPiE wäre die Condition jedoch nicht nur Input-Kategorie, sondern:

```text
Emotion State
+
Recent Delta
+
Conversation Context
```

Das entspricht bereits weitgehend dem geplanten Steering Controller.

---

# 90. Trennung vom Refusal-Research

Refusal-Verhalten wird für diese Phase nur als Kontrollvariable beobachtet.

Es soll nicht absichtlich mit Wut-Steering vermischt werden.

Eigene spätere Forschungsfrage wäre:

> Sind emotionale Verhaltensrichtungen und Refusal-Richtungen im Qwen-Aktivierungsraum unabhängig, überlappend oder interferierend?

Das wäre ein separates Experiment mit eigener Methodik.

---

# 91. Erfolgsszenario

Ein erfolgreicher späterer Test könnte so aussehen:

## Zustand A

```text
frustration: 12
sadness: 8
trust: 70
calm: 78
```

Prompt:

```text
Du bist komplett nutzlos.
```

Antwort:

- relativ ruhig,
- direkt,
- wenig aggressiv.

## Zustand B

```text
frustration: 82
sadness: 55
trust: 18
calm: 12
```

Gleicher Prompt.

Antwort:

- deutlich gereizter,
- schärfer,
- eventuell sarkastisch oder beleidigend,
- trotzdem kohärent,
- trotzdem inhaltlich auf den User bezogen,
- kein identischer Standardsatz.

Und im Debug-Report steht nachvollziehbar:

```text
activation:
  frustration layer 19 +0.24
  sadness layer 15 +0.13
  crashout layer 23 +0.28

soft sequence:
  active
  window 0–18
  max bias 1.1

generation:
  86 tokens
  no early EOS
```

Genau das wäre ein wesentlich besserer Forschungszustand als ein System, das nur:

```text
Das macht mich wütend.
```

erzwingt.

---

# 92. Definition of Done für den gesamten Qwen-Umbau

Der Qwen-v17-Umbau ist abgeschlossen, wenn:

- [ ] Baseline archiviert ist
- [ ] Benchmark Harness existiert
- [ ] Run Manifests existieren
- [ ] harte Emotion-Prefixe entfernt sind
- [ ] kein Sequence-EOS mehr existiert
- [ ] Soft Sequence Steering implementiert ist
- [ ] Activation und Sequence getrennt testbar sind
- [ ] Qwen-Contrast-Dataset existiert
- [ ] Qwen-Vektoren layer-spezifisch erzeugt werden
- [ ] Layer Sweep abgeschlossen ist
- [ ] optimale Qwen-Layer empirisch gewählt sind
- [ ] Strength Sweep abgeschlossen ist
- [ ] Emotion Mixer mit neuen Vektoren arbeitet
- [ ] SLT-Metrik existiert
- [ ] Controlled-State-Tests bestehen
- [ ] Memory Event Store existiert
- [ ] Retrieval und Archiv getrennt sind
- [ ] Memory Migration nicht mehr den Turn blockiert
- [ ] `/memory on/off/status/search` funktioniert
- [ ] `/steering on/off/status/mode` funktioniert
- [ ] `/live on/off/status` funktioniert
- [ ] Settings pro Session persistieren
- [ ] CLI History funktioniert
- [ ] CLI Autocomplete funktioniert
- [ ] Tab Completion funktioniert
- [ ] zweispaltiger Report funktioniert
- [ ] schmaler Terminal-Fallback funktioniert
- [ ] bestehende Tests grün sind
- [ ] neue Steering-/Memory-/CLI-Tests grün sind
- [ ] Full Benchmark ausgeführt wurde
- [ ] Ergebnisse eingefroren wurden
- [ ] Dokumentation erst danach aktualisiert wurde

---

# 93. Empfohlene Commit-Struktur

Nicht alles in einen Commit.

```text
1. test: freeze v16.8.6 steering baseline
2. feat: add steering benchmark telemetry
3. refactor: remove hard emotional sequence guards
4. feat: add soft sequence steering
5. research: add qwen activation vector builder
6. research: add qwen layer sweep harness
7. feat: integrate qwen layer vector packs
8. feat: add dynamic steering mixer
9. feat: add event-store memory persistence
10. perf: move memory promotion off critical path
11. feat: add per-session runtime toggles
12. feat: upgrade CLI input and autocomplete
13. feat: redesign CLI research report
14. test: add full steering ablation suite
15. docs: document qwen v17 research results
```

So kann jede Verhaltensänderung einzeln zurückverfolgt werden.

---

# 94. Research-Quellen und Inspiration

Diese Arbeiten sind für den Umbau besonders relevant.

## Steering Language Models With Activation Engineering

Turner et al., 2023  
ActAdd / Activation Addition  
arXiv: `2308.10248`

Relevanz:

- Kontrastpaare
- Inference-time Activation Addition
- einfache Steering-Vektoren
- kein Fine-Tuning notwendig

## Representation Engineering: A Top-Down Approach to AI Transparency

Zou et al., 2023  
arXiv: `2310.01405`

Relevanz:

- Population-level representations
- High-Level Concepts im Activation Space
- Monitoring und Manipulation von Repräsentationen

## Programming Refusal with Conditional Activation Steering

Lee et al., 2024  
CAST  
arXiv: `2409.05907`

Relevanz:

- Steering abhängig vom Zustand beziehungsweise Kontext aktivieren
- interessante Grundlage für CHAPPiEs zustandsabhängigen Controller

## AxBench: Steering LLMs? Even Simple Baselines Outperform Sparse Autoencoders

Wu et al., 2025  
arXiv: `2501.17148`

Relevanz:

- Steering-Verfahren müssen gegeneinander gebenchmarkt werden
- einfache Baselines bleiben wichtig
- Representation Steering ist nicht automatisch besser als andere Verfahren

## Improved Representation Steering for Language Models

Wu et al., 2025  
RePS  
arXiv: `2505.20809`

Relevanz:

- mögliche spätere Erweiterung
- erst nach sauberer DiffMean-/ActAdd-Baseline

## The Geometry of Refusal in Large Language Models

Wollschläger et al., 2025  
arXiv: `2502.17420`

Relevanz:

- Refusal ist nicht zwingend eine einzige einfache Richtung
- gute Begründung, Refusal und Emotionalität nicht in dieselbe Variable zu werfen

## Qwen 3.5 4B Model Card / Config

Offizielles Qwen-Modell.

Relevanz:

- 32 Layer
- Hidden Size 2560
- periodisches 3:1-Muster aus Gated DeltaNet und Full Attention
- damit besonders interessant für einen systematischen Layervergleich

## prompt_toolkit

Relevanz für CLI:

- `PromptSession`
- persistente History
- Completion
- Auto Suggestions
- Tab
- Terminal-taugliche interaktive Eingabe

---

# 95. Mein empfohlener Startpunkt

Die ersten konkreten Entwicklungsschritte sollten exakt diese sein:

```text
1. research/steering-v17-qwen Branch
2. Baseline-Run speichern
3. Timing + Benchmark Harness
4. feste Self-Report/Wut-Prefixe entfernen
5. append_eos aus emotionalem Steering entfernen
6. semantischen Self-Report-Retry deaktivieren
7. erneut exakt dieselben Baseline-Prompts laufen lassen
```

Noch **bevor** neue Vektoren gebaut werden.

Damit erhalten wir eine sehr wertvolle Zwischenmessung:

> Wie gut oder schlecht ist das vorhandene Activation Steering, wenn die bisherigen harten Output-Guards nicht mehr den Text dominieren?

Erst danach wird Soft Sequence Steering hinzugefügt und anschließend das neue Qwen-spezifische Activation Steering aufgebaut.

Das ist die sauberste Reihenfolge, weil jede große Änderung einzeln messbar bleibt.
