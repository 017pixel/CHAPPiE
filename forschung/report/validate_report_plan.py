#!/usr/bin/env python3
"""Validate the Run-2 report plan against its own offline design contract."""

from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import subprocess
from collections import Counter
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_HTML = ROOT / "forschung" / "report" / "report-plan.html"
DEFAULT_MARKDOWN = ROOT / "forschung" / "report" / "report-plan.md"
ISSUE_MATRIX = (
    ROOT
    / "forschung"
    / "runs"
    / "run-2-20260723-1108-cb6d011"
    / "known-issues-comparison.csv"
)

REQUIRED_IDS = {
    "overview",
    "entry",
    "terms",
    "system",
    "run2",
    "questions",
    "flow",
    "memory",
    "life",
    "emotion",
    "cloud",
    "method",
    "benchmarks",
    "findings",
    "comparison",
    "evidence",
    "risks",
    "conclusion",
    "repro",
    "demo",
    "pitch",
    "qa",
}
REQUIRED_TOKENS = {
    "--bg-page:#191919",
    "--bg-surface:#1e1e1e",
    "--text:#eee",
    "--sage:#8fae96",
    "--tertiary:#929292",
}
FORBIDDEN_CLAIMS = (
    "chappie hat bewusstsein",
    "chappie besitzt echte gefühle",
    "beweist bewusstsein",
    "beweist subjektive",
)


class PlanParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.links: list[str] = []
        self.images: list[str] = []
        self.external_scripts: list[str] = []
        self.external_styles: list[str] = []
        self.inline_scripts: list[str] = []
        self._in_inline_script = False
        self._script_buffer: list[str] = []

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(str(values["id"]))
        if tag == "a" and values.get("href"):
            self.links.append(str(values["href"]))
        if tag == "img" and values.get("src"):
            self.images.append(str(values["src"]))
        if tag == "script":
            source = values.get("src")
            if source:
                self.external_scripts.append(str(source))
            else:
                self._in_inline_script = True
                self._script_buffer = []
        if tag == "link" and values.get("rel") == "stylesheet":
            self.external_styles.append(str(values.get("href") or ""))

    def handle_data(self, data: str) -> None:
        if self._in_inline_script:
            self._script_buffer.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "script" and self._in_inline_script:
            self.inline_scripts.append("".join(self._script_buffer))
            self._in_inline_script = False
            self._script_buffer = []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--html", type=Path, default=DEFAULT_HTML)
    parser.add_argument("--markdown", type=Path, default=DEFAULT_MARKDOWN)
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()

    html = args.html.read_text(encoding="utf-8")
    markdown = args.markdown.read_text(encoding="utf-8")
    parsed = PlanParser()
    parsed.feed(html)
    checks: list[dict[str, Any]] = []

    def check(name: str, passed: bool, detail: Any) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    missing_ids = sorted(REQUIRED_IDS - parsed.ids)
    check("complete_section_hierarchy", not missing_ids, missing_ids)

    broken_anchors = sorted(
        href for href in parsed.links
        if href.startswith("#") and href[1:] not in parsed.ids
    )
    check("internal_navigation_targets_exist", not broken_anchors, broken_anchors)

    external_dependencies = [
        value
        for value in parsed.external_scripts + parsed.external_styles + parsed.images
        if urlsplit(value).scheme or value.startswith("//")
    ]
    check(
        "no_external_runtime_dependencies",
        not external_dependencies
        and not parsed.external_scripts
        and not parsed.external_styles,
        external_dependencies,
    )

    missing_tokens = sorted(token for token in REQUIRED_TOKENS if token not in html)
    forbidden_visuals = [
        token
        for token in ("linear-gradient", "radial-gradient", "box-shadow", "text-shadow")
        if token in html.casefold()
    ]
    check(
        "notion_dark_design_tokens",
        not missing_tokens and not forbidden_visuals,
        {"missing": missing_tokens, "forbidden": forbidden_visuals},
    )

    responsive_contract = all(
        token in html
        for token in (
            "@media(max-width:980px)",
            "@media(max-width:640px)",
            "@media(prefers-reduced-motion:reduce)",
            "@media print",
        )
    )
    check("responsive_reduced_motion_and_print", responsive_contract, "four media contracts")

    accessibility_contract = all(
        token in html
        for token in (
            'class="skip"',
            'aria-label="Dokumentnavigation"',
            'aria-controls="sidebar"',
            ":focus-visible",
            "<main",
            "<nav",
        )
    )
    check("accessibility_structure", accessibility_contract, "skip, labels, focus and landmarks")

    node = shutil.which("node")
    javascript_ok = bool(parsed.inline_scripts)
    javascript_detail = "no inline script"
    if node and parsed.inline_scripts:
        result = subprocess.run(
            [node, "--check", "-"],
            input="\n".join(parsed.inline_scripts),
            text=True,
            capture_output=True,
            check=False,
            timeout=15,
        )
        javascript_ok = result.returncode == 0
        javascript_detail = result.stderr.strip() or "node --check passed"
    check("inline_javascript_syntax", javascript_ok, javascript_detail)

    def normalized_visible(value: str) -> str:
        without_markup = re.sub(r"<[^>]+>|[`\*]", " ", value)
        return " ".join(without_markup.split())

    normalized_markdown = normalized_visible(markdown)
    normalized_html = normalized_visible(html)
    with ISSUE_MATRIX.open(encoding="utf-8", newline="") as handle:
        status_counts = Counter(
            row.get("status", "")
            for row in csv.DictReader(handle)
        )
    status_labels = tuple(
        f"{status_counts.get(status, 0)} {status}"
        for status in (
            "FIXED",
            "PARTIALLY_FIXED",
            "STILL_PRESENT",
            "NOT_RETESTED",
            "NEW_ISSUE",
        )
    )
    status_mismatches = [
        label
        for label in status_labels
        if label not in normalized_markdown or label not in normalized_html
    ]
    check("issue_counts_match_in_both_plans", not status_mismatches, status_mismatches)

    model_terms = (
        "Qwen",
        "Gemma",
        "GPT-OSS 120B",
        "GPT-OSS 20B",
        "Response-Plan",
        "Prompt",
    )
    missing_model_terms = [
        term for term in model_terms
        if term.casefold() not in markdown.casefold() or term.casefold() not in html.casefold()
    ]
    check("condition_separation_matches", not missing_model_terms, missing_model_terms)

    plan_terms = (
        "Pitch",
        "Live-Demo",
        "Forschungsfragen",
        "Run 1",
        "Run 2",
        "1920",
        "Smartphone",
    )
    missing_plan_terms = [
        term for term in plan_terms
        if term.casefold() not in markdown.casefold() or term.casefold() not in html.casefold()
    ]
    check("content_and_qa_plan_match", not missing_plan_terms, missing_plan_terms)

    combined = f"{markdown}\n{re.sub(r'<[^>]+>', ' ', html)}".casefold()
    claim_hits = [phrase for phrase in FORBIDDEN_CLAIMS if phrase in combined]
    epistemic_limits = (
        "funktional simuliert" in combined
        and "nicht nachgewiesen" in combined
    )
    check(
        "epistemic_language_contract",
        not claim_hits and epistemic_limits,
        {"forbidden_hits": claim_hits, "limits_present": epistemic_limits},
    )

    result = {
        "schema_version": 1,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "html": str(args.html),
        "markdown": str(args.markdown),
        "checks": checks,
        "passed": all(item["passed"] for item in checks),
    }
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(
            json.dumps(result, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    print(
        json.dumps(
            {
                "passed": result["passed"],
                "checks": len(checks),
                "failed": [item["name"] for item in checks if not item["passed"]],
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0 if result["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
