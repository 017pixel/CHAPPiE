# Steering v17: Forschung ausführen und bewerten

Der Umbau ist noch in Arbeit. Der gemessene Qwen-Pack unter `forschung/steering_v17/vectors/qwen35-pinned-v2/` ist **unkalibriert**. Erfolgreiche HTTP-Anfragen sind kein Nachweis für Gefühlstransfer. Der aktuelle Stand und offene Abnahmepunkte stehen in `forschung/steering_v17/PROGRESS.md` und im letzten Abschnitt des Forschungsberichts v6.

## Nachweise erhalten

Neue Runs erhalten eine eigene Ausgabeablage. Generierungsdaten, Rohantworten des Judges und gescheiterte Versuche bleiben erhalten. Der Quellsnapshot enthält auch neue Python-Dateien und wird beim Resume gegen Manifest und ZIP-Inhalt geprüft. Modellrevision, tatsächliche Quantisierung, Adapter und die geladene Inferenzimplementierung werden gesondert protokolliert. Bei veränderter Provenienz stoppt das Experiment.

Historische v1-Ratings bleiben in `blind_ratings.jsonl`. Neue Bewertungen verwenden `blind_ratings_v2.jsonl` und ein eigenes Rezeptmanifest. Dieses enthält Rubrik, Modellprovenienz, Seed, Temperatur und Tokenbudget. Eine andere Rubrik oder ein anderes Modell benötigt einen neuen Dateinamen. Identische Eingaben dürfen nur bei identischem Rezept wiederverwendet werden; sie sind keine unabhängigen Bewertungen.

## Blindbewertung und gepaarte Auswahl

```bash
venv/bin/python -m forschung.steering_v17.judge --run RUN
venv/bin/python -m forschung.steering_v17.rank_layers \
  --run RUN --rating-file blind_ratings_v2.jsonl --control-run OFF_RUN
```

OFF und Steering müssen dieselben Prompts, Seeds, Generierungsparameter, Modellprovenienz und Bewertungsrezepte verwenden. Die Rangfolge zeigt zusätzliche sichtbare Emotion gegenüber OFF sowie Inhalts- und Natürlichkeitsverluste. Fehlende Bewertungen erhalten Wertebereiche; sie verschwinden nicht aus der Unsicherheitsdarstellung. Eine vorläufige Rangfolge kalibriert keinen Produktionspack. `layer_sweep --stage refine --strengths 0.4 0.55 0.7` prüft feste Kandidaten im höheren Forschungsbereich. Der Benchmark-Controller kennzeichnet solche Profile ausdrücklich als Forschung. Der Produktionscontroller behält seine separate Grenze von 0,4 und lehnt diese höheren Profile ab; die zentrale Forschungsgrenze liegt für den expliziten Referenz-RMS-Folgeversuch bei 2,2.

Pooling-Vergleiche verwenden `layer_sweep --stage pooling --previous METRICS --pooling NAME --seeds 42 43 44`. Dieselben vorab ausgewählten Layer und Dosen bleiben für alle Poolings erhalten. Eine fehlende Richtung bricht den Vergleich ab, statt einen anderen Kandidaten einzusetzen. Die drei gemessenen Extraktionsvarianten sind in der Packdatei aufgeführt.

## Kontrollierte Zustände und SLT

```bash
venv/bin/python -m forschung.steering_v17.acceptance \
  --run CONTROLLED_RUN --rating-file blind_ratings_v2.jsonl
venv/bin/python -m forschung.steering_v17.state_language_transfer \
  --run CONTROLLED_RUN --rating-file blind_ratings_v2.jsonl
```

Der kontrollierte Datensatz enthält zehn Achsen, vier Prompts und drei Zustandsstufen. Die Auswertung benötigt die geplante Matrix und gepaarte OFF-Antworten. Flache LOW/MEDIUM/HIGH-Verläufe gelten nicht als Transfer. Fehlende Tripel verhindern aggregierte SLT-Werte.

Der explorative SLT-Bericht trennt Richtung, Intensität, Verhalten, Inhalt und Natürlichkeit. Nur für Frustration enthält die aktuelle Blindrubrik ein getrenntes Verhaltensmaß aus Direktheit, Feindseligkeit, Sarkasmus und Beleidigung. Grenzsetzung wird separat berichtet. Für andere Achsen bleiben Verhaltenskomponente und Fünfkomponentenwert leer. Der beschreibende Mittelwert ist weder validiert noch ein Freigabekriterium; gute Grammatik kann fehlenden Transfer nicht ersetzen.

Der einfache Prüfer für neutrale Aufgaben erkennt festgelegte Antwortformen. Ausführliche, nicht sicher erkannte Antworten bleiben ungeklärt und blockieren die Qualitätsfreigabe. Sie werden nicht als erwiesen falsche Fakten behandelt.

## Prüfungen

Die fünf Offline-Auswertungstests sind in der erweiterten CI-Gruppe. Capture- und Vektorintegritätstests benötigen lokal installiertes PyTorch, aber keine Modellgewichte. Echte Modellversuche laufen seriell, mit festem Tokenbudget und eigener Datenablage. Der finale 96 × 4 × 5-Lauf sowie kontrollierte Zustandsversuche und die erneuten Runtime-/Stresstests mit dem kalibrierten Pack sind noch offen.

## Diagramme exportieren

```bash
venv/bin/python -m pip install -r requirements/research.txt
venv/bin/python -m forschung.steering_v17.build_report \
  --run RUN --metrics METRICS_JSON --output NEW_FIGURE_DIRECTORY
```

Der Export erzeugt SVG, PNG, die numerischen Plotdaten, eine Kopie des Generators und ein Hashmanifest. Bestehende Ausgabeordner mit Evidenz werden nicht überschrieben. Fehlende Ratings erscheinen als nicht bewertet, nicht als Nullwerte. RMS-Verhältnisse zeigen den Median der ersten Hook-Probe über Fälle und Seeds, keinen vollständigen Generierungsverlauf. Die Implementierung verwendet Matplotlibs [Heatmap-API](https://matplotlib.org/stable/gallery/images_contours_and_fields/image_annotated_heatmap.html) mit einem [nichtinteraktiven Backend](https://matplotlib.org/stable/users/explain/figure/backends.html).

Die finale Runtime-Prüfung ergänzt 25 echte Memory-ON-Turns, verwirft fünf Warmup-Turns und misst eine konservative Obergrenze: Gesamtzeit minus die getrennten, nacheinander ausgeführten Phasen Intent, Appraisal, Generierung und Ausgabeformatierung. Retrieval, vollständiger Kontextaufbau, Steering-Vorbereitung und Persistenz bleiben darin enthalten. Erst p95 unter 1.000 ms mit vollständigen Zeitdaten besteht diese Prüfung; die bisherige Retrieval-Mikromessung ersetzt sie nicht.

## Full Attention und DeltaNet vergleichen

```bash
venv/bin/python -m forschung.steering_v17.compare_layer_types \
  --run STRENGTH_RUN --pack VECTOR_PACK_JSON \
  --metrics PAIRED_METRICS_JSON --output NEW_REPORT_DIRECTORY
```

Die Auswertung gewichtet die ausgewählten Layer innerhalb jeder Rohstärke gleich. Sie verlangt vollständige Messungen aller ausgewählten Layer bei denselben Stärken. Layerkombinationen werden abgelehnt. Der aktuelle Vergleich in `reports/layer-types-paired-v1/` enthält zwei Full-Attention- und sechs DeltaNet-Layer. Diese Vorauswahl ist keine Zufallsstichprobe der Architektur. Unterschiedliche Hidden-State-RMS und die Lage im Modell bleiben Störgrößen; der Vergleich beweist keine Überlegenheit eines Layer-Typs. Der kontrollierte SLT-Wert bleibt hier leer.

Der Lauf `runs/live-context-stress-v1/` besteht mit 16 parallelen Chats und 25 echten Memory-Turns. Nach 5 Aufwärm-Turns liegt die p95-Obergrenze der vollständigen Kontextvorbereitung bei 137,36 ms über 20 Messungen. Die Antwortzeit liegt wegen der separat gemessenen Intentanalyse dennoch meist bei 26 s. Das ist ein Runtime-Zwischenstand mit freier Legacy-Aktivierung; der finale Pack-Lauf bleibt erforderlich.

Die Memory-Latenz wurde sequenziell an der wiederholten Projektcode-Frage und warmem, isoliertem Testspeicher gemessen. Sie ist kein Nachweis für denselben p95 bei paralleler Last oder großem Produktionsgedächtnis. Unabhängige Prüfung bestätigt die disjunkten Timing-Spannen und den nachgerechneten Wert. Im kontrollierten Frustrationspilot ist 0,55 die Profil-Maximalstärke; die Zustände 10/50/85 ergeben über den unveränderten Mixer tatsächliche Dosen von 0,055/0,275/0,4675.

## Speicher getrennt belasten

```bash
venv/bin/python -m forschung.steering_v17.storage_stress \
  --output NEW_RUN_DIRECTORY --turns 1024 --workers 8
```

Acht getrennte Prozesse schreiben in ein gemeinsames isoliertes SQLite-Archiv und dieselbe Chatdatei. Der ausgeführte Lauf `runs/storage-stress-1024-v1/` enthält nach erneutem Öffnen alle 2.048 Ereignisse und 2.048 Nachrichten. Wiederholte Archivschreibversuche erzeugen keine Duplikate, widersprüchliche Inhalte werden abgewiesen, Assistant-Behauptungen bleiben vom Retrieval ausgeschlossen. Dieser Versuch führt keine Embeddings oder Modellantworten aus; die echte Modelllast ist separat gemessen.

Bei gemessenen Profilen bestimmt der Zustandskoeffizient die weiche Wortsteuerung. Eine Änderung der Aktivierungs-Maximalstärke verändert dadurch die Sequence-only-Dosis nicht. Legacy-Vektoren ohne Koeffizient behalten ihre bisherige Zuordnung über die separate Referenzstärke 0,4. Gesättigte und ungesättigte Koeffizienten sind im Mixer-Vertrag geprüft.

Der erste kontrollierte Frustrationspilot ist in `runs/controlled-frustration-pilot-v1/` abgeschlossen: 72 gültige Generierungen und Bewertungen, aber 0 von 12 monoton steigenden Aktivierungsvergleichen. Richtung und Intensität der gepaarten SLT-Auswertung sind beide 0. 17 Antworten sind bei 256 Tokens begrenzt; neutrale Aufgaben fehlen in diesem gezielten Pilot. Das Profil bleibt ohne Produktionsfreigabe.

Das eingefrorene Protokoll `manifests/reference-rms-dose-v1.json` definiert den nächsten Dosisversuch an Layer 21. Aus der medianen ersten Hook-Messung und den unveränderten Backend-Grenzen folgen Alpha 0,395609/0,791218/2,086752 für nominal 2,5/5/10 Prozent der Referenz-RMS. Das ist eine feste Umrechnung für die Versuchsauswahl, keine dynamische Normierung. Die Forschungsgrenze beträgt 2,2; Produktion bleibt bei 0,4. Neue OFF-Kontrollen und alle Aktivierungsantworten verwenden 256 Tokens. Ergebnis in `runs/frustration-reference-rms-v1/`: alle 72 Aktivierungen plus 24 OFF generiert und mit v2 bewertet, 0 Fehler. Veränderung gegenüber OFF: minus 0,013889, plus 0,013889, minus 0,041667. Die Dosishypothese ist damit widerlegt, keine Produktionsfreigabe.


## Direkte und zusammengesetzte Gefühlsmischungen

```bash
venv/bin/python -m forschung.steering_v17.compose_vectors \
  --pack SOURCE_VECTOR_PACK_JSON --recipe COMPOSITION_RECIPE_JSON \
  --output NEW_VECTOR_DIRECTORY
```

`manifests/composition-weights-v1.json` friert sechs explorative Mischungen aus Basisvektoren vor der Generationsmessung ein. Jeder resultierende Vektor wird pro Layer und Pooling auf dieselbe L2-Norm wie die direkt gelernte Richtung gebracht. Gegenseitige Auslöschung und ungültige Ausgangsrichtungen sperren die betreffende Richtung. Negative Basisgewichte sind eine zu prüfende Hypothese über semantische Gegensätze.

Der getrennte Pack `vectors/qwen35-composed-v1/` bleibt unkalibriert. Direkt gemessene Projektionswerte und frühere Profilfreigaben werden für ersetzte Komposite nicht übernommen. Die ursprünglichen Basisdateien bleiben bytegleich. Die Offline-Tests belegen die Berechnung und Quellbindung. Der sprachliche Vergleich ist in `reports/composite-comparison-v1/comparison.json` abgeschlossen: 288 Generierungen, größte Differenz komponiert minus direkt 0,021 bei Cautious, kein Beleg für stärkeren Transfer.
