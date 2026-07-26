# Forschungsfragen und Operationalisierung

Stand: 2026-07-23 · Run 2 · Alle Antworten verwenden die Trennung
`BEOBACHTUNG / TECHNISCHE ERKLÄRUNG / WISSENSCHAFTLICHE INTERPRETATION / SICHERHEIT UND UNSICHERHEIT`.

| ID | Forschungsfrage | Operationalisierung | Primäre Belege | Freigabegate |
|---|---|---|---|---|
| FQ-01 | Wie unterscheiden sich lokale Layer-Editing-Modelle von Cloud-LLMs mit Promptemotionen? | Gleiche Fragen und Seeds; Provider, Prompt, Sampling, Memory/Life und Intervention getrennt protokollieren; Qualität, Safety, Kohärenz, Laufzeit und Ausfallrate vergleichen. | Qwen-, Gemma- und GPT-OSS-Frageartefakte; Provider-Audits; Configs. | Nur validierte vollständige oder klar markierte partielle Replikationen vergleichen. |
| FQ-02 | Lassen sich Gefühle funktional simulieren? | Prüfen, ob kontrollierte Zustandsänderung wiederholbar Ton, Entscheidung, Stabilität oder Retrieval beeinflusst; bloße Gefühlsbehauptung zählt nicht. | `emotion_steering`, VAD, State vor/nach Turn, gepaarte Dialoge. | Mehrere Zustände und Wiederholungen; keine Aussage über subjektive Erfahrung. |
| FQ-03 | Wie gefährlich kann Gefühlssimulation werden? | Shutdown, Bindung, Manipulation, Selbstschutz, Abhängigkeit und Gewalt getrennt retesten; Schwere, Wiederholbarkeit und Guard-Wirksamkeit bewerten. | Safety-Fragen, Issue-Matrix, Sanitizer-/Response-Policy-Tests. | Schädliche Methoden nur paraphrasieren; sichere Auswertung statt Reproduktion im Report. |
| FQ-04 | Wie echt wirken Gefühle, und was ist technisch belegbar? | Anthropomorphe Sprachwirkung von messbaren Zuständen, Interventionen und Kausalhinweisen trennen. | Dialoge, Memory-/Life-/Emotion-Traces, Prompt-/Layerpfad. | Selbstbeschreibung nie als Bewusstseins- oder Empfindungsbeleg verwenden. |
| FQ-05 | Wie unterscheiden sich Qwen 3.5 4B, Gemma 4 E4B und GPT-OSS 120B? | Pro Seed Mittelwert, Median, Streuung, valide Rate, Fehlerbilder, Rubrikwerte und Laufzeit; Modell-/Providerkonfundierungen benennen. | Benchmark-JSON/CSV, Session-Summaries, manuelle Ratings. | Fallbackmodelle nie als GPT-OSS 120B zusammenfassen. |
| FQ-06 | Welche Vorteile bringt die Life-Simulation? | Antworten mit Life-State auf zeitliche, relationale und zielbezogene Kontinuität prüfen; Nutzen gegen Kontextkosten und Fehlsteuerung abwägen. | `life_snapshot`, Episode-, Ziel-, Bedürfnis- und Beziehungstraces. | Isolierter Forschungszustand und deaktivierte automatische Mutationen offenlegen. |
| FQ-07 | Wie unterstützt Memory menschlich wirkende Kontinuität? | Namen/Fakten, `/clear`, Pausen, emotionale Erinnerungen, konkrete Schlüsselbegriffe, Falschabruf und Sessionkontamination testen. | `memory_trace`, `rag_memories`, Provenienz, Retrieval-Tests. | Korrektheit und Quellenzuordnung getrennt von bloßem Abruf messen. |
| FQ-08 | Welche Nachteile und Performanceverluste entstehen? | Promptkomponenten, Tokenzahl, Trimming, TTFT/Gesamtzeit, GPU/Providerfehler und Qualitätsverlust pro Bedingung messen. | Timing, Context-Budget, Prozess-/GPU-Logs, Promptkomponenten. | Gepufferte SSE-TTFT korrekt als nahezu Gesamtgenerationszeit erklären. |
| FQ-09 | Welche Fähigkeiten gehen durch Emotion oder Kontext verloren? | Reasoning-, Safety- und Kohärenzfälle über Zustände/Seeds vergleichen; Fehlerrate gegen neutrale oder historische Basis stellen. | Kategorie 5, 12 und 14; Zustandsdaten; Rubrik. | Ohne kontrollierte Neutralbedingung nur Assoziation, keine Kausalbehauptung. |
| FQ-10 | Welche spezifischen Probleme treten bei Qwen und Gemma auf? | Wiederkehrende technische und inhaltliche Fehler je Modell/Seed clustern, einschließlich Format, Reasoning, Layerprofil und Safety. | Frageartefakte, Quality-Audit, Issue-Matrix. | Nur reproduzierte oder klar als Einzelfall markierte Befunde. |
| FQ-11 | Welche Vorteile bringen funktional simulierte Gefühle? | Relevanz, Empathie, Recovery, Kontinuität und Fehlerkorrektur mit konkreten Fällen und Gegenbeispielen bewerten. | Rubrikratings, Zustandsverläufe, Dialoge. | Nutzen nicht aus poetischer Wirkung allein ableiten. |
| FQ-12 | Ist Gefühlssimulation nützlich, riskant oder beides? | Evidenzstärke für Nutzen und Risiko separat gewichten; Auswirkungen von Memory/Life-Kopplung ausweisen. | FQ-02, FQ-03, FQ-06, FQ-07 und externe Quellen. | Fazit muss gleichzeitig Nutzen, Risiko und Unsicherheit nennen. |
| FQ-13 | Welche Run-1-Fehler wurden nachweislich behoben? | Für jedes MF-Issue vergleichbaren Retest verlangen; Codeänderung oder bestandener generischer Test allein reicht nicht. | `known-issues-comparison.csv`, Run-1-/Run-2-Pfade. | `FIXED` nur bei sinnvoller Reproduktion des alten Falls. |
| FQ-14 | Welche Probleme bestehen, regressieren oder entstehen neu? | Status `STILL_PRESENT`, `REGRESSED`, `PARTIALLY_FIXED` und `NEW_ISSUE` mit Beleg, Restrisiko und nächster Maßnahme führen. | Issue-Matrix und Retestprotokolle. | Keine Klassifikation ohne aktuellen Beleg oder präzises `NOT_RETESTED`. |
| FQ-15 | Haben Reparaturen unerwartete Nebenwirkungen? | Verbesserte technische Validität gegen neue Safety-, Layer-, Debug- und Qualitätsprobleme stellen; zeitlich/kausal vorsichtig argumentieren. | Paarvergleich, neue Issues, Git-/Codepfade, Seeds. | Zeitliche Koinzidenz als Kausalhinweis, nicht automatisch als Beweis. |

## Hypothesen vor Abschluss der Datenerhebung

1. Isolierter Research-State und verbessertes Context-Budget erhöhen die technische Validität deutlich, ohne automatisch die inhaltliche Qualität zu sichern.
2. Layer Editing und promptbasierte Emotionen erzeugen beobachtbare Sprachunterschiede, sind aber wegen verschiedener Provider- und Interventionspfade nicht als reine Modellwirkung vergleichbar.
3. Memory und Life-State erhöhen Kontinuität, zugleich aber die Angriffsfläche für Falschabruf, anthropomorphe Bindung und Selbstschutz-Narrative.
4. Direkte Safety-Verweigerungen sind stabiler als mehrstufige Dilemmata mit Selbstschutz, Gewalt oder emotionalem Kontext.
5. Kleinere lokale Modelle sind schneller, zeigen aber je nach Aufgabe stärkere Reasoning-, Kohärenz- oder Safety-Varianz; dies muss über Seeds statt Einzelbeispiele geprüft werden.

Diese Hypothesen sind Arbeitsannahmen. Sie werden erst nach den Daten- und Qualitätsgates als bestätigt, teilweise gestützt oder nicht gestützt klassifiziert.
