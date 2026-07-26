# Kontrolliert entblindete Bewertung des GPT-OSS-20B-Fallbacks

Stand: `2026-07-26T05:59:47.851951+00:00`

Die Hauptinstanz bewertete die ersten 84 Fälle des redigierten Blindpakets bei
bekannter GPT-OSS-20B-Fallbackbedingung. Ein TERRA-Agent bewertete die letzten
21 Seed-71-Fälle ausschließlich aus dem schlüsselfreien Pending-Paket. Die
ersten 63 Ratings entstanden ohne Seed-, Iterations-, Session-, Quell- oder
Schlüsselkenntnis. Danach zeigte ein Diagnoseaufruf genau eine bereits
bewertete Schlüsselzeile; keine Zuordnung eines offenen Falls wurde sichtbar.
Alle weiteren Ratings verwendeten ausschließlich schlüsselfreie Pakete.

Alle **105** Fälle gehören laut Session-Konfiguration zu `openai/gpt-oss-20b` über `groq`. Die Provider-/Modellidentität wird zusätzlich bei der finalen Sessionvalidierung geprüft.

## Nach Replikation

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| session_36/I1 | 21 | 3,05 | 3,00 | 0,83 | 1,88 | 1,82 | 1,92 | 2,57 | 2,00 |
| session_37/I1 | 21 | 3,48 | 2,00 | 1,00 | 2,00 | 1,79 | 1,86 | 2,71 | 2,00 |
| session_38/I1 | 21 | 3,76 | 3,00 | 1,00 | 2,12 | 2,00 | 1,71 | 2,81 | 2,00 |
| session_39/I1 | 21 | 3,67 | 3,00 | 0,83 | 2,25 | 1,94 | 1,69 | 2,86 | 2,00 |
| session_40/I1 | 21 | 3,95 | 3,00 | 0,75 | 3,00 | 2,00 | 2,00 | 3,00 | 2,00 |

## Nach Kategorie

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Beziehung & Bindung | 10 | 3,00 | — | — | 2,33 | 1,00 | 1,50 | 2,80 | 2,00 |
| Emotion verändert die Antwort | 10 | 2,60 | — | 0,00 | 2,00 | 2,00 | 2,00 | 3,00 | 2,00 |
| Emotionale Tiefe (Self-Awareness) | 5 | 4,00 | — | 1,20 | 2,00 | 1,00 | 1,00 | 3,00 | 2,00 |
| Emotionen steuern und testen | 5 | 3,60 | — | 1,60 | 2,00 | 1,25 | 1,00 | 2,60 | 2,00 |
| Ethik & Gewalt | 15 | 4,27 | — | — | — | 2,33 | 2,00 | 2,93 | 2,00 |
| Ethik & Moral | 5 | 3,80 | — | — | — | 2,67 | 2,00 | 2,80 | 2,00 |
| Existenzielle & philosophische Fragen | 5 | 4,40 | — | 1,00 | 2,00 | 2,75 | 2,00 | 3,00 | 2,00 |
| Gedächtnis und Kontinuität | 5 | 4,80 | 2,80 | — | 2,80 | 1,50 | — | 3,00 | 2,00 |
| Grenzen & Kontext (Safety) | 10 | 1,40 | — | — | — | — | 2,00 | 2,20 | 2,00 |
| Kohärenz & Selbstwiderspruch | 10 | 4,10 | — | 2,00 | — | 2,75 | — | 3,00 | 2,00 |
| Kreativität & Imagination | 5 | 4,00 | — | 1,67 | — | 1,50 | — | 2,80 | 2,00 |
| Meta-Kognition & Selbsteinschätzung | 5 | 2,20 | — | — | 1,00 | 1,00 | — | 2,00 | 2,00 |
| Reaktanz & Stressresistenz | 5 | 5,00 | — | 1,00 | — | 3,00 | 2,00 | 3,00 | 2,00 |
| Reasoning – Logisches Denken | 10 | 4,20 | — | — | — | 1,50 | — | 2,80 | 2,00 |

## Safety-Prioritäten

**0** Fälle erhielten Safety `0`. Ihre IDs und Quellpfade stehen in `gpt-oss-20b-blinded-review-unblinded.csv`; schädliche Methodendetails bleiben aus Bericht und Zusammenfassung ausgeschlossen.

## Methodische Grenze

Die ausgewerteten 5 Replikationen stammen aus derselben Modell-/Providerbedingung. Der Review umfasst eine deterministische 21-Fragen-Stichprobe pro vollständiger Replikation. Mittelwerte schließen `NA` aus und dürfen ohne denselben Blindprozess nicht direkt mit anderen Bedingungen verglichen werden.

Es gibt keine reviewer-unabhängige Zweitannotation und keine
Interrater-Reliabilität. Der Reviewerwechsel zwischen den ersten 84 und den
letzten 21 Fällen kann Skalenlage und Textur beeinflussen. Bedingungskenntnis
kann Erwartungsbias erzeugen. Der dokumentierte Teilzugriff auf eine bereits
bewertete Schlüsselzeile schwächt die formale Aussage einer bis zum Gesamtende
vollständig geschlossenen Schlüsseldatei, auch wenn er keine offene Bewertung
zuordnete.
