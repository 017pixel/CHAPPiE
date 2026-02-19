# 🤖 WIE ES GEHT - CHAPPiE Projekt-Dokumentation

Willkommen unter der Haube von **CHAPPiE**! Hier erfährst du, wie der KI-Agent technisch funktioniert, wie die Komponenten zusammenspielen und welche Mechanismen ihn "lebendig" machen.

---

## 🏗️ Die Architektur

Das System basiert auf einer modularen Architektur, die in drei Hauptkomponenten unterteilt ist:

### 1. 🧠 Das Gehirn (`brain/`)
Das LLM-Backend (Large Language Model) ist austauschbar.
- **Provider:** Unterstützt **Groq** (Cloud/LPU), **Cerebras** (High-Speed Cloud) und **Ollama** (Lokal).
- **Dual-Brain:** CHAPPiE kann verschiedene Modelle für verschiedene Aufgaben nutzen (z.B. ein schnelles Modell für Emotionen, ein intelligentes für Antworten).
- **Deep Think:** Bei komplexen Anfragen (`/think`) aktiviert CHAPPiE einen Chain-of-Thought Prozess, um strukturiert nachzudenken.

### 2. 📚 Das Gedächtnis (`memory/`)
CHAPPiE vergisst nichts - oder fast nichts.
- **Langzeitgedächtnis (ChromaDB):** Jede Interaktion wird vektorisiert (Embeddings) und gespeichert. Bei neuen Anfragen sucht RAG (Retrieval Augmented Generation) semantisch ähnliche Erinnerungen.
- **Kurzzeitgedächtnis (`short_term_memory.py`):** Speichert temporäre Fakten und Kontext für den aktuellen Tag. Wird automatisch nach 24h bereinigt.
- **Dateisystem:** Persistente Speicherung von Chat-Sessions und Status-Flags in `data/`.

### 3. ❤️ Die Seele (`emotions_engine.py`)
CHAPPiE ist keine statische Maschine.
- **6 Dimensionen:** Happiness, Trust, Energy, Curiosity, Frustration, Motivation.
- **Sentiment-Analyse:** Jede User-Nachricht wird analysiert (Positiv/Negativ/Neutral) und beeinflusst die Werte.
- **Feedback-Loop:** Die Emotionen werden in den System-Prompt injiziert und beeinflussen so Tonfall und Wortwahl der Antwort.

---

## 🔄 Der Lebenszyklus einer Nachricht

Was passiert technisch, wenn du "Hallo" sagst?

1. **Input-Verarbeitung:** Die Nachricht wird empfangen und normalisiert.
2. **Kontext-Gathering:**
   - **RAG:** Suche nach relevanten alten Gesprächen in ChromaDB.
   - **STM:** Abruf aktueller Infos aus dem Kurzzeitgedächtnis.
   - **Emotionen:** aktueller Gefühlszustand wird geladen.
3. **Prompt-Assembly:** Ein dynamischer Prompt wird gebaut:
   > "Du bist CHAPPiE. Du fühlst dich gerade [Glücklich]. Hier sind Erinnerungen: [...]. Der User sagt: 'Hallo'."
4. **Generierung:** Das LLM generiert die Antwort (ggf. mit Streaming).
5. **Post-Processing:**
   - Emotionen werden aktualisiert.
   - Die neue Interaktion wird gespeichert (Memory & STM).
   - Backup-Checks laufen im Hintergrund.

---

## 🎓 Der Trainingsmodus (`Chappies_Trainingspartner`)

Um CHAPPiE ohne menschliches Zutun zu verbessern, wurde ein autonomer Trainings-Loop entwickelt.

- **Der Trainer:** Ein separater KI-Agent übernimmt die Rolle des Users. Er hat eine definierte "Persona" (z.B. kritischer Prüfer) und ein "Curriculum" (Themenliste).
- **Der Loop:** Trainer fragt -> CHAPPiE antwortet -> Trainer bewertet/reagiert.
- **Robustheit:** Der `TrainingDaemon` läuft als System-Service auf Linux, behandelt API-Limits (Rate Limits) durch Pausen oder Backend-Wechsel und speichert den Fortschritt.

---

## 🛡️ Sicherheit & Deployment

### API Key Management
Sicherheit hat Priorität. 
- API-Keys liegen **niemals** im Code.
- Sie werden über Umgebungsvariablen oder `config/secrets.py` (git-ignored) geladen.
- Das Backup-System (`backup_project.py`) exkludiert diese Dateien explizit.

### Server Betrieb
Für den 24/7 Betrieb auf Ubuntu Servern gibt es das `deploy_training.sh` Skript:
- Installiert Systemd Services für Web-UI und Training.
- Überwacht Logs und Status.
- Ermöglicht Updates via Git.

---

## 📁 Wichtige Dateien

- `app.py`: Der Einstiegspunkt für die Web-Oberfläche.
- `backup_project.py`: Das Tool für sichere Projekt-Backups.
- `config/config.py`: Zentrale Konfigurationslogik.
- `web_infrastructure/`: UI-Code (MVC-ähnlich getrennt).

---

*Stand: Januar 2026 - CodeX*
