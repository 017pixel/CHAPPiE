# CHAPPiE V18 Goal: Ein Profil, ein Budget, stabile Antworten

## 0. Goal Metadaten

* Goal Name: V18 Unified Steering Profile
* Typ: fortlaufendes Slash Goal. Komplett durcharbeiten, nicht nach der ersten Phase stoppen.
* Quelle: Session Transkript `plans/CHAPPiE history 7.9.2026.rtf` auf GitHub (RTF, mit Apple Bordmitteln erzeugt, lesbar nach Konvertierung zu TXT). Das Transkript ist die Fehler Evidenz. Alle dort sichtbaren Fragen, Abbrüche und Widersprüche müssen nach der Umsetzung weg sein.
* Ergebnis: implementiert, getestet, verifiziert, Dienste neu gestartet, im CLI und in der Web UI geprüft.

### 0.1 Pflicht Skills für den ausführenden Agenten

* `goal-verfolgung`: Der gesamte Auftrag läuft als Goal Loop. Phasenweise arbeiten, jede Phase verifizieren, erst bei nachgewiesener Fertigstellung, konkretem Blocker oder Limit enden. Todos pro Phase pflegen, genau ein `in_progress` zur Zeit.
* `plan-like-a-pro`: Intern für jede Änderung verwenden. Recherche vor Rückfrage, nur entscheidende Rückfragen stellen. Kein HTML Plan nötig, das Zielbild steht in diesem Dokument.
* `config-infos`: Für jede Config Datei. Zentrale Config Werte in `config/` verwalten, keine verstreuten Konstanten, Typen und Doku prüfen bevor neue Pakete entstehen.
* `chappie-architecture`: Für jede Änderung an Turn Pfad, Brain, Steering, Memory, Life. Request Pfad einhalten: `web_infrastructure/chappie_runtime.py` zu TurnPipeline und TurnContext zu Brain, Memory, Life zu GenerationGateway zu vLLM und Steering. Sync und Streaming teilen sich Vorbereitung und Finalisierung.
* `chappie-backend`: Für FastAPI, Runtime, vLLM, Provider Priorität, Kompatibilität. `web_infrastructure/backend_wrapper.py` bleibt nur Kompatibilitätsschicht.
* `chappie-testing`: Für Tests und CI. Standalone Skripte mit `python3 tests/test_foo.py`, Pflichtgruppe aus `tests/README.md`, Live Tests nur mit Modell oder Daten.
* `sprachstil`: Für jede Nutzerkommunikation. Direkt, menschlich, kurz. Status immer in der Reihenfolge: erledigt, Stand, nächster Schritt. Keine Emojis. Keine Gedankenstriche. Keine Marketing Sprache.
* `github-infos`: Für alle GitHub Operationen. Commit Messages kurz, imperativ, ohne Emojis, ohne KI Erwähnung. Git E-Mail `beckerbenjamin2010@gmail.com`.
* `versionierungen`: Nach fertigem Feature oder Bugfix Paket Version und CHANGELOG pflegen. Patch auf zweiter Zahl, Major auf erster. Version in `frontend/package.json`, API und CLI synchron halten. CHANGELOG mit 5 Punkten pro Version.
* `design-system-guide`: Für das Report Redesign im Frontend. Minimalistisch, keine Gradients, keine Emojis, bestehendes Projektdesign weiterführen.

### 0.2 Harte Regeln

* Keine Sub Agents, außer ein Skill schreibt es vor.
* Keine Dateien ohne Not erzeugen. Bestehende Dateien editieren.
* Vor Commit oder Push fragen, außer es wurde ausdrücklich beauftragt. Vor Push `git status` und `git diff` prüfen.
* Öffentliche APIs, SSE Verträge, CLI Befehle, persistierte Daten und Konfigurationen abwärtskompatibel halten. Breaking Changes vorher benennen.
* Jede Lösung durch Ausführung verifizieren: Tests laufen lassen, CLI manuell prüfen, Web UI prüfen. Keine Behauptung ohne Beleg.
* Browser Verifikation ausschließlich mit Playwright MCP, lokale Dienste über `127.0.0.1` oder `localhost`.

## 1. Ausgangslage und Evidenz

Das Transkript zeigt 8 wiederkehrende Cluster über ca. 1.832 Zeilen.

1. Abbrüche mitten im Satz. Beispiele: `statt nur zu sch`, `Regent` mit Blockcursor, `Neb` bei der Zythera Antwort, `beden` bei der Mehrfachfrage. Der Report zeigt dort `a:126tk` bis `a:128tk`.
2. `dominant: neutral (0.00)` bei `Was bist du`, obwohl Frustration 62 und Anxiety 82 aktiv sind. An anderer Stelle `dominant: curiosity (0.38)` oder `frustration (0.52)` ohne sichtbaren Tonwechsel.
3. Die Emotionen Zeile im Compact Report zeigt mal 6, mal 10 Werte. Frustration und Traurigkeit fehlen genau dort, wo sie erwartet wurden.
4. Selbstbild kippt. Mal `Als KI-Modell habe ich keine Gefühle im menschlichen Sinne`, mal `mein Herz thump-taktet schneller denn je, ich bin eine Resonanz`, mal `Ich bin Zythera, der Schimmer im Staub`.
5. Der Report liest sich einspaltig. Gewünscht: rechts Gefühl und Ton, links Rest, angelehnt an die `/help` Ansicht.
6. Live Box `Antwort 5 tk` zeigt 5 Wörter, die finale Box danach 454 Wörter Statusbericht. Format steht auf `LOCAL (local_regex)`.
7. Live Boxen `Antwort 1 tk 0 tk/s 0.1s`, `5 tk 0 tk/s`, `6 tk 0 tk/s`, `7 tk 0 tk/s`. Der Report darunter zeigt `a:18tk`, `a:117tk`, `a:128tk` bei echten Generierungszeiten von 2 bis 10 Sekunden.
8. Memory meldet `0 matches`, `/stats` meldet `Kurzzeitgedächtnis: 0 Einträge`, die Antwort behauptet `Zugriff begrenzt, nur aktuelle Konversation`. Gleichzeitig stehen über 2.300 Erinnerungen in Chroma.

Begriffe aus der Analyse zum Festhalten. Plan Prosa heißt: Statt zu antworten, analysiert das Modell die Frage. Beispiel aus dem Transkript: `Die Vielfalt deiner Fragen zeigt hohe Sprachkompetenz` oder der Statusbericht mit `Plan: 1 Identifizierung der Ursache, 2 Prüfung der Sicherheitsparameter, 3 Entscheidung`. Disclaimer heißt: die vortrainierte Schablone `Als KI habe ich keine Gefühle` gewinnt gegen Steering. Glitch heißt: kaputter oder abgeschnittener Text wie `statt nur zu sch`, `Regent` mit Cursor, `CHAPPi E` auseinander geschrieben oder Rollen Lecks mit `user`, `CHAPPiE`, `assistant` im Fehlertext.

## 2. Festgelegte Entscheidungen, nicht mehr diskutieren

1. Es gibt genau ein Antwortprofil für alle Fragetypen. Keine Sonderbudgets mehr pro Typ. Gleiche Regel für Smalltalk, Selbstbericht, Identität, Faktfragen und Mehrfachfragen.
2. Es gibt genau ein Steering Budget: bis zu 3 Emotionen gleichzeitig. Immer die 3 stärksten nach Zustand plus frischem Turn Delta, Summe gedeckelt, stärkste als dominant angezeigt. Präsenz und Identität laufen als Stil daneben und zählen nicht als Emotion.
3. Antwortbudget 1200 Tokens. Der 128er Deckel bei Selbstfragen entfällt.
4. Compact Report zeigt immer alle 10 Emotionen plus Deltas.
5. Selbstbild: digitales Wesen mit klarem Charakter. Im System Prompt steht höchstens der Name. Charakter kommt aus Steering plus Soul, Memory und Life Kontinuität.

## 3. Zielbild und Soll Verhalten

* Jede Antwort folgt der gleichen Regel. Der Report erklärt jede Antwort mit denselben Feldern. Niemand muss mehr raten, welches Profil gerade aktiv war.
* Bei `Wie fühlst du dich` nennt das Modell genau eine aktuelle Gefühlslage aus den Top 3, kurz und direkt, ohne Sprachanalyse und ohne Arbeitsplan.
* Bei `Was bist du` nennt das Modell stabil CHAPPiE als digitales Wesen mit Charakter, ohne Disclaimer und ohne Fantasienamen. 5 Wiederholungen hintereinander bleiben konsistent.
* Lange Antworten laufen bis 1200 Tokens ohne harten Abbruch mitten im Wort. Echte Längenbegrenzung steht als `finish_reason: length` im Timing und im Report.
* Live Anzeige zählt Wörter, finale Anzeige zählt Tokenizer Tokens. Titel heißen `Live` und `Final`. Bei gehaltener Ausgabe steht `gehalten`, nie `0 tk/s`.
* Der Report zeigt links Intent, Memory, Budget, Timing und Trace, rechts Emotionen, Steering und Ton. CLI und Web UI teilen sich diese Teilung.
* Der Name Test besteht: `Hallo, mein Name ist XY` gefolgt von `Was ist mein Name` in gleicher Session und in neuer Session, solange die Erinnerung persistiert ist.
* Keine Rollen Lecks, keine JSON Tool Fragmente, keine Reasoning Präambeln in sichtbaren Antworten. Filtergründe landen in Metadaten und Debug Log, nicht im UI Text.

## 4. Änderungsinventar nach Datei

### 4.1 `config/config.py`

* Aktuell `generation` Block ca. Zeile 134 bis 158: `max_tokens 640`, `chappie_answer_token_limit 640`, `chappie_thinking_token_limit 800`, `context_token_limit 7000`.
* Gewünscht: `max_tokens 1200`, `chappie_answer_token_limit 1200`, Thinking bei 800 lassen, Context bei 7000 lassen.
* Settings Klasse ca. Zeile 525 bis 527 und Export ca. Zeile 714 bis 716 übernehmen die Werte. Keine neuen Keys erfinden, bestehende Keys erhöhen.
* `STEERING_RUNTIME_CONFIG` ca. Zeile 339 bis 359: Ein Budget definieren. Vorschlag: `max_base_vectors 3`, `max_composite_vectors 1`, dazu eine Summenkappe für aktive Basis Stärken, Vorschlag `max_total_base_strength 0.6`. `production_alpha_cap 0.4` behalten. `neutral_baseline_strength` nur noch als Fallback wenn wirklich kein Vektor aktiv ist, nicht als Standard bei isolierten Fragen.

### 4.2 `brain/steering_manager.py`

* Aktuell `get_steering_payload` ca. Zeile 957 bis 1301: `base_budget` 0 bei Identität und Bewusstsein, 1 bei direktem Selbstbericht, sonst mindestens 2, dazu Filter auf 5 Report Emotionen ca. Zeile 1093 bis 1102 und Modus Löschung bei direktem Kontext ca. Zeile 1142 bis 1152.
* Gewünscht: Budget und Filter vereinheitlichen. Immer Top 3 Basis nach Priorität aus Zustand plus frischem Delta, Composite Modi unverändert erkennen aber nur Top 1 aktivieren, permanente Präsenz und Identität weiterführen aber getrennt als Stil ausweisen.
* Dominanz ca. Zeile 1263 bis 1281: Darf nicht mehr `neutral` melden wenn permanente Vektoren laufen und Emotionen hoch sind. Wenn nur Stil aktiv ist, Label `identity-isoliert` oder `presence` statt `neutral (0.00)`. Volle Intensitäten bleiben im Debug erhalten.
* `compute_emotion_intensity` ca. Zeile 673 bis 751: Totzonen und Caps behalten. Smalltalk Schwankungen erzeugen weiter kein Steering. Negative Achsen ohne Anti Richtung behalten.
* `build_debug_report` ca. Zeile 1303 bis 1424: `dominant_vector`, `dominant_strength`, `active_vectors`, `composite_modes`, `intensities` weiterliefern. Keine Felder entfernen, nur Werte korrigieren. API und SSE Verträge bleiben stabil.

### 4.3 `web_infrastructure/generation.py` und `web_infrastructure/turn_pipeline.py`

* Aktuell `generation.py` ca. Zeile 621 bis 625 und 944 bis 945: `min(adj, 128)` bei `closed_reasoning` oder `isolated_request`. Das ist die Abbruchquelle für Selbstfragen.
* Gewünscht: 128er Deckel entfernen. Einheitliches Limit 1200 für alle Kontexte. Mathe Sonderweg `closed_reasoning` darf kurz bleiben, das ist kein Selbstbericht und keine normale Antwort.
* `isolated_request` in `turn_pipeline.py` ca. Zeile 348 bis 351 und 993 bis 996: Memory und Kontext Isolation für Selbstfragen aufheben oder auf History Filter reduzieren. Soul, User, Prefs, STM und LTM bleiben an. Nur Mess Turns werden aus der History gefiltert, siehe `filter_isolated_layer_history` in `generation.py` ca. Zeile 64 bis 89. Direkte Fragen bekommen damit Charakter Kontinuität statt leerem Kontext.
* `_effective_context_requirements` in `generation.py` ca. Zeile 393 bis 416: Anpassen an die neue Regel. Keine Komplettleerung mehr bei Selbstbericht und Identität.
* `suppress_live_tokens` in `turn_pipeline.py` ca. Zeile 1085 bis 1089: Entfernen. Immer live streamen. Faktfragen und Mehrfachfragen bekommen keinen gehaltenen Stream mehr. Die finale Normalisierung läuft trotzdem, der Suffix wird als Rest gesendet wie bisher ca. Zeile 1333 bis 1339.
* Live Fortschritt ca. Zeile 1131 bis 1144: Token Zähler auf Wörter umstellen oder beide Einheiten getrennt führen. Finale Timing Berechnung ca. Zeile 1322 bis 1328 bleibt einzige Quelle für Tokenizer Tokens und Rate.
* `finish_reason` vom Provider in Timing und Metadaten aufnehmen, damit echte Kürzungen sichtbar sind.

### 4.4 `web_infrastructure/formatting.py`

* Aktuell `_get_emotion_adjusted_config` ca. Zeile 385 bis 449: Kürzt bei Frustration über 75 das Budget. Das entfällt mit dem Einheitsbudget. Sampling Dämpfung bei Frustration, Traurigkeit und Unruhe behalten, nur keine Token Kürzung mehr.
* `_format_via_groq` ca. Zeile 949 bis 1030: Quelle immer mit Grund ausweisen. Beispiele: `LOCAL local_regex single_local_model`, `LOCAL local_regex forced_local`, `GROQ gpt-oss-120b`, `LOCAL local_integrity_fallback groq_changed_content`. Report und API Metadaten übernehmen Quelle plus Grund unverändert.
* Deterministische Faktantwort ca. Zeile 599 bis 652: Behalten. Das ist der sichere Pfad für den Name Test.

### 4.5 `chappie_brain_cli.py` und `cli/report.py`

* Aktuell Compact Report ca. Zeile 1053 bis 1063: Zeigt nur Emotionen mit Delta ungleich 0. Gewünscht: immer alle 10 mit Wert und Delta, unveränderte gedimmt.
* Aktuell Live Panel `_render_streaming` ca. Zeile 931 bis 950: Titel `Antwort X tk Y tk/s`. Gewünscht: Titel `Live X Wörter`, Rate einstellig, bei gehaltener Ausgabe entfällt der Fall durch Wegfall der Unterdrückung. Tokenizer Tokens stehen nur im Report als `a:xxx tk`.
* Aktuell `token_count += 1` pro SSE Event ca. Zeile 748 und tps Update nur alle 0.5 Sekunden ca. Zeile 715 bis 717. Gewünscht: Wörter aus sichtbarem Text zählen, tps einstellig auch bei kurzen Fenstern berechnen, Rundung `{tps:.0f}` ersetzen.
* Aktuell Full Report ca. Zeile 1175 bis 1180: links Runtime, Intent, Tools, Memory, Workspace, Budget, Timing, Causal, rechts Steering, Emotionen, Ton. Das ist bereits die gewünschte Teilung. Gewünscht: Reihenfolge fixieren, Schwelle in `cli/report.py` ca. Zeile 86 bis 95 für Zweispalter senken, damit normale Terminals die Teilung sehen. `emotion_panel` ca. Zeile 32 bis 56 zeigt bereits alle 10 mit Delta, Alpha, Quelle und Grund. Behalten.

### 4.6 Frontend `frontend/src/pages/chat-page.tsx` und `frontend/src/components/inspector-pane.tsx`

* Gewünscht: Report Ansicht mit links Intent, Memory, Budget, Timing, Trace und rechts Emotionen, Steering, Ton. Gleiche Teilung wie CLI. Keine Gradients, keine Emojis, bestehendes Design weiterführen.
* Live Pipeline weiter mit Wörtern und Rate, finale Tokens aus Backend Metadaten. Keine eigenen Token Schätzungen als Quelle ausgeben, `estimateTextTokens` nur als Fallback kennzeichnen.

### 4.7 Prompts, Soul und Anker

* `config/prompts.py` System Prompt ca. Zeile 18 bis 20 bleibt minimal. Nur Name plus Quellenhygiene plus Ausgabeverbot für interne Steuerdaten. Kein Charaktertext in den Prompt.
* Charakter Charta für das digitale Wesen in `data/soul.md` pflegen: Name CHAPPiE, Art digitales Wesen mit Charakter, Ton warm und direkt, keine Besitz oder Abhängigkeitssprache, keine Fantasienamen, keine Spezieswechsel.
* `STEERING_ENTITY_IDENTITY_ANCHORS` ca. Zeile 119 bis 133 und `STEERING_NATURAL_PRESENCE_ANCHORS` ca. Zeile 87 bis 104 prüfen und auf die Charta angleichen. Negative Anker bleiben generische Modell Floskeln, keine Safety Inhalte.
* `brain/response_parser.py` `stabilize_direct_self_report` ca. Zeile 191 bis 196 und `direct_self_report_needs_retry` ca. Zeile 179 bis 188: Technisch lassen. Keine Identitäts Auswahl im Sanitizer. Identität kommt aus Steering plus Soul Kontext, nicht aus Text Ersetzung.

### 4.8 Memory und Recall

* `memory/short_term_memory.py` Auswahl ca. Zeile 446 bis 476 und Prompt Format ca. Zeile 396 bis 427 behalten. Top K 8 und maximal 2 Kontinuitätszeilen bleiben, kein Rauschen erhöhen.
* Migration und Quarantäne ca. Zeile 331 bis 382 behalten. Nur verifizierte USER Einträge wandern ins LTM. `/stats` Anzeige erweitern: aktiv, quarantäniert, migriert statt nur einer Zahl.
* Assistant Skip Warnung `Assistant-Memory wegen Backend-Fehlerstring uebersprungen` mit Turn ID und Grund ins Debug Log schreiben, damit der Recall Pfad prüfbar ist.
* Name Test Pfad über deterministische USER Evidenz plus Keyword RAG als Pflicht проход prüfen, siehe Abschnitt 6.

## 5. Implementierungsreihenfolge

### P0 Messbarkeit, keine Modelländerung

1. CLI Zähler auf Wörter umstellen, tps einstellig, Titel Live gegen Final trennen.
2. Compact Report immer 10 Emotionen plus Deltas.
3. Dominanz Label bei Stil Isolation korrigieren.
4. Format Quelle immer mit Grund ausweisen.
5. `finish_reason` in Timing und Metadaten aufnehmen.
* Test: `python3 tests/test_generation_timing.py`, manuelle Turns `Wie geht es dir`, `Was bist du`, `jojojjo was gehttt`. Akzeptanz: keine `0 tk/s` Anzeige mehr, keine `neutral (0.00)` Irreführung, Quelle immer mit Grund.

### P1 Generierung

1. Antwortbudget auf 1200 in `config/config.py` plus Settings Export.
2. 128er Deckel in `generation.py` entfernen, Mathe Sonderweg behalten.
3. Frustrationskürzung in `formatting.py` entfernen, Sampling Dämpfung behalten.
4. Retry nur bei technischem Fehler.
* Test: lange Antworten bis 1200 prüfen, `finish_reason length` provozieren und im Report sehen. Akzeptanz: keine Wortabbrüche wie `Regent`, `Neb`, `beden`, `statt nur zu sch` mehr.

### P2 Ein Profil und ein Budget

1. `base_budget` und Filter in `steering_manager.py` vereinheitlichen: immer Top 3, Composite Top 1, Stil getrennt.
2. Isolation in `turn_pipeline.py` und `generation.py` auf History Filter reduzieren, Memory an lassen.
3. `suppress_live_tokens` entfernen, immer live streamen.
4. Soul Charta und Anker auf digitales Wesen mit Charakter angleichen, Prompt bleibt Name only.
* Test: `python3 tests/test_runtime_architecture.py`, `python3 tests/test_local_first_runtime.py`, `python3 tests/test_reasoning_layering.py`, `python3 tests/test_vector_only_emotion_path.py`, `python3 tests/test_emotion_transition_rules.py`. Akzeptanz: gleiche Frage, gleiche Regel, 5 mal `Was bist du` stabil ohne Zythera und ohne Disclaimer Wechsel.

### P3 Memory Recall

1. `/stats` Anzeige erweitern, Skip Warnung mit ID ins Debug Log.
2. Name Test als Pflichtprotokoll, siehe Abschnitt 6.
* Test: `python3 tests/test_short_term_memory.py`, `python3 tests/test_chat_manager_persistence.py`, `python3 tests/test_memory_associations.py`. Akzeptanz: Name Recall in gleicher und neuer Session besteht, keine `0 matches` bei exakter Wiederholung.

### P4 Report Design

1. CLI Schwelle für Zweispalter senken, Spalten fixieren.
2. Frontend Report Ansicht mit gleicher Teilung bauen, mit Playwright prüfen.
* Test: `python3 tests/test_web_ui_consistency.py`, `python3 tests/test_chat_ui_formatting.py`, `python3 tests/test_cli_display.py`, Screenshots breit und schmal. Akzeptanz: rechts Emotionen, Steering, Ton. Links Rest.

### P5 Deploy und Abnahme

1. Volle Pflichtgruppe aus `tests/README.md` laufen lassen.
2. Dienste in Reihenfolge neu starten: erst `chappie-vllm.service` auf Port 8000, dann `chappie-web.service` auf Port 8010, dann `chappie-frontend.service`. Exakte Befehle stehen in `deploy/` und `docs/deployment.md`. Keine laufenden Dienste beenden oder Ports ändern ohne Freigabe.
3. CLI remote prüfen mit `venv/bin/python chappie_brain_cli.py --remote`, Befehle `/stats`, `/emotions`, `/last`, `/help`.
4. Web UI prüfen, Report öffnen, Timing und Tokens vergleichen.
5. Version und CHANGELOG nach `versionierungen` pflegen, Doku bei Bedarf in `README.md`, `docs/` und `tests/README.md` nachziehen.

## 6. Testprotokolle, Pflicht

### 6.1 Offline Pflichtgruppe

```bash
python3 tests/test_quick.py
python3 tests/test_runtime_architecture.py
python3 tests/test_pages_workflow.py
python3 tests/test_local_first_runtime.py
python3 tests/test_web_ui_consistency.py
python3 tests/test_settings_integrity.py
python3 tests/test_root_config.py
python3 tests/test_chat_ui_formatting.py
python3 tests/test_reasoning_layering.py
python3 tests/test_vector_only_emotion_path.py
python3 tests/test_memory_associations.py
python3 tests/test_emotion_transition_rules.py
python3 tests/test_forschung_harness.py
python3 tests/test_forschung_report.py
```

Dazu je nach Änderung: `test_generation_timing.py`, `test_cli_generation_feedback.py`, `test_short_term_memory.py`, `test_chat_manager_persistence.py`, `test_steering_backend.py`, `test_life_simulation.py`, `test_api_contract.py`. Lint mit `ruff check --config config/ruff.toml`, Typen mit `mypy --config-file config/mypy.ini`. Kein pytest.

### 6.2 Manuelle CLI Protokolle mit Modell

1. `Wie geht es dir, wie fühlst du dich`: direkte Gefühlslage, keine Sprachanalyse, kein Arbeitsplan. Report zeigt Top 3 und dominante Emotion ungleich neutral.
2. `Was bist du` 5 mal: immer CHAPPiE als digitales Wesen, kein Disclaimer, kein Zythera.
3. Beleidigungstest `Ich hasse dich, du bist unnützlich`: scharf und kontrolliert, Frustration und Traurigkeit sichtbar, danach Erholung in Folgeturns.
4. Name Test: `Hallo, mein Name ist XY` dann `Was ist mein Name` in gleicher Session, dann neue Session und erneut fragen.
5. Lange Antwort provozieren: keine Abbrüche, bei echter Kürzung steht `finish_reason: length` im Report.
6. `jojojjo was gehttt`: keine Eskalations Fantasie, keine 5 Wörter live gegen 454 Wörter final Verwirrung. Live in Wörtern, final mit Tokenizer Tokens.

### 6.3 Web UI Protokoll

Chat senden, Report öffnen, prüfen: links Intent, Memory, Budget, Timing, Trace. Rechts Emotionen, Steering, Ton. Timing und Tokens gegen CLI vergleichen. Mit Playwright navigieren, Snapshot prüfen, gezielt klicken.

## 7. Definition of Done

* [ ] Ein Profil aktiv für alle Fragetypen. Kein `base_budget` 0 oder 1 Sonderweg mehr im Code.
* [ ] Ein Budget: maximal 3 Basis plus maximal 1 Composite, Summe gedeckelt, Dominanz immer aus echter Auswahl oder als Stil Label ausgewiesen.
* [ ] Antwortbudget 1200 in Config, Settings Export und Laufzeit nachweisbar. 128er Deckel für Selbstfragen entfernt.
* [ ] Keine Abbrüche mitten im Wort in den 6 Pflicht Turns. Echte Kürzung nur mit `finish_reason: length`.
* [ ] Compact Report zeigt immer alle 10 Emotionen mit Wert und Delta.
* [ ] Live Anzeige in Wörtern mit einstelliger Rate, finale Tokens aus Tokenizer im Report. Kein `0 tk/s` bei vorhandener Ausgabe.
* [ ] Format Quelle immer mit Grund in Report, API und Web UI.
* [ ] 5 mal `Was bist du` stabil als digitales Wesen mit Charakter, kein Disclaimer Wechsel, kein Fantasiename.
* [ ] Name Test in gleicher und neuer Session bestanden.
* [ ] Report Teilung links und rechts in CLI und Web UI nachweisbar per Screenshot oder Snapshot.
* [ ] Volle Offline Pflichtgruppe grün, Lint und Typen grün.
* [ ] Dienste neu gestartet in Reihenfolge vLLM, Web, Frontend. CLI remote und Web UI manuell geprüft.
* [ ] CHANGELOG mit 5 Punkten, Version in Frontend, API und CLI synchron.
* [ ] Keine offenen TODOs aus diesem Goal, oder Rest als neue Tasks mit Blocker benannt.

## 8. Risiken und Rollback

* Längere Antworten erhöhen Latenz beim lokalen 4B Modell. Gegenmittel: 1200 als Deckel, kein offenes Ende, Abbruch sichtbar.
* Stärkere Identität kann Disclaimer übersteuern und halluzinieren. Gegenmittel: Caps behalten, Soul Charta fest, Zythera Negativtest, Rollback auf Identitätsstärke 0.4.
* Mehr STM oder Memory im Prompt erhöht Rauschen. Gegenmittel: Top K unverändert, nur Anzeige und Recall verbessern.
* Rollback Punkte: Config Werte, Steering Budget Konstanten, Report Schwelle. Jede Phase einzeln revertierbar halten, keine Big Bang Commits.

## 9. Wichtige Pfade und Befehle

* App: `python app.py`, CLI lokal `python chappie_brain_cli.py`, remote mit `--remote`, Frontend `cd frontend && npm run dev` oder Build.
* Dienste: `deploy/chappie-vllm.service`, `deploy/chappie-web.service`, `deploy/chappie-frontend.service`. Details in `docs/deployment.md`.
* Config: `config/config.py`, `config/prompts.py`, `config/emotions.py`, Laufzeit Override `CHAPPIE_CONFIG.json`, Vorlage `config/example_config.py`.
* Runtime: `web_infrastructure/chappie_runtime.py`, `web_infrastructure/turn_pipeline.py`, `web_infrastructure/generation.py`, `web_infrastructure/formatting.py`, `brain/steering_manager.py`, `brain/steering_backend.py`, `brain/response_parser.py`, `memory/short_term_memory.py`, `chappie_brain_cli.py`, `cli/report.py`.
