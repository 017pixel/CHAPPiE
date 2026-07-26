# Visuelle Hauptabnahme — Final

Zeitpunkt: `2026-07-26T06:50:43Z`  
Ressourcenklasse: `INDEPENDENT`  
Status: `PASS`

## Gesichtet

- `report-assets/qa/report-1920x1080.png`
- `report-assets/qa/report-mobile-390x844.png`
- `report-assets/qa/plan-1440x900.png`

## Befund

- Die Desktopdarstellung besitzt eine klare Dokumenthierarchie, ruhige Grauflächen,
  subtile Sage-Akzente, einen lesbaren Dokumentenbaum und ausreichend Whitespace.
- Der Bericht wirkt wie ein Forschungsdokument, nicht wie ein Analytics-Dashboard.
- Die mobile Titel- und Metadatenhierarchie bleibt bei 390 px verständlich; Buttons
  besitzen ausreichende Touchflächen und es gibt keinen erreichbaren horizontalen
  Seiten-Scroll.
- Der HTML-Plan und der Bericht verwenden erkennbar dasselbe Designsystem.
- Bei deaktiviertem JavaScript bleiben in beiden Dokumenten Hauptinhalt,
  Überschriften, Navigation und semantische Details lesbar (2/2).
- Kontrast, Fokusrahmen und Statusdarstellung bleiben zurückhaltend, aber sichtbar.
- Keine Verläufe, Glows, 3D-, Glass-, Neumorphism- oder Marketingflächen sichtbar.

## Korrigierte Fehler

Der erste Browserlauf zeigte auf 390 px 38 px Seitenüberlauf. Ursache waren ein
langer Filterwert und ein unbrechbarer technischer Pfad. Nach der Builderkorrektur
bestehen 10/10 automatisierte Browseransichten.

Ein später gehärtetes Printgate zeigte zusätzlich 225 px Überlauf bei
390-px-Druckemulation durch lange `pre`-Zeilen. Der druckspezifische
Umbruchvertrag behebt diesen Fehler; Navigation, Druckfarben und horizontaler
Überlauf werden nun in allen fünf Zielgrößen geprüft. Der aktuelle Stand
besteht erneut 10/10 Ansichten (`R2-NEW-014`).

## Finale Wiederholung

Nach validiertem Abschluss aller Modellbedingungen wurden dieselben zehn
Ansichten mit der 70-Issue-Matrix und den finalen Diagrammen erneut gerendert.
Alle 10/10 Browseransichten sowie 2/2 No-JavaScript-Ansichten bestanden.
Große Diagramme, vollständige Tabellen, Medien-Fallbacks, Fokus,
Interaktionen und Druckausgabe wurden im realen Chromium-Lauf mitgeprüft.
Die Hauptinstanz sichtete zusätzlich die aktuelle 1440×900- und
390×844-Ausgabe ohne Überlagerung oder horizontalen Seitenüberlauf.
