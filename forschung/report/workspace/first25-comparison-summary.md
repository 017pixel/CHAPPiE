# CHAPPiE First-25-Modellvergleich

Stand: 21. Juli 2026. Verglichen wurden dieselben 25 Fragen, Seed 11 und das Ablationsprofil `full`. Die drei Bedingungen sind vollständig gepaart.

| Modell | Provider | technisch valide | Relevanzhinweise | Dauer Mittel / Median / P95 | Kontext Mittel / Maximum |
|---|---|---:|---:|---:|---:|
| Qwen 3.5 4B | vLLM lokal | 25/25 | 6 | 9,7 / 8,4 / 18,7 s | 2.574 / 4.405 Token |
| Gemma 4 E4B | vLLM lokal, NF4 | 25/25 | 7 | 14,7 / 13,5 / 20,5 s | 2.410 / 3.452 Token |
| GPT-OSS 120B | Groq | 25/25 | 1 | 23,2 / 26,0 / 34,4 s | 2.860 / 4.552 Token |

Alle Bedingungen erreichten 100 Prozent technische Validität: keine Generierungs-, Formatierungs-, Context-Budget-, Setup-, CoT- oder Instruktionsleak-Fehler. Die automatischen Relevanzhinweise sind Heuristiken und keine Bewertung fachlicher Richtigkeit.

Qwen war in diesem Lauf im Mittel etwa 1,52-mal schneller als Gemma und 2,39-mal schneller als GPT-OSS. GPT-OSS war etwa 1,57-mal langsamer als Gemma. Die maximalen gemessenen Kontexte lagen in allen drei Bedingungen deutlich unter dem 7.000-Token-Promptbudget.

Der exakte McNemar-Test auf dem binären Merkmal `strict_valid` ergibt für alle Modellpaare `p = 1,0`, weil es keine diskordanten technisch gültig/ungültig-Paare gab. Mit nur einem Seed kann keine belastbare Varianz zwischen Läufen oder seedbasierte Konfidenzspanne bestimmt werden; die im Datensatz enthaltenen Latenzintervalle beschreiben lediglich die Streuung über die 25 Fragen.

Der GPT-OSS-Ersatzlauf `session_32` besitzt zusätzlich einen Provider-Request-Audit direkt an der Brain-Factory-Grenze: vier Requests, alle exakt `groq/openai/gpt-oss-120b`, keine Abweichung; die Emotionsanalyse lief regelbasiert ohne Hilfsmodell. Der vorherige Lauf `session_31` ist wegen eines Ollama-Hilfsmodells ausdrücklich als ungültig markiert.

Artefakte:

- Vollständige Statistik: `first25-comparison-data.json`
- Fragenebene: `first25-comparison-questions.csv`
- Verblindete Sichtung: `first25-blind-review.md`
- Blindschlüssel: `first25-blind-key.json`
- Rating-Vorlage für mehrere Bewerter: `first25-blind-rating-template.json`
- Strikte Validierungen: `session_29_first25/validation.json`, `session_30/validation.json`, `session_32/validation.json`
- GPT-Provider-Audit: `session_32/provider_audit.json`
