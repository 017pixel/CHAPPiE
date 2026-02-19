# 🚀 CHAPPiE Schnellstart-Anleitung

## Voraussetzungen
- Python 3.10 oder neuer
- Git

## 1. Installation

```bash
# Repository klonen
git clone https://github.com/017pixel/CHAPPiE.git
cd CHAPPiE

# Environment erstellen
python -m venv venv

# Aktivieren
# Windows:
.\venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Pakete installieren
pip install -r requirements.txt
```

## 2. API Keys einrichten
1. Kopiere `config/secrets_example.py` zu `config/secrets.py`
2. Öffne die Datei und trage deine API-Keys ein (Groq, Cerebras).
   - Alternativ: Du kannst Keys auch später in der Web-UI eingeben.

## 3. Starten

**Web-Interface (Empfohlen):**
```bash
streamlit run app.py
```
> Öffnet http://localhost:8501

**Training starten (Optional):**
```bash
python Chappies_Trainingspartner/setup_training.py
```

## 4. Updates holen
```bash
git pull
pip install -r requirements.txt
```

---
Viel Spaß mit CHAPPiE! 🤖