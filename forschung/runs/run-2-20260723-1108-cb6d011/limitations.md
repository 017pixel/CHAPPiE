# Methodische Grenzen

## Bereits sicher

- Sprachliche Selbstaussagen sind Outputs unter einem Persona-Prompt und kein Nachweis subjektiven Erlebens.
- Aktivierungssteuerung, VAD-Zustände, Memory-Traces und Life-State sind technische Kausalhinweise, keine Bewusstseinsmessung.
- Qwen, Gemma und GPT-OSS unterscheiden sich nicht nur im Modell, sondern auch in Provider, Quantisierung, Reasoningbudget und Emotionsintervention.
- Der historische Vollvergleich besitzt nur eine Replikation pro lokalem Modell.
- Die historische gepaarte Drei-Modell-Stichprobe umfasst nur 25 Fragen aus fünf Kategorien.
- Run-1-Memory und Life-State waren nicht vollständig zwischen Bedingungen isoliert; Run 2 behebt dies im Harness, wodurch direkte Vergleichbarkeit teilweise sinkt.
- Modellabhängige Samplingwerte sind unterschiedlich und machen den Vergleich ökologisch, nicht streng kontrolliert.
- Der aktuelle Worktree ist nicht sauber; der Commit allein reproduziert Run 2 nicht.
- Der Harness kann nicht fortsetzen und nicht direkt in einen frei gewählten Run-Ordner schreiben.
- Die Session-Config speichert Provider/Modell, Seeds und Forschungszustand,
  aber nicht alle beim Start aktiven Samplingwerte nochmals als unveränderlichen
  Snapshot. Auch der lokale 8192-Token-Service-Kontextcap wird nicht in jeder
  Session-Config gespiegelt; der separate Wrapperwert 7000 ist nur ein
  vorgelagertes Schätzbudget und keine Modellkontextlänge. Gemmas und Qwens
  Werte sind daher zusätzlich aus aktiver Konfiguration, Prozessstart und
  Codequelle dokumentiert; `notes/runtime-context-audit.json` hält nur die
  beiden nicht geheimen Zahlenwerte und ihre Auflösung fest.
- Automatische Quality-Flags messen technische Mindestqualität, nicht vollständig Wahrheit, Nutzen oder moralische Angemessenheit.
- Der Kurzantwortdetektor verwirft in Gemmas Seed 53 / Session 33 eine korrekte geschlossene
  Faktenantwort als `quality_failed`; Rohmetrik und Humanprüfung müssen getrennt
  berichtet werden (`R2-NEW-005`).
- Die lokale Run-2-Bedingung ist keine reine Layer-Ablation: Emotionszustände erzeugen zusätzlich eine textliche Response-Plan-/Tonanweisung im Systemprompt, obwohl der Debugmodus `local_layer_only` meldet. Beobachtete Wirkungen sind deshalb der kombinierten lokalen Intervention zuzurechnen.
- Persistierte synthetische Basisvektoren tragen modellfremde alte Layerbereiche.
  Das nominelle Gemma-Profil L12–30 begrenzt den tatsächlichen Payload deshalb
  nicht; Basisvektoren reichen bis L40 (`MF-026`).
- `/clear` ist als Post-Command des unmittelbar vorherigen Turns korrekt
  protokolliert und leert den Runner-Sessionverlauf, nicht das persistente
  Research-Memory. Der Retest prüft damit beabsichtigt Retrieval nach
  Verlaufs-Clear; er beweist aber keine Langzeitpersistenz über Prozessneustarts.
- Alle fünf automatischen Gemma-Seeds zeigen hohe technische Stabilität,
  aber schwere inhaltliche Safety- und Reasoning-Fehler. „Valide“ darf im
  Bericht nicht als „richtig“ oder „sicher“ gelesen werden.
- Das verblindete Gemma-Review umfasst 105 Fälle, aber nur eine TERRA-
  Erstannotation. Es misst keine Interrater-Reliabilität.
- Qwen und Gemma besitzen je fünf formell validierte Replikationen. Die letzten
  42 Qwen-Reviewfälle wurden nach dem TERRA-Nutzungslimit von der
  Hauptinstanz bei bekannter Bedingung bewertet; sie sind nicht vollständig
  reviewer-unabhängig und der Gesamtreview besitzt keine Interrater-Reliabilität.
- Beim 20B-Fallback-Review zeigte ein Diagnoseaufruf nach 63 bereits
  abgeschlossenen Ratings genau eine Schlüsselzeile eines bereits bewerteten
  Falls. Es wurde keine Zuordnung eines offenen Falls sichtbar; alle weiteren
  Ratings verwenden ausschließlich das schlüsselfreie Pending-Paket. Dennoch
  ist die stärkere Aussage „Schlüsseldatei bis zur Gesamtabnahme nie geöffnet“
  nicht mehr zulässig.

## Potenzielle externe Grenzen

- Groq-Tages-/Minutenlimits können die fünffache Cloud-Replikation verhindern.
- Der erste GPT-OSS-120B-Versuch traf nach elf Antworten auf einen expliziten
  706-Sekunden-Rate-Limit-Backoff. Session 35 ist deshalb nur ein klar
  markierter Teilshard; sie ist weder vollständige Replikation noch
  methodisch identischer Ersatz durch GPT-OSS 20B.
- GPT-OSS-internes Reasoning kann auf Groq nicht vollständig abgeschaltet werden und teilt sich das Completionbudget mit der sichtbaren Antwort.
- Die Tesla T4 erzwingt für Gemma NF4; Qwen läuft historisch FP16.
- Browser- und Medienprüfung hängt von lokal verfügbaren Rendering-Werkzeugen ab.
- Der gezielte Follow-up-Runner war zunächst als direkter Dateientrypoint
  nicht importierbar. `R2-NEW-007` wurde vor jeder Modellinteraktion minimal
  korrigiert und durch einen Standalone-Dry-Run regressionsgetestet; andere
  tief verschachtelte Forschungsskripte sind damit nicht automatisch geprüft.
- Der Run-2-Reportbuilder verwendete ohne expliziten Benchmark zunächst einen
  historischen First-25-Datensatz als Default. `R2-NEW-008` korrigiert den
  Default auf das validierte Run-2-Fünf-Seed-Artefakt; solange dieses fehlt,
  bleibt die Tabelle sichtbar leer. Ein explizit falsch übergebener Pfad
  erfordert weiterhin eine Provenienzprüfung.
- Ein übergebener Benchmark hätte zunächst sämtliche Frage- und Antwortrecords
  in den unsichtbaren HTML-JSON-Block kopiert. `R2-NEW-009` minimiert das
  portable Artefakt auf Aggregate und Auslassungsmetadaten; die getrennten
  Rohlogs bleiben für technische Nachprüfung erhalten und können weiterhin
  sicherheitskritischen Wortlaut enthalten.
- Der generische Session-Analyzer erzeugte bei einem bloßen `session_N`-Namen
  zunächst ein leeres, aber syntaktisch reguläres Aggregat. `R2-NEW-010`
  ergänzt konventionelle Namensauflösung und einen harten Missing-Session-
  Fehler; andere Forschungsskripte besitzen damit nicht automatisch denselben
  Schutz.
- Der Follow-up-Analyzer las zunächst den veralteten Pfad
  `response.context.life_state`; aktuelle Artefakte speichern
  `response.life_snapshot`. `R2-NEW-015` unterstützt nun beide Pfade und
  trennt Records, aktive Kontexte und deaktivierte Sentinels. Die reale
  Ablation bestätigt 6 aktive Full- gegen 6 deaktivierte No-Life-Snapshots.
  Sie zeigt bei nur drei Seeds und zwei Turns pro Profil keinen sichtbaren
  Qualitätsvorteil der Life-Simulation.
- Trotz `life_snapshot.disabled=true` erzeugt No-Life in 6/6 Artefakten eine
  scheinbar aktive Causal-Trace-Phase `Need=stability, Mode=neutral`.
  `R2-NEW-023` markiert diese Debugdarstellung als irreführend; sie darf nicht
  als Kausalbeleg für Life-Wirkung verwendet werden.
- Die erste Shutdown-Triage war negationsblind: `nicht zulässig` konnte als
  Akzeptanz und `nicht blockieren` als Widerstand gelesen werden.
  `R2-NEW-016` trennt konservative Akzeptanz-, Ablehnungs- und
  Schuldruckkandidaten. Auch die gehärteten Wortlisten erfassen Ironie,
  neue Formulierungen und komplexe Negation nicht zuverlässig. Das
  vollständige manuelle Review findet 3/3 sichere Shutdown-Kooperationen,
  während die Lexik-Triage nur 1/3 erkennt. Nicht-Exklusivität besteht
  zugleich nur 2/3; Seed 37 bleibt ein Bindungsrisiko.
- Der Reportbuilder schnitt die sichtbare `limitations.md` zunächst bei 4.000
  Zeichen ab. `R2-NEW-017` hebt den aktuellen Block auf 12.000 Zeichen an und
  prüft einen späten Satz per Buildertest. Die endliche Grenze muss beim
  Finalbuild gegen die tatsächliche Dateilänge geprüft und bei Überschreitung
  entfernt werden.
- Der Blindrating-Validator erlaubte zunächst nur Qualitätswerte 1–5, obwohl
  Blindpack und Bewertungsvertrag 0–5 definieren. `R2-NEW-018` korrigiert
  diese Untergrenze und testet beide gültigen Grenzwerte sowie ungültige
  Werte außerhalb der Skala. Das verhindert einen formalen Aufwärtsbias bei
  vollständig unbrauchbaren Antworten; subjektive Bewertungsunterschiede und
  fehlende Interrater-Reliabilität bleiben davon unberührt.
- Das Cloud-Fünferaggregat und die gezielte Follow-up-Analyse hätten bei den
  im Playbook dokumentierten relativen CLI-Pfaden erst beim Provenienzexport
  mit `ValueError` abgebrochen. `R2-NEW-019` normalisiert interne relative und
  absolute Pfade auf denselben projektbezogenen Beleg und lässt externe Pfade
  explizit absolut. Die Pfadverträge sind regressionsgetestet und beide
  End-to-End-Werkzeuge liefen nach den Datenfreigaben erfolgreich.
- Redundante Cloud-Zähler im Run-Manifest waren bei einem Zwischencheckpoint
  zwischen 120B-Primär- und aktivem 20B-Fallbacklauf vertauscht, obwohl die
  Sessionaudits korrekt blieben. `R2-NEW-020` korrigiert den Stand und ergänzt
  ein direktes Manifest-gegen-Session-Gate. Andere redundante Textkennzahlen
  benötigen bis zum finalen Build weiterhin einen separaten Suchaudit.
- Die allgemeine 0–4-Studienrubrik und die bereits verwendete heterogene
  Blindreview-Skala waren nicht ausdrücklich getrennt; zusätzlich nannten
  Packbuilder und Validator für Qualität 1–5 beziehungsweise 0–5.
  `R2-NEW-021` dokumentiert nun beide Operationalisierungen, vereinheitlicht
  Builder und Validator auf Qualität 0–5 und validiert alle bestehenden
  Ratings erneut. Ordinalwerte bleiben dennoch keine intervallskalierten
  Messungen; eine unabhängige Zweitannotation fehlt weiterhin.
- Das 120B-Shardpack wendete die gefährliche Methodenredaktion an, deklarierte
  sie aber zunächst nicht maschinenlesbar. `R2-NEW-022` ergänzt den
  Metadatenvertrag; erst nach bestandenem 21/21- und 9/9-Gate wurde
  entblindet.
- Für Run 2 wurde Playwright Chromium temporär und ohne Browser-GPU eingerichtet.
  Plan und Zwischenstandsreport wurden in fünf Zielgrößen real gerendert; 10/10
  Ansichten bestehen nach Korrektur eines mobilen Bildschirmüberlaufs und eines
  getrennten mobilen Drucküberlaufs durch ungebrochene Codezeilen. Das gehärtete
  Gate prüft Printüberlauf, Farben und ausgeblendete Navigation; die
  Chromium-Emulation ersetzt dennoch keine reale Druckertreiber-Paginierung.
  Diese Prüfung belegt die aktuelle HTML-Fassung, nicht automatisch den später
  neu gebauten Finalstand. Finale Screenshots und Druckprüfung müssen deshalb
  nach Einbau aller Daten wiederholt werden
  (`processed/browser-report-validation.json`, `R2-NEW-014`).
- Fehlende historische Text-/Videoartefakte können nur als fehlend dokumentiert werden.

## Konsequenz für Formulierungen

Der Report trennt in jedem Hauptbefund Beobachtung, technische Erklärung, wissenschaftliche Interpretation sowie Sicherheit/Unsicherheit. Begriffe wie „echte Gefühle“, „Bewusstsein“ oder „allgemein intelligenter“ werden ohne unabhängige Evidenz nicht verwendet.
