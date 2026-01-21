# 🚀 SSH Befehle für CHAPPiE-Training

Hier sind alle wichtigen Befehle, um CHAPPiE auf deinem Ubuntu-Server zu verwalten.

## 1. Einloggen & Vorbereiten
Logge dich per SSH ein und navigiere zum Projektordner:

```bash
# Per SSH verbinden
ssh bbecker@100.105.94.71

# In den Ordner wechseln
cd ~/CHAPPiE

# Neuesten Code von GitHub holen
git pull

# Virtual Environment aktivieren (WICHTIG!)
source venv/bin/activate
```

## 2. Training Starten
Es gibt drei Modi für den Start:

```bash
# A: Vorheriges Training fortsetzen (Hintergrund)
nohup python3 Chappies_Trainingspartner/training_daemon.py > training_daemon.log 2>&1 &

# B: NEUES Training starten (Interaktive Abfrage)
# Hinweis: Ohne nohup starten, um Fragen zu beantworten, danach ggf. Hintergrund
python3 Chappies_Trainingspartner/training_daemon.py --neu

# C: Start mit direktem Fokus (Hintergrund)
nohup python3 Chappies_Trainingspartner/training_daemon.py --fokus "Thema" > training_daemon.log 2>&1 &
```

## 3. Monitoring & Status
So behältst du den Überblick:

```bash
# Live-Logs verfolgen (Was schreiben sie gerade?)
tail -f training_daemon.log

# Prüfen, ob der Prozess noch läuft
ps aux | grep training_daemon.py

# Die letzten 100 Zeilen des Logs lesen
tail -n 100 training_daemon.log
```

## 4. Training Stoppen
Um den aktiven Trainings-Prozess zu beenden:

```bash
# Alle Trainings-Dämonen pkillen
pkill -f training_daemon.py
```

---
✨ **Tipp:** Wenn du den Befehl mit `&` am Ende startest, kannst du das Terminal mit `exit` verlassen und Chappie arbeitet 24/7 weiter.
