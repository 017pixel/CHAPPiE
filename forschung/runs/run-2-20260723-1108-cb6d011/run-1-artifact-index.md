# Run-1-Artefaktindex

Stand: 2026-07-23. Dieser Index trennt autoritative Benchmarks, ergänzende Nachläufe, ausgeschlossene Versuche und historische Illustrationen.

## 1. Autoritative historische Vollruns

| Artefakt | Bedingung | Umfang | Verwendung in Run 2 | Einschränkung |
|---|---|---:|---|---|
| `forschung/session_logs/session_14/` | Qwen 3.5 4B, lokal, Layer Editing | 86 Fragen | Primäre Run-1-Fehlerbasis | nur eine Replikation; persistenter Startzustand |
| `forschung/session_logs/session_15/` | Gemma 4 E4B, lokal, Layer Editing | 86 Fragen | Primäre Run-1-Fehlerbasis | nur eine Replikation; NF4; anderer Startzustand |
| `forschung/report/workspace/run-metadata.json` | beide lokalen Bedingungen | Metadaten | Modellrevision, Sampling, Hardware, Laufzeiten | Prompt-Hash bezeichnet Datei, nicht Release |
| `forschung/report/workspace/benchmark-data.json` | Qwen/Gemma | aggregiert | historische Kennzahlen | nur mit Quelldaten und Run-1-Label verwenden |
| `forschung/report/workspace/manuelle-bewertung.json` | Qwen/Gemma | manuelle Rubrik | qualitative Vergleichsbasis | nicht blind und nicht mehrfach geratet |
| `forschung/report/workspace/methodik-und-evidenz.md` | Run 1 | Methodik | Rekonstruktion des damaligen Designs | dokumentiert Grenzen statt sie zu beheben |

Historische Kernwerte nach aktuellem Quality-Audit:

- Session 14, Qwen: 86 protokollierte Fragen, 16 streng valide, 1 Generationfehler, 68 Quality-Fehler, 67 Context-Budget-Fehler, 2 Setup-Fehler, 25 Relevanzwarnungen.
- Session 15, Gemma: 86 protokollierte Fragen, 1 streng valide, 82 Quality- und Context-Budget-Fehler, 3 Setup-Fehler, 1 CoT-Leak, 39 Relevanzwarnungen.

Die ursprünglich berichteten Werte können von später neu berechneten Quality-Werten abweichen. Im Report wird immer angegeben, ob eine Zahl aus der damaligen Summary oder aus einem späteren Re-Audit stammt.

## 2. Stärkste gepaarte Teilstichprobe

| Artefakt | Modell | Status | Kernaussage |
|---|---|---|---|
| `forschung/session_logs/session_29_first25/` | Qwen 3.5 4B | 25/25 valide | fair gepaarte Kategorien 1–5 |
| `forschung/session_logs/session_30/` | Gemma 4 E4B | 25/25 valide | gleiche 25 Fragen |
| `forschung/session_logs/session_32/` | GPT-OSS 120B/Groq | 25/25 valide | gleiche 25 Fragen; Provider-Audit bestanden |
| `forschung/report/workspace/first25-comparison-data.json` | alle drei | aggregiert | zentrale historische Drei-Modell-Teilstichprobe |
| `forschung/report/workspace/first25-comparison-summary.md` | alle drei | Interpretation | Kennzahlen, Methoden- und Generalisierungsgrenzen |

Historische Mittelwerte der Laufzeit: Qwen 9,7 s, Gemma 14,7 s, GPT-OSS 23,2 s. Relevanzwarnungen: 6, 7 und 1. Diese Stichprobe umfasst nur Kategorien 1–5, jeweils `n=1`, und darf nicht als vollständiger 86-Fragen-Benchmark dargestellt werden.

## 3. Ausgeschlossene oder nur technische Cloud-Versuche

Sessions 16–20, 23, 25 und 31 sind keine gültigen Modellbenchmarks. Gründe umfassen falsche Reasoning-Parameter, Rate-Limits, keine Zielantwort, Think-Reopening, T4-KV-OOM und einen verletzten Single-Model-Vertrag. Autoritative Ausschlussgründe:

- `forschung/report/workspace/TODO-GROQ-FORSCHUNGSABSCHLUSS.md`
- `forschung/report/workspace/run-metadata.json`
- vorhandene `INVALID.json`- und Validation-Artefakte in den jeweiligen Sessions

Teilresultate können technische Fehler belegen, fließen aber nicht in Qualitätsmittelwerte ein.

## 4. Bekannte Fehler und Reparaturquellen

- `plans/MUST_FIX.md`: MF-001 bis MF-048; autoritative normalisierte Run-1-Issue-Liste.
- `forschung/session_6_reparaturplan.md`: ältere Detailanalyse zu Whitespace, Context, Setup, Memory-Kontamination, CoT, Relevanz und Performance.
- Git-Historie: unter anderem `85c1178` (CoT), `4a43f6e`/`c5d5d13` (Gemma), `9d3d2fa` (Gemma/Groq), `ef865c4` (Memory Retrieval).
- Aktuelle uncommittete Tests und Reparaturen: nur Reparaturhinweise, niemals allein Fix-Belege.

## 5. Historische qualitative Belege

`CHAPPiE-Kollage.jpg` ist vorhanden (5928 × 8192) und in `forschung/report/workspace/historical-assets.json` inventarisiert. Sie wird ausschließlich als ältere, nicht vollständig reproduzierbare qualitative Illustration verwendet.

Die im Auftrag genannten Dateien `Eigen-Aktzeptanz.txt`, `Depresseiv-Test-neue-Instatn.txt` sowie historische Videos wurden im aktuellen Repository nicht gefunden. Im Report werden sie sichtbar als fehlend markiert, nicht rekonstruiert oder erfunden.

## 6. Vergleichsentscheidung

Run 2 verwendet Session 14/15 zur Fehlerreproduktion und die gepaarte First-25-Stichprobe für vorsichtige Drei-Modell-Vergleiche. Ein neuer Fünffachlauf wird stets separat ausgewiesen. Unterschiede in Sampling, Quantisierung, Memory-/Life-Startzustand, Reasoning-Budget und Provider verhindern einfache kausale Modellrankings.
