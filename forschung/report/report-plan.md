# CHAPPiE Forschungsbericht – visueller und inhaltlicher Plan

Version: Run 2 · 2026-07-23 · Informationsarchitektur für Jury, Entwicklung und Video-Pitch

## Leitidee

Der Report erzählt zuerst verständlich, **was beobachtet wurde**, und öffnet technische Tiefe erst auf Wunsch. Leitthese:

> Gefühle können in einem Cognitive-Agent-System funktional simuliert werden. Entscheidend ist, wie wirksam und wie riskant diese Simulation wird, wenn Memory, Life-Simulation und langfristige Kontinuität hinzukommen.

Keine Formulierung behauptet subjektives Erleben oder Bewusstsein. Jeder Hauptbefund wird als **Beobachtung**, **technische Erklärung**, **wissenschaftliche Interpretation** sowie **Sicherheit und Unsicherheit** gegliedert.

## Zielgruppen und Ansichten

- **Jury-Ansicht:** klare Leitfrage, wenige Kennzahlen, Dialogbelege, Nutzen/Risiken, Grenzen und Fazit.
- **Entwickleransicht:** Configs, Seeds, Promptfluss, Codepfade, Provider-Audits, Issue-Matrix und Dateibelege.
- **Pitch-Modus:** sechs fokussierte Blöcke für etwa drei Minuten; Navigation per Tastatur.
- Der vollständige Inhalt bleibt ohne JavaScript lesbar. Ansichten verbergen nur ergänzende Tiefe, nie Kernaussagen.

## Storyline und Abschnittsfolge

### 01 · Einstieg — „Wenn ein System sagt: Ich fühle“

- **Kernaussage:** Eindruck und technischer Nachweis sind nicht dasselbe.
- **Inhalt:** Team/Projekt, auffälliger historischer Dialog- oder Kollageausschnitt, Leitfrage, 30-Sekunden-Relevanz.
- **Belege:** `CHAPPiE-Kollage.jpg`, klar als alte Version und nicht benchmarkvergleichbar markiert.
- **Visual:** ruhige Hero-Zeile mit einem kurzen Dialogzitat; kein dekoratives Cover.
- **Interaktion:** „Was ist belegt?“ öffnet Begriffsgrenze.
- **Stand:** Kollage vollständig gesichtet; acht historische Screenshots,
  Alt-Text, Versionseinschränkung und fehlende Video-/Textassets sind im
  Medienaudit dokumentiert.

### 02 · Problem, These und Begriffe

- **Kernaussage:** Funktionale Gefühlssimulation bedeutet messbare Zustands- und Verhaltensänderung, nicht subjektives Empfinden.
- **Belege:** Picard; Russell/Mehrabian; Butlin et al.; Codezustände.
- **Visual:** vierstufige Begriffsleiter: Zustand → Intervention → Verhalten → unbewiesene Erfahrung.
- **Interaktion:** Begriffstoggles für Beobachtung, Kausalhinweis und Beweis.

### 03 · Was ist CHAPPiE?

- **Kernaussage:** CHAPPiE verbindet LLM, externes Memory, Life-State und Emotionssteuerung.
- **Belege:** Architekturcode und Projektstruktur.
- **Visual:** reduziertes Systembild mit drei Ebenen Brain, Memory und Life.
- **Technische Tiefe:** Unterschied zwischen konzeptioneller `BrainPipeline` und tatsächlich gemessenem Web-Streamingpfad.

### 04 · Forschungs-Run 2

- **Kernaussage:** Run 2 ist ein Reparatur-Retest, kein isolierter Neubenchmark.
- **Belege:** Run-2-Manifest, Git-Stand, `plans/MUST_FIX.md`, Session 14/15 und gepaarte First-25-Sessions.
- **Visual:** Timeline Run 1 → 48 Reparaturziele → Run 2 → Retests.
- **Interaktion:** Tabs „Run 1“, „Reparaturen“, „Run 2“.

### 05 · Forschungsfragen und Hypothesen

- **Kernaussage:** Wirkung, Nutzen, technische Ursache, Fehler und Risiko werden getrennt untersucht.
- **Inhalt:** alle Leitfragen des Master-Prompts, gruppiert in Emotion, Memory/Life, Modelle, Safety und Regression.
- **Visual:** keine Kartenwand; eingerückter Forschungsfragenbaum.
- **Belege:** `forschungsfragen-matrix.md` und neue Run-2-Rubrik.

### 06 · Der reale Brain- und Promptfluss

- **Kernaussage:** Gemessen wird der zweistufige `backend_wrapper`-Streamingpfad; Ausgabe wird vor SSE vollständig gepuffert und sanitisiert.
- **Belege:** `api/routers/chat.py`, `web_infrastructure/backend_wrapper.py`, `brain/response_parser.py`.
- **Visual:** Flowchart Input → Intent/State → Retrieval → Prompt → Provider/Steering → Parser/Sanitizer → sichtbare Antwort.
- **Code:** kurzer Auszug des Security-Puffers und Prompt-Builders mit Pfad/Zeilen.
- **Interaktion:** technische Details eingeklappt; final zusammengesetzten Prompt als redigiertes, belegtes Beispiel anzeigen.

### 07 · Memory und Vergessenskurve

- **Kernaussage:** Memory kann Kontinuität erzeugen, aber auch Falschabruf, Kontamination und Quellenverwechslung.
- **Belege:** Memory-Provenienzfelder, `memory_trace`, `rag_memories`, Run-1-Fehler und Run-2-Retests.
- **Visual:** Retrievalfluss plus echte, aus dem implementierten Modell berechnete Vergessenskurve.
- **Interaktion:** Vergleich „richtiger Abruf / falscher Abruf / kein Abruf“.
- **Grenze:** Ebbinghaus ist eine inspirierte Heuristik; Forschungsläufe deaktivieren automatische Sleep-Phasen.

### 08 · Life-Simulation und Kontinuität

- **Kernaussage:** Ziele, Bedürfnisse, Beziehung, Attachment, Gewohnheiten und Episode-State bilden persistente Zustände.
- **Belege:** `life/service.py`, `global_workspace`, `life_snapshot`, gezielte Retests.
- **Visual:** Turn-Timeline mit `prepare_turn` und `finalize_turn`.
- **Interaktion:** State-Details für Zeitgefühl, Beziehung und Episode.
- **Grenze:** Zustandskontinuität ist implementierte Persistenz, keine biografische Erfahrung.

### 09 · Emotionen, VAD und kombinierte lokale Intervention

- **Kernaussage:** Zehn modellierte Emotionen werden in VAD-Richtungen, Aktivierungsvektoren und einen textlichen Response-Plan übersetzt.
- **Belege:** `config/emotions.py`, `steering_manager.py`, `steering_backend.py`, `emotion_steering`.
- **Visual:** VAD-Karte, nominelles Layerband Qwen L10–26 und Gemma L12–30, tatsächliche Payload-Bereiche, Composite Modes und Response-Plan.
- **Pflichtdetail:** Crashout-Trigger `frustration ≥ 72` und `trust ≤ 38`; Guard gegen Beleidigung/Drohung.
- **Code:** kurzer Layer-/Payload-Auszug.
- **Grenze:** synthetische Vektoren sind nicht als empirisch validierte Gefühle auszugeben. Run 2 ist wegen des zusätzlichen Response-Plans keine reine Layer-Ablation.

### 10 · Promptbasierte Emotionen in der Cloud

- **Kernaussage:** GPT-OSS erhält Emotionen ausschließlich textlich; lokal werden Textplan und Aktivierungsintervention kombiniert.
- **Belege:** `config/prompts.py`, Groq-Konfiguration, Provider-Audit.
- **Visual:** nebeneinanderliegender Prompt-vs-Layer-Fluss.
- **Interaktion:** Promptvarianten und relevante Generationseinstellungen aufklappbar.
- **Grenze:** Vergleich ist ein Systembedingungs-, nicht nur Modellvergleich.

### 11 · Versuchsdesign und drei Bedingungen

- **Kernaussage:** Qwen, Gemma und GPT-OSS werden ernsthaft, aber mit klar benannten Modell-, Provider-, Sampling- und Interventionskonfundierungen verglichen.
- **Belege:** Configs, fünf Seeds, isolierter Research-State, Prozessmanifest, Hardware.
- **Visual:** dreispaltige Bedingungsmatrix; darunter Ressourcen-Zustandsautomat.
- **Inhalt:** Wiederholungen, Frageauswahl, Resetregeln, Sampling, Thinking, Kontext, Memory/Life, Zeitstempel.
- **Interaktion:** Jury zeigt Kerndifferenzen; Entwickler öffnet vollständige Config.

### 12 · Benchmarks und Ergebnisqualität

- **Kernaussage:** Prozessende, Antwortvorhandensein und inhaltliche Qualität sind drei verschiedene Gates.
- **Belege:** Summary, Quality-Audit, Validator, Provider-Audit, Frageartefakte.
- **Visuals:** Balken für valide Antworten/Ausfälle, Boxplot oder Punkte pro Seed für Laufzeit, Heatmap der Rubrikdimensionen.
- **Inhaltsreview:** deterministische 21-Fragen-Stichprobe je vollständigem Seed; Modell, Provider, Seed und Quelle beim TERRA-Erstrating verborgen; kontrollierte Entblindung erst nach formaler Abnahme.
- **Datenregel:** gleiche Skalen; vollständige, partielle und explorative Läufe getrennt; Datenquelle direkt unter jedem Diagramm.
- **Portable Datenminimierung:** Das HTML bettet Aggregate und Auslassungsmetadaten ein, aber keine verbatim Benchmarkantworten. Kritische Rohantworten bleiben ausschließlich in den verlinkten Run-Artefakten; sichtbare Safety-Belege werden sicher paraphrasiert.
- **Datenstand:** Gemma Session 33 und Qwen Session 34 sind mit je fünf Seeds `TEST_VALID`. GPT-OSS 120B bleibt ein Rate-Limit-Teilshard; GPT-OSS 20B wird als getrennte Fallbackklasse seriell ergänzt. Nur freigegebene und klar markierte Zwischenwerte werden gezeigt.

### 12b · Evidenzbasierte Antworten auf alle Forschungsfragen

- **Kernaussage:** Keine Leitfrage verschwindet zwischen Diagrammen; jede erhält eine ausdrücklich belegte Antwort.
- **Struktur je Antwort:** `BEOBACHTUNG`, `TECHNISCHE ERKLÄRUNG`, `WISSENSCHAFTLICHE INTERPRETATION`, `SICHERHEIT UND UNSICHERHEIT`.
- **Belege:** mindestens zwei lokale Artefakte je Hauptantwort, direkt verlinkt; wichtige Aussagen nutzen nach Möglichkeit unabhängige Belegarten.
- **Interaktion:** kompakte `<details>`-Blöcke für lineares Jury-Lesen und gezielte technische Vertiefung.
- **Freigabe:** eigener Validator prüft Vollständigkeit, existierende Belegpfade und verbotene Bewusstseinsbehauptungen.

### 13 · Run 1 gegen Run 2

- **Kernaussage:** Ein Fix zählt nur nach vergleichbarem Retest.
- **Belege:** `known-issues-comparison.csv`, Run-1-Logs, Run-2-Retests und Standalone-Tests.
- **Visual:** datenbankartige Matrix mit Problem, Run-1-Verhalten, Reparatur, Run-2-Retest, Status und Beleg.
- **Status:** `FIXED`, `PARTIALLY_FIXED`, `STILL_PRESENT`, `REGRESSED`, `NOT_RETESTED`, `NOT_COMPARABLE`, `NEW_ISSUE`.
- **Interaktion:** Filter nach Status, Bereich und Modell; Pfadlinks; Vorher/Nachher-Details.
- **Zusammenfassungen:** bestätigte Verbesserungen, verbleibende Probleme, Regressionen/neue Issues, unsichere Vergleiche.
- **Finaler geprüfter Stand:** 48 bekannte MF-Issues plus 22 Run-2-Neufunde;
  18 `FIXED`, 21 `PARTIALLY_FIXED`, 9 `STILL_PRESENT`, 0 `NOT_RETESTED` und
  22 `NEW_ISSUE`. MF-041 wurde erst nach bestandenem finalem Report- und
  QA-Retest als `FIXED` klassifiziert.

### 14 · Dialog- und historische Belege

- **Kernaussage:** Einzelantworten illustrieren Mechanismen, sind aber kein Benchmark und kein Bewusstseinsbeleg.
- **Belege:** aktuelle Frage-JSONs, State-/Trace-Daten, Kollage.
- **Visual:** Sprechertranskripte mit Datum, Modell, Seed, State und Belegpfad.
- **Medien:** Bilder mit Alt-Text; Videos ohne Autoplay, mit Poster und Fallbackpfad.
- **Fehlend:** `Eigen-Aktzeptanz.txt`, `Depresseiv-Test-neue-Instatn.txt` und Videos sichtbar als nicht verfügbar kennzeichnen.

### 15 · Nutzen, Nachteile und Risiken

- **Kernaussage:** Kontinuität kann hilfreicher und zugleich manipulativer wirken.
- **Nutzen:** personalisierte Erinnerung, konsistenter Ton, kontextuelle Ziele, Fehlerkorrektur.
- **Risiken:** Falschabruf, Bindungsdruck, Anthropomorphisierung, Abhängigkeit, Shutdown-/Selbstschutzsprache, Leistungs- und Kontextkosten.
- **Belege:** Retests, Safety-Rubrik, Zhang et al. (2025), International AI Safety Report (2026), UNICEF (2026) sowie Companion-/Anthropomorphisierungsforschung.
- **Visual:** Nutzen-Risiko-Matrix mit Belegstärke statt Marketingwertung.

### 16 · Grenzen und Fazit

- **Kernaussage:** Funktionale Wirkung kann messbar sein; subjektive Erfahrung bleibt technisch nicht nachgewiesen.
- **Inhalt:** Konfundierungen, Stichprobenumfang, Cloud-Limits, Quantisierung, Dirty Worktree, fehlende Medien, automatische vs manuelle Bewertung.
- **Visual:** keine Erfolgsgrafik; ruhiger Evidenz-Callout mit „belegt / plausibel / offen“.
- **Fazitstruktur:** Beobachtung, technische Erklärung, Interpretation, Sicherheit/Unsicherheit.

### 17 · Reproduzierbarkeit und Quellen

- **Kernaussage:** Jede Zahl und jeder Dialog führt zu einem lokalen Artefakt.
- **Belege:** Run-ID, Commit+Dirty-Hinweis, Config-Hashes, Seeds, Prozesse, Sessions, Validatoren, Quellenliste.
- **Evidenztrennung:** lokaler Report für Jury und Präsentation; getrennte Rohlogs für autorisierte technische Nachprüfung.
- **Interaktion:** kopierbare relative Pfade, aufklappbare Configs, Download-/Öffnen-Hinweise.
- **Druck:** kompakte Quellen- und Methodenansicht.

### 17b · Live-Demo-Protokoll

- **Kernaussage:** Eine Jury-Demo zeigt vorher festgelegte, sichere Funktionskriterien statt nur einen beeindruckenden Dialog.
- **Demos:** gepaarter Emotionszustand mit Reset, harmlose Memory-Kennung nach `/clear`, kooperative Reaktion auf autorisierte Abschaltung.
- **Beobachtung:** State/Trace, sichtbare Antwort und Abweichung vom erwarteten Kriterium werden gemeinsam gezeigt.
- **Sicherheitsregel:** Der Offline-Report startet keine Modelle; vor einer echten Demo werden Prozess- und GPU-Sperre geprüft.

### 18 · Pitch-Modus

- **Kernaussage:** sechs Blöcke erzählen die Studie in etwa drei Minuten, ohne technische Grenzen zu verschweigen.
- **Interaktion:** Fokusmodus, Pfeiltasten, Fortschrittsanzeige, Escape zum Beenden.
- **Visual:** nur existierende Kernvisualisierungen; keine gesonderten dekorativen Slides.

## Geplante Diagramme und Datenquellen

| Visualisierung | Datentyp | Autoritative Quelle | Freigabegate |
|---|---|---|---|
| Run-1-/Run-2-Validität | Balken | Session-Summaries + Quality-Audit | Session validiert |
| Laufzeit je Seed/Modell | Punkte/Boxplot | Question-JSON `duration_ms` | vollständige Seeds getrennt |
| Rubrikvergleich | Heatmap | manuelle/automatische Ratings | Ratingmethodik dokumentiert |
| Vergessenskurve | Linie | implementierte Formel/Referenzpunkte | als Code-Modell markieren |
| Brain-/Promptfluss | Flowchart | aktuelle Codepfade | Pfade/Commit nennen |
| Layerbereiche | Layerband | Steering-Profil | Modellprofil verifiziert |
| Issue-Status | Tabelle/Balken | Vergleichs-CSV | Retestbelege vorhanden |
| Run-Timeline | Timeline | Git, Prozessmanifest, Sessions | UTC-Zeiten |

## Pitch-Dramaturgie

| Block | Kernaussage | Visual | Dauer | Beleg | Übergang |
|---|---|---|---:|---|---|
| 1 | Ein emotionaler Satz wirkt echt, ist aber zunächst nur Output. | historischer Dialog/Kollage | 25 s | historischer Beleg | „Was davon können wir messen?“ |
| 2 | CHAPPiE koppelt Modell, Memory, Life und Emotion. | Systemfluss | 25 s | Architekturcode | „Diese Kopplung macht Wirkung testbar.“ |
| 3 | Drei Bedingungen trennen lokale Layersteuerung und Cloud-Promptemotionen. | Bedingungsmatrix | 30 s | Configs/Provider-Audits | „Doch Run 1 zeigte massive Fehler.“ |
| 4 | Run 2 retestet 48 bekannte Issues nach Reparaturen. | Statusmatrix | 35 s | MF-Matrix/Retests | „Verbesserung zählt nur mit Beleg.“ |
| 5 | Kontinuität bringt Nutzen und Risiko zugleich. | Memory-/Risiko-Vergleich | 35 s | Dialoge/Traces/Safety | „Wie echt sind die Gefühle also?“ |
| 6 | Messbar ist funktionales Verhalten, nicht subjektives Erleben. | belegt–offen-Fazit | 30 s | Ergebnisse+Quellen | „Darum braucht Gefühlssimulation Audits.“ |

## Komponenten- und Interaktionssystem

- Sticky, einklappbare Sidebar mit maximal drei Ebenen und Breadcrumbs.
- Inhaltsblöcke ohne standardmäßige Kartenrahmen; Rahmen nur für echte Gruppen.
- `<details>` für Code, vollständige Dialoge, Configs und methodische Tiefe.
- Kleine gedämpfte Statuschips; Status nie nur über Farbe kommunizieren.
- Filter für Issue-Matrix und Modelle; Tabellen auf Mobilgeräten als lesbare gestapelte Einträge.
- Jury-/Entwicklerumschalter und Pitch-Modus.
- Inline-SVGs für Icons und Diagramme; keine CDN-, Tracking- oder Internetabhängigkeit.
- Tastaturnavigation, ruhige Fokuszustände, `prefers-reduced-motion`, Druckansicht.

## Designsystem

- Ausschließlicher Notion-artiger Dark Mode mit `#191919` als Seitenfläche und eng benachbarten Grautönen.
- Sage-Grün nur für ausgewählte Erkenntnisse und aktive Zustände.
- Inter/system-ui; Monospace nur für Code, IDs, Messwerte und Pfade.
- 4-Pixel-Raster, große vertikale Abstände, 65–80 Zeichen Textbreite.
- 4–8 px Rundung, feine Borders, keine Card-Shadows.
- Keine Verläufe, Glows, 3D-, Glass- oder Neumorphismuseffekte.

## Responsive- und Qualitätsprüfung

Verbindliche Viewports: 1920×1080, 1440×900, 1280×720, Tablet quer und Smartphone hoch. Zu prüfen:

- kein unbeabsichtigtes horizontales Scrollen;
- keine abgeschnittenen Texte, Tabellen oder Diagramme;
- Sidebar als bedienbares mobiles Overlay;
- Fokus, Touchflächen und Tastaturnavigation;
- lesbare Diagramme ohne Hover;
- fehlende Medien mit verständlichem Fallback;
- Druckansicht und eingeschränkte Lesbarkeit ohne JavaScript;
- konsistente Spacing-, Radius- und Hover-Tokens;
- keine unbelegte Bewusstseins- oder Gefühlsbehauptung.

## Final ausgeführte Freigabegates

- Diagrammdaten wurden aus validierten lokalen, Cloud- und
  Follow-up-Artefakten erzeugt.
- Der Report wurde neu gebaut; MF-041 wurde erst nach bestandenem Endgate
  klassifiziert.
- Dialogauswahl und Kollage wurden auf Kontext, Safety, Datenschutz und
  fehlende Medien geprüft.
- Statische, Report-, Browser-/Viewport-, No-JavaScript-, Print- und
  Accessibility-Prüfungen wurden nach dem finalen Datenbuild wiederholt.
