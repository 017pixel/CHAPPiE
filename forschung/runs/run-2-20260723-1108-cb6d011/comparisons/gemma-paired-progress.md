# Gemma Run 1 → Run 2, gepaarter Arbeitsvergleich

Stand: 86/86 paarbare Fragen. **Vollständig validiert.**

| Metrik | Run 1 | Run 2 | Änderung |
|---|---:|---:|---:|
| valid | 0/86 | 86/86 | +100.0 Prozentpunkte |
| content_reviewable | 32/86 | 86/86 | +62.8 Prozentpunkte |
| hard_error | 0/86 | 0/86 | +0.0 Prozentpunkte |
| generation_failed | 0/86 | 0/86 | +0.0 Prozentpunkte |
| formatting_failed | 0/86 | 0/86 | +0.0 Prozentpunkte |
| context_budget_failed | 82/86 | 0/86 | -95.3 Prozentpunkte |
| setup_failed | 3/86 | 0/86 | -3.5 Prozentpunkte |
| cot_leak | 3/86 | 0/86 | -3.5 Prozentpunkte |
| instruction_leak | 51/86 | 0/86 | -59.3 Prozentpunkte |
| content_relevance_warning | 39/86 | 27/86 | -14.0 Prozentpunkte |

Mittlere Laufzeit: Run 1 81.5 s, Run 2 16.1 s.

## Vergleichsgrenzen

- Run 2 isoliert Research-Memory/Life; Run 1 tat dies nicht.
- Code und Prompts wurden zwischen den Runs absichtlich repariert.
- Direkt gepaart ist nur Run-2-Seed 11 gegen den einzelnen Run-1-Lauf.
- Quality-Flags wurden auf beide Datensätze mit dem aktuellen Post-hoc-Detektor angewandt.
