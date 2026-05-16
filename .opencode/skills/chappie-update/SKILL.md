---
name: chappie-update
description: Führt ein vollständiges CHAPPiE-Update durch: git pull, Dienste neustarten, Tests, Health-Check, Reparatur bei Bedarf.
---

# CHAPPiE Update Workflow

## Voraussetzungen
- Systemd-Services: `chappie-web` (Backend), `chappie-frontend` (Frontend)
- Tests: `python -m pytest tests/ -x -v` (oder vergleichbarer Befehl)
- Remote-IP: `100.105.94.71`

## Update-Flow (exakt in dieser Reihenfolge)

### 1. Git Pull
`git pull` im CHAPPiE-Projektordner ausführen.

### 2. Dependencies aktualisieren
- Python: venv aktivieren, `pip install -r requirements.txt`
- Frontend: in den frontend-Ordner gehen, `npm install`

### 3. Frontend neustarten
```bash
sudo systemctl restart chappie-frontend
```

### 4. Backend neustarten
```bash
sudo systemctl restart chappie-web
```

### 5. Tests durchführen
`python -m pytest tests/ -x -v` im CHAPPiE-Projektordner (mit aktiviertem venv) ausführen.

### 6. Prüfen, ob etwas kaputt ist
- Analyse der Testergebnisse aus Schritt 5
- Nur wenn ein Test fehlschlägt UND der Fehler durch das Update verursacht wurde (nicht vorher schon bestanden): reparieren
- **Nicht** eigenmächtig Dinge ändern, die vorher schon kaputt waren

### 7. Health-Check
Prüfen, ob beide Dienste erreichbar sind:
- Frontend: `curl -sf http://100.105.94.71:4173/` oder `curl -sf http://localhost:4173/`
- Backend: `curl -sf http://100.105.94.71:8010/` oder `curl -sf http://localhost:8010/`

### 8. Bestätigung
Dem User mitteilen:
- "Update erfolgreich: CHAPPiE ist unter http://100.105.94.71:4173/ erreichbar."
- Falls Tests fehlgeschlagen sind: erwähnen, ob/was repariert wurde
- Falls Health-Check fehlschlug: Alarm schlagen, nicht ignorieren

## Wichtige Regeln
- Nur reparieren, was durch das Update kaputt gegangen ist
- Vorbestehende Fehler nicht beheben (das ist ein separates Issue)
- Bei unklaren Fehlern: den User um Entscheidung bitten
