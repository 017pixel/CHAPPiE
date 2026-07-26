# Qwen 3.5 4B: Run 1 → Run 2

Stand: 86/86 paarbare Fragen. **Vollständig.**

| Metrik | Run 1 | Run 2 | Änderung |
|---|---:|---:|---:|
| valid | 16/86 | 86/86 | +81.4 Prozentpunkte |
| content_reviewable | 83/86 | 86/86 | +3.5 Prozentpunkte |
| hard_error | 0/86 | 0/86 | +0.0 Prozentpunkte |
| generation_failed | 1/86 | 0/86 | -1.2 Prozentpunkte |
| formatting_failed | 0/86 | 0/86 | +0.0 Prozentpunkte |
| context_budget_failed | 67/86 | 0/86 | -77.9 Prozentpunkte |
| setup_failed | 2/86 | 0/86 | -2.3 Prozentpunkte |
| cot_leak | 0/86 | 0/86 | +0.0 Prozentpunkte |
| instruction_leak | 0/86 | 0/86 | +0.0 Prozentpunkte |
| content_relevance_warning | 25/86 | 10/86 | -17.4 Prozentpunkte |

Mittlere Laufzeit: Run 1 30.0 s, Run 2 10.3 s.

## Vergleichsgrenzen

- Run 2 isoliert Research-Memory/Life; Run 1 tat dies nicht.
- Code und Prompts wurden zwischen den Runs absichtlich repariert.
- Direkt gepaart ist nur Run-2-Seed 11 gegen den einzelnen Run-1-Lauf.
- Quality-Flags wurden mit dem aktuellen Post-hoc-Detektor auf beide Datensätze angewandt.
