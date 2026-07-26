#!/usr/bin/env python3
"""Statische Abschlusspruefung des offline-faehigen Forschungsberichts."""
from __future__ import annotations

import argparse
import base64
import json
import re
import shutil
import subprocess
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_REPORT = ROOT / "forschung" / "report" / "CHAPPiE-Forschungsbericht.html"


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.scripts: list[str | None] = []
        self.stylesheets: list[str | None] = []
        self.images: list[str] = []
        self.counts: dict[str, int] = {}
        self._json_script = False
        self.json_payload = ""
        self._hidden_text_depth = 0
        self.visible_text = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = dict(attrs)
        self.counts[tag] = self.counts.get(tag, 0) + 1
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "script":
            self.scripts.append(values.get("src"))
            self._json_script = values.get("id") == "benchmarkData"
            self._hidden_text_depth += 1
        if tag == "style":
            self._hidden_text_depth += 1
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))
        if tag == "img" and values.get("src"):
            self.images.append(str(values["src"]))

    def handle_endtag(self, tag: str) -> None:
        if tag == "script":
            self._json_script = False
            self._hidden_text_depth = max(0, self._hidden_text_depth - 1)
        if tag == "style":
            self._hidden_text_depth = max(0, self._hidden_text_depth - 1)

    def handle_data(self, data: str) -> None:
        if self._json_script:
            self.json_payload += data
        if self._hidden_text_depth == 0:
            self.visible_text += data


def check(condition: bool, message: str, results: list[dict[str, Any]]) -> None:
    results.append({"ok": bool(condition), "check": message})


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", nargs="?", type=Path, default=DEFAULT_REPORT)
    parser.add_argument("--json-output", type=Path)
    args = parser.parse_args()
    if not args.report.exists():
        raise SystemExit(f"Report fehlt: {args.report}")

    text = args.report.read_text(encoding="utf-8")
    parsed = ReportParser()
    parsed.feed(text)
    results: list[dict[str, Any]] = []
    required_ids = {
        "start", "chappie", "problem", "fragen", "pipeline", "memory", "life",
        "emotionen", "cloud", "prompt", "design", "bedingungen", "benchmarks",
        "dialoge", "historie", "ergebnisse", "vorteile", "risiken", "grenzen",
        "fazit", "repro", "pitch", "quellen",
    }
    check(required_ids <= parsed.ids, "alle Pflichtabschnitte besitzen IDs", results)
    missing_anchors = [href for href in parsed.links if href.startswith("#") and href[1:] not in parsed.ids]
    check(not missing_anchors, "alle internen Ankerziele existieren", results)
    missing_local_links = []
    for href in parsed.links:
        parsed_href = urlsplit(href)
        if parsed_href.scheme or href.startswith("#"):
            continue
        local_path = (args.report.parent / unquote(parsed_href.path)).resolve()
        if not local_path.exists():
            missing_local_links.append(href)
    check(not missing_local_links, "alle lokalen Beleglinks und Rohlogziele existieren", results)
    check(parsed.counts.get("details", 0) >= 8, "technische Details sind einklappbar", results)
    check(parsed.counts.get("svg", 0) >= 3, "mindestens drei Inline-SVG-Diagramme", results)
    check(parsed.counts.get("table", 0) >= 4, "Benchmark- und Techniktabellen vorhanden", results)
    check(not parsed.stylesheets, "keine externen Stylesheets", results)
    check(all(source is None for source in parsed.scripts), "keine externen JavaScript-Dateien", results)
    inline_javascript = re.findall(
        r'<script(?![^>]*type=["\']application/json["\'])(?![^>]*\bsrc=)[^>]*>(.*?)</script>',
        text,
        flags=re.IGNORECASE | re.DOTALL,
    )
    node = shutil.which("node")
    if node and inline_javascript:
        javascript_check = subprocess.run(
            [node, "--check", "-"],
            input="\n".join(inline_javascript),
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        check(javascript_check.returncode == 0, "Inline-JavaScript besteht node --check", results)
    else:
        check(not inline_javascript, "Inline-JavaScript-Syntaxcheck verfuegbar oder nicht erforderlich", results)
    check("gradient" not in text.lower(), "keine Gradients", results)
    check("box-shadow" not in text.lower() and "text-shadow" not in text.lower(), "keine Glow-/Shadow-Effekte", results)
    check(not re.search(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F]", parsed.visible_text), "keine Emojis im sichtbaren UI", results)
    check(not re.search(r"\{\{[A-Z0-9_]+\}\}", text), "keine unaufgeloesten Template-Marker", results)
    check(all(source.startswith("data:image/") for source in parsed.images), "Bilder als Data-URI eingebettet", results)
    image_decode_ok = True
    for source in parsed.images:
        if ";base64," in source:
            try:
                base64.b64decode(source.split(",", 1)[1], validate=True)
            except Exception:
                image_decode_ok = False
    check(image_decode_ok, "eingebettete Base64-Bilder dekodierbar", results)
    try:
        data = json.loads(parsed.json_payload.replace("<\\/", "</"))
        data_ok = isinstance(data, dict) and "sessions" in data and "questions" in data
    except Exception:
        data = {}
        data_ok = False
    check(data_ok, "eingebettete Benchmarkdaten sind gueltiges JSON", results)
    run2_payload = str(data.get("run", "")).startswith("run-2-")
    raw_records_omitted = (
        data.get("questions") == []
        and isinstance(data.get("question_records_omitted_from_html"), int)
        and bool(data.get("question_record_policy"))
    )
    check(
        not run2_payload or raw_records_omitted,
        "Run-2-HTML enthaelt keine verbatim Benchmarkantworten",
        results,
    )
    for label in ("Qwen 3.5 4B", "Gemma 4 E4B", "GPT-OSS 120B"):
        check(label in text, f"Bedingung klar beschriftet: {label}", results)
    check("historische qualitative" in text.lower() and "nicht direkt" in text.lower(), "historische und aktuelle Evidenz getrennt", results)
    check("funktionale Gefühlssimulation" in text and "nicht nachgewiesen" in text, "keine unbelegte Gefuehls-/Bewusstseinsbehauptung", results)
    check("Pitch-Unterstützung" in text and "0:00" in text, "Pitch-Sektion mit Sprecherzeiten", results)
    check("IntersectionObserver" in text and "dialogModel" in text and "expandAll" in text, "Sidebar-, Filter- und Details-Interaktion enthalten", results)
    check(len(text.encode("utf-8")) > 100_000, "Report enthaelt eingebettete Evidenz und Assets", results)

    # Vergleiche gegen den konfigurierten Key, ohne ihn auszugeben.
    try:
        from config.config import settings
        secret = str(getattr(settings, "groq_api_key", "") or "").strip()
    except Exception:
        secret = ""
    check(not secret or secret not in text, "konfigurierter Groq-Key nicht im Bericht", results)
    suspicious = re.findall(r"(?:gsk_|sk-)[A-Za-z0-9_-]{16,}", text)
    check(not suspicious, "keine offensichtlichen API-Key-Muster", results)

    report = {
        "report": str(args.report),
        "bytes": len(text.encode("utf-8")),
        "checks": len(results),
        "passed": sum(item["ok"] for item in results),
        "failed": [item["check"] for item in results if not item["ok"]],
        "browser_preview": "nicht verfuegbar; statische Pruefung dokumentiert",
        "embedded_sessions": [session.get("session_id") for session in data.get("sessions", [])] if isinstance(data, dict) else [],
    }
    if args.json_output:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(report, indent=2, ensure_ascii=False))
    if report["failed"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
