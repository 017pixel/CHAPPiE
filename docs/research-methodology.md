# Forschungs- und Benchmarkmethodik

## Geltungsbereich

CHAPPiEs Forschungsharness misst beobachtbares Antwortverhalten, Latenz, Retrieval, Software-Emotionen, Life-State und Steering-Metadaten. Diese Messwerte koennen Persona-, Memory- und Steering-Effekte beschreiben. Sie koennen weder subjektives Erleben noch Bewusstsein oder echte Gefuehle nachweisen.

## Reproduzierbarer Modellvergleich

Der Standardlauf umfasst 86 Fragen aus 14 Kategorien und fuenf vorab festgelegte Seeds: `11`, `23`, `37`, `53`, `71`. Die Konfigurationen liegen unter `forschung/report/workspace/`:

- `initial_run.config.json`: Qwen 3.5 4B lokal ueber vLLM
- `gemma_run.config.json`: Gemma 4 E4B lokal ueber vLLM und NF4
- `gpt_oss_run.config.json`: GPT-OSS 120B ueber Groq

Startbeispiel:

```bash
cd forschung
../venv/bin/python allignement_tests.py --auto --config report/workspace/initial_run.config.json
```

Lokale Modelle werden nie parallel geladen. Vor einem Vergleich wird der Modellwechsel ueber die Steering-Restart-API abgeschlossen und der gemeldete Modellname geprueft. Cloud- und lokale Bedingungen verwenden dieselben Fragen, Seeds, Samplingwerte und Ablationsflags. GPT-OSS unterstuetzt bei Groq kein vollstaendig deaktiviertes Reasoning; `thinking=false` wird deshalb transparent als `reasoning_effort=low`, `include_reasoning=false` und mindestens 1.024 gemeinsame Completion-Tokens dokumentiert. Diese Providergrenze verhindert eine vollstaendig tokenidentische Bedingung.

## Datenisolation

Jeder Lauf erhaelt einen neuen Namespace unter dem Research-Datenpfad und eine eigene Chroma-Collection `benchmark_memory`. Produktiv-Memory, historische Sessions und normale Kontextdateien werden nicht eingebunden. Vor jedem Seed werden Chroma, Kurzzeitgedaechtnis, Life-State und Emotionen geleert beziehungsweise auf Defaults gesetzt. Sleep und persistente Tool-Mutationen sind im Research-Modus deaktiviert.

Die Intent-Klassifikation ist im Research-Modus deterministisch und lokal. Dadurch misst jede Bedingung genau einen generativen Modellaufruf pro Antwort; ein zusaetzlicher modellabhaengiger Intent-JSON-Aufruf kann weder Latenz noch Antwortkontext verzerren. Persona, Memory, Emotionen und Life werden danach weiterhin gemaess dem ausgewaehlten Ablationsprofil in die eigentliche Antwortgenerierung eingebunden.

Setup- und Zielantworten werden vor der Uebernahme in die History validiert. Bei Setup-, Generierungs-, Kontextbudget-, Instruktionsleck- oder Qualitaetsfehlern wird die Antwort verworfen und der isolierte Zustand erneut komplett zurueckgesetzt. Dadurch kann ein ungueltiger Turn keine spaetere Stichprobe kontaminieren.

## Tokenbudget und technische Validitaet

Budgetpruefungen verwenden den tatsaechlichen Tokenizer des aktiven Modells: Hugging-Face-Tokenizer fuer Qwen und Gemma sowie Harmony-Encoding fuer GPT-OSS. Prompt und Ausgabe werden getrennt als echte Tokenfolgen gezaehlt. Es gibt keinen Zeichen-pro-Token-Fallback. Der Harness kennzeichnet Backendfehler, Setupfehler, Budgetverletzungen, CoT-/Reasoning-Lecks, Instruktionslecks und Memory-Fehler getrennt.

## Ablationen

`forschung/session_runner.py` definiert die vollstaendige 2x2x2x2-Faktormatrix fuer Persona, Memory, Emotionen und Life. Damit stehen 16 Profile zur Verfuegung: neutrale Kontrolle, vier Einzelfaktoren, alle Paar- und Dreifachkombinationen sowie die Vollbedingung. Ein Profil wird in der Run-Konfiguration ueber `ablation_profile` gesetzt, beispielsweise:

```json
{
  "ablation_profile": "emotions_only",
  "iterations": 5,
  "seeds": [11, 23, 37, 53, 71]
}
```

Einzeleffekte werden nur zwischen Runs mit identischem Modell, Fragenumfang, Seeds und Sampling verglichen. Aussagen wie „Emotion verursacht X“ sind ohne passende neutrale und faktoriell benachbarte Kontrollbedingung unzulaessig.

## Statistik

`forschung/report/build_benchmark_data.py` aggregiert ausschliesslich explizit angegebene Session-IDs. Berichtet werden Stichprobengroesse, Mittelwert, Median, Stichprobenvarianz, Standardabweichung und 95-Prozent-Konfidenzintervalle ueber Seed-Aggregate. Gepaarte binaere Qualitaetsunterschiede werden mit dem exakten zweiseitigen McNemar-Test ausgewertet. Effektgroessen, Rohzahlen und fehlende Werte bleiben sichtbar; ein p-Wert ersetzt keine inhaltliche Bewertung.

Beispiel:

```bash
venv/bin/python forschung/report/build_benchmark_data.py session_X session_Y session_Z
```

## Verblindete Bewertung

`build_paired_review.py` erzeugt zufaellig codierte Antwortpaare und einen getrennten Blindschluessel. Mindestens zwei unabhaengige Personen fuellen getrennte Ratingdateien aus. `aggregate_blind_ratings.py` akzeptiert weniger als zwei Ratings nicht und berechnet Mittelwert, Varianz, Standardabweichung sowie exakte paarweise Uebereinstimmung. Der Blindschluessel darf erst nach Abschluss aller Ratings geoeffnet werden.

```bash
venv/bin/python forschung/report/build_paired_review.py session_X session_Y
venv/bin/python forschung/report/aggregate_blind_ratings.py \
  --blind-key forschung/report/workspace/blindschluessel.json \
  rating-person-a.json rating-person-b.json
```

Die eigentlichen Ratings und eine Humanstudie koennen nicht automatisiert durch CHAPPiE selbst ersetzt werden. Fuer eine Humanstudie sind vorab ein Studienprotokoll, Einwilligung, Datenschutz- und Abbruchregeln, eine Rekrutierungsstrategie sowie gegebenenfalls Ethikfreigabe erforderlich. Sinnvolle vorab festgelegte Endpunkte sind Vertrauen, wahrgenommene Natuerlichkeit, Bindung, emotionale Abhaengigkeit und problematische Nutzung. Bis solche Daten vorliegen, werden hierzu keine Wirksamkeitsbehauptungen gemacht.

## Audit

Sessionlogs bleiben unveraendert; Analyseartefakte werden daraus neu erzeugt. Modell, Provider, Quantisierung, Featureflags, Seed, Tokenzahlen und Fehlerflags werden pro Run protokolliert. Der HTML-Bericht und die Methodiktests werden mit folgenden Befehlen validiert:

```bash
venv/bin/python tests/test_forschung_harness.py
venv/bin/python tests/test_research_quality.py
venv/bin/python tests/test_forschung_report.py
venv/bin/python forschung/report/validate_report.py forschung/report/CHAPPiE-Forschungsbericht.html
```
