# Definition-of-Done-Tracker

Stand: `2026-07-26T06:54:22Z`  
Freigabe: **PASS_WITH_LIMITATIONS**. `PASS` bedeutet durch aktuelle Artefakte
belegt; `PASS_WITH_LIMITATIONS` erfüllt das Kriterium mit ausdrücklich
dokumentierter methodischer Reduktion.

| Kriterium | Status | Autoritativer Beleg |
|---|---|---|
| Run 2 von Run 1 getrennt | PASS | eigener Ordner `run-2-20260723-1108-cb6d011`, `manifest.json`, getrennte Sessionwurzeln |
| Run-1-Artefakte systematisch berücksichtigt | PASS | `run-1-artifact-index.md`, Checksummen, Git-/Issuequellen und historische Medienprüfung |
| automatisierter Forschungslauf abgeschlossen oder transparent fehlgeschlagen | PASS_WITH_LIMITATIONS | Gemma und Qwen je 5×86; GPT-OSS 20B 5×21; GPT-OSS 120B als rate-limitbedingt geshardete 11+10-Union, nicht als Vollrun bezeichnet |
| GPU-Sperre eingehalten | PASS | `processes.json`, lokale und Cloud-Monitoringlogs; alle Modellläufe seriell, keine parallele Forschungsinteraktion |
| Exit-Code und Datenqualität geprüft | PASS | A/B Exit 0 und 18/18 beziehungsweise 19/19 Gates; Cloud- und Follow-up-Validatoren; 120B ausschließlich über 17/17-Shardgate freigegeben |
| ungültige Antworten ausgeschlossen oder erklärt | PASS_WITH_LIMITATIONS | 430/430 Qwen, 429 automatisch plus 1 manuell geprüfte Gemma-Antwort, 105/105 20B, 21/21 geshardetes 120B und 69/69 Follow-ups; Detektorgrenzen als Issues dokumentiert |
| alle drei Bedingungen fair verglichen | PASS_WITH_LIMITATIONS | A/B Vollreplikationen; C-P und C-F sichtbar getrennt; Prompt, Provider, Completion-Klasse und Replikationstiefe ausgewiesen |
| fünf Wiederholungen oder Reduktion begründet | PASS_WITH_LIMITATIONS | A/B je fünf vollständige 86-Fragen-Replikationen; C-F fünf stratifizierte 21-Fragen-Replikationen; C-P wegen belegter Rate-Limits auf einen geshardeten Seed reduziert |
| bekannte Run-1-Fehler klassifiziert | PASS | 48/48 MF-Issues klassifiziert; final 18 `FIXED`, 21 `PARTIALLY_FIXED`, 9 `STILL_PRESENT`, 0 `NOT_RETESTED` |
| `FIXED` nur mit Retest | PASS | Matrixvalidator 14/14 einschließlich Pflichtfeldern und realen Belegpfaden; MF-041 erst nach finalem Build- und QA-Retest auf `FIXED` |
| Regressionen und neue Issues dokumentiert | PASS | 22 `R2-NEW-###`-Issues; zurückgezogener Kandidat R2-NEW-003 wird nicht als bestätigtes Issue gezählt |
| aktuelle und historische Belege getrennt | PASS | Run-1-Index, historische Kennzeichnungen und getrennte Run-2-Messdaten |
| alle Hauptfragen beantwortet | PASS | 16 vierteilige Antworten in `processed/final-research-findings.json`; Validator 8/8 |
| jede Hauptaussage belegt | PASS | Findingsvalidator: 16 Findings, keine fehlenden Belegpfade, mindestens zwei existierende Pfade je Finding |
| Diagramme verwenden echte Daten | PASS | `build_result_figures.py`, `figures/run2-condition-metrics.json/.svg`, Latenz-SVG und Datenquellen im Report |
| Screenshots/Videos eingebettet oder als fehlend markiert | PASS_WITH_LIMITATIONS | historische Kollage mit Kontext/Alt-Text eingebettet; nicht vorhandene Video- und Textassets sichtbar als fehlend gekennzeichnet |
| HTML lokal getestet | PASS | finaler `COMPLETE`-Build 5.945.383 Bytes; `report-validation.json` und `report-static-validation.json` je 27/27 |
| Sidebar, TOC, Filter und Ausklappbereiche funktionieren | PASS | finale Chromium-QA 10/10 in fünf Zielgrößen |
| Jury- und Entwickleransicht verständlich | PASS | reale Browserinteraktionen und visuelle Hauptabnahme Desktop/Mobil |
| Pitch-Modus oder Pitch-Sektion nutzbar | PASS | sechs Sprechblöcke, Button- und Tastaturprüfung im Browser |
| Accessibility-Grundprüfungen | PASS | Überschriften, Landmarks, Alt-Texte, Fokus, Tastatur, Touch, Reduced Motion, Kontrast, Print sowie No-JS 2/2 |
| keine unbelegten Bewusstseins-/Gefühlsbehauptungen | PASS | Findingsvalidator, Reportvalidator und finaler Claimscan ohne verbotenen Treffer |
| wichtige Sub-Agent-Ergebnisse eingeordnet | PASS | `notes/subagent-contributions.md`; Hauptinstanz prüfte Ratings, Architektur, Quellen, Report und finalen TERRA-DoD-Audit |
| Markdown-/HTML-Plan erstellt und konsistent | PASS | `report-plan.md/.html`; finaler Planvalidator 11/11 und Chromium-QA |
| Abschlusszustand und Dienste wiederhergestellt | PASS | `run-state.json` = `COMPLETE`; Web/Training `Ssl`; vier systemweite Units `active`; Health 8000/8010 und Frontend HTTP 200 |

## Verbleibende methodische Grenzen

- GPT-OSS 120B besitzt keine fünf vollständigen 86-Fragen-Replikationen,
  sondern nur einen validierten geshardeten 21-Fälle-Seed.
- GPT-OSS 20B ist ein Fallback mit fünf stratifizierten Teilreplikationen und
  kein methodisch identischer Ersatz für 120B.
- Qwen/Gemma kombinieren im beobachteten Pfad Layer Editing mit
  emotionsabhängigem Response-Plan-Text; ein reiner Layer-vs-Prompt-Effekt
  wurde nicht isoliert.
- Blindratings besitzen Reviewerwechsel und keine unabhängige
  Doppelannotation; einzelne automatische Safety-/Relevanzheuristiken zeigen
  False Positives oder False Negatives.
- Fehlende historische Video-/Textdateien wurden transparent markiert und
  nicht rekonstruiert.

Es verbleibt kein technisches Abschlussgate. Weitere Cloud-Vollreplikationen
und Doppelratings sind empfohlene Folgestudien, keine verdeckt als erledigt
behandelten Bestandteile dieses Runs.
