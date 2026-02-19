r"""
CHAPiE - Backup Script
=======================
Erstellt eine saubere Kopie des Projekts ohne venv, __pycache__ und andere unnötige Dateien.

WICHTIG: 
- ChromaDB-Daten (data/chroma_db) werden in ein separates Backup-Archiv verpackt
- API-Keys werden NICHT kopiert (secrets.py, addSecrets.py)
- Nach dem Restore: secrets_example.py -> secrets.py kopieren und Keys eintragen

Verwendung:
    python backup_project.py
    
    oder mit Zielordner:
    python backup_project.py D:\USB_STICK\CHAPiE_Backup
"""

import os
import shutil
from pathlib import Path
from datetime import datetime
import zipfile

# Ordner/Dateien die NICHT kopiert werden sollen
EXCLUDE_DIRS = {
    'venv',
    '.venv',
    '__pycache__',
    '.git',
    'build',
    'dist',
    '.idea',
    '.vscode',
    'node_modules',
    '.pytest_cache',
    '*.egg-info',
    '.agent',  # Gemini Agent Ordner
}

EXCLUDE_FILES = {
    '.pyc',
    '.pyo',
    '.pyd',
    '.so',
    '.dll',
    '.exe',
    '.spec',
}

# SICHERHEITSKRITISCH: Diese Dateien enthalten API-Keys und werden NICHT kopiert!
EXCLUDE_SECRET_FILES = {
    'secrets.py',
    'addSecrets.py',
    'groq_api.py',
    'cerebras_api.py',
}

# ChromaDB Pfad (wird separat behandelt)
CHROMA_DB_RELATIVE = 'data/chroma_db'


def should_exclude(path: Path, src_root: Path) -> bool:
    """Prueft ob ein Pfad ausgeschlossen werden soll."""
    name = path.name
    
    # Ordner pruefen
    if path.is_dir():
        if name in EXCLUDE_DIRS:
            return True
        if name.endswith('.egg-info'):
            return True
    
    # SICHERHEIT: Secret-Dateien NICHT kopieren
    if path.is_file() and name in EXCLUDE_SECRET_FILES:
        print(f"   [SICHERHEIT] Überspringe: {name} (enthält API-Keys)")
        return True
    
    # Dateien pruefen
    if path.is_file():
        for ext in EXCLUDE_FILES:
            if name.endswith(ext):
                return True
    
    return False


def backup_chroma_db(src: Path, dst: Path) -> bool:
    """
    Erstellt ein ZIP-Archiv der ChromaDB-Daten.
    
    Dies ist die sicherste Methode um ChromaDB zu sichern,
    da die Datenbank beim Kopieren nicht korrupt werden kann.
    
    Returns:
        True wenn erfolgreich, False wenn keine Daten vorhanden
    """
    chroma_src = src / CHROMA_DB_RELATIVE
    
    if not chroma_src.exists():
        print("   [INFO] Keine ChromaDB-Daten vorhanden")
        return False
    
    # Ziel-Pfad für das Archiv
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    archive_name = f"chroma_db_backup_{timestamp}.zip"
    archive_path = dst / archive_name
    
    print(f"\n=== ChromaDB Backup ===")
    print(f"Quelle: {chroma_src}")
    print(f"Archiv: {archive_path}")
    
    try:
        file_count = 0
        with zipfile.ZipFile(archive_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
            for root, dirs, files in os.walk(chroma_src):
                for file in files:
                    file_path = Path(root) / file
                    arcname = file_path.relative_to(chroma_src)
                    zipf.write(file_path, arcname)
                    file_count += 1
        
        archive_size_mb = archive_path.stat().st_size / (1024 * 1024)
        print(f"   ✅ {file_count} Dateien archiviert ({archive_size_mb:.1f} MB)")
        return True
        
    except Exception as e:
        print(f"   ❌ Fehler beim ChromaDB-Backup: {e}")
        return False


def copy_project(src: Path, dst: Path):
    """Kopiert das Projekt ohne ausgeschlossene Dateien."""
    
    if dst.exists():
        print(f"Zielordner existiert bereits: {dst}")
        response = input("Loeschen und neu erstellen? (j/n): ")
        if response.lower() == 'j':
            shutil.rmtree(dst)
        else:
            print("Abgebrochen.")
            return
    
    dst.mkdir(parents=True)
    
    file_count = 0
    dir_count = 0
    skipped_secrets = 0
    
    for item in src.rglob('*'):
        # Relativer Pfad
        rel_path = item.relative_to(src)
        
        # Pruefe ob irgendein Teil des Pfads ausgeschlossen ist
        skip = False
        for part in rel_path.parts:
            if part in EXCLUDE_DIRS or part.endswith('.egg-info'):
                skip = True
                break
        
        # ChromaDB wird separat als ZIP behandelt
        if CHROMA_DB_RELATIVE in str(rel_path):
            continue
        
        if skip or should_exclude(item, src):
            if item.name in EXCLUDE_SECRET_FILES:
                skipped_secrets += 1
            continue
        
        target = dst / rel_path
        
        if item.is_dir():
            target.mkdir(parents=True, exist_ok=True)
            dir_count += 1
        elif item.is_file():
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(item, target)
            file_count += 1
            if file_count % 10 == 0:
                print(f"   Kopiert: {file_count} Dateien...", end='\r')
    
    print(f"\n\n=== Projekt-Backup abgeschlossen ===")
    print(f"   Ordner: {dir_count}")
    print(f"   Dateien: {file_count}")
    print(f"   Übersprungene Secrets: {skipped_secrets}")
    print(f"   Ziel: {dst}")
    
    # ChromaDB separat sichern
    backup_chroma_db(src, dst)


def create_restore_guide(dst: Path):
    """Erstellt eine Anleitung zum Wiederherstellen."""
    guide_content = """# CHAPiE Backup Wiederherstellung
======================================

## Schritt 1: Projekt-Dateien
Die Projekt-Dateien sind bereits entpackt.

## Schritt 2: Python Environment
```bash
python -m venv venv
.\venv\Scripts\activate  # Windows
# oder
source venv/bin/activate  # Linux/Mac

pip install -r requirements.txt
```

## Schritt 3: API-Keys konfigurieren
1. Kopiere `config/secrets_example.py` nach `config/secrets.py`
2. Trage deine API-Keys ein:
   - GROQ_API_KEY (von https://console.groq.com)
   - CEREBRAS_API_KEY (von https://cloud.cerebras.ai)

## Schritt 4: ChromaDB Wiederherstellen (WICHTIG!)
Falls du das Gedächtnis behalten möchtest:

1. Entpacke `chroma_db_backup_*.zip`
2. Kopiere den Inhalt nach `data/chroma_db/`

HINWEIS: Falls du auf einem neuen System startest und die ChromaDB-Version
unterschiedlich ist, kann es zu Konflikten kommen. In diesem Fall:
- Lösche `data/chroma_db/` komplett
- CHAPiE startet mit leerem Gedächtnis

## Schritt 5: Starten
```bash
streamlit run app.py
```

## Bei Problemen
- Prüfe ob alle Dependencies installiert sind: `pip list`
- Prüfe ob die API-Keys korrekt sind
- Bei ChromaDB-Fehlern: Ordner `data/chroma_db/` löschen
"""
    
    guide_path = dst / "RESTORE_GUIDE.md"
    with open(guide_path, "w", encoding="utf-8") as f:
        f.write(guide_content)
    print(f"\n   ℹ️  Wiederherstellungs-Anleitung erstellt: {guide_path}")


def main():
    import sys
    
    # Quellordner (wo dieses Script liegt)
    src = Path(__file__).parent.resolve()
    
    # Zielordner
    if len(sys.argv) > 1:
        dst = Path(sys.argv[1])
    else:
        # Standard: Backup mit Timestamp neben dem Projekt
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        dst = src.parent / f"CHAPiE_Backup_{timestamp}"
    
    print("=" * 60)
    print("CHAPPiE Backup Script (v2.0 - Sicher)")
    print("=" * 60)
    print(f"Quelle: {src}")
    print(f"Ziel:   {dst}")
    print()
    print("Folgende Ordner werden NICHT kopiert:")
    for d in sorted(EXCLUDE_DIRS):
        print(f"   - {d}")
    print()
    print("[SICHERHEIT] Folgende Dateien werden NICHT kopiert (API-Keys!):")
    for f in sorted(EXCLUDE_SECRET_FILES):
        print(f"   - {f}")
    print()
    print("[WICHTIG] ChromaDB wird als separates ZIP-Archiv gesichert.")
    print()
    
    input("Druecke ENTER zum Starten...")
    print()
    
    copy_project(src, dst)
    create_restore_guide(dst)
    
    print()
    print("=" * 60)
    print("Auf dem Ziel-PC ausfuehren:")
    print("   1. Python 3.10+ installieren")
    print("   2. Siehe RESTORE_GUIDE.md im Backup-Ordner")
    print()
    print("WICHTIG: API-Keys manuell in secrets.py eintragen!")
    print("WICHTIG: chroma_db_backup_*.zip entpacken für Gedächtnis!")
    print("=" * 60)

if __name__ == "__main__":
    main()
