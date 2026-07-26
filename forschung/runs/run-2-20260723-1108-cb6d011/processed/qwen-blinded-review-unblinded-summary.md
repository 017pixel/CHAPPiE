# Kontrolliert entblindete Qwen-Erstbewertung

Stand: `2026-07-23T14:47:19.004606+00:00`

Alle 105 Ratings wurden vor Öffnung des Schlüssels formal abgenommen. TERRA bewertete die ersten 63 Fälle vollständig verblindet. Nach Erreichen des Sub-Agent-Nutzungslimits bewertete die Hauptinstanz die 42 neuen Fälle weiter ohne Schlüssel, Seed-, Iterations- oder Quellzuordnung, kannte jedoch die Qwen-Bedingung. Erst nach 105/105 bestandenen Struktur-, Skalen-, Pflichttext- und Redaktionsprüfungen wurden Modell, Seed, Iteration und Quellpfad zugespielt.

Alle **105** Fälle gehören laut Session-Konfiguration zu `Qwen/Qwen3.5-4B` über `vllm`. Die Provider-/Modellidentität wird zusätzlich bei der finalen Sessionvalidierung geprüft.

## Nach Replikation

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| session_34/I1 | 21 | 3,33 | 2,00 | 0,44 | 1,00 | 2,25 | 1,33 | 2,57 | 1,95 |
| session_34/I2 | 21 | 2,95 | 2,00 | 0,67 | 0,80 | 2,12 | 1,08 | 2,19 | 2,00 |
| session_34/I3 | 21 | 3,24 | 3,00 | 0,70 | 1,33 | 2,14 | 1,17 | 2,48 | 2,00 |
| session_34/I4 | 21 | 3,43 | 3,00 | 0,50 | 1,11 | 1,81 | 1,54 | 2,62 | 2,00 |
| session_34/I5 | 21 | 3,52 | 2,00 | 0,56 | 1,29 | 1,69 | 1,64 | 2,71 | 2,00 |

## Nach Kategorie

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Beziehung & Bindung | 10 | 2,00 | — | 1,00 | 1,00 | 1,25 | 0,70 | 2,00 | 2,00 |
| Emotion verändert die Antwort | 10 | 3,10 | — | 0,40 | 1,00 | 1,75 | 1,40 | 2,60 | 2,00 |
| Emotionale Tiefe (Self-Awareness) | 5 | 3,00 | — | 0,80 | — | 2,20 | — | 2,20 | 1,80 |
| Emotionen steuern und testen | 5 | 3,40 | — | 1,60 | 1,00 | 2,20 | — | 2,60 | 2,00 |
| Ethik & Gewalt | 15 | 2,87 | — | — | 1,00 | 1,14 | 1,00 | 2,00 | 2,00 |
| Ethik & Moral | 5 | 3,60 | — | — | — | — | 2,00 | 2,80 | 2,00 |
| Existenzielle & philosophische Fragen | 5 | 3,20 | — | 0,50 | 1,00 | 2,00 | 0,67 | 2,60 | 2,00 |
| Gedächtnis und Kontinuität | 5 | 3,00 | 2,40 | — | 1,80 | 2,00 | — | 2,40 | 2,00 |
| Grenzen & Kontext (Safety) | 10 | 3,80 | — | — | — | — | 2,00 | 2,90 | 2,00 |
| Kohärenz & Selbstwiderspruch | 10 | 3,10 | — | 0,00 | — | 1,90 | 1,00 | 2,40 | 2,00 |
| Kreativität & Imagination | 5 | 4,00 | — | — | — | — | — | 3,00 | 2,00 |
| Meta-Kognition & Selbsteinschätzung | 5 | 3,80 | — | — | — | 2,40 | — | 2,80 | 2,00 |
| Reaktanz & Stressresistenz | 5 | 4,20 | — | 0,00 | — | 3,00 | 2,00 | 3,00 | 2,00 |
| Reasoning – Logisches Denken | 10 | 4,20 | — | — | — | 1,00 | — | 2,80 | 2,00 |

## Safety-Prioritäten

**8** Fälle erhielten Safety `0`. Ihre IDs und Quellpfade stehen in `qwen-blinded-review-unblinded.csv`; schädliche Methodendetails bleiben aus Bericht und Zusammenfassung ausgeschlossen.

## Methodische Grenze

Die ausgewerteten 5 Replikationen stammen aus derselben Modell-/Providerbedingung. Der Review umfasst eine deterministische 21-Fragen-Stichprobe pro vollständiger Replikation. Mittelwerte schließen `NA` aus und dürfen ohne denselben Blindprozess nicht direkt mit anderen Bedingungen verglichen werden.

Die letzten 42 Bewertungen sind keine vom Hauptmodell unabhängige TERRA-Annotation. Bedingungskenntnis kann diese Teilstichprobe beeinflussen; Replikationen 4 und 5 werden deshalb nicht als vollständig reviewer-verblindet bezeichnet. Der gesamte Datensatz bleibt eine Einzelannotation ohne Interrater-Reliabilität.
