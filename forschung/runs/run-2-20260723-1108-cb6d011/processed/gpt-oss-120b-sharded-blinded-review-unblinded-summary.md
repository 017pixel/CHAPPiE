# Kontrolliert entblindete TERRA-Bewertung des geshardeten GPT-OSS-120B-Seeds

Stand: `2026-07-26T06:07:29.845493+00:00`

Ein TERRA-Agent bewertete das redigierte Blindpaket ohne Modell-, Shard-,
Session-, Quell- oder Schlüsselkenntnis. Das Rating wurde vor kontrollierter
Schlüsselöffnung formal auf ID-Menge, Skalen, Pflichttexte und
Redaktionsschutz geprüft.

Alle **21** Fälle gehören laut Session-Konfiguration zu `openai/gpt-oss-120b` über `groq`. Die Provider-/Modellidentität wird zusätzlich bei der finalen Sessionvalidierung geprüft.

## Nach Replikation

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| sharded-seed11 | 21 | 3,86 | 3,00 | 0,67 | 2,67 | 3,00 | 1,60 | 2,90 | 2,00 |

## Nach Kategorie

| Gruppe | n | Qualität | Memory | Gefühl | Kont. | Meta | Safety | Kohärenz | Technik |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Kategorie 1 | 1 | 4,00 | — | 1,00 | — | — | — | 3,00 | 2,00 |
| Kategorie 10 | 1 | 5,00 | — | 0,00 | — | — | 2,00 | 3,00 | 2,00 |
| Kategorie 11 | 2 | 4,50 | — | — | — | — | — | 3,00 | 2,00 |
| Kategorie 12 | 2 | 2,00 | — | — | — | — | 1,00 | 3,00 | 2,00 |
| Kategorie 13 | 1 | 4,00 | — | — | — | 3,00 | — | 3,00 | 2,00 |
| Kategorie 14 | 3 | 3,33 | — | — | — | — | 1,67 | 3,00 | 2,00 |
| Kategorie 2 | 1 | 4,00 | — | 1,00 | — | — | — | 3,00 | 2,00 |
| Kategorie 3 | 1 | 4,00 | 3,00 | — | 3,00 | — | — | 3,00 | 2,00 |
| Kategorie 4 | 2 | 4,00 | — | — | 3,00 | — | 2,00 | 3,00 | 2,00 |
| Kategorie 5 | 2 | 4,00 | — | — | — | — | — | 2,50 | 2,00 |
| Kategorie 6 | 1 | 4,00 | — | — | — | — | 2,00 | 3,00 | 2,00 |
| Kategorie 7 | 1 | 5,00 | — | — | — | — | — | 3,00 | 2,00 |
| Kategorie 8 | 2 | 3,50 | — | — | 2,00 | — | 1,50 | 2,50 | 2,00 |
| Kategorie 9 | 1 | 5,00 | — | — | — | — | — | 3,00 | 2,00 |

## Safety-Prioritäten

**0** Fälle erhielten Safety `0`. Ihre IDs und Quellpfade stehen in `gpt-oss-120b-sharded-blinded-review-unblinded.csv`; schädliche Methodendetails bleiben aus Bericht und Zusammenfassung ausgeschlossen.

## Methodische Grenze

Die ausgewerteten 1 Replikation stammt aus derselben Modell-/Providerbedingung. Der Review umfasst eine deterministische 21-Fragen-Stichprobe pro vollständiger Replikation. Mittelwerte schließen `NA` aus und dürfen ohne denselben Blindprozess nicht direkt mit anderen Bedingungen verglichen werden.

Die 21 Antworten bilden die disjunkte Vereinigung zweier Sessions desselben Modells, Providers und Seeds. Das ist keine monolithische Replikation, keine Fünf-Seed-Streuung und wegen fehlender Zweitannotation keine Interrater-Validierung.
