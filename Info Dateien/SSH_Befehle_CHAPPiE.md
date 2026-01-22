# 🚀 CHAPPiE Server Guide: Maximum Autonomy
*"Set and Forget" - Anleitung für den 24/7 Betrieb auf Ubuntu*

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

## 📊 4. Monitoring (Wichtig bei nohup!)
Überwache den Prozess im Hintergrund.

```bash
# Live-Logs verfolgen (Drücke STRG+C zum Verlassen)
tail -f training.log

# Prüfen, ob der Prozess noch läuft
ps aux | grep training_daemon

# Wie lange läuft der Prozess schon? (PID aus ps entnehmen)
ps -p <PID> -o etime=
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
