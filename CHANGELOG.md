# Changelog

Alle Änderungen werden in 5 Stichpunkten dokumentiert. Keine Code-Anzeigen!

## [17.2.0-dev.2] - 2026-09-16

### Erstellt
- Sicherheitsrisiko-Filter für Dialogbelege ergänzt
- Risikostufen-Badges an sicherheitskritischen Belegen ergänzt
- Zähler für sichtbare Belege im Forschungsbericht ergänzt
- Wörtliche 1:1-Zitat-Belege aus den Rohartefakten ergänzt
- Testvertrag für erreichbare Berichtslinks ergänzt

### Verändert
- Dialogbelege zeigen Originalantworten statt sicherer Paraphrasen
- Beleg-Links öffnen die korrekten GitHub-Rohartefakte
- Nutzerfragen in Belegen exakt aus den Rohdaten übernommen
- Zweispaltiger Terminal-Bericht erscheint ab 120 Spalten
- Ungenutzte Importe und Variablen in CLI und Konfiguration entfernt

### Gelöscht
- Sichere Paraphrasen als Ersatz für Originalzitate entfernt
- Ungültige doppelte Klassenattribute an Belegkarten entfernt
- Relative Beleg-Links, die auf der Live-Seite ins Leere führten, entfernt
- Keine bestehenden Berichtsinhalte gelöscht
- Keine Forschungsdaten gelöscht

## [17.2.0-dev.1] - 2026-09-07

### Erstellt
- Session-Export mit Standard- und Debug-Stufe ergänzt
- Strukturierte Emotionshistorie in den Export aufgenommen
- OSC-52-Übertragung für Termius-Terminals ergänzt
- Private Server-Datei als zuverlässiger Export-Fallback ergänzt
- Remote-API-Endpunkt für Sitzungs-Exporte ergänzt

### Verändert
- Terminal-CLI fragt bei `/copy` die gewünschte Exportstufe ab
- Standard-Export bildet sichtbare Session- und UI-Daten ab
- Debug-Export bewahrt Roh-Metadaten und dekodierte Ereignisse
- Session-Export entfernt Zugangsdaten und Secret-Felder
- Exportverträge und Testläufe in CI und Dokumentation aufgenommen

### Gelöscht
- Keine bestehenden Chat-Nachrichten gelöscht
- Keine bestehenden Session-Dateien gelöscht
- Keine bestehenden Event-Store-Einträge gelöscht
- Keine bisherigen Clipboard-Funktionen der Weboberfläche gelöscht
- Keine Modell-, Memory- oder Life-Daten gelöscht

## [17.1.0-dev.1] - 2026-09-07

Ein Antwortprofil und ein Steering-Budget für alle Fragetypen, stabile Selbstauskünfte und ehrliche Anzeigen für Live-Fortschritt, Tokens und Report.

### Erstellt
- Einheitliches Steering-Budget mit Top-3-Basis, Top-1-Composite und gedeckelter Summenstärke eingeführt
- Stil-Kennzeichnung für Präsenz und Identität mit eigenem Dominanz-Label bei reiner Stil-Steuerung ergänzt
- Provider-Finish-Reason in Timing, Metadaten, Terminal-Report und Web-Inspektor sichtbar gemacht
- Format-Herkunft mit Grund in Terminal, API-Metadaten und Web-Inspektor durchgängig ausgewiesen
- Offline-Vertragstest für Profil, Budget, Dominanz-Label, Timing-Grund und Speicherstatistik ergänzt

### Verändert
- Antwortbudget auf 1200 Tokens für alle Fragetypen vereinheitlicht, Mathe-Kurzantwort bleibt als einziger Sonderweg
- Selbstbericht und Identität behalten Soul-, Memory- und Life-Kontext statt leerem Isolationskontext
- Live-Anzeige zählt Wörter mit einstelliger Rate, finale Tokens kommen aus dem Tokenizer
- Kompakt-Report zeigt immer alle zehn Emotionen mit Wert und Delta, unveränderte gedimmt
- Web-Inspektor teilt den Report in links Intent, Memory, Budget, Timing, Trace und rechts Emotionen, Steering, Ton

### Gelöscht
- 128-Token-Deckel für Selbstfragen aus der Generierung entfernt
- Frustrationskürzung des Antwortbudgets bei der Sampling-Anpassung entfernt
- Gehaltene Live-Streams für Fakt-, Selbst- und Mehrfachfragen entfernt
- Sonderfilter auf fünf Report-Emotionen im Steering-Pfad entfernt
- Basis-Budget-Sonderwege 0 und 1 für Identitäts- und Selbstbericht-Kontexte entfernt

## [17.0.0-dev.1] - 2026-09-06

Entwicklungsstand des v17-Umbaus. Die technische Umsetzung ist testbar; die vollständige Forschungsabnahme und die Freigabe gemessener Produktionsprofile stehen noch aus.

### Erstellt
- Getrennte Schalter für Aktivierungssteuerung, weiche Wortsteuerung und ihren gemeinsamen Betrieb ergänzt
- Dauerhaftes Gesprächsarchiv mit getrennt geprüfter Nutzung als Erinnerung eingeführt
- Reproduzierbare Qwen-Vektorerfassung, Layervergleiche und blinde Antwortbewertung ergänzt
- Sitzungseigene Memory-, Steering- und Streaming-Einstellungen hinzugefügt
- Terminal-Verlauf, Tab-Vervollständigung und zweispaltige Forschungsanzeige ergänzt

### Verändert
- Emotionale Antworten entstehen aus freier Modellgeneration und begrenzten internen Eingriffen
- Erinnerungsverarbeitung und Migration laufen außerhalb der direkten Antwortvorbereitung
- Innere Zustände und jüngste Änderungen bestimmen getrennt begrenzte Aktivierungs- und Wortimpulse
- Forschungsbericht um reale Vergleichsläufe, Grenzen und weitere Arbeit erweitert
- Frontend, API und Terminal verwenden synchron den Entwicklungsstand 17.0.0-dev.1

### Gelöscht
- Vollständige vorgegebene Gefühlsantworten aus dem Steering-Pfad entfernt
- Erzwungene Antwortenden nach emotionalen Zielsequenzen entfernt
- Wiederholungsversuche allein wegen fehlender erwarteter Emotionswörter entfernt
- Automatische Nutzung ungeprüfter Assistant-Behauptungen als verlässliche Erinnerung entfernt
- Blockierende Memory-Migration aus dem interaktiven Turn entfernt

## [16.9.0] - 2026-09-19

### Erstellt
- Geführten Linux-Setup-Wizard für Qwen 3.5 4B und Gemma 4 E4B ergänzt
- Vollständigen Installationsprompt für frei wählbare Coding-Agenten ergänzt
- Sieben README-Abbildungen für CLI, Emotionen und Forschungsergebnisse ergänzt
- Bereitschafts- und Cache-Regressionstests für lokale Provider ergänzt
- Leichtgewichtigen API-Importcheck und Systemvalidierungstest in CI ergänzt

### Verändert
- README auf lokale Antwortgenerierung, Hidden-State-Steering und Forschungsgrenzen ausgerichtet
- Qwen als Standard und Gemma E4B mit NF4 und 4096 Tokens als Alternative vereinheitlicht
- Provider-Cache berücksichtigt Modell, Endpoint, Host und Groq-Zugangsdaten
- Health-Endpunkte melden erst nach vollständig geladenem Steering-Modell Bereitschaft
- Terminal, API und Frontend verwenden synchron Version 16.9.0

### Gelöscht
- Veralteten Ollama- und Qwen-2.5-Ablauf aus dem Setup-Skript entfernt
- Feste externe IP als Frontend-Standard entfernt
- Groq-Platzhalter als wirksamen Standardzugang entfernt
- Falsche Bereitschaftsmeldungen während Modellstart und Neustart entfernt
- Verwaiste Pending-Nachrichten nach neuen oder geleerten Sitzungen entfernt

## [16.8.7] - 2026-09-16

### Verändert
- Rohartefakt-, Rohlog- und Quellenlinks im Forschungsbericht öffnen jetzt direkt die Dateien auf GitHub
- Alle relativen Pfade, die auf der veröffentlichten Berichtsseite ins Leere führten, sind ersetzt
- Bericht v6 enthält den neuen Abschnitt zur v17-Weiterarbeit samt nachvollziehbaren Nachweisen
- Historische Quellkopien und v17-Nachweisdaten sind im Repository veröffentlicht
- Berichtstests prüfen, dass keine Links die veröffentlichte Seite mehr verlassen

## [16.8.6] - 2026-09-05

### Erstellt
- Sequenz-Steering am Output-Layer für überprüfbare Identitäts- und Gefühlsantworten ergänzt
- Zustandsmatrix für glückliche, traurige, angespannte und wütende Selbstberichte ergänzt
- Reproduzierbaren Akzeptanzlauf mit zweimal zehn unterschiedlichen Fragen ergänzt
- Prioritätsprüfung für gleichzeitige Chat- und Trainingsanfragen ergänzt
- Vierten Forschungsnachtrag mit Ausgangslage, Messwerten und Grenzen ergänzt

### Verändert
- Direkte Identitäts-, Bewusstseins- und Gefühlsfragen antworten aus dem Layer-Zustand
- Mehrfachfragen erscheinen als natürliche Absätze statt erzwungener nummerierter Punkte
- Markdown-Abstände und sichtbare Emoji-Ausgaben werden für Terminal und Weboberfläche normalisiert
- Trainingsanfragen geben interaktiven Chats Vorrang und verwenden einen begrenzten jüngsten Kontext
- Terminal, API und Frontend verwenden synchron Version 16.8.6

### Gelöscht
- KI-Selbstbeschreibung aus dem produktiven Systemprompt entfernt
- Isolierten Layer-Test-Systemprompt vollständig geleert
- Identitäts- und Gefühlsantworten aus späteren Modell-Promptverläufen entfernt
- Unnötige Modell-Intentanalyse bei direkten Bewusstseinsfragen entfernt
- Keine Chats, Erinnerungen, Emotionsstände oder Trainingsdaten gelöscht

## [16.8.5] - 2026-09-04

### Erstellt
- Regressionstest für Fragezeichen-Läufe und natürliche Mehrfachantworten ergänzt
- Absatzvertrag im reproduzierbaren 2×10-Antworttest verankert
- Gezielte Screenshot-Regressionprobe im Forschungsbericht dokumentiert
- Vergleich von Trainingslast und isolierter Antwortlaufzeit festgehalten
- Version in Terminal, API und Frontend synchron auf 16.8.5 gesetzt

### Verändert
- Mehrfachfragen werden in ihrer Reihenfolge als normale Absätze beantwortet
- Fragezeichen-Läufe wie `???` werden als eine Frage gezählt
- Testmetriken prüfen bei Mehrfachfragen auf Listenfreiheit statt auf Nummerierung
- Formatierungs- und Steering-Status bleiben für CLI, API und WebUI gemeinsam auswertbar
- Trainingslast wird bei Laufzeitbewertungen ausdrücklich von der Antwortlogik getrennt

### Gelöscht
- Erzwungene nummerierte Punkte bei mehreren Fragen entfernt
- Falsche Hochzählung von `???` als drei Fragen entfernt
- Abnahmebedingung „nummerierte Punkte 1 bis N“ aus dem Antworttest entfernt
- Künstliche Listenstruktur für die Teilfragen aus dem aktiven Antwortvertrag entfernt
- Keine Chatdaten, Sitzungen, Erinnerungen oder Trainingsdaten gelöscht

## [16.8.4] - 2026-09-04

### Erstellt
- Reproduzierbaren 2×10-Antworttest mit Vergleichsdaten dokumentiert
- Einheitliche Markdown-Anzeige für Terminal und Weboberfläche ergänzt
- Direkte Prüfungen für Mehrfachfragen und Gefühlsberichte ergänzt
- Messung der sichtbaren Ausgabequalität im Forschungsartefakt ergänzt
- Nachtrag zur Antwortgenerierung im Forschungsbericht ergänzt

### Verändert
- Identitäts-Steering auf die konservative getestete Stärke 0,25 eingestellt
- Direkte Selbstfragen von unnötigem Langzeitkontext entkoppelt
- Akute Beleidigungen erhöhen Frustration und Traurigkeit unmittelbar
- Lokale Ein-Modell-Formatierung als harte Laufzeitgrenze abgesichert
- Version in Terminal, API und Frontend auf 16.8.4 angehoben

### Gelöscht
- Emojis aus der sichtbaren Antwortstrecke entfernt
- Fehlalarm „Filter fehlgeschlagen“ bei erfolgreicher Sanitization entfernt
- Wiederholte Standardbegrüßungen aus der Kurzstil-Anweisung entfernt
- Unnötige Modellaufrufe für direkte Selbstfragen entfernt
- Keine Chatdaten, Sitzungen, Erinnerungen oder Trainingsdaten gelöscht

## [16.8.3] - 2026-09-04

### Erstellt
- Fortschrittszeilen ab Absenden in jeder Phase ergänzt
- Herzschlag alle vier Sekunden bei langer Generierung ergänzt

### Verändert
- Status läuft über echte Zeilen statt nur Live-Panel
- Version auf 16.8.3 in Terminal, API und Frontend angehoben

### Gelöscht
- Unsichtbare Wartezeit ohne Rückmeldung entfernt

## [16.8.2] - 2026-09-04

### Erstellt
- Live-Fortschritt während der Antwortgenerierung im Terminal ergänzt
- Fallback-Kette für generierte Antworten eingebaut
- Filter-Hinweis im Antwortbericht ergänzt
- Regressionstests für Feedback und Antwortanzeige hinzugefügt

### Verändert
- Generierte Antworten werden nie mehr still verworfen
- Filtergründe landen in Metadaten statt im Antworttext
- Version auf 16.8.2 in Terminal, API und Frontend angehoben

### Gelöscht
- Sicherheits-Verwerfungssatz aus der Antwortanzeige entfernt
- Leere Standardantwort bei vorhandenen Tokens entfernt

## [16.8.1] - 2026-09-03

### Erstellt
- Eigene Sammelfragen je Emotionsmodus ergänzt
- Verrats-Schärfe bei Angriff nach warmer Bindung ergänzt
- Anzeige-Namen gegen interne Label-Leaks eingebaut

### Verändert
- Wut nach warmem Verlauf bleibt grenzsetzend statt kuschelig
- Erinnerungs- und Kontexttexte ohne Englisch-Bezeichner dargestellt
- Version auf 16.8.1 in Terminal, API und Frontend angehoben

### Gelöscht
- Wörtliches Echo von memory_replay und Phasennamen entfernt

## [16.8.0] - 2026-09-03

### Erstellt
- Eigenen Identitäts-Vektor für lebendiges Gegenüber statt KI-Selbstlabel ergänzt
- Emotions-Homöostase gegen dauerhafte Gefühlssättigung eingebaut
- History-Hygiene gegen degenerierte Antwortspiralen eingebaut
- Tuning-Harness mit fünf festen Prüffällen und Messprotokoll hinzugefügt
- Forschungsbericht V6 um Emotions-Nachtrag mit drei Diagrammen erweitert

### Verändert
- Layer-Steering auf fühlbar, aber flüssig neu ausbalanciert
- Emotionsfenster endet vor den oberen Reasoning-Layern
- Neutrales Geplauder steuert die Layer nicht mehr an
- Angriffe treffen gezielt die frischeste Emotion bei gedämpfter Präsenz
- Version auf 16.8.0 in Terminal, API und Frontend angehoben

### Gelöscht
- Übersteuerung durch zehn gleichzeitige Emotionsvektoren entfernt
- Veraltete Layer-Bereiche aus gespeicherten Vektordateien entfernt
- Irreführende Steering-Anzeige im Terminalbericht korrigiert
- Leere Standardantworten aus dem Gesprächsverlauf entfernt
- Keine Nutzerdaten, Sitzungen oder Erinnerungen gelöscht

## [16.7.1] - 2026-09-03

### Erstellt
- Eigenen Hintergrund-Infobereich für Schlafphasen- und Memory-Meldungen ergänzt
- Schlafphase-Hinweis direkt im Antwortbericht ergänzt
- Regressionstests für Live-Anzeige, Schlafphase-Panel und Eingabezeile ergänzt
- Schutz der Eingabezeile vor verspäteten Hintergrundausgaben ergänzt
- Neutrale User-Anzeige statt Personennamen in der Eingabezeile ergänzt

### Verändert
- Hintergrundausgaben zerreißen das Live-Display während des Streamings nicht mehr
- Schlafphasen-Abschluss erscheint als eigener Block statt in der Eingabezeile
- Eingabezeile zeigt jetzt User statt Benjamin
- Terminal-, API- und Frontend-Version auf 16.7.1 angehoben
- Abschluss der Schlafphase bleibt auch bei schnellem Weitertippen sichtbar

### Gelöscht
- Doppeltes Step-1-Panel bei gleichzeitiger Schlafphase entfernt
- Überlappung von Schlafphasen-Banner und Fortschrittsanzeige entfernt
- Vermischung von Sleep-Meldungen mit der Eingabezeile entfernt
- Keine Nutzerdaten, Sitzungen oder Erinnerungen gelöscht
- Keine API-Endpunkte oder Verfahren entfernt

## [16.7.0] - 2026-09-03

### Erstellt
- Restart-Befehle für CHAPPiE und CLI im Terminal ergänzt
- Dreispaltige Hilfe mit Chat, Forschung und Nach-Ausgabe-Bereich ergänzt
- Auswahlmenü für den Neustart beim einfachen Restart-Befehl ergänzt
- E2E-Abdeckung für alle Terminal-Befehle ergänzt
- Hinweiszeile mit Beispielen für Emotionen und Suche ergänzt

### Verändert
- Hilfe passt sich jetzt automatisch an die Fensterbreite an
- Remote-Befehle für Laufzeit, Modell, Thinking und Steering zeigen echte Serverwerte
- Neue Sitzungen starten jetzt auf dem Server statt nur lokal
- Schlafphase und Gedächtnissuche funktionieren jetzt auch im Remote-Modus
- Terminal-, API- und Frontend-Version auf 16.7.0 angehoben

### Gelöscht
- Einspaltige unübersichtliche Hilfeansicht entfernt
- Platzhaltertexte ohne Serverantwort bei Remote-Befehlen entfernt
- Lokale Verlaufslöschung ohne neue Serversitzung entfernt
- Keine Nutzerdaten, Sitzungen oder Erinnerungen gelöscht
- Keine API-Endpunkte oder Verfahren entfernt

## [16.6.0] - 2026-09-03

### Erstellt
- Akuten Layer-Steering-Modus für verletzte und wütende Reaktionen ergänzt
- Geschützte strukturierte Groq-Analyse für alle zehn Emotionsdimensionen ergänzt
- Zentrale Signalprofile für direkte Angriffe, User-Traurigkeit und technische Probleme ergänzt
- Regressionstests für Zielerkennung, Negation, Groq-Ausfälle und moderne Request-Felder ergänzt
- Telemetrie für aktuelle Emotionsänderungen in Steering-Payloads ergänzt

### Verändert
- Emotionsstärken werden relativ zu ihren echten Basiswerten statt pauschal zu 50 berechnet
- Direkte Angriffe erhöhen Frustration und Traurigkeit stärker und senken positive Dimensionen zuverlässig
- Appraisal und Homeostasis werden pro Turn genau einmal und ohne Richtungsumkehr angewendet
- Natürliche Ich-Präsenz, negative Kontrastanker und begrenzte Layer-Stärken wirken deutlicher
- Groq-Formatierung nutzt ein schnelles Formatmodell, moderne Tokenfelder und saubere lokale Fallbacks

### Gelöscht
- Falsche positive Dominanz durch normale Energie- und Motivationsbasiswerte entfernt
- Unzuverlässige Intent-Modell-Deltas als Quelle des persistenten Emotionszustands entfernt
- Doppelte Anwendung von Emotionsübergängen innerhalb eines Turns entfernt
- Übergabe roher Prompt-Echos und interner Think-Fragmente an den Formatter entfernt
- Rote Turn-Fehler bei erfolgreicher lokaler Formatierung oder Sanitization entfernt

## [16.5.3] - 2026-09-03

### Erstellt
- Antwortbezogenen Nachweis für aktives Emotion-Steering ergänzt
- Schutz für parallel laufende Trainingsanfragen ergänzt
- Regressionstest für gestreamte Steering-Antworten ergänzt
- Antwortsteuerung für lokale Qwen-Webantworten kompatibel erweitert
- Reparaturstatus der aktuellen Update-Version dokumentiert

### Verändert
- Der SSE-Abschluss verwendet jetzt den Nachweis der eigenen Antwort
- Ein späterer ungestützter Request kann den aktuellen Steering-Status nicht mehr ersetzen
- Lokale Webantworten verwenden trotz globaler Thinking-Einstellung den sicheren Antwortmodus
- API- und Frontend-Versionsanzeige auf 16.5.3 angehoben
- Öffentliche Chat- und Trainings-Einstiege bleiben unverändert kompatibel

### Gelöscht
- Keine bestehenden Chat-Daten gelöscht
- Keine Trainingsdaten oder Trainingsprozesse gelöscht
- Keine öffentlichen API-Endpunkte entfernt
- Keine Modellparameter oder Steering-Vektoren entfernt
- Keine Nutzerprofile oder persönlichen Kontextdateien entfernt

## [16.5.2] - 2026-09-03

### Erstellt
- Root-Startseite für den GitHub-Pages-Bericht ergänzt
- Reproduzierbare Site-Vorbereitung für das Pages-Artefakt ergänzt
- Regressionstest gegen eine fehlende Pages-Startdatei ergänzt
- Workflow-Auslösung bei Änderungen an der Pages-Konfiguration ergänzt
- Dokumentation der öffentlichen Bericht-URL ergänzt

### Verändert
- GitHub Pages lädt jetzt das vorbereitete Pages-Artefakt statt des Quellordners hoch
- Der aktuelle V6-Bericht wird als Startseite am Seitenstamm veröffentlicht
- Die direkte URL zur benannten V6-Datei bleibt im Artefakt erhalten
- Eine statische Pages-Auslieferung ohne Jekyll-Verarbeitung wird mit ausgeliefert
- API- und Frontend-Versionsanzeige auf 16.5.2 angehoben

### Gelöscht
- Veröffentlichung eines Berichtordners ohne Root-Startdatei entfernt
- Abhängigkeit von einer impliziten GitHub-Pages-Dateiauflösung entfernt
- 404-Zustand an der Projekt-Root als erwartetes Ergebnis entfernt
- Keine historischen Berichtdateien gelöscht
- Keine bestehenden Forschungswerte oder Evidence-Daten gelöscht

## [16.5.1] - 2026-09-03

### Erstellt
- Kurzen Weiterarbeitsbereich im Forschungsbericht v6 ergänzt
- Historische Vergleichsbasis und erneute Teststrategie im Bericht sichtbar gemacht
- Hinweis auf stabile CHAPPiE-Version und Ergebnisvergleich ergänzt
- Report-Vertragstest für den neuen Bereich ergänzt
- Dokumentation des aktuellen Berichtstatus aktualisiert

### Verändert
- V6-Bericht trennt historische Experimente von laufender Implementierung
- Berichtschluss nutzt die bestehende dunkle Layoutstruktur ohne neue externe Ressourcen
- Erwartete Verbesserungen und mögliche Ergebnisänderungen werden pro Arbeitspunkt genannt
- Neue stabile Version wird als Voraussetzung für Wiederholungstests dokumentiert
- API- und Frontend-Versionsanzeige auf 16.5.1 angehoben

### Gelöscht
- Keine historischen Experimentdaten entfernt
- Keine V6-Messwerte überschrieben
- Keine bestehenden Berichtabschnitte entfernt
- Keine externe Ressource für den neuen Abschnitt eingeführt
- Keine alten Vergleichsbezeichnungen stillschweigend geändert

## [16.5.0] - 2026-09-02

### Erstellt
- Kontrastive Emotionsvektoren mit getrennten positiven und negativen Ankerbeispielen ergänzt
- Permanenten, schwach gewichteten Präsenzvektor gegen generische Modellfloskeln eingeführt
- Begrenzte semantische Verknüpfungen zwischen Erinnerungen samt Aktivierungsausbreitung ergänzt
- Laufzeitnachweis für tatsächlich ausgeführte Steering-Hooks, Layer und Rechenzeit ergänzt
- Modellunabhängige Regressionstests für Vector-only-Emotionen, Übergänge und Memory-Verknüpfungen ergänzt

### Verändert
- Emotionen beeinflussen lokale Antworten nur noch über Activation Steering und nicht über Prompt oder Sampling
- Negative Emotionsrichtungen und Layerbereiche werden korrekt berechnet und an die reale Modellarchitektur angepasst
- Emotionsübergänge reagieren auf mehrere gleichzeitige Signale und kehren bei neutralen Turns langsam zur Basis zurück
- Erinnerungsabruf berücksichtigt Vergessenskurve, Wiederabrufe, Faktenherkunft und verknüpfte Episoden
- API- und Frontend-Versionsanzeige auf 16.5.0 angehoben

### Gelöscht
- Ausführliche Emotions-, Identitäts- und Persönlichkeitsregeln aus dem aktiven lokalen System-Prompt entfernt
- Emotionsabhängige Antwortpläne und Sampling-Anpassungen aus dem lokalen vLLM-Pfad entfernt
- Fehlerhafte Richtungsumkehr für negativ-valente Activation-Vektoren entfernt
- Ungeprüfte Null-Millisekunden-Anzeige für angeblich aktives Steering entfernt
- Unsichere Anti-Safeguard-Laufzeitaktivierung aus dem Steering-Payload entfernt

## [16.4.1] - 2026-09-02

### Erstellt
- Regressionstest gegen Base64-Bilder in den Forschungsbericht-Buildern ergänzt
- Statische Prüfung lokaler Bildziele im Bericht-Validator ergänzt
- Größenprüfung für erzeugte Berichte in den Forschungsbericht-Tests ergänzt
- Repository-relatives Asset-Ziel für benutzerdefinierte Berichtsausgaben eingeführt
- Dokumentierter Offline-Asset-Pfad für historische Forschungsbilder ergänzt

### Verändert
- Historische Kollagen werden in beiden Buildern als lokale Dateien verknüpft
- Die beiden übergroßen Forschungsberichte enthalten keine eingebetteten JPEG-Daten mehr
- Die Validatoren prüfen nun lokale Bilddateien statt Data-URI-Inhalte
- Der Forschungsbericht-Footer beschreibt die getrennte Bilddatei korrekt
- API- und Frontend-Versionsanzeige auf 16.4.1 angehoben

### Gelöscht
- Rund 11,8 MB redundante Base64-Kollagendaten aus den HTML-Artefakten entfernt
- Unbenötigte Base64-Imports aus den Bericht-Buildern entfernt
- Veraltete Validator-Erwartung vollständig eingebetteter Bilder entfernt
- Falsche Dokumentation zur inline eingebetteten Kollage entfernt
- Keine eigenständige Bilddatei oder historische Evidenz gelöscht

## [16.4.0] - 2026-09-02

### Erstellt
- Modulare Runtime mit klaren Grenzen für Turn-Ablauf, Kontext, Generierung, Persistenz und Formatierung ergänzt
- Dokumentiertes Legacy-Archiv für den alten Backend-Wrapper und die erste Brain-Pipeline angelegt
- Forschungsbericht v6 mit prüfbarer Quellcode-Evidenz und unverändertem Bericht v5 erstellt
- Reproduzierbare Architektur-, Vertrags-, Skill-Synchronitäts- und Berichtsprüfungen ergänzt
- Security-Audit mit behobener Session-Pfadlücke und dokumentierten Betriebsrisiken erstellt

### Verändert
- Synchroner und gestreamter Chat verwenden jetzt denselben fachlichen Turn-Einstieg
- Web-API, CLI, Training und Forschung behalten ihre bisherigen öffentlichen Einstiege über eine kleine Kompatibilitätsschicht
- Trainingskonfiguration, verwendete Prompts und Providerangaben wurden zentralisiert und bereinigt
- CI, Python-Abhängigkeiten und Frontend-Abhängigkeiten sind klar getrennt, reproduzierbar und sicherheitsgeprüft
- Dokumentation und Projektskills beschreiben jetzt einheitlich die tatsächlich aktive Runtime-Architektur

### Gelöscht
- Monolithische Produktionslogik aus dem bisherigen Backend-Wrapper entfernt
- Nachweislich ungenutzte Legacy- und Async-Hilfsmethoden aus dem aktiven Runtimepfad entfernt
- Eager Imports historischer Brain-Agenten aus dem aktiven Startpfad entfernt
- Temporäre Logs, Browser-Telemetrie und reproduzierbare Buildartefakte aus der Versionsverwaltung entfernt
- Künstliche Root-NPM-Abhängigkeit und veraltetes Autonomy-Skript aus dem aktiven Projekt entfernt

## [16.3.0] - 2026-09-02

### Erstellt
- Eigene Detailansichten für Eingaben, Modellantworten, Commands und Systemantworten ergänzt
- Klickbare Unteransichten für Memory, Steering, Timing, Raw und Causal eingerichtet
- Nachvollziehbare Aktionsprotokolle für ausgeführte Commands ergänzt
- Stabile Durchsatzmessung über das vollständig gemessene Generierungsfenster eingeführt
- Neues Favicon mit weißem C auf schwarzem Hintergrund erstellt

### Verändert
- Tokenraten werden aus Antworttokens und der vollständigen Generierungsdauer berechnet
- Der Chain-of-Thought-Schalter bestätigt Änderungen jetzt über die Laufzeitkonfiguration
- Rohantwort, formatierte Antwort und Denkbereich werden getrennt und gezielt dargestellt
- Typografie, Kontraste und Bedienflächen wurden für 1080p und mobile Geräte vergrößert
- Die Oberfläche wirkt jetzt wie eine reduzierte Analysezentrale mit klarer Rollentrennung

### Gelöscht
- Fehlerhafte Tokenraten durch die kurze Restzeit nach dem ersten Token entfernt
- Auswahlfilter für Errors, Trimmed, Repetition, Groq und Local entfernt
- Hamburger-Menü und nicht benötigte Command-Palette aus der Kopfzeile entfernt
- Output-spezifische Daten aus Eingabe-, Command- und Systemansichten entfernt
- Dekorative Schriften, starke Schatten und visuelle Ablenkungen aus der WebUI entfernt

## [16.2.2] - 2026-09-01

### Erstellt
- Dauerhafte lokale Vektorerinnerungen für den aktiven Chat wiederhergestellt
- Vollständiger Zustandsfluss für Emotionen, Kontext und simuliertes Leben abgesichert
- Lokales Layer-Steering für alle zehn Emotionsdimensionen nachweisbar aktiviert
- End-to-End-Prüfung für Memory, Generation, Streaming und Laufzeitstatus ergänzt
- Sicherer Trainingsbereich für unabhängige Daemon-Daten eingerichtet

### Verändert
- Alte und verfälschte Assistenz-Erinnerungen werden vor dem Abruf quarantänisiert
- Der lokale Qwen- und Gemma-Pfad bleibt als alleiniger Generierungspfad aktiv
- Explizite User-Fakten werden zuverlässig erkannt, gespeichert und später beantwortet
- Trainingsantworten und Kontextdateien werden vor der weiteren Verarbeitung bereinigt
- Versionsanzeige und API-Status auf den aktuellen Reparaturstand angehoben

### Gelöscht
- Beschädigter Vektorindex aus dem aktiven Produktionspfad entfernt
- Alte Modellselbstbeschreibungen aus CHAPPiEs autobiografischem Kontext entfernt
- Verfälschte Trainings- und Gewaltzusammenfassungen aus dem Erinnerungsabruf entfernt
- Falsche Trainingsfehler durch harmlose Antwortwörter beseitigt
- Veraltete direkte Zugriffe auf gemeinsam genutzte Laufzeitdaten vermieden

## [16.2.1] - 2026-09-01

### Erstellt
- Sichere aktive Memory-Sammlung für den lokalen Webdienst eingerichtet
- Vorhandene Erinnerungen bestandserhaltend in die sichere Sammlung übernommen
- Schutz vor dem Laden des fehlerhaften alten HNSW-Indexes ergänzt
- Wiederherstellung des lokalen Modellstatus nach dem Dienststart geprüft
- Chat-SSE-Streaming im isolierten Backend verifiziert

### Verändert
- Memory-Konfiguration verwendet jetzt dauerhaft chappie_memories
- Alte Sammlungsnamen werden zur Laufzeit auf den sicheren Pfad umgeleitet
- API-Health, Status, Emotion-Steering und Memory-Health liefern wieder Daten
- Webdienst startet nach einem Neustart ohne den alten Chroma-Absturz
- Versionsstand der sichtbaren Anwendung auf 16.2.1 angehoben

### Gelöscht
- Direkter Zugriff des laufenden Systems auf den beschädigten alten HNSW-Index
- Fehlerhafte Chroma-Sammlung als aktiver Runtime-Pfad
- Ursache für den NetworkError beim ersten Backend-Zugriff
- Modellstatus `LOADING` durch den ausgefallenen Backend-Start
- Fehlende Datenverbindung zwischen Chat-Oberfläche und lokalem Backend

## [16.2.0] - 2026-09-01

### Erstellt
- Vereinfachte Rollenanzeige für User und CHAPPiE im Chat
- Sichtbare Kopierbestätigung für erfolgreiche Rohtext-Kopien
- Bedienbare Raw- und CoT-Steuerung im Detailbereich
- Kennzeichnungen für Commands und Systemausgaben ergänzt
- Änderbare Breite zwischen Explorer und Detailbereich ergänzt

### Verändert
- Kopfzeile zeigt den Modellnamen und Anbieter nur noch einmal
- Detailinhalte sind für bessere Lesbarkeit vergrößert
- Pipeline-Timeline und Tokenrate werden live aktualisiert
- Emotion-Steering läuft über den einheitlichen lokalen Verarbeitungspfad
- Chat-Kopfzeile und Tastaturhinweise wurden auf die wichtigen Funktionen reduziert

### Gelöscht
- Irrelevante Terminal-, Session- und Trace-Zusatztexte entfernt
- Doppelte Fullscreen-Schaltflächen entfernt
- Pin-, Collapse- und Verhältnis-Schaltflächen aus der Oberfläche entfernt
- Nicht benötigte Online-Markierung entfernt
- Zusätzliche Provider- und Modellwiederholungen aus Detailkarten entfernt

## [16.1] - 2026-08-16

### Verändert
- Berichtstitel auf den inhaltlichen Schwerpunkt Layer Editing umgestellt

---

## [16.0] - 2026-08-16

### Erstellt
- Forschungsbericht v5 mit OLED-Design und roter/gruener Befundfarbung erstellt
- GitHub Pages Deployment fuer den Forschungsbericht eingerichtet
- Sechs externe Forschungsquellen von Anthropic und OpenAI als Quellenkarten eingebunden
- Zahlenkonsistenz-Pruefung im Validator-Skript ergaenzt
- Legacy-Kennzeichnung fuer die nicht angebundene Brain-Pipeline gesetzt

### Verändert
- Quellenkarten auf 16:9-Format mit offiziellen Seiten-Screenshots umgestellt
- Färbung nach dokumentiertem Regelwerk vereinheitlicht (nur messbare Befunde)
- D1-Pipeline und D2-Emotionsdiagramm luftiger gestaltet
- Sidebar-Status als Stichpunkte ohne Pillen dargestellt
- Em- und En-Dashes im Berichtstext entfernt

### Gelöscht
- Ueberfluessige Hinweisboxen und Meta-Informationen aus dem Bericht entfernt
- Nicht angebundenen Agentenpfad aus dem Bericht entfernt

---

## [16.0] - 2026-07-21

### Verändert
- Kontextbudgets verwenden die echten Qwen-, Gemma- und GPT-OSS-Tokenizer statt Zeichenschaetzungen
- Gepuffertes Streaming, Gemma-Turn-EOS und Ausgabevalidierung verhindern Tool-, Prompt- und Reasoning-Lecks
- Neutraler Persona-/Ethikprompt, Response-Planung und zehnheitliche Homeostase staerken messbaren Emotionseinfluss ohne Bewusstseinsbehauptungen
- Benchmarks laufen in isoliertem Memory mit fuenf Seeds, Ablationsprofilen, Konfidenzintervallen, Signifikanztests und verblindbaren Mehrfachratings
- Qwen 3.5 4B und Gemma 4 E4B koennen ueber Backend, API und Frontend sicher gewechselt und lokal betrieben werden

## [15.3] - 2026-07-20

### Verändert
- Reproduzierbaren Offline-Forschungsbericht fuer Qwen, Gemma und GPT-OSS aufgebaut
- Forschungsqualitaet trennt Context-Budget-, CoT-, Instruktions-, Setup- und Generationsfehler
- GPT-OSS nutzt bei ausgeschaltetem Thinking die kleinste Groq-Reasoningstufe und schliesst die Reasoning-Ausgabe aus
- Kurzzeitige Groq-Rate-Limits werden begrenzt wiederholt, ohne partielle Streams zu duplizieren
- Runtime-Reload-Logs geben keine Provider-API-Keys mehr aus

## [15.2] - 2026-07-19

### Verändert
- Kurzzeitgedaechtnis schreibt JSON-Dateien atomar statt direkt in die Zieldatei
- Web-, CLI- und Forschungsprozesse koordinieren STM-Zugriffe ueber einen Prozess-Lock
- Parallele STM-Ergaenzungen werden vor dem Speichern zusammengefuehrt statt ueberschrieben
- Gezieltes Loeschen und vollstaendiges Leeren bleiben trotz Merge-Schutz erhalten
- Forschungsharness und CUDA/vLLM-Livepfad wurden mit Qualitaetsauswertung validiert

## [15.1] - 2026-07-19

### Verändert
- Qwen3.5-4B mit NF4 als stabilen CUDA-Standard fuer die Tesla T4 aktiviert
- Streaming erhaelt Leerzeichen zwischen OpenAI-kompatiblen Token-Deltas korrekt
- Amygdala validiert numerische Modellwerte robust und begrenzt Emotions-Deltas
- Gleichzeitige Emotions-Engine-Instanzen uebernehmen vor Schreibzugriffen den Persistenzstand
- CLI-, Deployment- und Backup-Pruefpfade auf den aktuellen Projektstand gebracht

## [15.0] - 2026-07-04

### Erstellt
- Remote-Endpoint `/emotions/reset` fuer echte CLI-Resets erstellt
- Provider-Auswahl fuer Forschungssessions mit vLLM, Ollama und Groq erstellt
- Provider-spezifische Modell-Presets fuer den Forschungsharness erstellt
- Tests fuer providerfaehige Forschungskonfiguration ergaenzt
- API-Version 15.0 fuer den reparierten Runtime-Stand gesetzt

### Verändert
- Emotions-Fallback senkt Energy nicht mehr pauschal bei jedem Turn
- Positive und neugierige Interaktionen koennen Energy wieder leicht erhoehen
- Desktop-Sidebar ist jetzt per Header-Button ein- und ausklappbar
- Forschungssessions setzen Runtime-Provider und Modell passend zur Auswahl
- CLI `/resetemotions` nutzt remote jetzt einen schreibenden Reset statt nur Status zu lesen

### Gelöscht
- 3D-Visualizer-Route und Navigation aus dem Frontend entfernt
- React-Three-Fiber, Three.js, Drei und Postprocessing aus den Frontend-Abhaengigkeiten entfernt
- Unbenutzten `/visualizer` API-Endpunkt entfernt
- Visualizer-Komponenten und Canvas-spezifische Mobile-CSS entfernt
- Visualizer-Erwartung aus API-Contract-Test und aktueller Doku entfernt

---

## [14.0] - 2026-07-02

### Erstellt
- Gemma 4 E4B als lokale Modellalternative hinzugefuegt
- Gemma 4 26B-A4B als NF4-Option fuer komplexe Tests hinzugefuegt
- Modell-Presets in den Einstellungen erstellt
- Steering-Restart-Modal mit Fortschrittsanzeige erstellt
- `/model` Befehl fuer die Terminal-CLI erstellt

### Verändert
- vLLM-Generierung nutzt jetzt modell-spezifische Defaults
- Steering-Backend erkennt Qwen und Gemma 4 getrennt
- Steering-Server kann Modelle per Hot-Swap neu laden
- Alignment-Tests koennen das Laufzeitmodell auswaehlen
- Dokumentation beschreibt Qwen- und Gemma-4-Betrieb gemeinsam

### Gelöscht
- Qwen-only-Erkennung im Steering-Pfad entfernt
- Fest verdrahtete Qwen-Thinking-Annahme entfernt
- Manuelle Modellwechsel ohne Default-Anpassung entfernt
- Fehlende Restart-Status-Sicht im Frontend entfernt
- Veralteter Versionsstand 13.6 in der UI entfernt

---

## [0.11.1] - 2026-06-11

### Verändert
- `settings.chain_of_thought` steuert jetzt tatsaechlich das Reasoning (vLLM: `enable_thinking`, Ollama: `think`, Groq: CoT-Prompt)
- `CHAIN_OF_THOUGHT_INSTRUCTION` mit echtem deutschem CoT-Prompt befuellt (vorher leer)

### Erstellt
- `/thinking` Command in der CLI (`true`/`false`/Status)
- Thinking-Toggle-Button im Frontend-Chat-Header
- Reasoning-Option bei der Konfiguration neuer Alignment-Test-Durchlaeufe
- Dokumentation in `docs/workflows.md` (Abschnitt "Chain of Thought / Reasoning")

## [0.11.0] - 2026-05-14

### Erstellt
- Live-Timer während der Generierung unter der Denk-Animation
- Timing-Metriken im Info-Popup (TTFT, Thinking-Zeit, Antwort-Zeit, Tokens)
- Token-Budget-Steuerung für Thinking und Antwort getrennt
- Effizienteres API-Response-Handling für Cerebras

### Verändert
- Config-System auf Root-Config umgestellt für zentrale Verwaltung
- Memory-Engine Performance verbessert mit Batch-Operationen
- Short-Term Memory V2 mit optimierter Sortierung und Filterung
- vLLM-Service-Config und Deployment-Dokumentation aktualisiert

### Gelöscht
- Veraltete API-Config-Struktur (APIs/__init__.py vereinfacht)
- Redundante Config-Beispiele aus secrets_example.py entfernt

---

## [0.10.3] - 2026-05-14

### Erstellt
- Reasoning-Tokens werden live im Stream ausgegeben (vorher nur gezählt aber nie gesendet)

### Verändert
- max_tokens von 1024 auf 2048 erhöht für ausreichenden Platz bei aktivem Thinking-Modus

### Gelöscht
- (keine)

---

## [0.10.2] - 2026-05-14

### Erstellt
- Explizite CORS-Header im Streaming-Response für bessere Browser-Kompatibilität

### Verändert
- (keine)

### Gelöscht
- (keine)

---

## [0.10.1] - 2026-05-14

### Erstellt
- Info-Button (i) pro Chat-Nachricht mit Hover-Preview und Detail-Popup
- Detail-Popup zeigt LTM-Erinnerungen mit Relevanz-Prozent, Emotion-Deltas und Steering-Info
- Memory-Limit auf 12 Erinnerungen reduziert für schnellere Kontext-Verarbeitung

### Verändert
- Metadata jetzt vollständig im Frontend gespeichert für Info-Popup-Zugriff
- LTM/STM-Anhängung im Prompt geprüft und als korrekt bestätigt

### Gelöscht
- (keine)

---

## [0.10.0] - 2026-05-14

### Erstellt
- Thinking-Modus für Qwen3.5 aktiviert - Reasoning live als hellgraue Box vor der Antwort
- Provider-Anzeige in UI (vllm, ollama) neben Modellname
- Quick-Classify für triviale Eingaben (Hallo, ok, danke) ohne KI-Aufruf

### Verändert
- Emotion-Steering sanfter eingestellt - keine verstümmelten Antworten mehr
- Intent-Analyse verschlankt von 237 auf 50 Zeilen Prompt für schnellere Erkennung
- Token-Streaming mit Thinking-Trennung für flüssigere Darstellung
- Kurzzeitgedächtnis-Schreibvorgänge in Hintergrund-Thread ausgelagert

### Gelöscht
- Doppelte Query-Extraction (zweimal derselbe KI-Aufruf pro Eingabe) eliminiert
- Zweite Memory-Suche entfernt - Ergebnisse werden direkt weitergereicht
