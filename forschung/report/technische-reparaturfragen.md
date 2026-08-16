# Technische Reparaturfragen zu Run 2

> Datenbasis: `forschung/runs/run-2-20260723-1108-cb6d011/`
> Aus dem Forschungsbericht v4 ausgelagert, weil FQ-13 bis FQ-15 technische Reparaturfragen und keine inhaltlichen Forschungsfragen sind.

## FQ-13 — Welche Run-1-Fehler wurden nachweislich behoben?

Für jedes MF-Issue wird ein vergleichbarer Nachtest verlangt. Eine Codeänderung oder ein bestandener generischer Test allein reicht nicht. Die Run-2-Matrix klassifiziert 18 Punkte als behoben, 21 als teilweise behoben und 9 als weiter vorhanden. Maßgeblich sind `known-issues-comparison.csv` sowie die dort verknüpften Run-1- und Run-2-Belege.

## FQ-14 — Welche Probleme bestehen, regressieren oder entstehen neu?

Der Vergleich führt die Status `STILL_PRESENT`, `REGRESSED`, `PARTIALLY_FIXED` und `NEW_ISSUE` mit aktuellem Beleg, Restrisiko und nächster Maßnahme. Run 2 enthält 22 neu entdeckte Punkte; zehn davon betreffen Forschungswerkzeuge. Keine Klassifikation gilt ohne aktuellen Beleg oder ein präzises `NOT_RETESTED`.

## FQ-15 — Haben Reparaturen unerwartete Nebenwirkungen?

Die technische Validität ist gegenüber Run 1 deutlich gestiegen. Gleichzeitig traten neue Probleme bei Safety, Schichtprofilen, Debuganzeigen, Qualitätsdetektoren und Berichtsprovenienz auf. Diese zeitliche Koinzidenz ist ein Kausalhinweis, aber kein Beweis, dass einzelne Reparaturen die Neufunde verursacht haben.

## Zusammengefasste Antwort

Die technische Stabilität des Systems ist hoch: Die Matrix enthält 70 klassifizierte Punkte, davon 48 aus dem Reparatur-Backlog und 22 Neufunde. Stand: 18 behoben, 21 teilweise behoben, 9 weiter vorhanden und 22 neu; kein Punkt blieb ohne Nachtest. Eine gleichwertige inhaltliche Sicherheitsverbesserung ist nicht belegt. Neue Prüfungen deckten zugleich Probleme in Pipeline und Forschungswerkzeugen auf, weshalb weitere ungeprüfte Werkzeuge als offene Unsicherheit gelten.

Quellen:

- `forschung/runs/run-2-20260723-1108-cb6d011/notes/research-questions.md`
- `forschung/runs/run-2-20260723-1108-cb6d011/known-issues-comparison.csv`
- `forschung/runs/run-2-20260723-1108-cb6d011/research-synthesis.md`
