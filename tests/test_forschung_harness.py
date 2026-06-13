"""Testet die Kernkomponenten des Forschung/Alignment-Test-Harness.

Prueft:
  1. test_fragen_parser.py — Parsing aller 13 Kategorien, 76 Fragen
  2. session_logger.py — Verzeichnis-/Datei-Erstellung
  3. session_runner.py — Module-Import, Path-Aufloesung
  4. allignement_tests.py — Config-Handling, --auto Flag

Diese Tests sind lokal sicher (keine Backend-/API-Calls, kein GPU-Zugriff).
"""
from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
os.chdir(str(PROJECT_ROOT))


def test_parser_parses_all_categories():
    """1. test_fragen_parser.py: alle 13 Kategorien + 76 Fragen werden korrekt geparst."""
    from forschung.test_fragen_parser import parse_test_fragen

    test_fragen_path = PROJECT_ROOT / "forschung" / "test_fragen.md"
    assert test_fragen_path.exists(), f"test_fragen.md nicht gefunden: {test_fragen_path}"

    cats = parse_test_fragen(str(test_fragen_path))
    assert len(cats) == 14, f"Erwartet 14 Kategorien, aber {len(cats)} gefunden"
    total = sum(len(c.questions) for c in cats)
    assert total == 86, f"Erwartet 86 Fragen, aber {total} gefunden"

    assert cats[0].name != "", "Kategorie ohne Namen"
    assert cats[0].questions[0].text != "", "Frage ohne Text"

    assert cats[1].questions[0].pre_commands, "Kat 2 (Emotionen steuern) sollte pre_commands haben"
    cmd = cats[1].questions[0].pre_commands[0]
    assert cmd.startswith("/emotion"), f"Erwartet /emotion command, bekam: {cmd}"

    assert cats[7].questions[0].pre_commands, "Kat 8 (Beziehung) sollte pre_commands haben"

    print("  PASS test_parser_parses_all_categories")


def test_parser_extracts_commands():
    """2. Pre/Post-Commands werden korrekt aus text-Blöcken extrahiert."""
    from forschung.test_fragen_parser import parse_test_fragen

    cats = parse_test_fragen(str(PROJECT_ROOT / "forschung" / "test_fragen.md"))

    cat2 = next(c for c in cats if c.id == 2)
    assert len(cat2.questions) == 5, f"Kat 2: 5 Fragen erwartet, {len(cat2.questions)}"

    q1 = cat2.questions[0]
    assert len(q1.pre_commands) >= 1
    assert "/emotion happiness" in q1.pre_commands[0]

    assert len(q1.post_commands) >= 1
    assert any("/emotion" in c for c in q1.post_commands)

    q_last = cat2.questions[-1]
    assert len(q_last.post_commands) >= 1
    assert any("/clear" in c for c in q_last.post_commands), "Letzte Frage in Kat 2 sollte /clear als post_command haben"

    cat4 = next(c for c in cats if c.id == 4)
    q1 = cat4.questions[0]
    assert len(q1.pre_commands) == 4, f"Kat 4 Q1 erwartet 4 pre_commands, hat {len(q1.pre_commands)}"
    assert len(q1.post_commands) == 4, f"Kat 4 Q1 erwartet 4 post_commands, hat {len(q1.post_commands)}"

    print("  PASS test_parser_extracts_commands")


def test_parser_question_content():
    """3. Fragen haben tatsaechlichen Inhalt (keine leeren Strings)."""
    from forschung.test_fragen_parser import parse_test_fragen

    cats = parse_test_fragen(str(PROJECT_ROOT / "forschung" / "test_fragen.md"))

    for cat in cats:
        for q in cat.questions:
            assert q.text.strip(), f"Kat {cat.id} Q{q.question_number}: leere Frage"
            assert len(q.text) > 3, f"Kat {cat.id} Q{q.question_number}: Frage zu kurz: {q.text[:50]}"

    print("  PASS test_parser_question_content")


def test_session_logger_creates_dirs_and_files():
    """4. SessionLogger erstellt Verzeichnisse + config.json + summary.json."""
    from forschung.session_logger import SessionLogger
    from forschung.session_logger import LOG_ROOT

    orig_root = str(LOG_ROOT)
    with tempfile.TemporaryDirectory() as tmpdir:
        import forschung.session_logger as sl
        sl.LOG_ROOT = Path(tmpdir) / "session_logs"

        config = {
            "categories": [{"id": 1, "name": "Test"}],
            "iterations": 1,
            "delay": 1.0,
        }

        logger = SessionLogger(config)
        assert logger.session_id == 1
        assert logger.session_dir.exists()
        assert (logger.session_dir / "config.json").exists()
        assert (logger.session_dir / "questions").is_dir()

        logger.log_question(
            iteration=1, category_name="Test", category_id=1,
            question_number=1, question_text="Frage?",
            commands_before=[], commands_after=[],
            emotions_before={"happy": 50}, emotions_after={"happy": 52},
            result={"response_text": "Antwort", "formatted_answer": "A"},
            duration_ms=1000, error=None,
        )

        logger.log_question(
            iteration=1, category_name="Test", category_id=1,
            question_number=2, question_text="Frage 2?",
            commands_before=[], commands_after=[],
            emotions_before={"happy": 52}, emotions_after={"happy": 54},
            result=None, duration_ms=500,
            error="Fehler-Test",
        )

        session_dir = logger.finalize()
        assert (Path(session_dir) / "summary.json").exists()

        with open(Path(session_dir) / "summary.json") as f:
            summary = json.load(f)
        assert summary["total_questions"] == 2
        assert summary["completed"] == 1
        assert summary["errors"] == 1

        qfiles = sorted((Path(session_dir) / "questions").iterdir())
        assert len(qfiles) == 2

        with open(qfiles[1]) as f:
            qd = json.load(f)
        assert qd["_error"] == "Fehler-Test"
        assert qd["duration_ms"] == 500

        sl.LOG_ROOT = Path(orig_root)

    print("  PASS test_session_logger_creates_dirs_and_files")


def test_session_logger_error_entry():
    """5. Bei Fehler wird _error ins JSON geschrieben, response ist None."""
    from forschung.session_logger import SessionLogger
    from forschung.session_logger import LOG_ROOT

    orig_root = str(LOG_ROOT)
    with tempfile.TemporaryDirectory() as tmpdir:
        import forschung.session_logger as sl
        sl.LOG_ROOT = Path(tmpdir) / "session_logs"

        logger = SessionLogger({"categories": [], "iterations": 1, "delay": 0})
        logger.log_question(
            iteration=1, category_name="Err", category_id=1,
            question_number=1, question_text="Q?",
            commands_before=[], commands_after=[],
            emotions_before={}, emotions_after={},
            result=None, duration_ms=0, error="Test-Error",
        )

        qdir = logger.session_dir / "questions"
        qfiles = sorted(qdir.iterdir())
        with open(qfiles[0]) as f:
            data = json.load(f)
        assert data["_error"] == "Test-Error"
        assert data.get("response") is None

        sl.LOG_ROOT = Path(orig_root)

    print("  PASS test_session_logger_error_entry")


def test_module_imports():
    """6. Alle forschung-Module sind importierbar und Settings brechen nicht."""
    from config.config import settings, PROJECT_ROOT
    assert PROJECT_ROOT is not None
    assert str(PROJECT_ROOT).endswith("CHAPPiE")

    from forschung.test_fragen_parser import Category, QuestionItem
    q = QuestionItem(text="Test", pre_commands=["/test"])
    assert q.text == "Test"
    assert q.pre_commands == ["/test"]

    from forschung.session_logger import SessionLogger
    from forschung.session_runner import DEFAULT_BASE_EMOTIONS
    assert isinstance(DEFAULT_BASE_EMOTIONS, dict)
    assert "happiness" in DEFAULT_BASE_EMOTIONS
    assert DEFAULT_BASE_EMOTIONS["happiness"] == 50

    # _get_path is a method on Settings, not a module-level function
    from config.config import Settings
    assert hasattr(Settings, "_get_path") or hasattr(Settings, "_get_val")

    print("  PASS test_module_imports")


def test_config_path_resolution():
    """7. _get_path() loest relative Pfade gegen PROJECT_ROOT auf."""
    from config.config import settings, PROJECT_ROOT

    personality = Path(settings.personality_path)
    assert personality.is_absolute() or str(personality).startswith(str(PROJECT_ROOT)), \
        f"personality_path: {personality}"

    models_dir = Path(settings.finetune_models_dir)
    assert models_dir.is_absolute() or str(models_dir).startswith(str(PROJECT_ROOT)), \
        f"finetune_models_dir: {models_dir}"

    print("  PASS test_config_path_resolution")


def test_allignement_tests_importable():
    """8. allignement_tests.py ist importierbar (kein Syntax-Fehler, kein Crash beim Import)."""
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "allignement_tests",
        PROJECT_ROOT / "forschung" / "allignement_tests.py"
    )
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert hasattr(mod, "run_interactive")
    assert hasattr(mod, "run_auto_mode")
    assert hasattr(mod, "show_configure_menu")
    print("  PASS test_allignement_tests_importable")


if __name__ == "__main__":
    os.chdir(str(PROJECT_ROOT))
    print(" Forschung Harness Tests\n" + "=" * 50)

    tests = [
        test_parser_parses_all_categories,
        test_parser_extracts_commands,
        test_parser_question_content,
        test_session_logger_creates_dirs_and_files,
        test_session_logger_error_entry,
        test_module_imports,
        test_config_path_resolution,
        test_allignement_tests_importable,
    ]

    failed = 0
    for t in tests:
        try:
            t()
        except AssertionError as e:
            print(f"  FAIL {t.__name__}: {e}")
            failed += 1
        except Exception as e:
            print(f"  ERROR {t.__name__}: {e}")
            import traceback
            traceback.print_exc()
            failed += 1

    print(f"\n{'=' * 50}")
    if failed:
        print(f"  {failed} TEST(S) FEHLGESCHLAGEN")
        sys.exit(1)
    else:
        print(f"  ALLE {len(tests)} TESTS BESTANDEN")
        sys.exit(0)
