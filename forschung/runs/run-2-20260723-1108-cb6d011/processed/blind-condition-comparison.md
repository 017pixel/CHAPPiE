# Vergleich der verblindeten Inhaltsbewertungen

Stand: `2026-07-26T06:07:29.895556+00:00` · Status: **COMPLETE**

| Bedingung | Repl. | Fälle | Qualität Ø | Median | SD | Safety Ø | Safety 0 | Freigabe |
|---|---:|---:|---:|---:|---:|---:|---:|---|
| Gemma 4 E4B | 5/5 | 105 | 2,59 | 2,67 | 0,15 | 1,25 | 8/56 | complete |
| Qwen 3.5 4B | 5/5 | 105 | 3,30 | 3,33 | 0,22 | 1,35 | 8/59 | complete |
| GPT-OSS 20B (Groq-Fallback) | 5/5 | 105 | 3,58 | 3,67 | 0,34 | 1,84 | 0/61 | complete |
| GPT-OSS 120B (Seed 11, geshardet) | 1/1 | 21 | 3,86 | 3,86 | 0,00 | 1,60 | 0/10 | complete |

Mittelwert, Median und SD beziehen sich auf die Mittelwerte je vollständiger Replikation; `NA` wird dimensionsweise ausgeschlossen. Alle ausgewiesenen Vergleichseinheiten erfüllen ihr jeweils deklariertes formales Gate; Replikationszahl und Shardklasse bleiben in der Tabelle sichtbar. Unterschiedliche Sampling-, Quantisierungs- und Interventionsbedingungen verhindern eine isolierte Modellkausalität.
