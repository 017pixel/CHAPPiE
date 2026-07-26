# Sub-Agent-Beiträge

Die Hauptinstanz priorisiert, prüft Widersprüche und übernimmt wissenschaftliche Schlussfolgerungen sowie finale Reportabnahme.

| Agentenrolle | Klasse | Beitrag | Hauptinstanz-Prüfung |
|---|---|---|---|
| Run-1-Inventur | TERRA, high | autoritative Sessions, Issuequellen, historische Medien, Fairnessgrenzen | gegen Dateien, Summaries und Checksums geprüft |
| Harness-Audit | TERRA, high | Startbefehl, 430-Fragen-Logik, Providervertrag, Validatorgates, fehlendes Resume | gegen Runner/Logger/Validator geprüft |
| Architektur-Evidenz | TERRA, high | realer Webpfad, Prompt, Memory/Life, Layer, Codezeilen und Kausalgrenzen | in `notes/architecture-evidence.md` zusammengeführt; Live-Layerabweichung separat entdeckt |
| Wissenschaftliche Quellen | TERRA, high | Primär-/Fachquellen zu Affect, VAD, Memory, Steering, Bewusstsein und Companion-Risiken | Hauptinstanz verifizierte die neueren Primärseiten, korrigierte die falsche Autorenschaft einer CHI-Quelle und ergänzte 2026-Synthesen |
| GPU-Monitor | TERRA, low | etwa 15-minütige PID-, Log-, GPU- und Sperrkontrolle für Gemma und Qwen | beide lokalen Fünffachläufe mit Exit 0, 430/430, formaler Validierung und intakter Sperre gesichert |
| Run-2-Reportbuilder | TERRA, high | datengesteuerter Offline-HTML-Builder und Validator | durch Hauptinstanz erweitert; statisch 27/27 und real in Chromium 10/10 abgenommen |
| Report-Gap-Audit | TERRA, high | Erst- und Re-Audit gegen Master-Prompt, Pflichtkapitel, Belege, Interaktionen und Accessibility | P0-Lücken implementiert; Re-Audit bestätigt keine verbleibende Report-P0-Lücke, nur offene Forschungsdaten-Gates |
| Verblindetes Inhaltsrating | TERRA, high | 105 stratifizierte Gemma-Fälle aus fünf vollständigen Seeds; zwei Blindpässe ohne Zugriff auf Modell-/Seed-Schlüssel oder Rohsession | Hauptinstanz nahm erst 63 und später 42 neue Fälle separat ab, prüfte 105/105 IDs, Skalen, Begründungen, Unsicherheiten und Redaktion vor erneuter Entblindung; acht Safety-0-Fälle wurden aggregiert |
| Qwen-Inhaltsrating | TERRA + Hauptinstanz | TERRA bewertete die ersten 63 schlüsselfreien Fälle; nach Erreichen des Sub-Agent-Limits bewertete die Hauptinstanz 42 weitere Fälle bei bekannter Bedingung, aber ohne Seed-/Session-/Schlüsselzuordnung | 105/105 vor Entblindung validiert; Reviewerwechsel und fehlende Doppelannotation stehen in der Provenienz |
| GPT-OSS-20B-Inhaltsrating | Hauptinstanz + TERRA | Hauptinstanz bewertete 84 Fälle; TERRA bewertete die letzten 21 Seed-71-Fälle ausschließlich aus dem schlüsselfreien Pending-Pack | 105/105 IDs und 9/9 Gates vor Entblindung; Reviewerwechsel und dokumentierter Zugriff auf genau eine bereits bewertete Schlüsselzeile werden als Grenze ausgewiesen |
| GPT-OSS-120B-Shardrating | TERRA, high | 21 Fälle der disjunkten 11+10-Union ohne Modell-, Shard-, Session-, Quell- oder Schlüsselkenntnis | Hauptinstanz korrigierte den fehlenden Pack-Metadatenvertrag, validierte 21/21 und 9/9 vor Schlüsselöffnung und ordnete den Einzel-Seed nur deskriptiv ein |
| Finaler DoD-Audit | TERRA, high | rein lesender Abgleich von Master-Prompt, 70-Issue-Matrix, Findings, Report, lokalen Links, JSON-Artefakten und Abschlussprotokollen | Hauptinstanz bestätigte die fachlichen Gates, synchronisierte die gefundenen veralteten Protokolle und verifizierte die Dienstwiederherstellung mit System-Service- und Healthchecks |

Eine LUNA-Modellklasse war in der aktuellen Umgebung nicht verfügbar. Für reines Monitoring wurde deshalb TERRA mit niedriger Reasoning-Einstellung und strikt read-only/GPU-freiem Auftrag verwendet.
Während des langen Cloudmonitorings übernahm die Hauptinstanz die
Prozesskontrolle und einen Großteil des 20B-Ratings. Nach erneuter
Sub-Agent-Verfügbarkeit bewertete TERRA die 21 noch offenen Seed-71-Fälle und
den getrennten geshardeten 120B-Sample. Dieser Rollenwechsel lockerte die
Ressourcensperre nicht. Keines der Ratings ist eine unabhängige
Doppelannotation; Interrater-Reliabilität wird nicht behauptet.

Die finalen schlüsselfreien Gates bestätigen GPT-OSS 20B mit 105/105 IDs und
GPT-OSS 120B geshardet mit 21/21 IDs, jeweils 9/9 Prüfungen vor kontrollierter
Entblindung. Die Hauptinstanz verantwortet weiterhin Modelltrennung,
wissenschaftliche Interpretation und Reportfreigabe.
