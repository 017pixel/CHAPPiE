#!/usr/bin/env python3
"""Offline integrity validator for the current CHAPPiE report v6."""

from __future__ import annotations

import hashlib
import json
import re
from html import unescape
from pathlib import Path
from urllib.parse import unquote, urlsplit


ROOT = Path(__file__).resolve().parents[2]
REPORT = Path(__file__).with_name("CHAPPiE-Forschungsbericht-v6.html")
MANIFEST = Path(__file__).with_name("report-evidence-v6.json")


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _local_link_errors(html: str) -> list[str]:
    errors: list[str] = []
    values = re.findall(r'(?<![-\w])(?:href|src)="([^"]+)"', html)
    values.extend(re.findall(r"url\(['\"]?([^)'\"]+)", html))
    for raw in values:
        value = unescape(raw).strip()
        parsed = urlsplit(value)
        if not value or value.startswith("#") or parsed.scheme in {"http", "https", "mailto", "data"}:
            continue
        target = (REPORT.parent / unquote(parsed.path)).resolve()
        if not target.exists():
            errors.append(f"Lokaler Link fehlt: {value}")
    return errors


def validate() -> list[str]:
    errors: list[str] = []
    html = REPORT.read_text(encoding="utf-8")
    manifest = json.loads(MANIFEST.read_text(encoding="utf-8"))

    required_html = (
        "<title>CHAPPiE · Forschungsbericht v6</title>",
        'id="architektur-v6"',
        "CHAPPiERuntime",
        "TurnPipeline",
        "GenerationGateway",
        "Legacy-Code/README.md",
        "report-evidence-v6.json",
        "vor</b> der späteren Runtime-Modularisierung",
        "keine gemessene Beschleunigung",
        'id="weiterarbeit"',
        "Neue stabile CHAPPiE-Version",
        "bestehenden V6-Ergebnissen verglichen",
    )
    for marker in required_html:
        if marker not in html:
            errors.append(f"Pflichtinhalt fehlt: {marker}")

    if manifest.get("report_version") != "6":
        errors.append("Evidence-Manifest hat nicht Version 6")
    if manifest.get("validator_version") != "1":
        errors.append("Unbekannte Validatorversion im Evidence-Manifest")

    for item in manifest.get("evidence", []):
        relative_path = item.get("path", "")
        source = ROOT / relative_path
        if not source.is_file():
            errors.append(f"Evidence-Quelle fehlt: {relative_path}")
            continue
        if _sha256(source) != item.get("sha256"):
            errors.append(f"Evidence-Hash weicht ab: {relative_path}")
        symbol = item.get("symbol", "")
        if symbol and symbol not in source.read_text(encoding="utf-8"):
            errors.append(f"Evidence-Symbol fehlt: {relative_path}::{symbol}")
        if item.get("role") not in {"active", "historical"}:
            errors.append(f"Ungueltige Evidence-Rolle: {relative_path}")

    errors.extend(_local_link_errors(html))

    active_brain_pipeline_claims = (
        "aktive BrainPipeline",
        "BrainPipeline ist der aktive",
        "BrainPipeline ist produktiv",
    )
    for claim in active_brain_pipeline_claims:
        if claim.casefold() in html.casefold():
            errors.append(f"Veraltete aktive BrainPipeline-Aussage: {claim}")

    combined = html + MANIFEST.read_text(encoding="utf-8")
    secret_patterns = (
        r"\bsk-[A-Za-z0-9_-]{20,}\b",
        r"\bgsk_[A-Za-z0-9_-]{20,}\b",
        r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----",
    )
    for pattern in secret_patterns:
        if re.search(pattern, combined):
            errors.append(f"Moegliches Secret-Muster gefunden: {pattern}")

    if re.search(r"(?:src|href)=['\"]https?://", html) and re.search(
        r"<(?:script|link)[^>]+(?:src|href)=['\"]https?://",
        html,
    ):
        errors.append("Bericht bindet externe Script- oder Stylesheet-Ressourcen ein")
    return errors


def main() -> int:
    errors = validate()
    if errors:
        for error in errors:
            print(f"FEHLER: {error}")
        return 1
    print("OK: Forschungsbericht v6 und Evidence-Manifest sind valide")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
