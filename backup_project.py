r"""
CHAPiE - Backup Script
=======================
Erstellt eine saubere Kopie des Projekts ohne venv, __pycache__ und andere unnoetige Dateien.

Verwendung:
    python backup_project.py
    
    oder mit Zielordner:
    python backup_project.py D:\USB_STICK\CHAPiE_Backup
"""

import os
import shutil
from pathlib import Path
from datetime import datetime

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

def should_exclude(path: Path) -> bool:
    """Prueft ob ein Pfad ausgeschlossen werden soll."""
    name = path.name
    
    # Ordner pruefen
    if path.is_dir():
        if name in EXCLUDE_DIRS:
            return True
        if name.endswith('.egg-info'):
            return True
    
    # Dateien pruefen
    if path.is_file():
        for ext in EXCLUDE_FILES:
            if name.endswith(ext):
                return True
    
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
    
    for item in src.rglob('*'):
        # Relativer Pfad
        rel_path = item.relative_to(src)
        
        # Pruefe ob irgendein Teil des Pfads ausgeschlossen ist
        skip = False
        for part in rel_path.parts:
            if part in EXCLUDE_DIRS or part.endswith('.egg-info'):
                skip = True
                break
        
        if skip or should_exclude(item):
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
    
    print(f"\n\nBackup abgeschlossen!")
    print(f"   Ordner: {dir_count}")
    print(f"   Dateien: {file_count}")
    print(f"   Ziel: {dst}")

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
    print("CHAPiE Backup Script")
    print("=" * 60)
    print(f"Quelle: {src}")
    print(f"Ziel:   {dst}")
    print()
    print("Folgende Ordner werden NICHT kopiert:")
    for d in sorted(EXCLUDE_DIRS):
        print(f"   - {d}")
    print()
    
    input("Druecke ENTER zum Starten...")
    print()
    
    copy_project(src, dst)
    
    print()
    print("=" * 60)
    print("Auf dem Ziel-PC ausfuehren:")
    print("   1. Python 3.10+ installieren")
    print("   2. cd CHAPiE_Backup_...")
    print("   3. python -m venv venv")
    print("   4. .\\venv\\Scripts\\activate")
    print("   5. pip install -r requirements.txt")
    print("   6. streamlit run app.py")
    print("=" * 60)

if __name__ == "__main__":
    main()
