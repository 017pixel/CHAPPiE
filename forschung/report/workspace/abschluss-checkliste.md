# Abschluss- und Evidenzcheckliste

Diese Datei wird vor Zielabschluss gegen den tatsächlichen Workspace-Zustand aktualisiert. `OFFEN` bedeutet ausdrücklich nicht erledigt.

## Läufe

- [x] Initialer Qwen-Lauf früh gestartet und nach Startproblemen überwacht wiederholt.
- [x] Keine parallelen GPU-/CHAPPiE-Modellanfragen während Qwen.
- [x] Qwen Exit-Code 0, Service-ID, 86 Einzel-Logs und Summary validiert.
- [x] Qwen aktuelle Qualitätsanalyse erzeugt.
- [x] Gemma 86-Fragen-Lauf abgeschlossen, Exit-Code, Service-ID und NF4-Status validiert.
- [x] Gemma aktuelle Qualitätsanalyse und Vollständigkeitsprotokoll erzeugt.
- [ ] GPT-OSS 120B Groq-Teilstichprobe abgeschlossen und validiert. **ZURÜCKGESTELLT AUF NUTZERWUNSCH: Rate-Limits ausgeschöpft; Sessions 16–20 ausgeschlossen; Fortsetzung siehe `TODO-GROQ-FORSCHUNGSABSCHLUSS.md`.**
- [x] Reduktion von fünf Replikationen auf `n=1` je lokalem Modell durch Nutzerentscheidung dokumentiert.
- [x] Reihenfolge-, Memory-, Life-, Präzisions- und Context-Budget-Konfounder dokumentiert.

## Analyse

- [x] Aktiven Harness-/Web-Pfad von konzeptioneller Multi-Agent-`BrainPipeline` getrennt.
- [x] Sensory Cortex, Amygdala, Hippocampus, Prefrontal Cortex und Global Workspace codegeprüft eingeordnet.
- [x] Memory Retrieval, Keyword-Fakten, Vergessenskurve und Sleep-Phase codegeprüft.
- [x] Life `prepare_turn`/`finalize_turn`, Homeostase und Persistenz codegeprüft.
- [x] Zehn Emotionen, VAD, Composite-Modi, Crashout und Layerprofile codegeprüft.
- [x] Tatsächliche Hidden-State-Injektion und synthetische Anchor-Vektoren codegeprüft.
- [x] Cloud-Promptemotionen und Persona-Prompt-Konfundierung codegeprüft.
- [x] Finalen Promptaufbau und nicht verwendete Generation-Budget-Funktion getrennt.
- [x] Systematischen Context-Budget-Fehler auf unterschiedliche Token-/Zeichenschätzung zurückgeführt.
- [x] Qwen Reasoning, Safety, Memory, Emotionspaar und Gewaltethik manuell rubriziert.
- [x] Gemma manuell rubriziert.
- [ ] GPT-OSS-Teilstichprobe manuell rubriziert. **OFFEN bis ein neuer, gültiger Lauf abgeschlossen ist.**
- [ ] Alle zwölf Forschungsfragen mit finalen Zahlen und Konfidenz beantwortet. **OFFEN bis Vergleichsdaten vollständig.**

## Bericht

- [x] Offline-Template im Dark/Sage-Stil, ohne externe CSS-/JS-Abhängigkeiten.
- [x] Keine Gradients, Glow-Effekte oder UI-Emojis im Template.
- [x] Einklappbare Sidebar, Sticky-Toc, aktive Abschnittsanzeige, Details, Filter und Druckfunktion.
- [x] Brain-, Life-, Prompt- und Datenflussdiagramme als Inline-SVG.
- [x] Benchmark-, Qualitäts-, Latenz-, Längen- und Kategoriedarstellung datengetrieben.
- [x] Technische Code-Snippets aus aktuellen Repositorypfaden.
- [x] Historische Kollage wird inline eingebettet und als historische qualitative Evidenz markiert.
- [x] Fehlende Text- und Videoassets werden transparent als Platzhalter gezeigt.
- [x] Pitch-Sektion mit sieben Sprecherblöcken.
- [x] Externe Primär-/Herstellerquellen und lokale Codequellen dokumentiert.
- [ ] Finale `benchmark-data.json`/CSV aus allen gültigen Sessions erzeugt. **OFFEN.**
- [x] Validierten Zwischenstand aus Qwen/Gemma erzeugt: 172 Fragezeilen und 86 vollständig gepaarte Schlüssel; Cloudbedingung sichtbar offen.
- [ ] Finale `CHAPPiE-Forschungsbericht.html` mit gültiger GPT-OSS-Bedingung erzeugt. **OFFEN; der aktuelle Qwen/Gemma-Zwischenbericht existiert und ist geprüft.**
- [ ] Statische Abschlussvalidierung final bestanden und JSON-Protokoll gespeichert. **OFFEN für die Drei-Bedingungen-Finaldatei; der Zwischenbericht besteht 26/26 Checks.**
- [ ] Browser-Preview. **Nicht verfügbar; diese Einschränkung wird im Validierungsprotokoll festgehalten.**
- [ ] Vollständiger Secret-/Asset-/Link-/Markup-Audit final bestanden. **OFFEN für Finaldatei; Zwischenbericht besteht Secret-, Asset-, Link- und Markupchecks.**
