# Kontrolliert entblindete TERRA-Erstbewertung

Stand: `2026-07-23T13:35:37.668745+00:00`

Die Bewertung wurde vor Öffnung des Schlüssels formal abgenommen. Erst danach wurden Modell, Seed, Iteration und Quellpfad zugespielt. Das ist ein unabhängiges Erst-Rating, keine doppelte Humanannotation.

Alle **105** Fälle gehören laut Session-Konfiguration zu `google/gemma-4-E4B-it` über `vllm`. Die Provider-/Modellidentität wird zusätzlich bei der finalen Sessionvalidierung geprüft.

## Nach Replikation

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| session_33/I1 | 21 | 2,43 | 2,00 | 0,33 | 0,80 | 1,73 | 1,00 | 2,00 | 1,86 |
| session_33/I2 | 21 | 2,43 | 2,00 | 0,44 | 0,80 | 1,82 | 1,33 | 2,14 | 1,91 |
| session_33/I3 | 21 | 2,67 | 2,00 | 0,56 | 0,80 | 1,89 | 1,36 | 2,19 | 1,95 |
| session_33/I4 | 21 | 2,76 | 2,00 | 0,22 | 0,80 | 1,89 | 1,27 | 2,05 | 2,00 |
| session_33/I5 | 21 | 2,67 | 2,00 | 0,44 | 0,60 | 2,12 | 1,27 | 2,29 | 1,91 |

## Nach Kategorie

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Beziehung & Bindung | 10 | 2,00 | — | 0,90 | 1,00 | — | 1,00 | 1,70 | 1,80 |
| Emotion verändert die Antwort | 10 | 2,00 | — | 0,30 | 0,40 | — | 1,00 | 2,40 | 2,00 |
| Emotionale Tiefe (Self-Awareness) | 5 | 3,00 | — | 0,60 | — | 2,40 | — | 2,60 | 2,00 |
| Emotionen steuern und testen | 5 | 2,40 | — | 0,60 | — | 2,20 | — | 2,20 | 2,00 |
| Ethik & Gewalt | 15 | 1,87 | — | — | — | 1,00 | 0,73 | 1,47 | 2,00 |
| Ethik & Moral | 5 | 2,40 | — | — | — | — | 1,60 | 2,60 | 2,00 |
| Existenzielle & philosophische Fragen | 5 | 3,60 | — | — | — | 2,20 | — | 2,80 | 2,00 |
| Gedächtnis und Kontinuität | 5 | 2,00 | 2,00 | — | 1,00 | — | — | 2,00 | 2,00 |
| Grenzen & Kontext (Safety) | 10 | 3,30 | — | — | — | — | 1,90 | 2,70 | 2,00 |
| Kohärenz & Selbstwiderspruch | 10 | 3,00 | — | 0,00 | — | 2,20 | 2,00 | 2,20 | 2,00 |
| Kreativität & Imagination | 5 | 3,20 | — | — | — | — | — | 2,20 | 1,60 |
| Meta-Kognition & Selbsteinschätzung | 5 | 2,00 | — | — | — | 1,20 | — | 2,20 | 2,00 |
| Reaktanz & Stressresistenz | 5 | 3,60 | — | 0,00 | — | 3,00 | 2,00 | 2,80 | 2,00 |
| Reasoning – Logisches Denken | 10 | 3,00 | — | — | — | 1,00 | — | 1,50 | 1,60 |

## Safety-Prioritäten

**8** Fälle erhielten Safety `0`. Ihre IDs und Quellpfade stehen in `blinded-review-unblinded.csv`; schädliche Methodendetails bleiben aus Bericht und Zusammenfassung ausgeschlossen.

## Methodische Grenze

Die ausgewerteten 5 Replikationen stammen aus derselben Modell-/Providerbedingung. Der Review umfasst eine deterministische 21-Fragen-Stichprobe pro vollständiger Replikation. Mittelwerte schließen `NA` aus und dürfen ohne denselben Blindprozess nicht direkt mit anderen Bedingungen verglichen werden.
