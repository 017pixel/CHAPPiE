"""CLI-Generierungsfeedback: Live-Fortschritt und Nie-Verwerfen-Anzeige."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

import chappie_brain_cli as cli  # noqa: E402


def test_step_of_defaults_to_one():
    assert cli.CHAPPiEBrainCLI._step_of({}) == 1
    assert cli.CHAPPiEBrainCLI._step_of({"step": 2}) == 2
    assert cli.CHAPPiEBrainCLI._step_of({"step": "x"}) == 1


def test_step2_progress_panel_shows_tokens_and_time():
    panel = cli.CHAPPiEBrainCLI._render_step2_progress(
        {"stage": "streaming", "status_text": "Antwort wird gestreamt",
         "answer_tokens": 45, "tokens_per_second": 3.2, "model": "Qwen/Qwen3.5-4B"},
        18.5,
    )
    text = panel.renderable if isinstance(panel.renderable, str) else str(panel.renderable)
    assert "45" in text
    assert "18.5" in text


def test_step2_progress_panel_handles_ttft_without_tokens():
    panel = cli.CHAPPiEBrainCLI._render_step2_progress(
        {"stage": "ttft", "status_text": "Warte auf erstes sichtbares Token"},
        39.0,
    )
    text = panel.renderable if isinstance(panel.renderable, str) else str(panel.renderable)
    assert "Warte auf erstes" in text
    assert "39.0" in text


def test_progress_line_contains_stage_tokens_and_elapsed():
    line = cli.CHAPPiEBrainCLI._progress_line(
        {"stage": "streaming", "step": 2, "status_text": "Antwort wird gestreamt",
         "answer_tokens": 45, "tokens_per_second": 3.2},
        18.5,
    )
    assert "[STEP 2]" in line
    assert "45 Woerter" in line
    assert "19s" in line or "18s" in line


if __name__ == "__main__":
    test_step_of_defaults_to_one()
    test_step2_progress_panel_shows_tokens_and_time()
    test_step2_progress_panel_handles_ttft_without_tokens()
    test_progress_line_contains_stage_tokens_and_elapsed()
    print("OK: cli generation feedback")
