
# CHAPPiE – Gesamtplan für Repository-Cleanup, Architektur-Migration und Forschungsbericht v6

**Dokumenttyp:** Umsetzungsplan für einen Coding-Agenten  
**Status:** Planung; in diesem Arbeitsschritt werden keine produktiven Codeänderungen ausgeführt  
**Geltungsbereich:** gesamtes Repository /home/bbecker/projects/CHAPPiE  
**Ziel:** eine aufgeräumte, verständliche, präsentierbare und funktional rückwärtskompatible Codebasis

---

## 1. Auftrag und Leitgedanke

Das gesamte CHAPPiE-Repository soll schrittweise bereinigt und für die Vorstellung beziehungsweise Abgabe des Forschungsprojekts vorbereitet werden.

Die zentrale technische Realität, von der bei der Umsetzung auszugehen ist:

- Die aktuell verwendete Antwortverarbeitung läuft über web_infrastructure/backend_wrapper.py.
- Die frühere Brain-Pipeline in brain/brain_pipeline.py war der erste Architekturversuch und ist kein aktiver Produktionspfad mehr.
- Die spezialisierten Module unter brain/agents/ sind zum großen Teil Bestandteile dieses ersten Versuches beziehungsweise Test- und Forschungscode.
- Die aktuelle lokale, zweistufige Verarbeitung funktioniert grundsätzlich und soll funktional erhalten bleiben.
- Der große Backend-Wrapper soll in nachvollziehbare Module zerlegt und als saubere, gut erklärbare Runtime-Architektur verpackt werden.
- Nicht mehr verwendeter Code soll nicht still verschwinden. Er soll als Legacy-Code klar gekennzeichnet, dokumentiert und bei Bedarf nachvollziehbar aufbewahrt werden.
- Der Forschungsbericht v5 bleibt unverändert erhalten. Daraus wird eine v6-Kopie erstellt, die die neue Architektur, die Legacy-Abgrenzung und die aktuelle Code-Evidenz beschreibt.
- Tests, Dokumentation, Konfiguration, Skills, CI, Deployment-Dateien und Frontend gehören ausdrücklich zum Cleanup. Es handelt sich nicht nur um ein Refactoring der Wrapper-Datei.

Die wichtigste Einschränkung lautet:

> Funktionalität, öffentliche API-Verträge, persistierte Daten, Nutzerverhalten und externe Integrationen dürfen sich durch das Aufräumen nicht unbemerkt ändern.

Eine Änderung ist nur dann zulässig, wenn sie entweder intern bleibt oder vorher als bewusst entschiedene Migration mit Auswirkung, Test und Rückfallmöglichkeit dokumentiert wurde.

---

## 2. Verbindliche Arbeitsregeln für den Coding-Agenten

### 2.1 Vor jedem Umsetzungsschritt

1. AGENTS.md vollständig lesen und befolgen.
2. Den Skill repo-kennenlernen verwenden, um Root-Struktur, Entrypoints, Config, Abhängigkeiten und Build-/Testsystem erneut zu verifizieren.
3. Diesen Plan als aktive Arbeitsgrundlage übernehmen und eine laufende To-do-Liste führen.
4. Das vorhandene Goal-Tracking verwenden:
   - Falls im Harness ein goal-Skill verfügbar ist, diesen vor der Umsetzung verwenden.
   - Falls kein eigenständiger goal-Skill vorhanden ist, das eingebaute Goal-Tracking mit create_goal, get_goal und update_goal nutzen.
   - Das Goal muss das Gesamtziel, die aktuellen Phasen, Blocker und den Abschlussstatus abbilden.
   - Das Goal erst dann als erreicht markieren, wenn Tests, Dokumentation, Bericht v6 und Abschlussprüfung tatsächlich erledigt sind.
5. Vor Änderungen den Git-Status, den aktuellen Branch und den Ausgangszustand der betroffenen Dateien dokumentieren.
6. Niemals destruktive Git-Befehle wie git reset --hard oder git checkout -- verwenden.
7. Bestehende Nutzeränderungen im Arbeitsbaum bewahren und nicht überschreiben.
8. Keine laufenden Nutzer-Preview-Dienste, Slots, Sessions oder Ports verändern. Für Verifikation gegebenenfalls einen eigenen Dienst auf einem freien Port verwenden.

### 2.2 Verbindliche Skills

Die Skills sind nicht nur am Ende zu erwähnen, sondern an den passenden Phasen tatsächlich zu verwenden.

Pflicht beziehungsweise direkt relevant:

- sprachstil: für kurze, klare Statusmeldungen, Rückfragen und Abschlussberichte.
- repo-kennenlernen: vor der Strukturmigration und bei der finalen Strukturprüfung.
- plan-like-a-pro: für die planorientierte Durchführung, Ist-Zustand, Risiken, Teststrategie, Rollback und Definition of Done.
- chappie-backend: bei der Zerlegung von backend_wrapper.py, API-/vLLM-/Provider-Themen und Backend-Tests.
- chappie-architecture: bei Brain-, Memory-, Life-, Steering- und Global-Workspace-Grenzen.
- chappie-config: bei allen Änderungen an Config, Config-Schemas, Provider-Einstellungen und Konfigurationsdokumentation.
- config-infos: damit globale Konfiguration zentral bleibt und keine neue verteilte Konfigurationslogik entsteht.
- chappie-testing: beim Erweitern und Ausführen der standalone Tests, beim CI-Umbau und bei der Teststrategie.
- versionierungen: nach fachlichen Meilensteinen und zwingend vor jedem Commit/Push; CHANGELOG, sichtbare Versionen und gegebenenfalls Storage-Versionen synchron halten.
- github-infos: für jede GitHub-Operation und insbesondere vor Commit, Branch-Operation, Push oder CI-Prüfung.
- commit-and-push-workflow-xxl: ausschließlich als abschließender Veröffentlichungsworkflow, nachdem der Nutzer den Commit/Push ausdrücklich freigegeben hat.
- security-audit: vor der Freigabe, wenn API-, Deployment-, Secret-, CORS- oder Authentifizierungsdateien verändert wurden.
- design-system-guide und mobile-design: nur wenn beim Frontend-Cleanup tatsächlich sichtbare UI- oder Layoutänderungen vorgenommen werden.
- versionierungen: zusätzlich bei einer sichtbaren Dokument-, UI- oder Projektversionierung des Berichts beziehungsweise der Anwendung.

Wichtig:

- tiefgehender-projekt-audit darf nicht automatisch verwendet werden, weil er nur bei ausdrücklicher Anforderung aktiviert werden soll. Dieser Plan enthält bereits die notwendigen Audit-Arbeitspakete. Nur verwenden, wenn der Nutzer ihn separat ausdrücklich anfordert.
- Keine neuen Skills erfinden. Falls ein genannter Skill im aktuellen Harness nicht verfügbar ist, im Status transparent vermerken und die nächstbeste vorhandene Regel anwenden.
- Keine Sub-Agents einsetzen, solange der Nutzer dies nicht ausdrücklich verlangt.

### 2.3 Commit- und Push-Grenze

In den Phasen dieses Plans dürfen lokale Dateien geändert, getestet und dokumentiert werden. Ein Commit oder Push ist jedoch nicht automatisch erlaubt.

Vor dem ersten Commit:

1. Nutzerfreigabe einholen, sofern sie nicht bereits ausdrücklich für diesen konkreten Arbeitsstand erteilt wurde.
2. github-infos lesen und anwenden.
3. versionierungen ausführen und CHANGELOG/Versionen prüfen.
4. git status, git diff, Branch und Remote prüfen.

Nach ausdrücklicher Freigabe soll der vollständige commit-and-push-workflow-xxl verwendet werden. Dieser Workflow umfasst:

- alle Änderungen und ungewollten Artefakte prüfen,
- Änderungen in logisch getrennte Commits aufteilen,
- lokale Tests und CI-relevante Prüfungen ausführen,
- Dokumentation und Changelog kontrollieren,
- mit kurzen imperativen Conventional-Commit-Nachrichten arbeiten,
- erst danach pushen,
- GitHub-CI beobachten,
- gemeldete Fehler iterativ beheben,
- bis die CI grün ist oder ein konkret dokumentierter externer Blocker vorliegt.

Die KI darf im Rahmen dieses Plans keinen Push selbstständig ausführen, solange die ausdrückliche Freigabe fehlt.

---

## 3. Ziele, Nichtziele und Erfolgskriterien

### 3.1 Ziele

- Aktiven Produktionscode und historische Versuche klar trennen.
- Den 4.000+-Zeilen-Wrapper in verständliche Verantwortungsbereiche zerlegen.
- Den aktiven Runtime-Pfad für neue Leser erklärbar machen.
- Synchronen und gestreamten Chatpfad möglichst aus gemeinsamer Logik ableiten.
- Öffentliche Entrypoints und Antwortverträge kompatibel halten.
- Die Brain-Pipeline v1 archivieren, statt sie als parallel aktive Architektur erscheinen zu lassen.
- Nur nachgewiesen ungenutzten Code entfernen.
- Tests gegen Verhaltensregressionen ausbauen.
- Konfiguration und Prompts zentralisieren.
- Frontend-, API-, Trainings-, Memory-, Life-, Forschungs- und Deployment-Teile in denselben Qualitätsrahmen einbeziehen.
- Bericht v5 unverändert bewahren und Bericht v6 mit überprüfbarer aktueller Architektur-Evidenz erstellen.
- Skills und Dokumentation an den tatsächlichen Ist-Zustand angleichen.
- Wiederholbare CI- und Repository-Hygieneprüfungen etablieren.

### 3.2 Nichtziele

Folgende Vorhaben gehören nicht automatisch in dieses Cleanup:

- ein Wechsel des LLM-Modells,
- eine Änderung der Provider-Priorität,
- eine Neugestaltung des Brain-Konzepts,
- eine Änderung von Emotionsmodell, Memory-Semantik oder Life-Simulation,
- eine neue UI-Funktion,
- eine Datenbankmigration,
- ein Umbau der Forschungsversuchsdaten,
- eine komplette Neuschreibung des Systems,
- eine Optimierung nur nach subjektiv schönerem Code,
- das Löschen von Forschungsartefakten, nur weil sie groß oder alt aussehen.

Wenn während des Refactorings ein solcher Punkt notwendig erscheint, als separates Risiko beziehungsweise Änderungsentscheid dokumentieren und nicht still in den Cleanup aufnehmen.

### 3.3 Definition von Erfolg

Der Cleanup ist erst abgeschlossen, wenn:

- der aktive Requestpfad über eine kleine, gut benannte Runtime-Fassade läuft;
- der bisherige Factory-/Importvertrag kompatibel bleibt oder bewusst migriert und getestet wurde;
- synchroner und gestreamter Chat denselben fachlichen Verarbeitungskern verwenden;
- der alte Brain-Pipeline-Pfad nicht mehr als aktiv dokumentiert wird;
- aktive Steering-Funktionalität nicht versehentlich mit den alten Agents archiviert wurde;
- Legacy-Code einen eigenen Einstieg, README, Herkunft, Grund der Ablösung und Status besitzt;
- v5 unverändert und nachweisbar erhalten ist;
- v6 gebaut, validiert und mit aktueller Architektur sowie Legacy-Erklärung versehen ist;
- keine nicht belegten Löschungen oder fehlenden Importe vorliegen;
- der relevante Testbestand reproduzierbar läuft;
- CI nicht mehr relevante Prüfungen still verschluckt;
- aktive Dokumentation und Skills denselben Architekturstand beschreiben;
- generierte Dateien, temporäre Logs und falsche Build-Artefakte nicht mehr als Quellcode getrackt werden;
- Versionierung und CHANGELOG korrekt sind;
- der Nutzer den abschließenden Commit-/Push-Workflow freigegeben hat und dessen Ergebnis dokumentiert ist.

---

## 4. Verifizierter Ausgangszustand

Dieser Abschnitt dient dem Coding-Agenten als Ausgangshypothese. Vor der Umsetzung muss er mit aktuellen Befehlen erneut geprüft und bei Abweichungen angepasst werden.

### 4.1 Repository-Größe und Forschungsbestand

- Das Repository enthält ungefähr 3.176 getrackte Dateien.
- forschung/ enthält ungefähr 2.906 getrackte Dateien.
- Darunter befinden sich ungefähr 2.253 Session-Logs, 574 Run-Artefakte und 69 Report-Dateien.
- Diese Dateien sind überwiegend Forschungs- und Evidenzdaten und nicht automatisch toter Code.
- Forschungsdaten dürfen nicht pauschal in Legacy-Code/ verschoben oder gelöscht werden.
- Stattdessen braucht forschung/ eine klare Indexierung und Klassifizierung zwischen:
  - reproduzierbarer aktueller Harness-/Tooling-Code,
  - eingefrorenen Versuchsdaten,
  - historischen Berichten,
  - Arbeitsnotizen und Entwürfen,
  - temporären oder versehentlich getrackten Artefakten.

### 4.2 Aktiver Backend-Pfad

Der derzeitige Hauptpfad ist sinngemäß:

    API-Router / CLI / Forschungs-Harness
        -> create_chappie_backend()
        -> CHAPPiEBackend
        -> process() oder process_stream()
        -> Life-Vorbereitung
        -> Intent-/Tool-/Emotion-/Memory-Verarbeitung
        -> Short-Term-Memory und Kontext
        -> Global Workspace beziehungsweise Arbeitskontext
        -> Prompt-Erstellung
        -> lokale vLLM-Generierung mit Steering
        -> Parsing, Sanitizing und lokale Formatierung
        -> Life-Abschluss, Persistenz und Sleep-/Session-Verarbeitung

Zu den relevanten Stellen in web_infrastructure/backend_wrapper.py gehören derzeit ungefähr:

- die Factory create_chappie_backend,
- die verschachtelt definierte Klasse CHAPPiEBackend,
- process,
- _process_two_step,
- _process_legacy,
- _process_legacy_stream,
- _extract_legacy_generation,
- process_stream,
- _process_two_step_stream.

Die genaue Zeilennummer darf im Plan nicht als dauerhafte API-Dokumentation verwendet werden, da sie sich beim Refactoring ändert. Code-Evidenz soll über Dateipfad, Symbolname, Commit-Hash und Hash-/Manifestdaten referenziert werden.

Auffälligkeiten:

- Die Klasse ist aktuell innerhalb der Factory verschachtelt. Das erschwert Imports, Typisierung, Tests und Präsentation.
- Die Datei ist über 4.000 Zeilen groß und mischt Orchestrierung, Provider-Aufruf, Prompt-/Kontextaufbereitung, Streaming, Formatierung, Persistenz und historische Pfade.
- CHAT_PROVIDER ist im Wrapper auf vLLM festgelegt. Die sichtbare Konfiguration kann teilweise einen Provider anzeigen, der vom tatsächlichen Web-Requestpfad abweicht. Das muss dokumentiert und technisch eindeutig gemacht werden, ohne unbemerkt Verhalten zu ändern.
- settings.enable_two_step_processing ist persistiert und UI-sichtbar, entscheidet den aktuellen Requestpfad aber nicht zuverlässig. Diese Diskrepanz darf nicht still durch eine Entfernung oder neue Semantik verändert werden.

### 4.3 Brain und Agents

- brain/brain_pipeline.py beschreibt selbst einen Legacy-/historischen Pipeline-Versuch.
- Die Datei wird nicht durch den normalen Produktionspfad verwendet.
- Direkte Instanziierung kommt vor allem in Tests, manuellen Tests oder historischen Research-Pfaden vor.
- brain/agents/ enthält mehrere spezialisierte alte Agenten und einen alten BrainOrchestrator.
- brain/agents/steering_manager.py ist dagegen fachlich aktiv beziehungsweise wird vom aktuellen vLLM-/Steering-Pfad benötigt.
- brain/agents/__init__.py importiert derzeit viele alte Agenten eager. Dadurch können historische Agenten schon beim Import von brain.agents.steering_manager geladen werden.
- Deshalb darf brain/agents/ nicht als kompletter Ordner blind verschoben werden.

Aktiv zu prüfen und grundsätzlich zu erhalten sind unter anderem:

- brain/global_workspace.py,
- brain/action_response.py,
- brain/deep_think.py,
- brain/steering_backend.py,
- brain/vllm_brain.py,
- brain/ollama_brain.py,
- brain/groq_brain.py,
- brain/response_parser.py,
- aktive Memory-, Life- und Trainingsmodule.

### 4.4 Tests und Werkzeugstatus

Der Projektleitfaden definiert standalone Tests, nicht pytest:

- Einzeltests werden mit python tests/test_foo.py ausgeführt.
- CI nutzt einen begrenzten Satz schneller Tests.
- Erweiterte Tests sind teilweise als nicht blockierend markiert.
- Live-/integrationsnahe Tests benötigen externe Dienste und dürfen nicht unkontrolliert in Offline-CI laufen.
- Manuelle Tests liegen in tests/manual/.

Zum dokumentierten Ausgangsstand gehören:

- python -m compileall für die relevanten Python-Bereiche lief erfolgreich.
- Mehrere schnelle Logik-, Forschungs-, Config-, UI- und Formatierungstests liefen erfolgreich.
- tests/test_api_contract.py war lokal wegen fehlendem FastAPI-Modul nicht reproduzierbar. Die Umgebung beziehungsweise Dependency-Gruppierung muss sauber beschrieben werden.
- Eine Ruff-Bestandsprüfung meldete ungefähr 176 Befunde außerhalb von Forschungs-Runs, Archiv- und Testausschlüssen:
  - ungenutzte Imports,
  - f-Strings ohne Platzhalter,
  - Imports nicht am Dateianfang,
  - ungenutzte Variablen,
  - Lambda-Zuweisungen und weitere Stil-/Syntaxbefunde.
- Eine Mypy-Bestandsprüfung meldete ungefähr 135 Fehler in ungefähr 25 Dateien. Dazu zählen optionale Typen, Union-/Dict-Probleme, doppelte Definitionen, falsche Provider-Namen und nicht definierte historische Variablen.
- Der direkte Frontend-TypeScript-Check mit der lokalen Compiler-Version lief erfolgreich. Die Toolchain muss dennoch gepinnt und reproduzierbar gemacht werden.
- Es existiert kein vollständiger Frontend-Test-/Lint-Skriptbestand; aktuell wird vor allem der Build geprüft.

Diese Befunde sind eine Baseline, keine Erlaubnis für blinde Massenreparaturen. Vor jeder Bereinigung muss zwischen echtem Fehler, bewusstem dynamischem Code, historischem Code und Test-/Forschungscode unterschieden werden.

### 4.5 Versionen

Aktuell existieren mindestens mehrere Versionierungsquellen:

- Frontend-Version ungefähr 16.3.0,
- CHANGELOG-Version ungefähr 16.3.0,
- API-Version ungefähr 16.3.0,
- UI-Version in web_infrastructure/ui_utils.py ungefähr 14.0,
- separate Steering-Service-Version 1.0.0,
- separates Steering-Payload-/Kompatibilitätsfeld mit eigener Versionsbedeutung.

Diese Werte dürfen nicht pauschal auf eine Zahl zusammengezogen werden. Zuerst festlegen:

1. Welche Version ist die Produkt-/Release-Version?
2. Welche Versionen sind API-, Service-, Payload- oder Datenformatversionen?
3. Welche Werte müssen synchron sein?
4. Welche Werte dürfen unabhängig bleiben?
5. Wie wird ein Drift künftig automatisiert erkannt?

Für einen reinen rückwärtskompatiblen Cleanup ist grundsätzlich ein Minor-Schritt wie 16.4.0 plausibel. Das ist erst nach der tatsächlichen Änderungsbilanz zu entscheiden.

---

## 5. Architekturprinzipien für das Zielsystem

### 5.1 Ein öffentlicher Runtime-Einstieg

Die aktuelle Implementierung soll unter einem verständlicheren Namen sichtbar werden, beispielsweise:

    web_infrastructure/chappie_runtime.py

Dort liegt eine auf Modulebene definierte öffentliche Runtime-Fassade, beispielsweise CHAPPiERuntime. Der konkrete Name ist vor der Umsetzung anhand bestehender Importe und Berichtssprache final zu entscheiden.

Der bisherige Pfad bleibt zunächst als Kompatibilitätsschicht bestehen:

    web_infrastructure/backend_wrapper.py

Diese Datei soll danach nur noch:

- die kompatiblen Factory-Funktionen exportieren,
- die neue Runtime-Fassade re-exportieren beziehungsweise aliasen,
- gegebenenfalls kurze Deprecation-Hinweise enthalten,
- keine eigene fachliche Pipeline mehr implementieren.

Bestehende Aufrufer wie create_chappie_backend() und init_chappie() müssen zunächst weiter funktionieren. Ein Umbenennen darf nicht gleichzeitig ein ungetestetes API-Breaking-Change sein.

### 5.2 Verantwortungsbereiche

Eine sinnvolle Zielaufteilung ist:

    web_infrastructure/
    ├── chappie_runtime.py
    ├── turn_pipeline.py
    ├── turn_context.py
    ├── contracts.py
    ├── generation.py
    ├── persistence.py
    ├── formatting.py
    └── backend_wrapper.py

Die Namen sind Vorschläge und dürfen nach dem Importgraphen angepasst werden. Es sollen keine Mikrodateien ohne eigene fachliche Verantwortung entstehen.

Verantwortungen:

- chappie_runtime.py
  - öffentliche Fassade,
  - Dependency-/Komponentenaufbau,
  - Lifecycle,
  - Delegation an die Pipeline,
  - keine langen Prompt- oder Providerdetails.

- turn_pipeline.py
  - fachliche Reihenfolge eines Turns,
  - gemeinsame Vorbereitungs- und Abschlusslogik,
  - normaler und Streaming-Aufruf über gemeinsame Zustandsmodelle,
  - Fehler- und Abbruchverhalten.

- turn_context.py
  - typisierter interner Kontext eines Turns,
  - Nachrichten, Sessiondaten, Intent, Emotion, Memory-/Life-Kontext,
  - keine direkte globale Zustandsmutation, wenn sie nicht ausdrücklich vorgesehen ist.

- contracts.py
  - interne typisierte Datenstrukturen,
  - Response-/Event-Verträge,
  - keine Veränderung der externen JSON-Form ohne Migration.

- generation.py
  - vLLM-/Steering-Aufruf,
  - Sampling- und Generationseinstellungen,
  - Provideradapter beziehungsweise klare Delegation,
  - Fehlerklassifizierung.

- persistence.py
  - Speichern von Chat, STM/LTM, Session- und Life-Daten,
  - Sleep-/Finalisierungs-Übergänge,
  - klare Transaktions- oder Rollback-Grenzen.

- formatting.py
  - Parser, Sanitizing und UI-/Chatformatierung nur dort, wo sie zum Backendvertrag gehören,
  - keine unklare Duplizierung von ui_utils.py und api/services/text_formatting.py.

- backend_wrapper.py
  - ausschließlich Legacy-Kompatibilität und öffentliche Re-Exports.

### 5.3 Gemeinsamer Kern für Sync und Streaming

process() und process_stream() dürfen nicht zwei vollständig unabhängige fachliche Implementierungen behalten.

Ziel:

- gemeinsame Turn-Vorbereitung,
- gemeinsamer Intent-/Emotion-/Memory-/Life-Kontext,
- gemeinsamer Prompt- und Generationvertrag,
- unterschiedliche Ausgabeadapter für:
  - fertige Response,
  - SSE-/Streaming-Events,
- gemeinsamer Abschluss und Persistenz,
- eindeutig definierte Abbruchsemantik.

Streaming darf weiterhin andere zeitliche Ereignisse liefern, aber Inhalt, Felder, Fehlerform und Persistenz müssen dem synchronen Vertrag entsprechen.

### 5.4 Grenzen zur Brain-, Memory- und Life-Schicht

Die Runtime orchestriert. Sie soll nicht die gesamte Fachlogik von Brain, Memory und Life duplizieren.

- Brain-Module liefern aktive Modell-/Steering-/Workspace-Funktionen.
- Memory-Module verwalten Memory-Semantik.
- Life-Module verwalten Homeostasis, Goals, Social und Lebenszyklus.
- Die Runtime koordiniert Reihenfolge und Datenfluss.
- Historische BrainPipeline-Logik wird nicht teilweise in die neue Runtime kopiert, wenn sie nicht für den aktuellen Pfad benötigt wird.
- Gemeinsame Begriffe und Verträge werden in kleinen, gut getesteten Modulen definiert.

### 5.5 Keine heimliche Semantikänderung

Insbesondere unverändert prüfen:

- Providerwahl,
- Modell- und Samplingwerte,
- Steering-Layer und Vektoren,
- Emotionsmapping und zehn Emotionen,
- Intent-Erkennung,
- Toolaufrufe,
- Memory-Speicherung,
- Sessionverhalten,
- Life-Simulation und Sleep,
- Response-Felder,
- SSE-Eventnamen und Reihenfolge,
- CLI-Ausgabe,
- Fehlerbehandlung,
- Settings-Reload,
- Trainings- und Forschungsadapter.

Jede beabsichtigte Änderung erhält einen kurzen Änderungsentscheid mit Begründung und Regressionstest.

---

## 6. Legacy-Code-Strategie

### 6.1 Grundregel

Legacy-Code ist Code, der historisch relevant oder für Vergleichbarkeit wertvoll ist, aber nicht Teil des normalen aktiven Produktionspfades sein soll.

Toter Code ist Code, der nach einer vollständigen Aufrufer-, Import-, Test-, Script- und Dokumentationsprüfung keine unterstützte Funktion mehr erfüllt.

Diese Kategorien sind zu trennen:

- Legacy-Code wird verschoben oder eingefroren und dokumentiert.
- Nachgewiesen toter Code darf entfernt werden.
- Unsicherer Code wird zunächst als candidate dokumentiert und erst nach einer Entscheidung verschoben oder gelöscht.
- Forschungsbelege bleiben Forschungsbelege und werden nicht nur wegen ihres Alters als Legacy-Code bezeichnet.

### 6.2 Zielstruktur

Vorgeschlagene Struktur:

    Legacy-Code/
    ├── README.md
    ├── legacy-index.md
    ├── brain-pipeline-v1/
    │   ├── README.md
    │   ├── brain_pipeline.py
    │   ├── agents/
    │   └── tests/
    ├── backend-wrapper-v1/
    │   ├── README.md
    │   ├── source/
    │   └── migration-notes.md
    ├── report-v5-source/
    │   ├── README.md
    │   └── source-snapshot/
    ├── old-reports/
    ├── old-plans/
    └── old-scripts/

Der Ordnername mit Bindestrich ist für eine Ablage geeignet, aber kein Python-Paket. Legacy-Dateien dürfen nicht versehentlich in den aktiven Importpfad gelangen.

### 6.3 Pflichtinhalt von Legacy-Code/README.md

Die README muss enthalten:

- Zweck des Ordners,
- klare Warnung: nicht aktiver Produktionscode,
- Datum beziehungsweise Commit der Archivierung,
- welche Dateien aus welchen aktiven Pfaden stammen,
- warum der erste Versuch nicht als aktueller Requestpfad verwendet wird,
- welche Probleme beobachtet wurden:
  - konkurrierende Orchestrierung,
  - schwer nachvollziehbarer Datenfluss,
  - enge Kopplung,
  - doppelte beziehungsweise divergierende Sync-/Stream-Logik,
  - schwierige Tests,
  - unnötige eager Imports,
  - unklare Provider-/Konfigurationsgrenzen,
  - schlechte Präsentierbarkeit bei großer monolithischer Datei,
- welche Teile konzeptionell weiterhin wichtig sind,
- welche aktiven Nachfolger die Verantwortungen übernommen haben,
- wie der historische Code nur zu Forschungs- und Vergleichszwecken gelesen wird,
- dass Änderungen im Legacy-Ordner nicht automatisch Produktionsverhalten beeinflussen,
- Links zum aktuellen Architektur-Dokument, README und Bericht v6.

Jedes Unterverzeichnis erhält eine eigene README mit Herkunft, Status, Abhängigkeiten, nicht unterstütztem Ausführungsstatus und Nachfolger.

### 6.4 Sonderfall brain/agents

Nicht den kompletten Ordner verschieben.

Vorgehen:

1. Import- und Referenzgraph aller Agent-Dateien erstellen.
2. Aktive Steering-Funktionalität isolieren.
3. Aktiven SteeringManager in ein aktives Modul, beispielsweise brain/steering_manager.py, verschieben.
4. brain/agents/steering_manager.py zunächst als kompatiblen Re-Export erhalten.
5. brain/agents/__init__.py auf minimale beziehungsweise lazy Exporte reduzieren.
6. Erst danach alte Agenten und BrainOrchestrator nach Legacy-Code/brain-pipeline-v1/agents/ verschieben.
7. Tests sicherstellen, dass der Runtime-Import keine historischen Agenten mehr eager lädt.
8. Falls historische Tests die alten Agenten noch benötigen, ihre Pfade explizit auf Legacy beziehungsweise manuelle Forschungstests umstellen.

### 6.5 Konkrete Legacy-/Dead-Code-Kandidaten

Jeder Kandidat benötigt vor einer Entscheidung eine Checkliste:

- alle Python- und Frontend-Referenzen mit rg finden,
- dynamische Imports und CLI-Aufrufe prüfen,
- systemd-, Shell- und CI-Verwendungen prüfen,
- README-/Report-/Skill-Verwendungen klassifizieren,
- Tests und manuelle Tests prüfen,
- Ersatz oder Nachfolger benennen,
- Test vor und nach der Änderung ausführen,
- Löschung oder Archivierung im Changelog dokumentieren.

Zu prüfen sind insbesondere:

- brain/brain_pipeline.py und die damit verbundenen alten Agents,
- historische Agenten und alter BrainOrchestrator,
- _process_legacy, _process_legacy_stream und _extract_legacy_generation im Wrapper,
- start_async_chat, _run_chat_job und is_chat_job_active; vor Löschung klären, ob externe oder geplante Aufrufer existieren,
- _shrink_message_to_fit und _estimate_msg_tokens; bisher keine produktiven Python-Aufrufer gefunden,
- web_infrastructure/ui_utils.py und api/services/text_formatting.py; aktuell überwiegend beziehungsweise ausschließlich durch Tests referenziert, daher vor Entfernung den Vertrag entscheiden,
- config/APIs/__init__.py, das sich selbst als altes Schlüsselpaket beschreibt,
- veraltete Cerebras-Mocks und Providerreferenzen in Tests,
- Root-package.json und package-lock.json, die offenbar nur eine künstliche python3-Abhängigkeit enthalten; erst nach globaler Referenzprüfung entfernen,
- autonomy.sh mit hartcodiertem altem Pfad /home/bbecker/CHAPPiE,
- alte Pläne und historische Ordner mit unklarer Schreibweise wie Planing_and_Ideas,
- alte Reports und Entwürfe erst nach Link- und Forschungsprovenienzprüfung,
- alte Scripts, sofern sie nicht in Deployment, Forschung, Backup, Setup oder CI benötigt werden.

### 6.6 Getrackte Artefakte und temporäre Dateien

Folgende Dateien sind als Hygiene-Kandidaten zu prüfen:

- backend-test.err,
- leere oder temporäre frontend-test.err,
- orbit-browser-*.ts,
- telemetry-id,
- frontend/tsconfig.app.tsbuildinfo,
- frontend/tsconfig.node.tsbuildinfo,
- generierte frontend/vite.config.js,
- generierte frontend/vite.config.d.ts,
- generierte frontend/tailwind.config.d.ts.

Die Quelltypdatei frontend/src/vite-env.d.ts ist davon zu unterscheiden und bleibt erhalten, sofern sie benötigt wird.

Vorgehen:

- Herkunft und Entstehungsprozess jedes Artefakts prüfen,
- notwendige Artefakte in .gitignore aufnehmen,
- bereits getrackte nicht benötigte Artefakte kontrolliert entfernen,
- keine Nutzdaten oder Forschungsbelege löschen,
- im Abschlussbericht exakt nennen, was entfernt wurde und ob es aus Build-/Testprozessen wieder erzeugt werden kann.

---

## 7. API-, CLI- und Vertragsmigration

### 7.1 Öffentliche Verträge erfassen

Vor dem Refactoring eine Vertragsmatrix anlegen:

| Oberfläche | Aktueller Einstieg | Vertrag |
|---|---|---|
| FastAPI Chat | api/routers/chat.py | Request-Schema, JSON-Felder, Fehler, Statuscodes |
| FastAPI Streaming | api/routers/chat.py | SSE-Eventnamen, Reihenfolge, Datenfelder, Abschluss |
| CLI lokal | chappie_brain_cli.py | Argumente, Ausgabe, Exit-Codes |
| CLI remote | chappie_brain_cli.py --remote | Remote-URL, Auth-/Fehlerverhalten |
| Research Harness | forschung/ | Input-/Output-Dateien, Metadaten, Reproduzierbarkeit |
| Training | Chappies_Trainingspartner/ | Daemon-Einstieg, Konfigurations- und Laufverträge |
| Frontend API | frontend/src/services/api.ts | JSON-/SSE-Parsing, Fehler und Typen |
| Provideradapter | vLLM/Ollama/Groq | Antwortform, Fallback und Fehlersemantik |

Die Matrix muss im Projekt dokumentiert oder in einen passenden Architektur-/API-Abschnitt integriert werden.

### 7.2 Router nicht an private Wrapperdetails koppeln

api/routers/chat.py greift derzeit teilweise direkt auf private Wrapper-Helfer zu. Ziel:

- Router benutzen die öffentliche Runtime-Fassade oder einen klaren Chat-Service.
- Private Hilfsmethoden bleiben innerhalb der zuständigen Runtime-/Pipeline-Module.
- Keine fachliche Logik aus dem Router in die neue Modulstruktur verschieben, wenn sie dort nicht hingehört.
- JSON- und SSE-Verträge über Tests absichern.
- Änderungen an extern sichtbaren Namen nur als explizite, dokumentierte Migration.

### 7.3 Factory-Kompatibilität

Mindestens vorübergehend erhalten:

- create_chappie_backend,
- init_chappie,
- alle nachweislich extern importierten Wrapper-Symbole,
- erwartete Attribute oder Methoden, sofern sie von API, CLI, Training oder Forschung benutzt werden.

Die verschachtelte Klasse soll auf Modulebene liegen. Ein Alias oder Re-Export stellt sicher, dass alte Imports nicht ohne Warnung brechen.

### 7.4 Providersemantik

Die aktuelle Web-Runtime verwendet bevorzugt beziehungsweise fest vLLM. Ollama und Groq bleiben aktiv, wenn sie durch Factory, Training, CLI, Tests oder Research genutzt werden.

Daher:

- alle Provideraufrufe und tatsächlichen Aufrufer inventarisieren,
- keine Provideradapter nur wegen geringer Nutzung löschen,
- vLLM als aktuellen Hauptpfad dokumentieren,
- Ollama/Groq als unterstützte Neben-/Fallbackpfade dokumentieren, falls ihre Verträge noch gelten,
- alte Cerebras-Bezüge aus aktivem Code, Tests, README und Skills entfernen oder ausdrücklich als historische Information kennzeichnen,
- Konfigurationsanzeige und tatsächlich verwendeten Provider nicht widersprüchlich darstellen,
- eine Änderung der Fallback-Reihenfolge ausdrücklich als Funktionsänderung behandeln.

---

## 8. Detailplan für die Zerlegung des Backend-Wrappers

### Phase A – Bestand schützen

Vor der ersten strukturellen Änderung:

1. Alle öffentlichen Symbole und Aufrufer des Wrappers mit rg erfassen.
2. Sync- und Streaming-Responses mit Fake-Providern aufzeichnen.
3. Für deterministische Inputs Response-Shape, Eventfolge und Persistenz-Sideeffects festhalten.
4. Fehlerfälle und Abbrüche aufzeichnen.
5. Testfixtures für:
   - einfache Nachricht,
   - neue Session,
   - bestehende Session,
   - Intent mit Tool,
   - Emotion,
   - Memory-Kontext,
   - Life-State,
   - vLLM-Erfolg,
   - vLLM-Fehler,
   - Streaming-Abbruch,
   - ungültige oder unvollständige Providerantwort
   erstellen.
6. Keine exakten zufälligen Modelltexte als alleinige Regressionserwartung verwenden. Stattdessen Provider faken und deterministische Zwischenverträge prüfen.

### Phase B – Klasse und Abhängigkeiten entkoppeln

1. Die verschachtelte CHAPPiEBackend-Klasse auf Modulebene verschieben.
2. Konstruktorabhängigkeiten explizit machen.
3. Globale Imports und Initialisierung schrittweise reduzieren.
4. Factory zunächst unverändert lassen und nur die neue Klasse erzeugen.
5. Bestehende öffentliche Attribute nur entfernen, wenn keine Aufrufer existieren und ein Ersatzvertrag dokumentiert ist.
6. Direkte Abhängigkeiten von API-Routern auf private Methoden beseitigen.
7. Nach jedem Schritt Import-, Syntax- und Vertragstests ausführen.

### Phase C – Turn-Kontext und Verträge

1. Einen internen, typisierten TurnContext definieren.
2. Alle Werte dokumentieren, die tatsächlich zwischen Phasen fließen.
3. Einen internen ResponseEnvelope und Streaming-Eventtyp definieren.
4. Externe Dict-/JSON-Form am Rand erzeugen, nicht in jeder Pipelinephase.
5. Optionalität und Fehlerzustände explizit typisieren.
6. Mutable globale Zustände, Caches und Sessionbezüge markieren.
7. Keine neuen Konfigurationsglobalen außerhalb von config/ einführen.

### Phase D – Gemeinsame Vorbereitungsphase

Aus der aktuellen Reihenfolge eine klar benannte Vorbereitung machen:

1. Eingabe normalisieren.
2. Session und Nutzerkontext auflösen.
3. Life-Vorbereitung ausführen.
4. Intent ermitteln.
5. Tools nur nach bestehender Semantik ausführen.
6. Emotion/VAD nach aktueller Konfiguration bestimmen.
7. STM, LTM und relevanten Kontext laden.
8. Global Workspace beziehungsweise Arbeitskontext füllen.
9. Prompt über die bestehende Promptquelle erzeugen.
10. Generationseinstellungen und Steering-Kontext vorbereiten.

Die Reihenfolge muss durch Regressionstests geschützt werden, weil eine scheinbar harmlose Umordnung die Modellantwort oder Persistenz ändern kann.

### Phase E – Generation und Parsing

1. Provideraufruf in generation.py kapseln.
2. vLLM-Steering-Integration über die aktive Steering-Komponente halten.
3. Providerantworten in eine interne Normalform überführen.
4. Fehler in technische Fehler und nutzerseitige Fallbackantworten trennen.
5. Bestehenden Parser und Sanitizer mit ihren Regeln erhalten.
6. Prompt-/Output-Formatierung nicht nebenbei neu erfinden.
7. Harte Prompttexte inventarisieren und erst in der Config-/Prompt-Phase zentralisieren.

### Phase F – Abschluss und Persistenz

1. Response finalisieren.
2. Life-State aktualisieren.
3. Session-/Chatdaten schreiben.
4. Memory beziehungsweise STM/LTM schreiben.
5. Sleep- oder Hintergrundverarbeitung nach aktueller Semantik auslösen.
6. Bei Fehlern dokumentieren, welche Sideeffects bereits erfolgt sind.
7. Sync und Stream müssen denselben Abschlussweg verwenden, sofern der aktuelle Vertrag nichts anderes verlangt.

### Phase G – Streamingadapter

1. Gemeinsame Vorbereitungslogik aus Phase D aufrufen.
2. Generator- beziehungsweise Provider-Chunks in die bestehende SSE-Form bringen.
3. Eventnamen und Abschlussfelder unverändert halten.
4. Fehler- und Cancel-Events explizit testen.
5. Persistenz nicht versehentlich nur im Sync-Pfad ausführen.
6. Nach Möglichkeit denselben ResponseEnvelope beziehungsweise dieselbe Abschlussfunktion wie Sync verwenden.

### Phase H – Kompatibilität abschließen

1. backend_wrapper.py auf dünne Re-Exports reduzieren.
2. Alte Imports testen.
3. Neue Architektur in README und docs/architecture.md erklären.
4. Erst danach alte interne Helfer löschen oder nach Legacy-Code/backend-wrapper-v1/ verschieben.
5. Eine Liste der absichtlich erhaltenen Kompatibilitätssymbole dokumentieren.
6. Wenn der alte Dateiname später entfernt werden soll, nur über einen separaten, ausdrücklich freigegebenen Breaking-Change-Prozess.

---

## 9. Brain-, Steering-, Memory-, Life- und Trainings-Cleanup

### 9.1 Brain

- Aktive Brain-Module anhand realer Importpfade kennzeichnen.
- brain/brain_pipeline.py aus dem aktiven Architekturdiagramm entfernen.
- Historischen Pipeline-Code nach Legacy-Code/brain-pipeline-v1/ verschieben.
- Aktive GlobalWorkspace-, Action-/Response-, Deep-Think-, Provider- und Parser-Komponenten erhalten.
- Veraltete Cerebras-Beispiele in aktiven Skills und Docs entfernen oder als Historie kennzeichnen.
- Keine aktive Funktion aus brain/steering_backend.py oder dem vLLM-Pfad verschieben, nur weil sie in der Nähe historischer Agenten liegt.

### 9.2 Steering-Importisolierung

- Aktive SteeringManager-Implementierung in einem aktiven Modul bereitstellen.
- Alter Importpfad als Re-Export erhalten.
- brain/agents/__init__.py minimal/lazy machen.
- Test hinzufügen, der den Runtime-Import ohne historische Agenten prüft.
- Testen, dass Steering-Config, Layer L10–26 und Vektorpfad unverändert wirken.
- Separate Version des Steering-Service und Payload-Version nicht mit der Produktversion vermischen.

### 9.3 Memory und Life

Große aktive Dateien nicht blind splitten. Zuerst Verantwortungen und Sideeffects kartieren.

Für memory/memory_engine.py, memory/sleep_phase.py, life/service.py und angrenzende Module:

- öffentliche Methoden und Aufrufer inventarisieren,
- reine Transformationen von Seiteneffekten trennen,
- typisierte Eingaben/Ausgaben ergänzen,
- persistente Datenformate nicht verändern,
- Pfade und temporäre Verzeichnisse über die Config beziehen,
- Tests für STM, LTM, Vergessen, Sleep, Homeostasis, Goals und Social erhalten,
- keine Änderungen am Emotionsmapping oder an der Sleep-Semantik ohne eigene Entscheidung.

### 9.4 Training

- Korrekte systemd-Entrypoint-Regel beachten: python -m Chappies_Trainingspartner.training_daemon.
- training_loop.py nicht mit dem Daemon verwechseln.
- Doppelte Definitionen, Re-Imports und optionale Typfehler im Training separat bereinigen.
- Training darf nicht durch minimale Runtime-Installation von GPU-/Trainingsabhängigkeiten blockiert werden.
- Daemon-, Config-, Status- und Stop-Verhalten testen.
- Trainingsartefakte und Checkpoints nicht löschen; nur temporäre Logs und Builddateien nach Herkunft entfernen.
- Training als eigener Subsystem-Bereich dokumentieren.

### 9.5 CLI

- chappie_brain_cli.py ist mit ungefähr 1.600+ Zeilen ebenfalls ein Kandidat für spätere modulare Aufteilung.
- Zuerst Argumente, lokale/remote Modi, Ausgabe und Exit-Codes testen.
- Gemeinsame Runtime-Fassade verwenden.
- CLI-spezifische Darstellung nicht in die Backend-Pipeline ziehen.
- Nur sichere, rein mechanische Extraktionen durchführen; keine parallele neue CLI-Architektur ohne Bedarf.

---

## 10. Konfigurations- und Prompt-Cleanup

### 10.1 Zentrale Config

Die aktive zentrale Config liegt nach aktuellem Stand in:

- config/config.py,
- Vorlage config/example_config.py,
- gegebenenfalls config/schemas beziehungsweise api/schemas,
- ignorierte lokale CHAPPIE_CONFIG.json und Secrets.

Alle globalen Konfigurationswerte sollen unter config/ liegen. Keine neue globale Einstellung in Wrapper, Router, Frontend-Komponente oder Trainingsmodul anlegen.

Prüfen und bereinigen:

- doppelte Settings,
- veraltete Pfade,
- falsche Providerbezeichnungen,
- Importe alter Config-Dateien,
- lokale Defaults gegenüber Beispielconfig,
- Secret-Handling,
- Config-Namen in README, Skills und systemd-Dateien,
- Kompatibilität zu bestehenden JSON-/Environment-Werten.

Die aktuelle config/config.py erzeugt beim Import Verzeichnisse wie data, chroma und research. Entscheiden und dokumentieren:

- ob dieser Import-Sideeffect weiterhin benötigt wird,
- ob er in eine explizite Initialisierungsfunktion verschoben werden kann,
- welche Entrypoints diese Initialisierung aufrufen,
- wie Tests isolierte temporäre Verzeichnisse verwenden.

Keinen Sideeffect entfernen, bevor Start- und Testpfade geprüft sind.

### 10.2 Projekt-Config-Skill aktualisieren

Der projektinterne Config-Skill beschreibt nach aktuellem Stand teilweise veraltete Pfade wie config/root_config.py und CHAPPIE_CONFIG.example.json sowie einen veralteten Cerebras-Provider.

Er muss an die Realität angepasst werden:

- config/config.py als aktuelle Quelle,
- config/example_config.py als Vorlage,
- echte Schemaorte,
- aktuelle Provider vllm, ollama, groq,
- lokale Qwen-/vLLM-Priorität,
- Secret-Regeln,
- aktuelle Tests und Entrypoints,
- keine widersprüchlichen Aussagen zu sieben beziehungsweise zehn Emotionen.

### 10.3 Prompt-Zentralisierung

config/prompts.py ist nach aktuellem Stand die vorgesehene zentrale Promptquelle, aber aktive Prompt-/Guidance-Texte liegen zusätzlich in Wrapper, Steering-Backend und Life-Modulen.

Vorgehen:

1. Alle Prompt- und Instruction-Literale mit rg inventarisieren.
2. Zwischen:
   - echtem Prompttemplate,
   - technischem Parsertext,
   - Logmeldung,
   - UI-Text,
   - Testfixture,
   - historischem Text
   unterscheiden.
3. Nur echte aktive Templates zentralisieren.
4. Variablen, Defaults und Formatierung explizit machen.
5. Prompt-Ausgaben mit repräsentativen Fixtures testen.
6. Historische Promptvarianten nach Legacy-Code oder Forschung einordnen.
7. Aktive Skills von veralteten Aussagen über Emotionen, Provider und Pipeline bereinigen.

---

## 11. Abhängigkeiten, Build und Toolchain

### 11.1 Python

requirements.txt mischt nach aktuellem Stand Laufzeit-, GPU-, Trainings-, Provider- und Entwicklungsabhängigkeiten, unter anderem FastAPI, Uvicorn, NumPy, vLLM, Ollama-/OpenAI-nahe Pakete, Chroma, Sentence Transformers, Unsloth, TRL, Datasets und PEFT.

Ziel:

- Laufzeitabhängigkeiten,
- Trainings-/GPU-Abhängigkeiten,
- Forschungs-/optionale Abhängigkeiten,
- Test-/Entwicklungsabhängigkeiten

klar unterscheiden, ohne den bestehenden Installationsweg unbemerkt zu brechen.

Vor einer Aufteilung:

- alle Importpfade und CI-Installationen prüfen,
- minimale Web-/Testinstallation definieren,
- lokale GPU-/Training-Installation definieren,
- optionale Provider transparent machen,
- Versionsgrenzen und Python-Version dokumentieren,
- gegebenenfalls Constraints oder Lockfile-Strategie festlegen,
- keine schwere GPU-Abhängigkeit in Offline-CI erzwingen.

Der lokale tests/test_api_contract.py-Fehler wegen fehlendem FastAPI muss entweder durch reproduzierbare Testinstallation oder durch klare Testgruppen gelöst werden. Ein Test darf nicht einfach aus CI entfernt werden.

### 11.2 Frontend

- frontend/package.json ist die relevante Frontend-Abhängigkeitsschicht.
- Root-package.json mit der künstlichen python3-Abhängigkeit ist ein separater Cleanup-Kandidat.
- TypeScript-/Vite-Versionen und Lockfile reproduzierbar halten.
- Keine automatisch wechselnde Compiler-Version durch unfixiertes npx in Dokumentation.
- moduleResolution-Änderungen nur bewusst und mit Vite-/TypeScript-Kompatibilität durchführen.
- Bestehende Buildfähigkeit erhalten.

Typisierungs-Cleanup:

- as any in api.ts, Chat, Settings, Inspector, Memory-, Life- und Trainingsseiten schrittweise reduzieren.
- API- und SSE-Typen aus den Backendverträgen ableiten.
- inspector-pane.tsx mit über 1.000 Zeilen nur nach Komponentengrenzen aufteilen.
- Keine UI-Semantik ändern.
- Bei Testinfrastruktur pure Parser-/Formatierungslogik mit kleinen Unit-Tests und zentrale UI-Flows mit Playwright prüfen.
- Für Browserprüfung die im Projekt vorgeschriebene Playwright-MCP verwenden; wenn sie nicht verfügbar ist, das als separates Tooling-Problem melden.

### 11.3 Generierte und falsche Root-Dateien

- Prüfen, ob frontend/vite.config.js, Deklarationsdateien und tsbuildinfo generiert sind.
- Quell- und Builddateien eindeutig trennen.
- .gitignore um reale Build-/Testartefakte ergänzen.
- Root-NPM-Dateien nur entfernen, wenn keine CI-/Setup-/Dokumentationsreferenz verbleibt.
- Keine Konfigurationsdatei löschen, deren Inhalt von Vite, TypeScript oder Deployment benötigt wird.

---

## 12. Teststrategie und Regression-Schutz

### 12.1 Grundsatz

Das Projekt verwendet standalone Python-Skripte. Nicht eigenmächtig auf pytest umstellen.

Jede strukturelle Änderung wird in kleinen Schritten getestet. Ein Test, der nur wegen einer schwer reproduzierbaren Umgebung nicht läuft, muss als Umgebungsproblem mit reproduzierbarer Installationsanweisung dokumentiert werden.

### 12.2 Bestehende Baseline ausführen

Vor und nach jedem großen Meilenstein mindestens:

- Syntax-/Compile-Check für produktive Python-Bereiche,
- tests/test_quick.py,
- tests/test_forschung_report.py,
- tests/test_local_first_runtime.py,
- tests/test_web_ui_consistency.py,
- tests/test_settings_integrity.py,
- tests/test_root_config.py,
- Chat-UI-Formatierung,
- Reasoning-Layering,
- relevante test_cli_*,
- Forschungsharness,
- API-Contract-Test mit installierten Minimalabhängigkeiten,
- relevante Memory-, Life-, Provider- und Trainingsprüfungen.

Die genaue Liste in .github/workflows/ci.yml und tests/README.md aktualisieren und zentral dokumentieren.

### 12.3 Neue Backend-Regressionstests

Mindestens folgende standalone Tests beziehungsweise Testbereiche anlegen:

1. Factory-Kompatibilität:
   - alter Import,
   - neuer Import,
   - create_chappie_backend,
   - init_chappie.

2. Sync-Contract:
   - identische Pflichtfelder,
   - Sessionbezug,
   - Fehlerform,
   - Life-/Memory-Abschluss.

3. Streaming-Contract:
   - SSE-Format,
   - Eventnamen,
   - Eventreihenfolge,
   - Abschlussereignis,
   - Fehlerereignis,
   - Abbruch/Cancellation.

4. Sync-/Stream-Parität:
   - gleiche Eingabeverarbeitung,
   - gleiche Prompt-/Kontextfixtures,
   - gleiche Persistenzabsicht,
   - unterschiedliche Ausgabe nur dort, wo Streaming es erfordert.

5. Provider-Antwortnormalisierung:
   - vLLM,
   - Ollama,
   - Groq, sofern weiterhin unterstützt,
   - ungültige und leere Antworten,
   - Timeout und Providerfehler.

6. Steuerungslogik:
   - SteeringManager-Import ohne historische Agenten,
   - Layer-/Vektor-Konfiguration,
   - kein versehentliches Laden alter Orchestratoren.

7. Daten- und Lifecycle-Schutz:
   - neue Session,
   - bestehende Session,
   - Memory,
   - Sleep,
   - Life-Finalisierung,
   - Fehler vor und nach Persistenz.

8. Konfigurationsschutz:
   - Beispielconfig,
   - lokale Config,
   - Settings-Reload,
   - Defaults,
   - unbekannte und fehlende Werte.

9. CLI- und Forschungsadapter:
   - lokale/remote Argumente,
   - Exit-Codes,
   - Forschungsharness-Output,
   - Evidence-Manifest.

### 12.4 Testdoubles und deterministische Ausführung

- Keine echten vLLM-/Ollama-/Groq-Dienste für reine Logiktests benötigen.
- Provider, Speicher, Zeit und zufällige Modellantworten faken oder injizieren.
- Temporäre Verzeichnisse verwenden.
- Secrets und lokale Nutzerdaten nie in Fixtures committen.
- Zufall und Zeit kontrollierbar machen, wo die aktuelle Semantik das erlaubt.
- Externe Integrationstests klar markieren und separat ausführen.

### 12.5 CI verbessern

Die CI soll nicht einfach || true oder continue-on-error verwenden, um relevante Regressionen zu verstecken.

Vorgehen:

1. Bestehende Pflicht- und Erweiterungstests dokumentieren.
2. Wirklich externe Tests separat als opt-in/live markieren.
3. Lokale deterministische Tests als required machen.
4. Erweiterte, aber reproduzierbare Tests schrittweise von nicht-blockierend auf required setzen.
5. Fehlende Dependencies in Testgruppen beheben.
6. Python-Syntax, Ruff, Mypy, Frontend-Build und gegebenenfalls Frontend-Tests als eigene verständliche CI-Schritte ausweisen.
7. Forschungsdatenvalidierung offline und reproduzierbar machen.
8. Bericht v5-Unverändertheit und v6-Validator in CI aufnehmen.
9. Legacy-Code bewusst aus Produktionslinting ausschließen, aber nicht aus Archiv-/Dokumentationsvalidierung.
10. Ausschlüsse im CI kommentieren und begründen.

### 12.6 Lint- und Typisierungspfade

Ruff-Baseline schrittweise abbauen:

- zuerst echte ungenutzte Imports und Variablen,
- danach f-Strings ohne Platzhalter,
- danach Importordnung,
- danach Lambda-/E722-/E741-/E701-/E702-Befunde,
- keine mechanische Reparatur in historischen oder generierten Dateien,
- jede Gruppe testen.

Mypy-Baseline schrittweise abbauen:

- öffentliche Runtime- und API-Grenzen zuerst,
- Optional- und Dict-/Union-Verträge explizit machen,
- doppelte Definitionen und Re-Imports auflösen,
- falsche Provider-Enums korrigieren,
- historische undefinierte Variablen nur im aktiven Code beheben,
- Legacy-Code nicht künstlich typisieren, sondern aus dem aktiven Mypy-Scope nehmen und dokumentieren.

Ziel ist ein ehrlicher aktiver Scope. Ein kleinerer, begründeter Scope ist besser als ein scheinbar grüner Check mit versteckten Fehlern.

---

## 13. Dokumentationsplan

### 13.1 README

README.md muss die aktuelle Wahrheit abbilden:

- aktueller API-/CLI-Einstieg,
- lokale vLLM-Priorität,
- Rolle der Provider,
- aktuelle Runtime-/Pipeline-Struktur,
- Brain v1 als Legacy,
- Link zu Legacy-Code/README.md,
- Link zu Bericht v5 und v6,
- korrekter Config-Setup-Pfad über config/example_config.py,
- korrekte Service-/Entrypoint-Befehle,
- Testbefehle und Testgruppen,
- Hinweise zu optionalen GPU-/Trainingsabhängigkeiten.

Veraltete Angaben wie eine nicht existierende CHAPPIE_CONFIG.example.json oder eine aktive brain_pipeline müssen entfernt beziehungsweise als Historie gekennzeichnet werden.

### 13.2 Architektur- und Workflow-Dokumentation

Aktualisieren:

- docs/architecture.md,
- docs/workflows.md,
- docs/project-map.md,
- docs/local-models.md,
- docs/vLLM-Setup.md,
- docs/deployment.md,
- docs/testing.md,
- docs/integration_gemma4.md, falls der Inhalt noch aktiv verlinkt oder relevant ist,
- tests/README.md,
- gegebenenfalls Brückendokumente in Info Dateien/.

Die Dokumentation muss die tatsächliche Route darstellen:

    API / CLI / Research
        -> Runtime-Fassade
        -> Turn-Pipeline
        -> Brain-/Memory-/Life-Komponenten
        -> Provider/Steering
        -> Response- und Persistenzabschluss

Historische Architekturdiagramme dürfen bleiben, müssen aber mit historisch und einem Datum/Commit gekennzeichnet sein.

### 13.3 Fehlende und falsche Pfade

Vor dem Abschluss alle Dokumentationspfade automatisiert oder manuell prüfen:

- Links auf verschobene Python-Dateien,
- Links auf v5/v6,
- Links auf Config-Vorlagen,
- Links auf Service-Dateien,
- Links auf nicht vorhandene root_config.py-/brain_config.py-Dateien,
- alte Providernamen,
- falsche Entrypoints,
- falsche Ports,
- falsche Aussagen zur Brain-Pipeline.

Keine Zeilennummern als einzige Evidenz verwenden. Wenn Zeilennummern für den Forschungsbericht verwendet werden, zusätzlich Commit-Hash und Quellhash speichern.

---

## 14. Skills und Agentendokumentation

### 14.1 Kanonische Quelle festlegen

Es gibt projektbezogene Skills sowohl in .agents/skills/ als auch in .claude/skills/; die relevanten SKILL.md-Dateien sind nach aktuellem Stand weitgehend byte-identisch.

Festlegen:

- Eine Quelle wird kanonisch, vorzugsweise .agents/skills/.
- .claude/skills/ bleibt entweder ein bewusst synchronisierter Spiegel oder wird durch einen dokumentierten Mechanismus ersetzt.
- Keine still auseinanderlaufenden Kopien behalten.
- Hash-/Synchronisationsprüfung in einem kleinen Script oder CI-Schritt ergänzen.
- .claude/skills/README.md dabei berücksichtigen.

### 14.2 Inhaltliche Aktualisierung

Die Skills müssen insbesondere korrigieren:

- aktiver Pfad ist Wrapper/Runtime, nicht Brain-Pipeline,
- aktuelle Config-Pfade,
- aktuelle Provider,
- zehn statt veralteter sieben Emotionen,
- korrekte Training-/Steering-Entrypoints,
- aktuelle Testbefehle,
- aktuelle Formatter-/Parserstruktur,
- aktive und historische Komponenten,
- Verhalten bei Kompatibilität und Legacy-Code.

Die Skills sollen keine Architektur versprechen, die der Code noch nicht implementiert. Während der Migration darf ein Skill den Zwischenstand ausdrücklich als Übergangsphase nennen; nach Abschluss muss er die Zielarchitektur beschreiben.

---

## 15. Forschungsbericht v5 und Migration zu v6

### 15.1 V5 unverändert einfrieren

forschung/report/CHAPPiE-Forschungsbericht-v5.html ist ein historisches Artefakt und muss erhalten bleiben.

Vor jeder Änderung:

1. Datei byteweise hashen.
2. Dateigröße und Titel prüfen.
3. Git-Commit und Arbeitsbaumstatus dokumentieren.
4. Eine Validierungsregel anlegen, die v5 unverändert erwartet.
5. Nach allen Refactorings erneut hashen.
6. Bei Abweichung sofort stoppen und die Ursache beheben; v5 nicht beiläufig formatieren, minifizieren oder Links umschreiben.

V5 darf nicht überschrieben werden und erhält keinen neuen Inhalt aus v6.

### 15.2 V6 als Kopie anlegen

Die v6 wird aus v5 kopiert und danach gezielt weiterentwickelt:

- neuer Pfad: forschung/report/CHAPPiE-Forschungsbericht-v6.html,
- v5 bleibt daneben bestehen,
- v6 erhält eine sichtbare Versionskennzeichnung,
- keine globale Suche-und-Ersetzen-Aktion über den gesamten HTML-Text,
- bestehendes Layout, Stil und Forschungsnarrativ erhalten, sofern sie nicht sachlich veraltet sind.

### 15.3 Inhaltliche Änderungen für v6

V6 muss ausdrücklich enthalten:

1. Aktuelle Architektur:
   - Runtime-Fassade,
   - modulare Turn-Pipeline,
   - Generation/Steering,
   - Memory/Life,
   - API/CLI/Research-Anbindungen.

2. Historische Entwicklung:
   - Brain-Pipeline v1 als erster Versuch,
   - weshalb sie nicht mehr der aktive Pfad ist,
   - welche konzeptionellen Ideen erhalten blieben,
   - welche strukturellen Probleme die Ablösung motivierten.

3. Legacy-Abgrenzung:
   - Link auf Legacy-Code/README.md,
   - klare Kennzeichnung historischer Agenten,
   - Erhaltungsgrund für Vergleichbarkeit/Forschung,
   - kein Anspruch, dass Legacy-Code produktiv ausgeführt werden soll.

4. Effizienz- und Geschwindigkeitsargument:
   - die aktuelle neue Idee ist der genutzte, effizientere Pfad,
   - qualitative beziehungsweise gemessene Aussagen nur mit vorhandenen Messdaten belegen,
   - keine frei erfundenen Benchmarks,
   - unterscheiden zwischen Messung vor und nach dem Refactoring,
   - falls die Daten aus Run 2 vor der Migration stammen, dies offen als Provenienz angeben.

5. Codebelege:
   - aktuelle Dateipfade,
   - stabile Symbolnamen,
   - kurze relevante Ausschnitte,
   - Commit-Hash/Quellhash,
   - Rolle active oder historical,
   - Erklärung, warum der Ausschnitt die Aussage belegt.

6. Reproduzierbarkeit:
   - verwendete Harness-/Validator-Befehle,
   - Abhängigkeiten,
   - Offline-/Live-Anforderungen,
   - Datenprovenienz,
   - bekannte Grenzen.

### 15.4 Umgang mit alten V5-Links

V5 verweist teilweise auf aktuelle Quellpfade und alte Zeilenpositionen. Nach dem Refactoring können diese Links technisch nicht mehr live sein.

Der Agent muss vor der Entscheidung einen Link-Audit durchführen und anschließend eine der folgenden Strategien dokumentiert wählen:

- Empfohlen: v5 bleibt ein unveränderter historischer Bericht; die zugehörige alte Quellstruktur wird als unveränderter Snapshot unter Legacy-Code/report-v5-source/ abgelegt, und v5 wird als historische Momentaufnahme erklärt.
- Alternativ: V5-Links bleiben auf absichtlich erhaltene Kompatibilitätsdateien zeigen. Dies widerspricht aber einer strikten Trennung und darf nur gewählt werden, wenn der Nutzer dies ausdrücklich bevorzugt.
- Nicht zulässig: v5 heimlich anpassen oder so tun, als beschreibe es nachträglich den refaktorierten Stand.

Für v6 sollen Links und Belege auf die aktuelle aktive Struktur zeigen. Historische Belege müssen ausdrücklich als historisch markiert werden.

### 15.5 V6-Evidence-Manifest

Eine maschinenlesbare Datei wie forschung/report/report-evidence-v6.json anlegen, sofern sie zum bestehenden Harness passt. Sie sollte mindestens enthalten:

- Berichtsversion,
- Erstellungsdatum,
- Quellcommit,
- relevante Dateipfade,
- Symbolnamen,
- Quellhash,
- Abschnitt im Bericht,
- kurze Aussage,
- Rolle active oder historical,
- Zweck des Belegs,
- verwendete Validatorversion.

Keine Secrets, lokalen absoluten Pfade oder personenbezogenen Daten eintragen.

### 15.6 Validatoren

Den bestehenden Report-Validator prüfen. Der aktuelle Validator ist inhaltlich bereits auf einen v5-nahen Stand ausgerichtet und referenziert v5. Er soll nicht einfach umbenannt werden.

Ziel:

- v5-Freeze-Validator:
  - Hash-/Bytegleichheit,
  - Titel/Version,
  - unveränderte lokale Ressourcen,
  - keine Secrets.

- v6-Validator:
  - Titel und Versionsangabe,
  - Offline-Fähigkeit,
  - lokale Links und Ressourcen,
  - aktuelle Architekturbegriffe,
  - Legacy-Link und Legacy-Kennzeichnung,
  - Evidence-Manifest,
  - keine veralteten Aussagen über aktiven Brain-Pipeline-Pfad,
  - keine Secrets oder ungewollten Modell-/Toolausgaben,
  - korrekte Provenienz der Forschungsdaten.

- Report-README:
  - v3, v4, v5, v6 und Run-Berichte klar indexieren,
  - Status historisch, aktuell, Arbeitsentwurf oder Evidenz verwenden,
  - v5 und v6 nicht verwechseln.

Die HTML-Dateien nur so weit ändern, wie eine sachlich korrekte v6 es erfordert. Rohdaten nicht inhaltlich manipulieren, um ein schöneres Narrativ zu erzeugen.

---

## 16. Forschungsordner und Datenhygiene

forschung/ wird nicht pauschal bereinigt, sondern klassifiziert.

### 16.1 Klassifizierungsfelder

Für Reports, Runs, Session-Logs und Arbeitsnotizen festhalten:

- Dateityp,
- Entstehungszeitpunkt,
- zugehöriger Commit/Run,
- reproduzierbar oder eingefroren,
- aktiv vom Harness verwendet oder nur Evidenz,
- öffentlich präsentierbar oder intern,
- sensibel/personenbezogen,
- behalten, archivieren oder löschen,
- Grund der Entscheidung.

### 16.2 Sichere Bereinigung

- Keine Session-Logs ohne Inhalts- und Forschungsprüfung löschen.
- Keine Run-Ergebnisse verschieben, wenn Validatoren oder Berichte sie referenzieren.
- Temporäre Browser-/Telemetry-Artefakte von echten Forschungsdaten unterscheiden.
- Persönliche Daten, Secrets und lokale Pfade vor Präsentation prüfen.
- Alte Arbeitsnotizen nicht als aktuelle Architektur ausgeben.
- Verweise mit relativen Links nach jedem Verschieben prüfen.
- Große Evidenzordner nicht in den Python-Lint-Scope aufnehmen, aber deren Metadaten/Validatoren testen.

### 16.3 Problematische Reportstellen

Bekannte problematische Beispiele wie ein fehlerhafter Link mit überflüssigem Leerzeichen oder unbereinigte Rohfragmente müssen in der v6-Prüfung erfasst werden. Sie dürfen nicht unkritisch in v6 übernommen werden.

---

## 17. Deployment, Scripts und operative Dateien

### 17.1 systemd und feste Pfade

Deployment-Dateien enthalten teilweise feste Pfade wie /home/bbecker/CHAPPiE und feste Python-/vLLM-Aufrufe.

Nicht automatisch ändern. Zuerst unterscheiden:

- absichtlich zielserverbezogener Pfad,
- veralteter lokaler Pfad,
- für andere Installationen nicht portabler Wert,
- sicherheits- oder wartungsrelevante Konfiguration.

Dann gegebenenfalls:

- Pfad als dokumentierte Variable/Template konfigurierbar machen,
- Beispielservice und konkrete lokale Override-Datei trennen,
- Arbeitsverzeichnis, Benutzer, EnvironmentFile und Ports dokumentieren,
- korrekte Startreihenfolge erhalten:
  - vLLM-Steering-Service,
  - Web-API,
  - Frontend,
  - Training separat.
- korrekte Entrypoints erhalten:
  - python app.py,
  - python -m brain.steering_api_server,
  - python -m Chappies_Trainingspartner.training_daemon.

### 17.2 Shell- und Setup-Scripts

Für jedes Script:

- wird es durch README, CI, systemd, Cron, Deployment oder Forschung aufgerufen?
- ist es idempotent?
- enthält es veraltete Pfade?
- verändert es Daten destruktiv?
- benutzt es Secrets unsicher?
- ist es ein einmaliger historischer Versuch?

Aktive Scripts behalten und dokumentieren. Historische Scripts nach Legacy-Code/old-scripts/ verschieben. Unbelegte Löschungen vermeiden.

---

## 18. Security- und Datenschutz-Prüfung

Vor Abschluss den Skill security-audit verwenden, sobald API-/Deployment-/Config-Dateien betroffen sind.

Mindestens prüfen:

- Secrets in Config, Reports, Logs, Fixtures und Git-Historie des aktuellen Arbeitsstands,
- API-Keys in config/APIs/,
- lokale absolute Pfade und Benutzernamen in präsentierbaren Dateien,
- permissive CORS-Konfiguration wie allow_origins=["*"],
- Streaming-Header und Authentifizierung,
- Session-/Memory-Zugriff und Autorisierung,
- Prompt-/Tool-Injection-Grenzen,
- unvalidierte Dateipfade im Forschungs- oder Report-Harness,
- Shell-Scripts und systemd-Environment,
- Debug- und Telemetrie-Artefakte,
- sensible Session-Logs in Reports oder Tests.

Security-Änderungen dürfen ebenfalls nicht unbemerkt den Nutzervertrag brechen. Findings nach Schweregrad klassifizieren und bei nicht trivialen Änderungen separat dokumentieren.

---

## 19. Konkrete Phasenreihenfolge

### Phase 0 – Arbeitsbaum und Baseline

Ergebnisse:

- bestätigter Git-Ausgangsstatus,
- bestätigte Repo-Struktur,
- Tool-/Dependency-Baseline,
- Import-/Aufruferinventar,
- Test-Baseline,
- Ruff-/Mypy-Baseline,
- v5-Hash,
- vorläufige Legacy-Matrix,
- vorläufige öffentliche Vertragsmatrix.

Gate:

- Keine Datei verschoben oder gelöscht.
- V5-Hash ist gespeichert.
- Alle bekannten lokalen Test-/Dependency-Probleme sind dokumentiert.

### Phase 1 – Sicherheitsnetz aus Verträgen und Fixtures

Ergebnisse:

- Sync-/Stream-Regressionstests,
- Factory-Kompatibilitätstests,
- Provider-Fakes,
- Memory-/Life-/Session-Fakes,
- API-/SSE-Fixtures,
- v5-Freeze-Check,
- Ausgangsmanifest.

Gate:

- Die Tests können den Ist-Zustand abbilden.
- Testfehler durch Umgebung sind reproduzierbar erklärt.
- Keine zufällige Modellantwort ist der einzige Testanker.

### Phase 2 – Backend-Wrapper modularisieren

Ergebnisse:

- neue module-level Runtime-Fassade,
- backend_wrapper.py als Kompatibilitätsschicht,
- interne Context-/Contract-Typen,
- getrennte Generation, Persistenz und Formatierung,
- gemeinsamer Sync-/Stream-Kern,
- unveränderte äußere Antwortverträge.

Gate:

- alte und neue Importe funktionieren,
- API-/CLI-/Research-Aufrufer funktionieren,
- Sync und Stream testen denselben fachlichen Verlauf,
- keine zweite vollständige Parallelpipeline zurückbleibt,
- aktive Datei deutlich kleiner und verständlicher ist.

### Phase 3 – Brain-/Steering-Grenze bereinigen

Ergebnisse:

- aktiver SteeringManager isoliert,
- alter Importpfad kompatibel,
- eager Imports historischer Agents entfernt,
- historische Pipeline eindeutig als Legacy markiert,
- aktive Brain-Module dokumentiert.

Gate:

- Runtime-Import lädt keine unnötigen historischen Agenten,
- Steering-Regressionstests bestehen,
- Brain-Pipeline ist im aktiven Diagramm nicht mehr als Live-Pfad dargestellt.

### Phase 4 – Legacy-Code ablegen und toten Code entscheiden

Ergebnisse:

- Legacy-Code/README.md,
- Unter-READMEs und Legacy-Index,
- Brain-Pipeline-/Agent-Snapshot,
- Wrapper-v1-Snapshot, falls für v5-Provenienz nötig,
- alte Reports/Pläne/Scripts nach Link-Audit geordnet,
- nachgewiesen toter Code kontrolliert entfernt,
- Artefakte bereinigt und ignoriert.

Gate:

- Jede verschobene Datei hat Herkunft und Nachfolger.
- Jede gelöschte Datei hat eine Referenzprüfung und Begründung.
- Aktive Importe enthalten keine unbeabsichtigten Legacy-Pfade.
- Forschungsdaten sind vollständig und korrekt klassifiziert.

### Phase 5 – Aktive Subsysteme vereinfachen

Ergebnisse:

- CLI, Memory, Life, Training und API mit klaren Grenzen,
- echte Ruff-Befunde reduziert,
- Mypy im aktiven Scope verbessert,
- keine Funktionsänderung in Life/Memory/Training,
- öffentliche Router greifen nicht mehr auf private Backenddetails zu.

Gate:

- subsystembezogene Tests bestehen,
- Sideeffects und persistierte Formate unverändert,
- Training- und Steering-Entrypoints unverändert nutzbar.

### Phase 6 – Config, Prompts und Abhängigkeiten

Ergebnisse:

- zentrale Configpfade,
- aktualisierte Beispielconfig,
- geklärte Import-Sideeffects,
- aktive Prompttemplates zentralisiert,
- Provider- und Emotionstexte aktuell,
- Dependency-/Testgruppen dokumentiert,
- Root-/Frontend-Paketdateien bereinigt, falls bestätigt.

Gate:

- frische lokale Testumgebung kann die relevanten Testgruppen installieren und ausführen,
- keine Secrets im Repository,
- Config- und Providerverträge bestehen,
- bestehende Startbefehle funktionieren.

### Phase 7 – Frontend und API-Dokumentation

Ergebnisse:

- typed API-/SSE-Schicht,
- as any nur noch begründet,
- große Komponenten nur bei klarer Grenze aufgeteilt,
- Build und gezielte UI-Flows geprüft,
- keine unnötigen Designänderungen.

Gate:

- Frontend-Build besteht,
- API-/SSE-Vertrag mit Backend besteht,
- bei UI-Änderungen Playwright-Prüfung dokumentiert,
- bestehende Nutzerinteraktionen bleiben gleich.

### Phase 8 – Bericht v6

Ergebnisse:

- v5 unverändert,
- v6-Kopie,
- aktuelle Architekturkapitel,
- Legacy-Erklärung,
- aktuelle Codebelege,
- Evidenzmanifest,
- v5-/v6-Validatoren,
- Report-README-Index.

Gate:

- v5-Hash unverändert,
- v6 offline validiert,
- alle lokalen Links gültig,
- aktive/historische Quellen eindeutig,
- keine erfundenen Performanceaussagen.

### Phase 9 – Gesamtdokumentation, Skills, CI und Security

Ergebnisse:

- README und docs/ aktuell,
- AGENTS.md nur bei tatsächlich nötigen Projektänderungen angepasst,
- Skills synchron und sachlich korrekt,
- CI ehrlich und reproduzierbar,
- Security-Audit abgeschlossen,
- Changelog-/Versionierungsentscheid vorbereitet.

Gate:

- kein aktiver Dokumentationspfad behauptet den alten Brain-Pipeline-Livebetrieb,
- Skills und Code widersprechen sich nicht,
- CI prüft die neuen Architektur-/Report-/Hygieneregeln.

### Phase 10 – Abschluss und Veröffentlichung

Ergebnisse:

- vollständiger Testbericht,
- Diff-/Statusprüfung,
- aktualisierte Version und CHANGELOG,
- logische Commitaufteilung,
- Nutzerfreigabe,
- XXL-Commit-/Push-Workflow,
- grüne GitHub-CI oder dokumentierter externer Blocker.

Gate:

- Definition of Done vollständig,
- keine unbeabsichtigten Dateien,
- kein Push ohne Freigabe,
- Abschlussstatus im Goal-Tracking aktualisiert.

---

## 20. Test- und Prüfkommandos für die Umsetzung

Die konkreten Kommandos müssen an die aktuelle Umgebung angepasst werden. Erwartete Prüfgruppen sind:

    git status --short
    git diff --stat
    rg --files
    rg "create_chappie_backend|init_chappie|CHAPPiEBackend|process_stream|brain_pipeline|BrainOrchestrator" .
    python -m compileall -q api brain config life memory web_infrastructure Chappies_Trainingspartner chappie_brain_cli.py app.py scripts forschung tests
    python tests/test_quick.py
    python tests/test_forschung_report.py
    python tests/test_local_first_runtime.py
    python tests/test_web_ui_consistency.py
    python tests/test_settings_integrity.py
    python tests/test_api_contract.py
    cd frontend && npm run build

Für Lint und Typen:

    ruff check --no-cache <aktiver-scope>
    mypy --no-incremental --cache-dir <temporärer-cache> --ignore-missing-imports <aktiver-scope>

Für den Bericht:

    python forschung/report/<v5-freeze-validator>
    python forschung/report/<v6-validator>

Für den Browser:

- zuerst die vorgeschriebene Playwright-MCP-Verfügbarkeit prüfen,
- Navigation,
- Snapshot,
- gezielte Chat-/Streaming-/Settings-Aktionen,
- keine Nutzer-Preview verändern.

Die Kommandos sind Beispiele für die Prüfstrategie. Die tatsächlichen Dateinamen neuer Tests und Validatoren werden erst nach der Bestandsprüfung festgelegt.

---

## 21. Risiken und Gegenmaßnahmen

### Risiko: Funktionale Regression durch Reihenfolgeänderung

Gegenmaßnahme:

- Turn-Reihenfolge als Testvertrag festhalten,
- Context-Snapshots,
- Fake-Provider,
- Sync-/Stream-Parität,
- schrittweise Extraktion ohne semantische Umordnung.

### Risiko: Legacy-Code wird versehentlich weiterhin importiert

Gegenmaßnahme:

- aktive Importpfade explizit machen,
- minimale/lazy brain.agents-Initialisierung,
- Importtest,
- Legacy-Ordner außerhalb des Python-Pakets halten.

### Risiko: V5 wird durch Refactoring unabsichtlich verändert

Gegenmaßnahme:

- Vorher-/Nachher-Hash,
- Freeze-Validator,
- keine Bearbeitung der v5-Datei,
- historischer Source-Snapshot,
- Stop bei Hashabweichung.

### Risiko: Forschungsbelege zeigen auf falschen Stand

Gegenmaßnahme:

- v6-Evidence-Manifest,
- Commit-/Quellhash,
- active/historical-Kennzeichnung,
- Report-Link-Audit,
- getrennte Darstellung von Run-2-Daten und Post-Refactor-Verifikation.

### Risiko: Zu breite Löschung

Gegenmaßnahme:

- keine Löschung ohne Referenzmatrix,
- candidate-Status,
- erst archivieren, dann später separat löschen,
- Nutzerfreigabe bei unsicherem Forschungs-/Deployment-Code.

### Risiko: Wrapper-Refactoring erzeugt zwei divergierende Systeme

Gegenmaßnahme:

- Kompatibilitätsschicht statt paralleler fachlicher Implementierung,
- gemeinsamer Kern,
- gemeinsame Tests,
- alte private Pfade nach Migration entfernen/archivieren.

### Risiko: Dependency-Cleanup bricht lokale GPU-/Training-Installation

Gegenmaßnahme:

- Dependency-Gruppen,
- Installationsmatrix,
- Minimal-CI-Umgebung,
- lokale GPU-Umgebung separat prüfen,
- keine ungetestete Entfernung schwerer Pakete.

### Risiko: Dokumentation und Skills veralten erneut

Gegenmaßnahme:

- Architekturbegriffe zentral festlegen,
- Links/Provider/Entrypoints validieren,
- Skill-Synchronisationscheck,
- Dokumentationsprüfung als CI-Schritt.

### Risiko: Security- und CORS-Änderung wird fälschlich als Cleanup behandelt

Gegenmaßnahme:

- Security-Audit separat klassifizieren,
- Auswirkungen und Migration dokumentieren,
- keine Auth-/CORS-Verschärfung ohne Vertrags-/Deploymentprüfung.

### Risiko: Laufende Dienste oder Nutzerdaten werden beeinflusst

Gegenmaßnahme:

- keine systemd-Neustarts in dieser Planphase,
- keine Datenlöschung,
- eigene Testports und temporäre Verzeichnisse,
- Backups/Snapshots nur nach klarer Zielbestimmung.

---

## 22. Rollback- und Wiederherstellungsstrategie

- Jede Phase in kleine logisch rückgängig machbare Schritte teilen.
- Vor Datei-Moves Hash/Status und Zielpfade dokumentieren.
- git mv beziehungsweise eine historieerhaltende Verschiebung verwenden, soweit passend.
- Kompatibilitäts-Re-Exports zuerst einführen; erst danach Aufrufer umstellen.
- Alte Dateien zunächst archivieren, wenn die Löschsicherheit nicht vollständig ist.
- Forschungsdaten nicht im Rahmen eines Code-Rollbacks verschieben oder löschen.
- Bei Testregressionen den letzten kleinen Refactoring-Schritt zurücknehmen, nicht den gesamten Arbeitsbaum zerstören.
- Keine destruktiven Git-Befehle.
- V5-Hash als harter Rückhalt.
- Bei Problemen mit Provider, Memory, Life oder Training den alten aktiven Kompatibilitätspfad lokal weiter nutzbar halten, bis der neue Pfad verifiziert ist.
- Vor dem Push Diff und Status gemeinsam prüfen.
- Falls CI nach Push fehlschlägt, über den XXL-Workflow gezielt korrigieren; nicht durch Weglassen von Tests grün machen.

---

## 23. Versionierung und CHANGELOG

Nach dem Skill versionierungen vor jedem Commit/Push:

1. tatsächlichen Änderungsumfang bestimmen;
2. Patch/Minor/Major anhand der SemVer-Regeln entscheiden;
3. CHANGELOG unter der neuen Version aktualisieren;
4. genau ungefähr fünf verständliche Stichpunkte in den vorgesehenen Kategorien pflegen:
   - Erstellt,
   - Verändert,
   - Gelöscht;
5. keine Codeblöcke oder unnötigen Implementierungsdetails im CHANGELOG;
6. sichtbare UI-/Doku-Versionen aktualisieren, wenn betroffen;
7. Storage-Version prüfen, falls localStorage-/IndexedDB-Formate betroffen sind;
8. API-/Payload-/Steering-Versionen getrennt bewerten;
9. Commit-Nachricht mit Version entsprechend dem Skill prüfen.

Für diese Migration ist ein Minor-Release nur dann angemessen, wenn öffentliche Verträge kompatibel bleiben. Ein Major-Release darf nicht nur wegen einer internen Dateiaufteilung entstehen. Ein Major-Schritt ist nötig, wenn absichtlich ein öffentlicher Import-, API-, Daten- oder Nutzervertrag gebrochen wird.

---

## 24. Abschluss-Checkliste für den Coding-Agenten

### Architektur

- [ ] Aktiver Pfad ist in einem kurzen Architekturdiagramm erklärt.
- [ ] Runtime-Fassade ist auf Modulebene definiert.
- [ ] backend_wrapper.py ist nur noch Kompatibilität oder sinnvoll umbenannt und sauber migriert.
- [ ] Turn-Kontext, Generation, Persistenz und Formatierung haben klare Grenzen.
- [ ] Sync und Streaming teilen fachliche Logik.
- [ ] Private Backenddetails werden nicht direkt von Routern verwendet.
- [ ] Providerverhalten ist korrekt dokumentiert.
- [ ] Brain-, Memory-, Life- und Steering-Grenzen sind nachvollziehbar.

### Legacy und Dead Code

- [ ] Legacy-Code/README.md existiert.
- [ ] Legacy-Index und Unter-READMEs existieren.
- [ ] Brain-Pipeline v1 ist klar archiviert.
- [ ] Historische Agents sind nicht mehr aktiver Runtimepfad.
- [ ] Aktiver SteeringManager ist erhalten und isoliert.
- [ ] Wrapper-Legacy-Methoden sind entfernt oder archiviert.
- [ ] Jeder gelöschte Kandidat hat eine belegte Referenzprüfung.
- [ ] Forschungsdaten wurden nicht pauschal gelöscht.
- [ ] Temporäre Artefakte sind entfernt/ignoriert und erklärt.

### Vertrag und Tests

- [ ] Factory-/Importkompatibilität getestet.
- [ ] JSON- und SSE-Verträge getestet.
- [ ] Sync-/Stream-Parität getestet.
- [ ] Provider, Steering, Memory, Life, Sleep und Training getestet.
- [ ] CLI und Research-Harness getestet.
- [ ] Config und Settings-Reload getestet.
- [ ] v5-Freeze-Test besteht.
- [ ] v6-Validator besteht.
- [ ] Frontend-Build besteht.
- [ ] Relevante UI-Flows mit Playwright geprüft.
- [ ] CI ist ehrlich, reproduzierbar und nicht durch pauschales Ignorieren grün.

### Config, Doku und Skills

- [ ] Config liegt zentral unter config/.
- [ ] Beispielconfig und lokale Config-Dokumentation stimmen.
- [ ] Aktive Prompts sind nachvollziehbar zentralisiert.
- [ ] README und alle betroffenen docs/-Dateien stimmen.
- [ ] v5 bleibt unverändert.
- [ ] v6 beschreibt aktuelle Architektur und Legacy.
- [ ] Skills sind aktualisiert und synchron.
- [ ] Falsche Provider-, Pfad-, Entrypoint- und Emotionsangaben sind entfernt.
- [ ] Deployment- und Scriptpfade sind geprüft.

### Veröffentlichung

- [ ] Security-Audit bei betroffenem Scope erledigt.
- [ ] Ruff-/Mypy-Baseline ist reduziert oder ehrlich begründet.
- [ ] Version und CHANGELOG sind aktualisiert.
- [ ] git status und git diff geprüft.
- [ ] Nutzerfreigabe für Commit/Push liegt vor.
- [ ] github-infos wurde verwendet.
- [ ] commit-and-push-workflow-xxl wurde vollständig verwendet.
- [ ] GitHub-CI ist grün oder ein externer Blocker ist dokumentiert.
- [ ] Goal-Tracking wurde erst jetzt auf complete gesetzt.

---

## 25. Empfohlene Arbeitsweise für die andere KI

Die andere KI soll nicht versuchen, das gesamte Repository in einem unkontrollierten großen Patch umzuschreiben.

Arbeitsmuster:

1. Eine Phase auswählen.
2. Ist-Zustand mit Such- und Importprüfungen verifizieren.
3. Eine kleine Änderung mit eindeutiger Verantwortung ausführen.
4. Relevante Tests ausführen.
5. Diff und Status prüfen.
6. To-do-/Goal-Status aktualisieren.
7. Dokumentation direkt mit dem betroffenen Code aktualisieren.
8. Erst nach bestandenem Gate die nächste Phase beginnen.
9. Bei widersprüchlicher Evidenz anhalten und den Konflikt als Rückfrage oder Änderungsentscheid dokumentieren.
10. Unklare Dateien zunächst als candidate behandeln, nicht löschen.
11. Nach jeder Verschiebung Links, Imports, Tests, CI und Report-Evidenz erneut prüfen.
12. Am Ende die Versionierungs- und XXL-Commit-/Push-Regeln ausführen, jedoch nur nach ausdrücklicher Nutzerfreigabe.

Das Ziel ist eine elegante, effiziente und verständliche Verpackung der bereits funktionierenden neuen Idee. Eleganz darf nicht durch eine zusätzliche abstrakte Schichtensammlung entstehen, sondern durch klare Verantwortungen, geringe Kopplung, überprüfbare Verträge und eine nachvollziehbare Trennung zwischen aktivem System und historischer Entwicklung.

