"""GPU-free contract test for the generic Run-2 session analyzer."""
from __future__ import annotations

import json
import subprocess
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
RUN_DIR = ROOT / "forschung/runs/run-2-20260723-1108-cb6d011"
ANALYZER = RUN_DIR / "analyze_run2_session.py"
GEMMA_SESSION = ROOT / "forschung/session_logs/session_33"


def test_generic_analyzer_uses_session_contract() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "aggregate.json"
        markdown = Path(temporary) / "aggregate.md"
        completed = subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session",
                GEMMA_SESSION.name,
                "--json-output",
                str(output),
                "--markdown-output",
                str(markdown),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["expected_model"] == "google/gemma-4-E4B-it"
        assert result["expected_provider"] == "vllm"
        assert result["expected_iterations"] == 5
        assert result["expected_questions_per_iteration"] == 86
        assert result["expected_total_questions"] == 430
        assert result["written_question_files"] == 430
        assert result["complete_iterations"] == 5
        assert result["run_complete_by_count"] is True
        assert result["model_contract_ok"] is True
        assert result["provider_contract_ok"] is True
        assert result["hard_error_count"] == 0
        rendered = markdown.read_text(encoding="utf-8")
        assert "google/gemma-4-E4B-it" in rendered
        assert "vllm" in rendered
    print("  PASS test_generic_analyzer_uses_session_contract")


def test_error_without_response_is_not_technically_valid() -> None:
    fixture_root = RUN_DIR / "raw"
    with tempfile.TemporaryDirectory(dir=fixture_root) as temporary:
        session = Path(temporary) / "session_fixture"
        questions = session / "questions"
        questions.mkdir(parents=True)
        (session / "config.json").write_text(
            json.dumps(
                {
                    "model": "fixture/model",
                    "llm_provider": "groq",
                    "iterations": 1,
                    "expected_questions": 2,
                }
            ),
            encoding="utf-8",
        )
        common = {
            "iteration": 1,
            "seed": 11,
            "category_id": 1,
            "category": "Fixture",
        }
        valid = {
            **common,
            "question_number": 1,
            "duration_ms": 10,
            "response": {
                "response_text": "Eine technisch vorhandene Testantwort.",
                "quality": {},
                "emotion_steering": {
                    "model": "fixture/model",
                    "provider": "groq",
                },
            },
        }
        failed = {
            **common,
            "question_number": 2,
            "duration_ms": 10,
            "_error": "Timeout",
            "response": None,
        }
        (questions / "q1.json").write_text(json.dumps(valid), encoding="utf-8")
        (questions / "q2.json").write_text(json.dumps(failed), encoding="utf-8")
        output = Path(temporary) / "aggregate.json"
        markdown = Path(temporary) / "aggregate.md"
        completed = subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session",
                str(session),
                "--json-output",
                str(output),
                "--markdown-output",
                str(markdown),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode == 0, completed.stderr or completed.stdout
        result = json.loads(output.read_text(encoding="utf-8"))
        assert result["iterations"][0]["questions"] == 2
        assert result["iterations"][0]["valid_technical"] == 1
        assert result["empty_answers"] == ["q2.json"]
        assert result["hard_error_count"] >= 1
    print("  PASS test_error_without_response_is_not_technically_valid")


def test_missing_session_fails_instead_of_writing_empty_aggregate() -> None:
    with tempfile.TemporaryDirectory() as temporary:
        output = Path(temporary) / "aggregate.json"
        markdown = Path(temporary) / "aggregate.md"
        completed = subprocess.run(
            [
                sys.executable,
                str(ANALYZER),
                "--session",
                "session_does_not_exist",
                "--json-output",
                str(output),
                "--markdown-output",
                str(markdown),
            ],
            cwd=ROOT,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )
        assert completed.returncode != 0
        assert "Sessionordner fehlt" in completed.stderr
        assert not output.exists()
        assert not markdown.exists()
    print("  PASS test_missing_session_fails_instead_of_writing_empty_aggregate")


if __name__ == "__main__":
    test_generic_analyzer_uses_session_contract()
    test_error_without_response_is_not_technically_valid()
    test_missing_session_fails_instead_of_writing_empty_aggregate()
    print("  ALLE TESTS BESTANDEN")
