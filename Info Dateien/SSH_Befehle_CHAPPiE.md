# 🚀 CHAPPiE Server Guide: Maximum Autonomy
*"Set and Forget" - Anleitung für den 24/7 Betrieb auf Ubuntu*

## 📋 Inhaltsverzeichnis

| Abschnitt | Beschreibung |
|-----------|-------------|
| [🛠 0. Setup & Updates](#-0-setup--updates) | Projekt aktualisieren und Environment einrichten |
| [🚀 1. Training Starten](#-1-training-starten-nohup---empfohlen) | Verschiedene Methoden das Training zu starten |
| [🖥 2. Screen für Interaktion](#-2-alternative-screen-fr-interaktion) | Interaktives Arbeiten mit dem Training |
| [🤖 3. Systemd Service](#-3-alternative-systemd-service) | Automatischer Start beim Booten |
| [📊 4. Monitoring & Logs](#-4-monitoring-wichtig-bei-nohup) | Prozesse überwachen und Logs analysieren |
| [🛑 5. Training Stoppen](#-5-training-stoppen) | Das Training graceful beenden |
| [🏥 6. Server Health Check](#-6-server-health-check) | System-Überwachung und Diagnose |
| [📂 7. Daten-Management](#-7-daten-management--backups) | Backups und Datenverwaltung |
| [📝 Service Template](#-service-template) | Systemd-Service Konfiguration |

## 🛠 0. Setup & Updates
Bevor du startest, sichere dir immer den neuesten Stand.

```bash
# 1. Verbinden
ssh bbecker@100.105.94.71

# 2. In Projektordner
cd ~/CHAPPiE

# 3. Update & Environment
git pull
source venv/bin/activate
pip install -r requirements.txt
```

---

## 🚀 1. Training Starten (nohup - Empfohlen)
Die einfachste Methode: Starten und Logout möglich.

**Wichtig:** Nutze `training_daemon.py` (NICHT `training_loop.py` - das hat keinen Einstiegspunkt!)

```bash
# A: Standard-Start (Setzt vorheriges Training fort mit training_config.json)
nohup python3 Chappies_Trainingspartner/training_daemon.py > training.log 2>&1 &

# B: NEUES Training starten (interaktiv - fragt Konfiguration ab)
python3 Chappies_Trainingspartner/training_daemon.py --neu

# C: NEUES Training mit direkter Angabe (non-interactive - perfekt für SSH)
python3 Chappies_Trainingspartner/training_daemon.py --fokus "Logik und Programmierung" --persona "Ein kritischer Code-Reviewer" --start "Hallo Chappie, prüfe bitte diesen Code..."
# Danach im Hintergrund: nohup python3 Chappies_Trainingspartner/training_daemon.py > training.log 2>&1 &
```

**Erklärung:**
- `nohup`: Verhindert Beenden beim Logout
- `training_daemon.py`: Hat den eigentlichen main() Einstiegspunkt
- `> training.log`: Speichert alle Ausgaben in diese Datei
- `2>&1`: Leitet auch Fehler in die Datei um
- `&`: Startet den Prozess im Hintergrund

---

## 🖥 2. Alternative: "Screen" (für Interaktion)
Falls du zwischendurch in die Konsole schauen willst.
1. `screen -S chappie`
2. `python3 Chappies_Trainingspartner/training_daemon.py`
3. `STRG+A`, dann `D` zum Verlassen.

---

## 🤖 3. Alternative: Systemd Service
Für automatischen Start beim Booten (siehe `chappie-training.service`).

---

---

## 📊 4. Monitoring & Logs (Wichtig bei nohup!)
Überwache den Prozess im Hintergrund und analysiere Logs.

### 🔍 Prozess-Monitoring
```bash
# Prüfen, ob das Training läuft
ps aux | grep training_daemon

# Wie lange läuft der Prozess schon? (PID aus ps entnehmen)
ps -p <PID> -o etime=

# CPU & RAM Auslastung des Training-Prozesses
ps aux | grep training_daemon | head -1
```

### 📝 Log-Analyse
```bash
# Live-Logs verfolgen (STRG+C zum Verlassen)
tail -f training.log

# Letzte 50 Zeilen der Logs ansehen
tail -50 training.log

# Vollständige Logs durchsuchen (mit less für Navigation)
less training.log
# Mit /suchbegriff suchen, q zum Beenden

# Nach Fehlern suchen
grep -i error training.log

# Nach Chappie-Antworten suchen
grep "CHAPPIE:" training.log

# Logs der letzten Stunde filtern
tail -f training.log | grep "$(date -d '1 hour ago' +'%Y-%m-%d %H')"

# Training-Statistiken aus Logs extrahieren
grep -E "(Austausche|Fehler|Traum-Phasen)" training.log | tail -10
```

### 🖥️ Alternative: Screen für Log-Monitoring
```bash
# Screen für kontinuierliches Log-Monitoring starten
screen -S chappie-logs
tail -f training.log

# Screen verlassen: STRG+A, dann D
# Zurückkommen: screen -r chappie-logs
# Screen beenden: exit (im Screen)
```

## 🛑 5. Training Stoppen
Um den Prozess zu beenden:

```bash
# Prozess-ID finden
ps aux | grep training_daemon

# Prozess killen (soft: SIGTERM)
kill <PID>

# Falls nicht reagiert: hard kill (SIGKILL)
kill -9 <PID>

# Alternative: Alle Training-Prozesse gleichzeitig beenden
pkill -f training_daemon
pkill -f python.*Chappies_Trainingspartner
```

---

## 🏥 6. Server Health Check
Allgemeine Server-Überwachung.

```bash
# CPU & RAM Auslastung (Bunt & Interaktiv)
htop

# Speicherplatz prüfen
df -h

# Wie groß ist die ChromaDB Datenbank?
du -sh data/*
```


---

## 📂 7. Daten-Management & Backups
Sichere das Gehirn deines KI-Partners.

```bash
# Backup der Datenbank erstellen (Zeitstempel im Namen)
tar -czf backup_chappie_$(date +%F).tar.gz data/

# Backup auf deinen PC ziehen (Befehl auf WINDOWS ausführen!)
scp bbecker@100.105.94.71:~/CHAPPiE/backup_chappie_*.tar.gz .
```

---

## 📝 Service Template (`/etc/systemd/system/chappie-training.service`)
Falls du den Service nutzen willst, hier ist die Vorlage. Passe `User` und `WorkingDirectory` an!

```ini
[Unit]
Description=CHAPPiE Autonomous Training Service
After=network.target

[Service]
# User unter dem es laufen soll
User=bbecker
Group=bbecker

# Pfad zum Projekt
WorkingDirectory=/home/bbecker/CHAPPiE

# Environment Variablen laden
Environment="PATH=/home/bbecker/CHAPPiE/venv/bin:/usr/local/bin:/usr/bin:/bin"
Environment="PYTHONUNBUFFERED=1"

# Start-Befehl (Direkt den Daemon starten)
ExecStart=/home/bbecker/CHAPPiE/venv/bin/python3 Chappies_Trainingspartner/training_daemon.py

# Restart bei Crash (Wichtig für Autonomie!)
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```
