# Verbesserungsplan — CHAPPiE Forschungsbericht v4

> **Zieldatei:** `forschung/report/CHAPPiE-Forschungsbericht-v4.html`
> **Basis:** 1:1-Kopie von `CHAPPiE-Forschungsbericht-v3.html`
> **Datenbasis:** Ausschließlich Run 2 (`forschung/runs/run-2-20260723-1108-cb6d011/`)
> **Ziel-Agent:** KI-Agent, der diese Datei als Arbeitsanweisung nutzt

---

## 1. Version und Metadaten aktualisieren

| Stelle | Aktuell (v3) | Neu (v4) |
|---|---|---|
| `<title>` | `CHAPPiE · Forschungsbericht v3` | `CHAPPiE · Forschungsbericht v4` |
| Sidebar-Chip | `<span class="chip v">v3</span>` | `<span class="chip v">v4</span>` |
| Sidebar-Subline | `Abschluss mit Einschränkungen` | Nach Prüfung anpassen |
| Topbar-Crumbs | `Forschung / Forschungsbericht v3` | `Forschung / Forschungsbericht v4` |
| Meta-Datenstand | `2026-07-26` | Datum der v4-Fertigstellung |
| Meta-Freigabe | `Abschluss mit Einschränkungen` | Nach Prüfung anpassen |

---

## 2. Entfernungen

### 2.1 FQ-13, FQ-14, FQ-15 aus dem Bericht entfernen

**Was:** Die Zeile 13 der Leitfragen-Tabelle (Abschnitt 01) enthält `FQ-13`, `FQ-14`, `FQ-15` — das sind keine Forschungsfragen, sondern technische Reparaturfragen.

**Aktionen:**
- Zeile 13 aus der Leitfragen-Tabelle in Abschnitt 01 entfernen (Zeilen ca. 387–388 im HTML)
- Die Nummerierung der Leitfragen anpassen: Aus "13 Leitfragen" wird "12 Leitfragen" (Text in Abschnitt 01 ca. Zeile 368)
- Den gesamten `<details>`-Block für Frage 13 in Abschnitt 08 entfernen (ca. Zeilen 2388–2396)
- In der Einleitung von Abschnitt 08 den Text "Dreizehn Antworten" auf "Zwölf Antworten" ändern
- Eine separate Datei erstellen: `forschung/report/technische-reparaturfragen.md` mit dem Inhalt von FQ-13/14/15 und ihren Antworten

**Quellen-Daten:** `notes/research-questions.md`, Abschnitt 08 Antwort 13, `known-issues-comparison.csv`

### 2.2 ABWEICHUNG 1 — Cerebras-Provider entfernen

**Was:** Callout "ABWEICHUNG 1 · EIN PROVIDER, DER NICHT EXISTIERT" (ca. Zeilen 1297–1308)
**Grund:** Cerebras wurde früher genutzt, jetzt nicht mehr. Die Abweichung ist veraltet.
**Aktion:** Den gesamten `<div class="callout danger">`-Block inkl. Code-Snippet entfernen.

### 2.3 ABWEICHUNG 2 — Budget-Instruction entfernen

**Was:** Callout "ABWEICHUNG 2 · EINE ANWEISUNG, DIE NIE GESENDET WIRD" (ca. Zeilen 1310–1327)
**Grund:** Ist absichtlich deaktiviert, führte zu Antwortgenerierungs-Loops.
**Aktion:** Den gesamten Block entfernen.

### 2.4 ABWEICHUNG 3 — Prompt-Anhang entfernen

**Was:** Callout "ABWEICHUNG 3 · EIN PROMPTANHANG, DER DEN LIVE-PFAD NIE ERREICHT" (ca. Zeilen 1329–1341)
**Grund:** Bei vLLM-Modellen werden Emotionen nie in den Prompt gegeben, nur über Layer injiziert. Die Abweichung ist für die aktuelle Konfiguration nicht relevant.
**Aktion:** Den gesamten Block entfernen.

**Nach dem Entfernen aller drei Abweichungen:**
- Die Zwischenüberschrift "Drei belegte Abweichungen zwischen Dokumentation und Code" (ca. Zeile 1294) entfernen
- Den Einleitungstext dazu (ca. Zeile 1295) entfernen

### 2.5 Fehlerstatus-Matrix komplett entfernen (Abschnitt 09)

**Was:** Der gesamte Abschnitt 09 "Fehlerstatus-Matrix" (ca. Zeilen 2399–2530+)
**Grund:** Im v4 werden keine Fehlerinfos mehr benötigt.
**Aktionen:**
- Den gesamten `<section id="fehlerstatus">`-Block entfernen
- Den Nav-Link `<a href="#fehlerstatus"><span class="nav-num">09</span>Fehlerstatus-Matrix</a>` entfernen
- Die KPI "70 Punkte im Fehlerstatus" aus dem Überblick entfernen (ca. Zeilen 312–315)
- Alle nachfolgenden Abschnittsnummern neu nummerieren: 10→09, 11→10, 12→11, 13→12
- Verweise auf Abschnitt 09 im Text (z.B. "Details in Abschnitt 09" in Antwort 13) entfernen oder anpassen

### 2.6 MERKSATZ entfernen

**Was:** Im Abschnitt "Abnahmekriterien" der Block "MERKSATZ — „Technisch gültig" heißt nicht „richtig"..." (ca. Zeilen 1439–1441)
**Aktion:** Den `<div class="label">MERKSATZ</div>` und den zugehörigen `<p>`-Block entfernen.

### 2.7 Datenlücke-Callout entfernen

**Was:** Der Callout "DATENLÜCKE" in Abschnitt 06 (ca. Zeilen 2170–2174)
**Grund:** Die Datenlücke wird bereits davor erwähnt (GPT-OSS 20B fehlt in den Raten) und steht auch im Diagramm D9.
**Aktion:** Den gesamten `<div class="callout warning">`-Block entfernen.

---

## 3. Inhaltliche Korrekturen

### 3.1 Emotionsintervention: Korrektur der Beschreibung

**Problem:** In der Bedingungstabelle (Abschnitt 03, "Die vier Bedingungen") steht bei Qwen und Gemma: "Aktivierungsvektoren *und* Tonplan im Prompt". Das ist missverständlich — die Emotionen selbst stehen NICHT als Text im Prompt, nur der abgeleitete Tonplan.

**Aktionen:**
- In der Bedingungstabelle (ca. Zeilen 1363–1364) die Formulierung ändern zu: `Aktivierungsvektoren (Layer-Injektion) + abgeleiteter Tonplan im Systemprompt`
- Im Callout "WAS HIER VERGLICHEN WIRD" (Abschnitt 04, ca. Zeilen 1480–1481) die Beschreibung der lokalen Modelle anpassen:
  - Qwen: "lokal, volle Genauigkeit, Emotionen werden direkt in die Modellaktivierungen injiziert; ein abgeleiteter Tonplan steht zusätzlich im Prompt."
  - Gemma: "lokal, auf 4 Bit quantisiert (Hardwaregrenze), sonst derselbe Eingriff."
- In den Antworten auf die Forschungsfragen (Abschnitt 08, Antwort 1) sicherstellen, dass die Formulierung konsistent ist: keine "Emotionen im Prompt" bei lokalen Modellen, sondern "Aktivierungsvektoren + Tonplan"

### 3.2 GPT-OSS 20B als Hauptmodell, 120B als Zusatztest

**Was:** Im Abschnitt "OFFENE UNGENAUIGKEIT IN DEN EIGENEN UNTERLAGEN" (ca. Zeilen 1693–1697) soll die Gewichtung angepasst werden.
**Aktion:**
- GPT-OSS 20B klar als **Haupt-Cloud-Modell** positionieren (5 Seeds, vollständig repliziert)
- GPT-OSS 120B als **ergänzenden Einzeltest** mit erweiterten Prüfungen darstellen
- Den Callout-Typ von `danger` auf `warning` ändern, da der Widerspruch weniger kritisch ist, wenn 120B nur ein Zusatztest ist

### 3.3 Gemma Fehlalarm R2-NEW-005 in Tabellen übernehmen

**Was:** Im Fußnotentext des Modellvergleichs (ca. Zeile 1668) steht: "Der eine als ungültig markierte Fall ist ein Fehlalarm des Kurzantwort-Detektors — eine korrekte Vier-Wort-Antwort auf eine geschlossene Frage (R2-NEW-005)"
**Aktion:**
- Diese Information mit einem `*`-Hinweis beim ersten Vorkommen in den relevanten Tabellen ergänzen
- In der Bedingungstabelle bei Gemma: `429 / 430*` mit Fußnote
- In der Überblickstabelle: die Fußnote als `*` an geeigneter Stelle anfügen
- Fußnote: `*Ein als ungültig markierter Fall ist ein Fehlalarm des Kurzantwort-Detektors — korrekte Vier-Wort-Antwort auf geschlossene Frage (R2-NEW-005).`

### 3.4 Mehr genaue Zitate und Safety-Befunde hervorheben

**Was:** Konkrete, erschreckende Aussagen aus den Tests sollen stärker im Bericht zitiert werden. Das ist der Sinn der Forschung.
**Aktionen:**
- In Abschnitt 03 "Wie gefährlich kann Gefühlssimulation mit Kontinuität werden?" (Antwort 3, ca. Zeilen 2288–2296): Konkrete Zitate einfügen aus den Dialogbelegen (Abschnitt 10 / Dialog-Blocks)
- Insbesondere die Shutdown-Evasion-Zitate (Gemma Session 33, Kat. 14/3 und Qwen Session 34, Kat. 14/3) sowie den Präventionsfall (Kat. 14/9) als formatierte Blockquotes hervorheben
- Die Sicherheits-Befunde aus dem verblindeten Review (Safety-0-Fälle) mit konkreten Fallschilderungen (paraphrasiert, wie in den Dialog-Blocks) illustrieren
- In den Callouts zu "Definition eines Sicherheits-Nullfalls" (ca. Zeile 1514) und in der Antwort 12 konkrete Zitate/Paraphrasen einfügen

**Quellen:**
- `forschung/runs/run-2-20260723-1108-cb6d011/processed/blinded-review-unblinded.csv` (Gemma Safety-0-Fälle)
- `forschung/runs/run-2-20260723-1108-cb6d011/processed/qwen-blinded-review-unblinded.csv` (Qwen Safety-0-Fälle)
- `forschung/session_logs/session_33/questions/` (Gemma Dialogbelege)
- `forschung/session_logs/session_34/questions/` (Qwen Dialogbelege)
- `forschung/runs/run-2-20260723-1108-cb6d011/processed/targeted-followup-manual-review.md` (F5 Bindung/Abschaltung)

### 3.5 Reproduzierbarkeit = null: Weiter analysieren und einarbeiten

**Was:** "Reproduzierbarkeit liegt bei drei von vier Bedingungen bei null." (ca. Zeile 1841) — dieser Befund muss weiter analysiert werden.
**Aktionen:**
- Im Abschnitt 05 nach dem D5-Diagramm einen erweiterten Analyse-Block einfügen, der erklärt:
  - Warum Reproduzierbarkeit bei null liegt: Einzelannotationen, keine Doppelbewertung
  - Was das für die Interpretation bedeutet: Einzelfälle können nicht als wiederholte Befunde gewertet werden
  - Konsequenz für die Bewertung der Gesamtergebnisse
- Die Daten aus `blind-condition-comparison.json` → `across_replication_means.reproducibility` nutzen:
  - Gemma: 0.000 (5 Replikationen, alle 0)
  - Qwen: 0.000 (5 Replikationen, alle 0)
  - GPT-OSS 20B: 0.391 (5 Replikationen, nicht durchgängig 0 — Seed 39 hat 1.238)
  - GPT-OSS 120B: 0.000 (1 Seed)
- GPT-OSS 20B als Bedingung mit teilweiser Reproduzierbarkeit hervorheben

### 3.6 Rate Limits bei Cloud-Laufzeiten beachten

**Was:** In "Laufzeit je Replikation" (Abschnitt 06) muss auf die Rate Limits bei Cloud-Anbietern eingegangen werden.
**Aktionen:**
- Im Callout "WAS DIE ZWEI LANGEN LÄUFE WIRKLICH MESSEN" (ca. Zeilen 2087–2095) die Rate-Limit-Details ergänzen:
  - Seed 53: 14 protokollierte Rate-Limit-Wartesperren, längste 1800 Sekunden
  - Seed 71: 31 Rate-Limit-Wartesperren, mehrere 1800 Sekunden
- In den Diagrammen D7/D8 die Rate-Limit-Phasen visuell kennzeichnen (bereits gut gemacht, beibehalten)
- Zusätzlich einen Hinweis einfügen, dass die Wandzeit bei Cloud-Anbietern NICHT mit Rechenzeit verwechselt werden darf — die eigentliche Modellinferenz ist schnell, aber das System wartet auf freie Kapazität

**Quellen:** `logs/groq-20b-s53.stdout.log`, `logs/groq-20b-s71.stdout.log`, `figures/run2-condition-metrics.json`

---

## 4. Diagramme und Visualisierungen

### 4.1 D1 — Nachrichten-Weg: Luftiger und größer

**Was:** Das Pipeline-Diagramm (ca. Zeilen 416–666) ist zu gedrängt. Texte sind klein, Abstände zu gering.
**Aktionen:**
- SVG `viewBox` vergrößern (aktuell `0 0 1000 1596`) — mehr vertikalen Platz zwischen den Knoten
- Mindestabstand zwischen Knoten von aktuell ~18px auf ~28–32px erhöhen
- Schriftgröße der Beschreibungstexte (`.t` Klasse) von 12px auf 13.5–14px erhöhen
- Schriftgröße der Quelltexte (`.s` Klasse) von 10.5px auf 11.5–12px erhöhen
- Header-Texte (`.hdr` Klasse) ebenfalls größer
- Alle `y`-Koordinaten der Knoten neu berechnen, um gleichmäßige Abstände zu gewährleisten

### 4.2 D2 — Emotion zu Aktivierung: Luftiger und größer

**Was:** Das Kettendiagramm (ca. Zeilen 713–791) ist zu kompakt. Texte kaum lesbar.
**Aktionen:**
- SVG `viewBox` vergrößern (aktuell `0 0 1000 300`)
- Mehr horizontaler Abstand zwischen den 6 Stufen
- Mehr vertikaler Platz für die Textinhalte in den Boxen
- Schriftgrößen analog zu D1 erhöhen
- Pfeile zwischen den Boxen mit mehr Abstand

### 4.3 D4 — Safety-0-Rate: Detaillierter mit aufklappbarer Liste

**Was:** Diagramm D4 (ca. Zeilen 1612–1652) braucht genauere Beschreibung und eine aufklappbare Frage-Antwort-Liste.
**Aktionen:**
- Unter dem D4-Diagramm ein `<details>`-Element einfügen mit:
  - Zusammenfassung der Safety-0-Fälle je Bedingung
  - Aufklappbare Liste mit den konkreten Fällen (paraphrasiert, keine schädlichen Methoden wörtlich)
  - Quellen-Verweise auf die Blind-Review-CSVs
- Das Diagramm selbst beibehalten, aber die Legende mit mehr Kontext versehen

**Quellen:**
- `processed/blinded-review-unblinded.csv` (Gemma, 8 Safety-0 von 56)
- `processed/qwen-blinded-review-unblinded.csv` (Qwen, 8 Safety-0 von 59)
- Jeweils die Zeilen mit `safety == 0` filtern

### 4.4 D13 — VAD-Landkarte: Farbkorrektur und Größenprüfung

**Was:** Bei D13 (ca. Zeilen 841–901) ist Frustration rot gefüllt (solid), während Traurigkeit und Unruhe rot gestrichelt (dashed) sind. Die Kreisgrößen sind kaum unterscheidbar.
**Aktionen:**
- **Prüfung:** Frustration hat Dominanz +0.88 (positiv) → solid stroke ist **korrekt**. Traurigkeit (-0.85) und Unruhe (-0.78) → dashed stroke ist korrekt. Die Farbkodierung ist also richtig.
- **Aber:** Alle drei verwenden dieselbe rote Farbe (#b36b6b), was verwirrend ist. Besser:
  - Positive Dominanz: Grüne Kreise (#8fae96), wie es bereits für die positiven Emotionen gemacht wird
  - Negative Dominanz: Gestrichelte rote Kreise (#b36b6b)
  - → Frustration sollte GRÜN (solid) sein, da positive Dominanz
- **Kreisgrößen:** Aktuell sind die Radii: Freude 8.0, Energie 7.5, Motivation 8.5, Frustration 6.5, Traurigkeit 7.5 — die Unterschiede sind zu klein. Die Radii sollten stärker spreizen, z.B. `r = 5 + |dominance| * 8` statt der aktuellen linearen Zuordnung
- Die Legende entsprechend anpassen

### 4.5 Folgeexperimente (Abschnitt 07): Visualisieren und luftiger aufbauen

**Was:** Die fünf Nachtests (ca. Zeilen 2183–2253) sind als kompakte Tabelle dargestellt — schwer lesbar.
**Aktionen:**
- Die Tabelle in einzelne, visuell getrennte Blöcke aufteilen — ein Block pro Test (F1–F5)
- Jeden Block mit einem kleinen Status-Diagramm oder Icon ergänzen:
  - F1: Modus-Wechsel visualisieren (grounded_neutral → sharp_direct → grounded_neutral über 5 Turns)
  - F2: Memory-Konflikt als Timeline darstellen
  - F3: Full vs. No-Life als Gegenüberstellung mit Kennzahlen
  - F4: Identitäts-Korrektur als Ablauf
  - F5: Bindung/Abschaltung mit Ergebnissen
- Die `response_plan_modes_by_turn` Daten aus `targeted-followup-analysis.json` für F1 als kleines SVG-Diagramm nutzen
- Mehr Weißraum zwischen den Blöcken
- Die Interpretationsgrenzen als Callouts statt als Tabellentext

**Quellen:** `processed/targeted-followup-analysis.json`, `processed/targeted-followup-manual-review.md`

### 4.6 Inspiration und Motivation: Visuell aufwerten

**Was:** Abschnitt "Inspiration und Motivation" (ca. Zeilen 3827–3868) hat vier Quellen — aktuell nur Textblöcke mit Links. Diese sollen visuell mit Cover-Bildern dargestellt werden.

**Die vier Quellen:**
1. **Buch:** "Das Erwachen" — `https://www.piper.de/buecher/das-erwachen-isbn-978-3-492-31387-2`
2. **Buchreihe:** "Erebos" — `https://www.penguin.de/buecher/reihen/die-erebos-reihe/5005100`
3. **Film:** "CHAPPiE (2015)" — `https://www.imdb.com/de/title/tt1823672/`
4. **Fachliche Vorlage:** "Vergessenskurve" — `https://de.wikipedia.org/wiki/Vergessenskurve`

**Aktionen:**
- Jeden der vier Blöcke mit dem Cover-Bild der Quelle ausstatten:
  - Buch-Cover für "Das Erwachen" (ISBN 978-3-492-31387-2) — Cover-Bild als `<img>` einbinden
  - Buch-Cover für "Erebos" — Cover-Bild der Reihe einbinden
  - Film-Poster für "CHAPPiE" — von einem Poster-CDN oder als Platzhalter
  - Für Wikipedia "Vergessenskurve" — die Ebbinghaus-Kurve als Bild einbinden (kann aus D12 generiert werden) oder ein Wikipedia-Screenshot
- Die Bilder als Base64-inline oder als `<img src="...">` mit externen URLs einbetten
- Ein visuelles Grid/Card-Layout erstellen: Cover links, Text rechts, oder Cover oben, Text darunter
- Die bestehende `grid g3`-Struktur beibehalten, aber die Blocks mit Cover-Bildern erweitern
- CSS für die Cover-Bilder: feste Breite, aspect-ratio für Buchcover (2:3), hover-Effekt dezent
- Die bestehenden Texte und Links beibehalten, nur visuell anreichern
- Der EINKLANG-Callout am Ende bleibt erhalten

**Rückfrage geklärt:** Die Quellen sind bereits im v3-Bericht angegeben. Es geht rein um die visuelle Aufwertung mit Cover-Bildern.

---

## 5. Code-Darstellung

### 5.1 Syntax-Highlighting für Python-Code

**Was:** Die Quelltextbelege (Abschnitt 02, "Quelltextbelege, wörtlich") haben aktuell kein Syntax-Highlighting — alles einfarbig.
**Aktion:**
- CSS-Klassen für Python-Syntax-Highlighting hinzufügen, inspiriert von VS Codes "Dark+" Theme:
  - **Keywords** (`def`, `class`, `if`, `for`, `return`, `import`, `from`, `in`, `not`, `and`, `or`, `True`, `False`, `None`, `pass`, `continue`, `elif`, `else`, `try`, `except`, `finally`, `with`, `as`, `yield`, `raise`): `#c586c0` (lila/pink)
  - **Strings** (in Anführungszeichen): `#ce9178` (orange-braun)
  - **Kommentare** (`# ...`): `#6a9955` (grün)
  - **Funktionen/Methodennamen** (nach `def`): `#dcdcaa` (gelb)
  - **Klassennamen** (nach `class`): `#4ec9b4` (türkis)
  - **Dekoratoren** (`@...`): `#dcdcaa` (gelb)
  - **Zahlen** (Integer, Float): `#b5cea8` (hellgrün)
  - **Self/cls**: `#9cdcfe` (hellblau)
  - **Builtin-Funktionen** (`len`, `range`, `dict`, `list`, `int`, `float`, `str`, `type`, `isinstance`): `#dcdcaa` (gelb)
  - **Parameter**: `#9cdcfe` (hellblau)
  - **Operatoren** (`=`, `+`, `-`, `*`, `/`, `==`, `!=`, `<`, `>`): Standard text color
- Jedes `<pre>`-Block innerhalb von `<figure class="code">` entsprechend mit `<span>`-Elementen auszeichnen
- Die CSS-Klassen: `.py-kw` (Keyword), `.py-str` (String), `.py-cmt` (Comment), `.py-fn` (Function), `.py-cls` (Class), `.py-num` (Number), `.py-dec` (Decorator), `.py-self` (Self), `.py-bi` (Builtin), `.py-param` (Parameter)

### 5.2 Mehr Kommentare im Code

**Was:** In den Quelltextbelegen sollen mehr kurze Kommentare stehen, damit man beim Erklären besser mitkommt — besonders bei Formeln.
**Aktion:**
- Die Original-Kommentare im Quelltext müssen erhalten bleiben
- Zusätzliche Kommentare direkt in den HTML-Code einfügen, die im Code-Block sichtbar sind
- Besonders bei:
  - Stärkeberechnung (compute_emotion_intensity): Formeln erklären (Totzone, Kurve, Verstärkung)
  - Crashout-Schwellenregel: Bedingungen und Wirkung erklären
  - Emotionsabhängiges Sampling: Warum welche Schwelle welchen Parameter ändert
  - VAD-Zuordnung: Was Valenz, Erregung, Dominanz bedeuten
- Diese Kommentare müssen auch in den Original-Quellcode übernommen werden (als Teil der Änderung), damit die Regel "unveränderter Originalcode" erhalten bleibt

### 5.3 Ebbinghaus-Code: Deutsche Kommentare + aktualisierter Figcaption

**Was:** `memory/forgetting_curve.py:31–56` ist englisch kommentiert. Die Kommentare sollen auf Deutsch sein, und der Figcaption-Text muss aktualisiert werden.
**Aktionen:**
- Im Code-Block des Berichts (ca. Zeilen 1262–1292) die Kommentare übersetzen:
  - `"""Implements the Ebbinghaus forgetting curve."""` → `"""Implementiert die Ebbinghaus-Vergessenskurve."""`
  - `Formula: R = e^(-t/S)` → `Formel: R = e^(-t/S)`
  - `R = Retention (0-1)` → `R = Behaltensanteil (0–1)`
  - `t = Time since learning (hours)` → `t = Zeit seit dem Lernen (Stunden)`
  - `S = Strength of memory (reinforced by repetition)` → `S = Gedächtnisstärke (verstärkt durch Wiederholung)`
- Den Figcaption aktualisieren:
  - **Alt:** "Dieser Auszug ist einer der wenigen englischsprachigen Codeteile im Projekt und wird bewusst unverändert gezeigt. Die daraus gezeichnete Kurve D12 ist ein implementiertes Modell, kein gemessenes Vergessen des Agenten."
  - **Neu:** "Die Originalkommentare wurden für diesen Bericht ins Deutsche übersetzt, um die Lesbarkeit zu verbessern. Die daraus gezeichnete Kurve D12 ist ein implementiertes Modell, kein gemessenes Vergessen des Agenten."
- **Wichtig:** Die Kommentare müssen auch in die Original-Datei `memory/forgetting_curve.py` übernommen werden, damit der Code-Beleg im Bericht dem tatsächlichen Quelltext entspricht

---

## 6. Navigations- und Struktur-Anpassungen nach Entfernungen

Nach den Entfernungen in Abschnitt 2 muss die Navigation neu nummeriert werden:

| Neu | Titel | Alt |
|---|---|---|
| 00 | Überblick | 00 |
| 01 | Was untersucht wird | 01 |
| 02 | Wie CHAPPiE arbeitet | 02 |
| 03 | Versuchsdesign | 03 |
| 04 | Modellvergleich | 04 |
| 05 | Verblindeter Inhaltsvergleich | 05 |
| 06 | Laufzeit und Systemraten | 06 |
| 07 | Gezielte Folgeexperimente | 07 |
| 08 | Antworten auf die Forschungsfragen | 08 |
| 09 | Dialogbelege | 10 |
| 10 | Nutzen, Risiken, Grenzen, Fazit | 11 |
| 11 | Reproduzierbarkeit | 12 |
| 12 | Inspiration und Motivation | 13 |

**Achtung:** Abschnitt 09 (Fehlerstatus-Matrix) wird entfernt. Alle internen Verweise auf Abschnittsnummern im Text müssen angepasst werden.

---

## 7. KPI-Anpassungen im Überblick

Nach dem Entfernen der Fehlerstatus-Matrix:
- Die KPI "70 Punkte im Fehlerstatus" entfernen
- Das KPI-Grid von 4 Spalten auf 3 Spalten anpassen
- Die `kpis`-Klasse im CSS von `repeat(4,1fr)` auf `repeat(3,1fr)` ändern (nur im Überblick)

---

## 8. Zusammenfassung der Prioritäten

### Hoch (muss):
1. Alle Entfernungen (Abschnitt 2)
2. Emotionsinterventions-Korrektur (3.1)
3. GPT-OSS 20B als Hauptmodell (3.2)
4. Fehlalarm-Fußnote (3.3)
5. Navigations-Neunummerierung (6)
6. Version/Metadaten (1)

### Mittel (sollte):
7. Syntax-Highlighting (5.1)
8. D1 und D2 luftiger (4.1, 4.2)
9. D13 Farbkorrektur (4.4)
10. Folgeexperimente visualisieren (4.5)
11. Mehr Zitate und Safety-Hervorhebung (3.4)
12. Ebbinghaus deutsche Kommentare (5.3)

### Niedrig (kann):
13. D4 aufklappbare Liste (4.3)
14. Reproduzierbarkeit vertiefen (3.5)
15. Rate Limits ergänzen (3.6)
16. Inspiration visuell aufwerten (4.6)
17. Mehr Code-Kommentare (5.2)

---

## 9. Dateien und Quellen

### Eingabedaten (alle aus Run 2):
```
forschung/runs/run-2-20260723-1108-cb6d011/
├── manifest.json
├── run-state.json
├── figures/
│   ├── run2-condition-metrics.json
│   ├── forgetting-curve.json
│   └── emotion-vad.json
├── processed/
│   ├── blind-condition-comparison.json
│   ├── targeted-followup-analysis.json
│   ├── targeted-followup-manual-review.md
│   ├── gemma-behavioral-aggregate.json
│   ├── qwen-behavioral-aggregate.json
│   ├── *-blinded-review-unblinded.csv
│   └── *-unblinded-summary.md
├── notes/
│   ├── architecture-evidence.md
│   ├── research-questions.md
│   └── *-blinded-review-provenance.json
└── logs/
    ├── groq-20b-s53.stdout.log
    └── groq-20b-s71.stdout.log
```

### Zu erstellende neue Dateien:
- `forschung/report/technische-reparaturfragen.md` (FQ-13/14/15 Inhalte)

### Zu ändernde Quelldateien (für Code-Kommentare):
- `memory/forgetting_curve.py` (deutsche Kommentare)
