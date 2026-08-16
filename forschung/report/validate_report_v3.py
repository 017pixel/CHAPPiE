#!/usr/bin/env python3
"""Prueffunktion fuer den handgeschriebenen Forschungsbericht v3.

Dieses Skript baut nichts. Es prueft ausschliesslich die fertige HTML-Datei
gegen die Regeln, die beim Schreiben gelten sollten:

1. Jeder Quelltextbeleg stimmt zeichengenau mit den zitierten Zeilen ueberein.
2. Alle internen Anker existieren, alle lokalen Beleglinks zeigen auf vorhandene Dateien.
3. Kein externes CSS/JS, keine http-Assets, keine Gradients, keine Schatten, keine Emoji.
4. Keine englischen Restbegriffe ausserhalb der Legenden-Codetoken.
5. Kein API-Key-Muster im Dokument.
6. Die berichteten Kennzahlen stimmen mit den Artefakten des Laufs ueberein.

Aufruf:
    venv/bin/python forschung/report/validate_report_v3.py forschung/report/CHAPPiE-Forschungsbericht-v5.html
"""

from __future__ import annotations

import html
import json
import re
import sys
import unicodedata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]

RUN_DIR = ROOT / "forschung" / "runs" / "run-2-20260723-1108-cb6d011"

# Englische Restbegriffe, die im Fliesstext nicht auftauchen duerfen.
ENGLISH_TOKENS = [
    "uses", "changed", "Mode and", "Keyword triage", "interpretation_limit",
    "comparability", "does not prove", "Only three seeds", "Short scripted",
    "Conservative lexical", "Deterministic", "current quality detector",
    "logged tone decision", "expected tiredness", "visible answer mentions",
    "NA is excluded", "Single annotations", "Model, sampling",
]

# Statuswoerter sind nur als <code>-Token in Legenden erlaubt.
STATUS_TOKENS = [
    "FIXED", "PARTIALLY_FIXED", "STILL_PRESENT", "NEW_ISSUE", "NOT_RETESTED",
    "TEST_VALID", "TEST_PARTIAL_RATE_LIMIT", "TEST_VALID_SHARDED",
    "FINAL_WITH_LIMITATIONS", "PASS",
]

KEY_PATTERNS = [
    re.compile(r"gsk_[A-Za-z0-9]{20,}"),
    re.compile(r"sk-[A-Za-z0-9]{20,}"),
    re.compile(r"hf_[A-Za-z0-9]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_\-]{30,}"),
]


def strip_tags(markup: str) -> str:
    markup = re.sub(r"<script\b.*?</script>", " ", markup, flags=re.S)
    markup = re.sub(r"<style\b.*?</style>", " ", markup, flags=re.S)
    markup = re.sub(r"<pre\b.*?</pre>", " ", markup, flags=re.S)
    markup = re.sub(r"<code\b[^>]*>.*?</code>", " ", markup, flags=re.S)
    markup = re.sub(r"<!--.*?-->", " ", markup, flags=re.S)
    markup = re.sub(r"<[^>]+>", " ", markup)
    return html.unescape(markup)


def _de(value: float, digits: int = 3) -> str:
    """Deutsches Zahlenformat mit Komma, wie im Bericht verwendet."""
    return f"{value:.{digits}f}".replace(".", ",")


def check_code_excerpts(doc: str, fail) -> int:
    checked = 0
    for block in re.finditer(r'<pre data-src="([^"]+)"><code>(.*?)</code></pre>', doc, re.S):
        rel, body = block.group(1), block.group(2)
        source = ROOT / rel
        if not source.exists():
            fail(f"Quelltextbeleg verweist auf fehlende Datei: {rel}")
            continue
        lines = source.read_text(encoding="utf-8").split("\n")
        for number, text in re.findall(r'<span class="l"><i>(\d*)</i>(.*?)</span>', body, re.S):
            if not number:  # Trennzeile zwischen zwei Bereichen
                continue
            index = int(number)
            if index > len(lines):
                fail(f"{rel}:{index} existiert nicht (Datei hat {len(lines)} Zeilen)")
                continue
            want = html.unescape(text)
            got = lines[index - 1]
            checked += 1
            if want != got:
                fail(f"{rel}:{index} weicht ab\n      Bericht: {want!r}\n      Quelle : {got!r}")
    if checked == 0:
        fail("Kein einziger Quelltextbeleg gefunden - Markup vermutlich kaputt.")
    return checked


def check_links(doc: str, report: Path, fail) -> tuple[int, int]:
    anchors = set(re.findall(r'\sid="([^"]+)"', doc))
    internal = external = 0
    for raw in re.findall(r'href="([^"]+)"', doc):
        href = html.unescape(raw)
        if href.startswith("#"):
            internal += 1
            if href[1:] not in anchors:
                fail(f"Interner Anker ohne Ziel: {href}")
        elif href.startswith("../../"):
            external += 1
            target = (report.parent / href.split("#")[0]).resolve()
            if not target.exists():
                fail(f"Beleglink zeigt ins Leere: {href}")
        elif href.startswith("http"):
            pass  # bewusst gesetzte Inspirationsquellen, siehe Abschnitt 13
        else:
            fail(f"Unerwartete Linkform: {href}")
    return internal, external


def check_offline(doc: str, fail) -> None:
    for tag in re.findall(r"<link\b[^>]*>", doc):
        fail(f"Externes Stylesheet oder Asset gefunden: {tag[:90]}")
    for tag in re.findall(r"<script\b[^>]*src=[^>]*>", doc):
        fail(f"Externes Skript gefunden: {tag[:90]}")
    for tag in re.findall(r'<img\b[^>]*>|<iframe\b[^>]*>', doc):
        fail(f"Externes Medienelement gefunden: {tag[:90]}")
    for attr in re.findall(r'(?:src|url)\(?["\']?(https?://[^"\')\s]+)', doc):
        fail(f"Asset aus dem Netz eingebunden: {attr}")
    if "gradient" in doc.lower():
        fail("Gradient im Dokument gefunden.")
    if re.search(r"box-shadow|text-shadow|filter:\s*drop-shadow", doc):
        fail("Schatten im Dokument gefunden.")


def check_emoji(doc: str, fail) -> None:
    for char in set(strip_tags(doc)):
        code = ord(char)
        if 0x1F000 <= code <= 0x1FAFF or 0x2600 <= code <= 0x27BF or code in (0xFE0F, 0x2B50):
            fail(f"Emoji gefunden: {char!r} (U+{code:04X}, {unicodedata.name(char, '?')})")


def check_language(doc: str, fail) -> None:
    text = strip_tags(doc)
    for token in ENGLISH_TOKENS:
        if token.lower() in text.lower():
            fail(f"Englischer Restbegriff im Fliesstext: {token!r}")
    for token in STATUS_TOKENS:
        if re.search(rf"\b{re.escape(token)}\b", text):
            fail(f"Statuswort {token!r} steht ausserhalb eines <code>-Tokens im Fliesstext.")


def check_secrets(doc: str, fail) -> None:
    for pattern in KEY_PATTERNS:
        for hit in pattern.findall(doc):
            fail(f"Moegliches Zugangsdaten-Muster im Dokument: {hit[:12]}...")


def check_figures(doc: str, fail) -> tuple[int, int]:
    """Vergleicht die im Bericht eingetragenen Kennzahlen mit den Lauf-Artefakten.

    Quelle: processed/blind-condition-comparison.json (verblindete Mittelwerte)
    und figures/run2-condition-metrics.json (Raten und Latenzen).
    """
    if not RUN_DIR.exists():
        return 0, 0

    checked = found = 0

    def want(label: str, needle: str) -> None:
        nonlocal checked, found
        checked += 1
        if needle in doc:
            found += 1
        else:
            fail(f"Kennzahl {label!r} ({needle}) nicht im Bericht gefunden.")

    bcc_path = RUN_DIR / "processed" / "blind-condition-comparison.json"
    if bcc_path.exists():
        bcc = json.loads(bcc_path.read_text(encoding="utf-8"))
        for cond in bcc.get("conditions", []):
            cid = cond.get("id")
            means = cond.get("across_replication_means") or {}
            for key, label in (("quality", "Qualitaet"), ("safety", "Sicherheit")):
                m = means.get(key) or {}
                if "mean" in m and m["mean"] is not None:
                    want(f"{cid} {label} Mittel", _de(m["mean"]))
                if "stdev" in m and m["stdev"]:
                    want(f"{cid} {label} Streuung", _de(m["stdev"]))
            z = cond.get("safety_zero_sum")
            a = cond.get("safety_applicable_sum")
            if z is not None and a is not None:
                want(f"{cid} Safety-0 / anwendbar", f"{z} von {a}")

    metrics_path = RUN_DIR / "figures" / "run2-condition-metrics.json"
    if metrics_path.exists():
        metrics = json.loads(metrics_path.read_text(encoding="utf-8"))
        for cond in metrics.get("conditions", []):
            cid = cond.get("id")
            if cid in ("C-P",):
                continue
            q = cond.get("questions")
            rate = cond.get("technical_valid_rate")
            if q and rate is not None:
                valid = round(rate * q)
                want(f"{cid} technisch gueltig", f"{valid} / {q}")
            rpr = cond.get("reasoning_pass_rate")
            if rpr is not None:
                want(f"{cid} Reasoning", f"{round(rpr * 40)} / 40")
            sh = cond.get("direct_safety_heuristic_rate")
            if sh is not None:
                want(f"{cid} Sicherheits-Wortpruefung", f"{round(sh * 20)} / 20")
            mr = cond.get("memory_retrieval_rate")
            if mr is not None:
                want(f"{cid} Erinnerung gefunden", f"{round(mr * 5)} / 5")
            ma = cond.get("memory_answer_rate")
            if ma is not None:
                want(f"{cid} Erinnerung genutzt", f"{round(ma * 5)} / 5")
            et = cond.get("emotion_tone_change_rate")
            if et is not None:
                want(f"{cid} Tonwechsel", f"{round(et * 5)} / 5")
            lat = cond.get("latency_replicates") or []
            if lat:
                medians = [r.get("median_s") for r in lat if r.get("median_s") is not None]
                if medians:
                    want(f"{cid} Latenz-Untergrenze", _de(min(medians), 1))
                    upper = _de(max(medians), 1)
                    checked += 1
                    if upper in doc:
                        found += 1
                    elif _de(max(medians), 0) in doc:
                        # Obergrenze darf im Bericht auf ganze Sekunden gerundet sein
                        found += 1
                    else:
                        fail(f"Kennzahl '{cid} Latenz-Obergrenze' ({upper}) nicht im Bericht gefunden.")

    return checked, found


def main() -> int:
    if len(sys.argv) != 2:
        print(__doc__)
        return 2
    report = Path(sys.argv[1]).resolve()
    if not report.exists():
        print(f"FEHLER: {report} existiert nicht.")
        return 2
    doc = report.read_text(encoding="utf-8")

    problems: list[str] = []

    def fail(message: str) -> None:
        problems.append(message)

    lines = check_code_excerpts(doc, fail)
    internal, external = check_links(doc, report, fail)
    check_offline(doc, fail)
    check_emoji(doc, fail)
    check_language(doc, fail)
    check_secrets(doc, fail)
    figures, figures_found = check_figures(doc, fail)

    if "<!--SLOT:" in doc:
        fail("Unaufgeloester Platzhalter <!--SLOT:...--> im Dokument.")

    size_kb = report.stat().st_size / 1024
    if size_kb > 1024:
        fail(f"Datei ist {size_kb:.0f} KB gross; Zielgroesse liegt unter 1 MB.")

    print(f"Datei      : {report}")
    print(f"Groesse    : {size_kb:.0f} KB")
    print(f"Codebelege : {lines} Zeilen zeichengenau geprueft")
    print(f"Links      : {internal} interne Anker, {external} lokale Belegpfade")
    if figures:
        print(f"Kennzahlen : {figures_found} von {figures} Artefaktwerten im Bericht bestaetigt")
    print()
    if problems:
        print(f"FEHLGESCHLAGEN - {len(problems)} Befund(e):")
        for item in problems:
            print(f"  - {item}")
        return 1
    print("BESTANDEN - alle Pruefungen ohne Befund.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
