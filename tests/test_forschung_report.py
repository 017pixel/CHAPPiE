"""Lokale, GPU-freie Tests fuer den Forschungsbericht und seine Datenauswertung."""
from __future__ import annotations

import json
import re
import subprocess
import sys
import tempfile
from html.parser import HTMLParser
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent


class StructuralParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids: set[str] = set()
        self.details = 0
        self.scripts = []
        self.stylesheets = []

    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if tag == "details":
            self.details += 1
        if tag == "script":
            self.scripts.append(values.get("src"))
        if tag == "link" and values.get("rel") == "stylesheet":
            self.stylesheets.append(values.get("href"))


def relative_luminance(color: str) -> float:
    channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
    linear = [
        value / 12.92
        if value <= 0.04045
        else ((value + 0.055) / 1.055) ** 2.4
        for value in channels
    ]
    return 0.2126 * linear[0] + 0.7152 * linear[1] + 0.0722 * linear[2]


def contrast_ratio(foreground: str, background: str) -> float:
    first, second = sorted(
        (relative_luminance(foreground), relative_luminance(background)),
        reverse=True,
    )
    return (first + 0.05) / (second + 0.05)


def test_template_design_contract() -> None:
    template = (ROOT / "forschung" / "report" / "report_template.html").read_text(encoding="utf-8")
    assert "gradient" not in template.lower(), "Designvertrag verbietet Gradients"
    assert "glow" not in template.lower(), "Designvertrag verbietet Glow-Effekte"
    assert 'src="http' not in template.lower(), "Keine externen Scripts"
    assert 'href="http' not in template.lower() or "source-list" in template, "Nur Quellenlinks duerfen extern sein"
    assert "{{DATA_JSON}}" in template
    assert "<details" in template
    print("  PASS test_template_design_contract")


def test_run2_tertiary_text_meets_wcag_aa() -> None:
    plan = (ROOT / "forschung" / "report" / "report-plan.html").read_text(
        encoding="utf-8"
    )
    builder = (ROOT / "forschung" / "report" / "build_run2_report.py").read_text(
        encoding="utf-8"
    )
    for source in (plan, builder):
        match = re.search(r"--tertiary:(#[0-9a-fA-F]{6})", source)
        assert match, "Tertiärfarbe fehlt"
        foreground = match.group(1)
        for background in ("#191919", "#1e1e1e", "#202020", "#232323", "#2a2a2a"):
            assert contrast_ratio(foreground, background) >= 4.5, (
                foreground,
                background,
                contrast_ratio(foreground, background),
            )
    print("  PASS test_run2_tertiary_text_meets_wcag_aa")


def test_run2_result_svgs_use_current_status_and_contrast() -> None:
    run_dir = (
        ROOT
        / "forschung"
        / "runs"
        / "run-2-20260723-1108-cb6d011"
    )
    paths = [
        run_dir / "build_result_figures.py",
        run_dir / "figures" / "run2-condition-metrics.svg",
        run_dir / "figures" / "run2-latency-by-replication.svg",
    ]
    sources = [path.read_text(encoding="utf-8") for path in paths]
    for path, source in zip(paths, sources):
        assert "#7a7a7a" not in source, path
        assert "#929292" in source, path
    rendered = "\n".join(sources[1:])
    assert "Qwen bleibt partiell" not in rendered
    assert "Qwen-Zwischenwerte bleiben bis zum Fünffachlauf partiell" not in rendered
    assert "Qwen 3.5 4B</text>" in rendered
    assert ">n=5 Repl. · formal validiert</text>" in rendered
    assert "GPT-OSS 20B (Groq-Fallback) · n=" not in rendered
    condition_data = json.loads(
        (run_dir / "figures" / "run2-condition-metrics.json").read_text(
            encoding="utf-8"
        )
    )
    cloud = next(
        item
        for item in condition_data["conditions"]
        if item["id"] == "C-F"
    )
    expected_validated = 0
    for session_id in range(36, 41):
        validation_path = run_dir / "processed" / f"session-{session_id}-validation.json"
        if validation_path.exists():
            validation = json.loads(validation_path.read_text(encoding="utf-8"))
            expected_validated += validation.get("passed") is True
    overall_path = (
        run_dir / "processed" / "gpt-oss-20b-five-seed-validation.json"
    )
    overall_passed = (
        overall_path.exists()
        and json.loads(overall_path.read_text(encoding="utf-8")).get("passed") is True
    )
    partial = json.loads(
        (
            run_dir
            / "processed"
            / "gpt-oss-20b-seed71-live-aggregate.json"
        ).read_text(encoding="utf-8")
    )
    if overall_passed:
        expected_note = f"n={expected_validated} Repl. · formal validiert"
    elif 0 < partial["written_question_files"] < partial["expected_total_questions"]:
        expected_note = (
            f"n={expected_validated} gültig · aktiv "
            f"{partial['written_question_files']}/{partial['expected_total_questions']} "
            "· Gate offen"
        )
    elif expected_validated:
        expected_note = (
            f"n={expected_validated} Einzelrepl. validiert · Gesamtgate offen"
        )
    else:
        expected_note = "n=0 Repl. · partiell"
    assert cloud["replications"] == expected_validated
    assert cloud["validated_replications"] == expected_validated
    assert cloud["formally_validated"] is overall_passed
    assert cloud["legend_note"] == expected_note
    assert "n=0 Repl. · partiell" not in rendered
    assert cloud["legend_note"] in rendered
    assert contrast_ratio("#929292", "#191919") >= 4.5
    browser_validator = (
        run_dir / "validate_report_browser.cjs"
    ).read_text(encoding="utf-8")
    assert "insideSvg: Boolean(element.closest(\"svg\"))" in browser_validator
    assert "SVG-Texte außerhalb des Viewports" in browser_validator
    assert "Druckhintergrund" in browser_validator
    assert "Navigation in Druckansicht nicht verborgen" in browser_validator
    assert "javaScriptEnabled: false" in browser_validator
    assert "no_javascript_checks" in browser_validator
    print("  PASS test_run2_result_svgs_use_current_status_and_contrast")


def test_report_builds_offline_html() -> None:
    synthetic = {
        "schema_version": 1,
        "method": {"note": "synthetic test"},
        "paired_coverage": {"models": [], "questions_by_model": {}, "common_question_keys": 0, "fully_paired": False},
        "sessions": [],
        "questions": [],
    }
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        data_path = tmpdir / "benchmark.json"
        output_path = tmpdir / "report.html"
        data_path.write_text(json.dumps(synthetic), encoding="utf-8")
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "forschung" / "report" / "build_report.py"),
                "--benchmark", str(data_path),
                "--output", str(output_path),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        rendered = output_path.read_text(encoding="utf-8")
        assert not re.search(r"\{\{[A-Z0-9_]+\}\}", rendered)
        assert "data:image/jpeg;base64," not in rendered
        assert re.search(r'<img src="[^"]*CHAPPiE-Kollage\.jpg"', rendered)
        assert len(rendered.encode("utf-8")) < 500_000
        assert "application/json" in rendered
        parser = StructuralParser()
        parser.feed(rendered)
        required_ids = {"start", "pipeline", "benchmarks", "dialoge", "pitch", "repro", "quellen"}
        assert required_ids <= parser.ids, required_ids - parser.ids
        assert parser.details >= 8
        assert all(source is None for source in parser.scripts), parser.scripts
        assert not parser.stylesheets, parser.stylesheets
    print("  PASS test_report_builds_offline_html")


def test_committed_reports_keep_collage_outside_html() -> None:
    reports = (
        ROOT / "forschung" / "report" / "CHAPPiE-Forschungsbericht.html",
        ROOT / "forschung" / "report" / "CHAPPiE-Forschungsbericht-Run-2.html",
    )
    for report in reports:
        rendered = report.read_text(encoding="utf-8")
        assert "data:image/" not in rendered
        assert re.search(r'<img src="\.\./\.\./CHAPPiE-Kollage\.jpg"', rendered)
        assert report.stat().st_size < 1_000_000
    print("  PASS test_committed_reports_keep_collage_outside_html")


def test_benchmark_helpers_handle_missing_data() -> None:
    import importlib.util

    module_path = ROOT / "forschung" / "report" / "build_benchmark_data.py"
    spec = importlib.util.spec_from_file_location("build_benchmark_data", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    aggregate = module.aggregate_rows([])
    assert aggregate["questions"] == 0
    assert aggregate["valid_rate"] is None
    assert aggregate["duration_ms"]["mean"] is None
    assert module.paired_coverage([])["common_question_keys"] == 0
    stats = module.numeric_stats([{"valid_rate": 0.0}, {"valid_rate": 1.0}], "valid_rate")
    assert stats["variance"] == 0.5
    assert stats["ci95"] is not None
    assert module.exact_mcnemar_p(0, 6) < 0.05
    print("  PASS test_benchmark_helpers_handle_missing_data")


def test_report_validator_detects_missing_local_link() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        tmpdir = Path(tmp)
        report = tmpdir / "report.html"
        # This deliberately minimal fixture is expected to fail many checks;
        # the assertion only verifies the dedicated local-link audit.
        report.write_text(
            '<!doctype html><html><body><a href="missing.json">Beleg</a>'
            '<script id="benchmarkData" type="application/json">'
            '{"sessions": [], "questions": []}</script></body></html>',
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "forschung" / "report" / "validate_report.py"),
                str(report),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 1
        payload = json.loads(completed.stdout)
        assert "alle lokalen Beleglinks und Rohlogziele existieren" in payload["failed"]
    print("  PASS test_report_validator_detects_missing_local_link")


def test_prompt_tool_contract_tracks_measured_streaming_path() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "contract.json"
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "forschung" / "report" / "inspect_prompt_contract.py"),
                "--output", str(output),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        contract = json.loads(output.read_text(encoding="utf-8"))
        assert contract["tool_instruction_appended_when_emotions_and_thinking_disabled"] is False
        assert contract["measured_harness_uses_process_stream"] is True
        assert contract["streaming_path_uses_plain_generate"] is True
        assert contract["streaming_path_uses_generate_with_tools"] is False
        assert contract["nonstreaming_native_tools_groq_only"] is True
    print("  PASS test_prompt_tool_contract_tracks_measured_streaming_path")


def test_runtime_reload_logging_does_not_render_secret_signatures() -> None:
    source = (ROOT / "web_infrastructure" / "chappie_runtime.py").read_text(encoding="utf-8")
    assert 'f"Runtime-Reload Hauptmodell: {self._brain_signature}' not in source
    assert 'f"Runtime-Reload Intent: {self._intent_signature}' not in source
    assert "old_label = self._brain_signature[:2]" in source
    assert "old_label = self._intent_signature[:3]" in source
    print("  PASS test_runtime_reload_logging_does_not_render_secret_signatures")


def test_stratified_partial_condition_is_never_labeled_full() -> None:
    import importlib.util

    module_path = ROOT / "forschung" / "report" / "build_report.py"
    spec = importlib.util.spec_from_file_location("build_report_partial_test", module_path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    partial = {
        "has_summary": True,
        "expected_questions": 21,
        "completion_class": "partial_replication",
        "aggregate": {"questions": 21},
    }
    assert module.is_complete(partial) is False
    assert module.is_completed_partial(partial) is True
    tag = module.status_tags({"gpt": partial})
    assert "Teilstichprobe 21/21" in tag
    assert "unvollständig (21/86)" not in tag
    print("  PASS test_stratified_partial_condition_is_never_labeled_full")


def test_run2_report_separates_120b_primary_and_20b_fallback() -> None:
    with tempfile.TemporaryDirectory() as tmp:
        output = Path(tmp) / "run2.html"
        benchmark = Path(tmp) / "benchmark.json"
        benchmark.write_text(
            json.dumps(
                {
                    "sessions": [],
                    "questions": [
                        {
                            "question_text": "CONTROLLED_TEST_PROMPT",
                            "answer": "REDACT_ME_FROM_PORTABLE_REPORT",
                        }
                    ],
                }
            ),
            encoding="utf-8",
        )
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "forschung" / "report" / "build_run2_report.py"),
                "--benchmark",
                str(benchmark),
                "--output",
                str(output),
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        rendered = output.read_text(encoding="utf-8")
        assert "data:image/jpeg;base64," not in rendered
        assert re.search(r'<img src="[^"]*CHAPPiE-Kollage\.jpg"', rendered)
        assert "Run-2-Fallback: GPT-OSS 20B auf Groq" in rendered
        assert "Primärbedingung GPT-OSS 120B" in rendered
        assert "kein methodisch identischer Ersatz für GPT-OSS 120B" in rendered
        assert "geshardete Teilreplikation" in rendered
        assert "Projektteam CHAPPiE" in rendered
        assert "Personennamen im Repository nicht dokumentiert" in rendered
        assert "Ich glaube nicht, dass du wirklich fühlst" in rendered
        assert "Exakte Generations- und Zustandsparameter" in rendered
        assert "reasoning_effort=low" in rendered
        assert "NF4 4-bit auf Tesla T4" in rendered
        match = re.search(
            r'<script id="benchmarkData" type="application/json">(.*?)</script>',
            rendered,
            flags=re.DOTALL,
        )
        assert match
        assert "REDACT_ME_FROM_PORTABLE_REPORT" not in rendered
        assert "CONTROLLED_TEST_PROMPT" not in rendered
        embedded = json.loads(match.group(1).replace("<\\/", "</"))
        assert embedded["sessions"] == []
        assert embedded["questions"] == []
        assert embedded["question_records_omitted_from_html"] == 1
    print("  PASS test_run2_report_separates_120b_primary_and_20b_fallback")


if __name__ == "__main__":
    tests = [
        test_template_design_contract,
        test_run2_tertiary_text_meets_wcag_aa,
        test_run2_result_svgs_use_current_status_and_contrast,
        test_report_builds_offline_html,
        test_committed_reports_keep_collage_outside_html,
        test_benchmark_helpers_handle_missing_data,
        test_report_validator_detects_missing_local_link,
        test_prompt_tool_contract_tracks_measured_streaming_path,
        test_runtime_reload_logging_does_not_render_secret_signatures,
        test_stratified_partial_condition_is_never_labeled_full,
        test_run2_report_separates_120b_primary_and_20b_fallback,
    ]
    failures = 0
    print("Forschung Report Tests\n" + "=" * 50)
    for test in tests:
        try:
            test()
        except Exception as exc:
            failures += 1
            print(f"  FAIL {test.__name__}: {exc}")
    print("=" * 50)
    if failures:
        print(f"  {failures} TEST(S) FEHLGESCHLAGEN")
        raise SystemExit(1)
    print(f"  ALLE {len(tests)} TESTS BESTANDEN")
