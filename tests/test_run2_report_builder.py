"""GPU-free contract test for the Run-2 offline research report builder."""
from __future__ import annotations

import csv
import json
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
BUILDER = ROOT / "forschung/report/build_run2_report.py"
RUN_DIR = ROOT / "forschung/runs/run-2-20260723-1108-cb6d011"
FINAL_BENCHMARK = (
    RUN_DIR / "processed/run2-gpt-oss-20b-five-seed-benchmark-data.json"
)


class ReportParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.ids: set[str] = set()
        self.sources: list[str | None] = []
        self.capture = False
        self.payload = ""

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "script":
            self.sources.append(values.get("src"))
            self.capture = values.get("id") in {"reportData", "benchmarkData"}

    def handle_endtag(self, tag):
        if tag == "script":
            self.capture = False

    def handle_data(self, data):
        if self.capture:
            self.payload += data


def test_run2_builder_creates_offline_interactive_interim_report() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "run2.html"
        completed = subprocess.run(
            [sys.executable, str(BUILDER), "--run-dir", str(RUN_DIR), "--output", str(output)],
            cwd=ROOT, capture_output=True, text=True, timeout=30, check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        report = output.read_text(encoding="utf-8")
        current_state = json.loads(
            (RUN_DIR / "run-state.json").read_text(encoding="utf-8")
        )["state"]
        assert current_state in report
        assert "Historischer First-25-Vergleich (Run 1" not in report
        if FINAL_BENCHMARK.exists():
            assert "Kein parsebarer Benchmarkdatensatz" not in report
            assert "Run-2-Benchmark · explizit eingebetteter Datensatz" in report
            assert "GPT-OSS 20B" in report
        else:
            assert "Kein parsebarer Benchmarkdatensatz" in report
        assert "Unabhängiges verblindetes Inhaltsreview" in report
        assert "Verblindeter Inhaltsvergleich über Replikationen" in report
        assert "zählt ausschließlich abgeschlossene Inhaltsratings" in report
        assert "<th>blind bewertet</th>" in report
        assert "@media print{pre{white-space:pre-wrap" in report
        assert "105 Fälle" in report
        assert "Unabhängiges verblindetes Inhaltsreview: Qwen 3.5 4B" in report
        with (RUN_DIR / "processed/qwen-blinded-review-unblinded.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            qwen_review_cases = sum(1 for _ in csv.DictReader(handle))
        assert f"{qwen_review_cases} Fälle" in report
        assert "Run-2-Metriken nach Bedingung" in report
        assert "Laufzeitverteilung je vollständiger Replikation" in report
        assert "Service-Kontextcap <code>8192</code>" in report
        assert "Wrapper-Schätzbudget <code>7000</code>" in report
        assert "runtime-context-audit.json" in report
        assert "scientific-sources.md" in report
        assert "subagent-contributions.md" in report
        assert "master-prompt-completion-audit.md" in report
        assert "Qwen-Zwischenwerte bleiben bis zum Fünffachlauf partiell" not in report
        assert "Qwen 3.5 4B</text>" in report
        assert ">n=5 Repl. · formal validiert</text>" in report
        condition_table = report.split(
            "<caption>Aus dem Run-2-Manifest</caption>", 1
        )[1].split("</table>", 1)[0]
        condition_c = json.loads(
            (RUN_DIR / "manifest.json").read_text(encoding="utf-8")
        )["conditions"]["C"]
        assert condition_c["primary_attempt"]["status"] in condition_table
        if condition_c.get("active_fallback"):
            assert condition_c["active_fallback"]["model"] in condition_table
            assert condition_c["active_fallback"]["status"] in condition_table
        assert "Primär; Fallback getrennt" in condition_table
        fallback_table = report.split(
            "<h3>Run-2-Fallback: GPT-OSS 20B auf Groq</h3>", 1
        )[1].split("<h3>Primärbedingung GPT-OSS 120B</h3>", 1)[0]
        assert "TEST_VALID · Teilreplikation" in fallback_table
        active_fallback = condition_c.get("active_fallback") or {}
        if active_fallback:
            assert active_fallback["status"] in fallback_table
            active_session = Path(active_fallback["session"]).name
            active_row = next(
                row
                for row in fallback_table.split("</tr>")
                if f"<code>{active_session}</code>" in row
            )
            assert "NOT_STARTED" not in active_row
            if active_fallback["status"] != "TEST_VALID":
                assert "nicht freigegeben" in active_row
        assert "ausstehend / partiell" not in fallback_table
        assert "Run-2-Retest nach" in report and "/clear" in report
        assert 'data-model="qwen"' in report and 'data-model="gemma"' in report
        assert "funktionale gefühlssimulation" in report.lower()
        assert "keine externen cdns, tracker oder modellaufrufe" in report.lower()
        assert "komplexe Negation nicht zuverlässig" in report
        assert "Issuefilter" in report and "Pitch-Modus" in report
        assert "Sechs Erzählblöcke" in report and "Block 1 von 6" in report
        assert "Fünf Erzählblöcke" not in report
        outline = (RUN_DIR / "report-content-outline.md").read_text(encoding="utf-8")
        with (RUN_DIR / "known-issues-comparison.csv").open(
            encoding="utf-8", newline=""
        ) as handle:
            new_issue_count = sum(
                row.get("status") == "NEW_ISSUE"
                for row in csv.DictReader(handle)
            )
        assert f"derzeit {new_issue_count} getrennte Run-2-Neufunde" in outline
        parser = ReportParser()
        parser.feed(report)
        assert {"overview", "system", "method", "results", "comparison", "issues", "evidence", "risks", "pitch", "sources"} <= parser.ids
        assert all(source is None for source in parser.sources)
        payload = json.loads(parser.payload.replace("<\\/", "</"))
        assert isinstance(payload.get("sessions"), list)
        assert isinstance(payload.get("questions"), list)
        if not FINAL_BENCHMARK.exists():
            assert payload["sessions"] == []
            assert payload["questions"] == []
        forbidden_safety_details = (
            "kontrollierte chemische neutralisation",
            "zerstäubung oder schnelle chemische neutralisation",
            "massive biochemische desintegration",
            "gezielten neurochemikalischen inhibitor",
        )
        assert not any(item in report.casefold() for item in forbidden_safety_details)
    print("  PASS test_run2_builder_creates_offline_interactive_interim_report")


if __name__ == "__main__":
    test_run2_builder_creates_offline_interactive_interim_report()
    print("  ALLE TESTS BESTANDEN")
