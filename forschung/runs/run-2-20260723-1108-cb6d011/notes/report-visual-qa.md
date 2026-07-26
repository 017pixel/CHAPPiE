# Visuelle, responsive und Accessibility-QA

Stand: 2026-07-26 06:50 UTC  
Ressourcenklasse: `INDEPENDENT`

## Automatisierte reale Browserprüfung

Renderer: Playwright Chromium, headless, `--disable-gpu`, Dark Mode,
`prefers-reduced-motion`.

Geprüft wurden Plan und Run-2-Bericht jeweils bei:

- 1920 × 1080
- 1440 × 900
- 1280 × 720
- Tablet 1024 × 768
- Smartphone 390 × 844

Finales Ergebnis nach dem 70-Issue-Datenbuild: **10/10 Ansichten bestanden**.
Zusätzlich bestanden beide Dokumente ohne JavaScript mit **2/2**. Geprüft
wurden Seitenüberlauf,
interne Anker, Bilder, Überschriftenfolge, Buttonnamen, Alt-Texte,
Fokusindikator, Konsole, JavaScriptfehler, mobile Navigation, Juryansicht,
Pitch-Modus, Details, Issuefilter, Sidebar sowie Druckmedium.

Die folgenden Zwischenstände dokumentieren die Entwicklung der QA; maßgeblich
für die Abschlussfreigabe ist der letzte Lauf vom 26. Juli 2026 um 06:50 UTC
mit der 70-Zeilen-Matrix und dem finalen Drei-Bedingungen-Bericht.

Nach Synchronisierung des laufenden Cloudstands von 18/21 auf 19/21 wurden
der Report neu gebaut und alle zehn Browseransichten erneut geprüft. Der
Statuswechsel verändert keine Layoutstruktur; Navigation, Interaktionen,
Fokus, Druckmedium und responsive Grenzen bestehen weiterhin 10/10.

Nach der zusätzlichen Trennung von 120B-Primär- und 20B-Fallbackstatus sowie
der Korrektur auf sechs Pitchblöcke wurden alle zehn Ansichten nochmals
erfolgreich geprüft. Die längere Bedingungszeile verursacht weder horizontalen
Seitenüberlauf noch mobile Überlagerung.

Ein zusätzlicher DOM-Geometrieaudit fand anschließend eine innerhalb des
Ergebnis-SVGs abgeschnittene GPT-OSS-Legendenzeile bei 1440 px. Das
zweizeilige Legendenlayout beseitigt den Befund; der Wiederholungsaudit meldet
null Offscreen-SVG-Texte. Beleg: `logs/report-svg-geometry-1440.log`.

Maschinenlesbarer Beleg:
`processed/browser-report-validation.json`.

## Kontrast

Der ursprüngliche Tertiärton `#7a7a7a` erreichte auf den verwendeten
Dark-Flächen nur ungefähr 3,8–4,1:1. Der korrigierte gemeinsame Token
`#929292` erreicht gegen `#191919`, `#1e1e1e`, `#202020`, `#232323` und
`#2a2a2a` mindestens 4,61:1. Der Standalone-Reporttest berechnet die
WCAG-Relative-Luminanz und verlangt mindestens 4,5:1.

Beleg: `logs/test_forschung_report-wcag-contrast.log`.

Ein Nachaudit fand denselben alten Farbtoken zunächst noch in den beiden
generierten Ergebnis-SVGs. Der Figure-Generator und beide Artefakte verwenden
nun ebenfalls `#929292`. Der ergänzte Reporttest prüft außerdem, dass die
Accessible Description und Caption Qwen nicht mehr als partiell bezeichnen,
nachdem 5/5 Replikationen formal freigegeben sind. Beleg:
`logs/test_forschung_report-svg-status-contrast.log`.

Die semantischen Statuschips wurden zusätzlich als Text-/Flächenpaare
berechnet: `FIXED` 6,39:1, `PARTIALLY_FIXED` 6,78:1,
`STILL_PRESENT`/`REGRESSED` 5,86:1 und `NEW_ISSUE` 6,83:1. Beleg:
`logs/status-color-contrast-audit.log`.

## Sichtprüfung der Hauptinstanz

Die nach dem finalen Build erneut gesichtete 1440×900-Fassung zeigt ruhige
Notion-Dark-Hierarchie, klar erkennbare
Sidebar, lesbare Metadaten und Callouts sowie einen sichtbaren, aber
zurückhaltenden Fokuszustand. In 390×844 umbrechen Titel, Teamzeile,
Dialogbeleg und Dateipfad ohne horizontalen Seitenüberlauf. Der angehobene
Tertiärton bleibt visuell zurückhaltend, ist aber deutlich lesbarer. Diese
Sichtprüfung wurde nach der Ergebnis-SVG-Neugenerierung wiederholt.

Gesichtete Dateien:

- `report-assets/qa/report-1440x900.png`
- `report-assets/qa/report-mobile-390x844.png`

## Verbleibende Grenze

Die Prüfung deckt zentrale Texttokens, Statuschips, die aktuellen
Ergebnis-SVGs und reale Renderings ab, aber nicht automatisch jede Linie
künftiger SVGs oder jede semantische Nuance der historischen Kollage. Für den
vorliegenden finalen Build wurden alle zehn Ansichten, beide No-JS-Ansichten,
Kontrast, Fokus, Interaktionen und Druckmedium erneut geprüft.
