"""
CHAPPiE - Cleanup Script
========================
Loescht Cache-Dateien und unnnoetige Ordner um Speicherplatz freizugeben.

Usage:
    python cleanup.py --dry-run           # Zeigt was geloescht wuerde
    python cleanup.py                     # Fuehrt Cleanup durch
    python cleanup.py --include-chromadb  # Loescht auch ChromaDB (VORSICHT!)
    python cleanup.py --yes               # Ohne Bestaetigung
"""

import os
import sys
import shutil
import argparse
from pathlib import Path

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich.progress import Progress
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

PROJECT_ROOT = Path(__file__).parent


def get_size(path: Path) -> int:
    """Berechnet die Groesse eines Pfades in Bytes."""
    if not path.exists():
        return 0
    if path.is_file():
        return path.stat().st_size
    total = 0
    try:
        for item in path.rglob("*"):
            if item.is_file():
                try:
                    total += item.stat().st_size
                except (PermissionError, OSError):
                    pass
    except (PermissionError, OSError):
        pass
    return total


def format_size(size_bytes: int) -> str:
    """Formatiert Bytes in lesbare Groesse."""
    for unit in ["B", "KB", "MB", "GB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} TB"


def find_cleanup_targets(include_chromadb: bool = False) -> list:
    """Findet alle Ordner/Dateien die geloescht werden koennen."""
    targets = []
    
    venv_path = PROJECT_ROOT / "venv"
    if venv_path.exists():
        targets.append({
            "path": venv_path,
            "name": "venv/",
            "description": "Virtual Environment",
            "safe": True,
            "size": get_size(venv_path)
        })
    
    venv_old_path = PROJECT_ROOT / "venv_old"
    if venv_old_path.exists():
        targets.append({
            "path": venv_old_path,
            "name": "venv_old/",
            "description": "Altes Virtual Environment",
            "safe": True,
            "size": get_size(venv_old_path)
        })
    
    for pycache in PROJECT_ROOT.rglob("__pycache__"):
        if pycache.is_dir():
            targets.append({
                "path": pycache,
                "name": str(pycache.relative_to(PROJECT_ROOT)) + "/",
                "description": "Python Bytecode Cache",
                "safe": True,
                "size": get_size(pycache)
            })
    
    for pyc_file in PROJECT_ROOT.rglob("*.pyc"):
        targets.append({
            "path": pyc_file,
            "name": str(pyc_file.relative_to(PROJECT_ROOT)),
            "description": "Kompilierte Python Datei",
            "safe": True,
            "size": pyc_file.stat().st_size if pyc_file.exists() else 0
        })
    
    cache_path = PROJECT_ROOT / ".cache"
    if cache_path.exists():
        targets.append({
            "path": cache_path,
            "name": ".cache/",
            "description": "Lokaler Cache Ordner",
            "safe": True,
            "size": get_size(cache_path)
        })
    
    pytest_cache = PROJECT_ROOT / ".pytest_cache"
    if pytest_cache.exists():
        targets.append({
            "path": pytest_cache,
            "name": ".pytest_cache/",
            "description": "Pytest Cache",
            "safe": True,
            "size": get_size(pytest_cache)
        })
    
    mypy_cache = PROJECT_ROOT / ".mypy_cache"
    if mypy_cache.exists():
        targets.append({
            "path": mypy_cache,
            "name": ".mypy_cache/",
            "description": "Mypy Type Checker Cache",
            "safe": True,
            "size": get_size(mypy_cache)
        })
    
    if include_chromadb:
        chroma_path = PROJECT_ROOT / "data" / "chroma_db"
        if chroma_path.exists():
            targets.append({
                "path": chroma_path,
                "name": "data/chroma_db/",
                "description": "ChromaDB Langzeitgedaechtnis",
                "safe": False,
                "size": get_size(chroma_path)
            })
    
    return targets


def print_simple_output(targets: list, dry_run: bool):
    """Einfache Ausgabe ohne Rich."""
    total_size = sum(t["size"] for t in targets)
    
    print("\n" + "=" * 50)
    print("CHAPPiE Cleanup")
    print("=" * 50)
    
    if not targets:
        print("\nKeine Cache-Dateien gefunden. Projekt ist sauber!")
        return
    
    print(f"\nGefundene Ziele ({len(targets)}):\n")
    for t in targets:
        warning = " [!] " if not t["safe"] else "     "
        print(f"{warning}{t['name']:<30} {format_size(t['size']):>10}  ({t['description']})")
    
    print(f"\nGesamt: {format_size(total_size)}")
    
    if dry_run:
        print("\n[DRY RUN] Nichts geloescht. Fuehre ohne --dry-run aus.")
    else:
        print("\nVerwende --dry-run um zu sehen was geloescht wuerde.")


def print_rich_output(console: Console, targets: list, dry_run: bool):
    """Farbige Ausgabe mit Rich."""
    total_size = sum(t["size"] for t in targets)
    
    console.print()
    console.print(Panel.fit(
        "[bold cyan]CHAPPiE Cleanup Script[/bold cyan]",
        subtitle="Speicherplatz optimieren"
    ))
    
    if not targets:
        console.print("\n[green]Keine Cache-Dateien gefunden. Projekt ist sauber![/green]")
        return
    
    table = Table(title="\nGefundene Ziele", show_header=True, header_style="bold")
    table.add_column("Ziel", style="cyan")
    table.add_column("Groesse", justify="right", style="yellow")
    table.add_column("Beschreibung", style="dim")
    table.add_column("Status", justify="center")
    
    for t in targets:
        status = "[red]![/red]" if not t["safe"] else "[green]OK[/green]"
        table.add_row(t["name"], format_size(t["size"]), t["description"], status)
    
    console.print(table)
    console.print(f"\n[bold]Gesamt:[/bold] {format_size(total_size)}")
    
    unsafe = [t for t in targets if not t["safe"]]
    if unsafe:
        console.print("\n[yellow]![/yellow] = Enthaelt wichtige Daten - wird nur mit --include-chromadb geloescht")
    
    if dry_run:
        console.print("\n[dim][DRY RUN] Nichts geloescht. Fuehre ohne --dry-run aus.[/dim]")


def delete_targets(targets: list, console=None):
    """Loescht alle Ziele."""
    deleted_size = 0
    
    for t in targets:
        try:
            if t["path"].is_dir():
                shutil.rmtree(t["path"])
            else:
                t["path"].unlink()
            deleted_size += t["size"]
            if console:
                console.print(f"  [green]Geloescht:[/green] {t['name']}")
            else:
                print(f"  Geloescht: {t['name']}")
        except PermissionError as e:
            if console:
                console.print(f"  [red]Fehler:[/red] {t['name']} - Keine Berechtigung")
            else:
                print(f"  Fehler: {t['name']} - Keine Berechtigung")
        except Exception as e:
            if console:
                console.print(f"  [red]Fehler:[/red] {t['name']} - {e}")
            else:
                print(f"  Fehler: {t['name']} - {e}")
    
    return deleted_size


def main():
    parser = argparse.ArgumentParser(
        description="CHAPPiE Cleanup Script - Loescht Cache-Dateien",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Beispiele:
  python cleanup.py --dry-run           # Zeigt was geloescht wuerde
  python cleanup.py                     # Standard Cleanup
  python cleanup.py --include-chromadb  # Loescht auch ChromaDB (VORSICHT!)
  python cleanup.py --yes               # Ohne Bestaetigung

Hinweis: Die Embedding-Modelle (~500MB-2GB) liegen in:
  Windows: %%USERPROFILE%%\\.cache\\huggingface\\
  Linux: ~/.cache/huggingface/
Diese werden NICHT von diesem Script geloescht.
        """
    )
    parser.add_argument("--dry-run", action="store_true", help="Zeigt nur was geloescht wuerde")
    parser.add_argument("--include-chromadb", action="store_true", help="Loescht auch ChromaDB (VORSICHT: Alle Erinnerungen!)")
    parser.add_argument("--yes", "-y", action="store_true", help="Ueberspringt Bestaetigung")
    args = parser.parse_args()
    
    console = None
    if RICH_AVAILABLE:
        console = Console()
    
    targets = find_cleanup_targets(include_chromadb=args.include_chromadb)
    
    if console:
        print_rich_output(console, targets, args.dry_run)
    else:
        print_simple_output(targets, args.dry_run)
    
    if not targets or args.dry_run:
        return
    
    if args.include_chromadb:
        chroma_targets = [t for t in targets if not t["safe"]]
        if chroma_targets:
            if console:
                console.print("\n[bold red]WARNUNG:[/bold red] Du loeschst das Langzeitgedaechtnis (ChromaDB)!")
                console.print("[red]Alle Erinnerungen werden unwiderruflich geloescht![/red]")
            else:
                print("\nWARNUNG: Du loeschst das Langzeitgedaechtnis (ChromaDB)!")
                print("Alle Erinnerungen werden unwiderruflich geloescht!")
    
    if not args.yes:
        if console:
            confirm = console.input("\n[bold]Fortfahren? (j/n):[/bold] ")
        else:
            confirm = input("\nFortfahren? (j/n): ")
        
        if confirm.lower() not in ["j", "ja", "y", "yes"]:
            if console:
                console.print("[yellow]Abgebrochen.[/yellow]")
            else:
                print("Abgebrochen.")
            return
    
    if console:
        console.print("\n[cyan]Loesche Dateien...[/cyan]")
    else:
        print("\nLoesche Dateien...")
    
    deleted_size = delete_targets(targets, console)
    
    if console:
        console.print(f"\n[green bold]Fertig![/green bold] {format_size(deleted_size)} freigegeben.")
        console.print("\n[dim]Tipp: Virtual Environment neu erstellen mit:[/dim]")
        console.print("[dim]  python -m venv venv[/dim]")
        console.print("[dim]  .\\venv\\Scripts\\activate  # Windows[/dim]")
        console.print("[dim]  pip install -r requirements.txt[/dim]")
    else:
        print(f"\nFertig! {format_size(deleted_size)} freigegeben.")
        print("\nTipp: Virtual Environment neu erstellen mit:")
        print("  python -m venv venv")
        print("  .\\venv\\Scripts\\activate  # Windows")
        print("  pip install -r requirements.txt")


if __name__ == "__main__":
    main()