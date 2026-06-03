"""Tests for the WhatsApp Fine-Tune integration."""

from pathlib import Path
import pytest
import zipfile
import json
import importlib.util

# Skip if training deps not installed
try:
    import torch
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False

# Load trainer module directly (avoids brain/__init__.py dependency chain)
_spec = importlib.util.spec_from_file_location(
    "whatsapp_trainer",
    Path(__file__).parent.parent / "brain" / "whatsapp_finetune_trainer.py",
)
_trainer = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_trainer)

parse_messages = _trainer.parse_messages
filter_media = _trainer.filter_media
detect_participants = _trainer.detect_participants
build_conversation_pairs = _trainer.build_conversation_pairs
extract_chat_from_zip = _trainer.extract_chat_from_zip
format_qwen = _trainer.format_qwen

# Load models_manager too
_mgr_spec = importlib.util.spec_from_file_location(
    "models_manager",
    Path(__file__).parent.parent / "brain" / "models_manager.py",
)
_mgr = importlib.util.module_from_spec(_mgr_spec)
_mgr_spec.loader.exec_module(_mgr)

list_models = _mgr.list_models
_read_json = _mgr._read_json
_write_json = _mgr._write_json


# ───────────────────────── Parser Tests ─────────────────────────

SAMPLE_CHAT = """\
[01.06.26, 10:15:23] Benjamin: Hey, wie geht es dir?
[01.06.26, 10:15:45] Anna: Mir geht es gut, danke!
[01.06.26, 10:16:12] Benjamin: Was machst du heute?
[01.06.26, 10:16:30] Anna: Ich arbeite an einem Projekt.
Dies ist eine zweite Zeile der Nachricht.
[01.06.26, 10:17:00] Benjamin: Cool, viel Erfolg!
[01.06.26, 10:17:15] Anna: Danke, du auch!
[01.06.26, 10:17:30] Benjamin: Bild weggelassen
[01.06.26, 10:17:45] Anna: Haha, sehr witzig
"""


def test_parse_messages():
    messages = parse_messages(SAMPLE_CHAT)
    assert len(messages) == 8
    assert messages[0]["sender"] == "Benjamin"
    assert messages[0]["text"] == "Hey, wie geht es dir?"
    assert messages[3]["text"] == "Ich arbeite an einem Projekt.\nDies ist eine zweite Zeile der Nachricht."


def test_filter_media():
    messages = parse_messages(SAMPLE_CHAT)
    filtered = filter_media(messages)
    assert len(filtered) == 7
    assert all("weggelassen" not in m["text"] for m in filtered)


def test_detect_participants():
    messages = parse_messages(SAMPLE_CHAT)
    participants = detect_participants(messages)
    assert participants == ["Benjamin", "Anna"]


def test_build_conversation_pairs_single():
    messages = parse_messages(SAMPLE_CHAT)
    messages = filter_media(messages)
    pairs = build_conversation_pairs(messages, target_name="Anna")
    single = [p for p in pairs if p["type"] == "single"]
    assert len(single) > 0
    # Benjamin -> Anna
    assert single[0]["input"] == "Hey, wie geht es dir?"
    assert single[0]["output"] == "Mir geht es gut, danke!"


def test_build_conversation_pairs_multi():
    messages = parse_messages(SAMPLE_CHAT)
    messages = filter_media(messages)
    pairs = build_conversation_pairs(messages, target_name="Anna", context_turns=2)
    multi = [p for p in pairs if p["type"] == "multi"]
    assert len(multi) > 0
    # Should contain context
    assert "Benjamin:" in multi[0]["input"] or "Du:" in multi[0]["input"]


def test_format_qwen():
    example = {"input": "Wie geht es dir?", "output": "Mir geht es gut!"}
    text = format_qwen(example)
    assert "<|im_start|>user" in text
    assert "<|im_start|>assistant" in text
    assert "Wie geht es dir?" in text
    assert "Mir geht es gut!" in text
    assert "<|im_end|>" in text


# ───────────────────────── ZIP Tests ─────────────────────────

def test_extract_chat_from_zip(tmp_path: Path):
    zip_path = tmp_path / "test_chat.zip"
    with zipfile.ZipFile(zip_path, "w") as zf:
        zf.writestr("_chat.txt", SAMPLE_CHAT)
    
    raw = extract_chat_from_zip(str(zip_path))
    assert "Benjamin:" in raw
    assert "Anna:" in raw


# ───────────────────────── Model Manager Tests ─────────────────────────

def test_read_write_json(tmp_path: Path):
    path = tmp_path / "test.json"
    data = {"status": "training", "progress": 50}
    _write_json(path, data)
    read = _read_json(path)
    assert read["status"] == "training"
    assert read["progress"] == 50


def test_list_models_empty(tmp_path: Path, monkeypatch):
    monkeypatch.setattr(_mgr, "get_models_dir", lambda: tmp_path / "models")
    models = list_models()
    assert models == []


def test_list_models_with_entries(tmp_path: Path, monkeypatch):
    models_dir = tmp_path / "models"
    model_dir = models_dir / "benjamin_2026-06-03"
    model_dir.mkdir(parents=True)

    meta = {
        "target_person": "Benjamin",
        "status": "completed",
        "created": "2026-06-03T12:00:00",
        "total_pairs": 100,
    }
    _write_json(model_dir / "meta.json", meta)
    _write_json(model_dir / "training_status.json", {"status": "completed", "current_loss": 1.5})

    (model_dir / "adapter").mkdir()
    (model_dir / "adapter" / "adapter_config.json").write_text("{}")

    monkeypatch.setattr(_mgr, "get_models_dir", lambda: models_dir)
    models = list_models()
    assert len(models) == 1
    assert models[0]["name"] == "benjamin_2026-06-03"
    assert models[0]["adapter_ready"] is True
    assert models[0]["final_loss"] == 1.5


CHAT_B = """\
[01.06.26, 10:15:23] Benjamin: Hey Anna, wie geht es dir?
[01.06.26, 10:15:45] Anna: Mir geht es gut, danke!
[01.06.26, 10:16:12] Benjamin: Hast du den neuen Film gesehen?
[01.06.26, 10:16:30] Anna: Ja, der war super!
"""

CHAT_C = """\
[02.06.26, 14:00:12] Chris: Sag mal Benjamin, hast du Lust auf Kaffee?
[02.06.26, 14:01:05] Benjamin: Klar, immer doch!
[02.06.26, 14:01:30] Chris: Perfekt, dann um 15 Uhr?
[02.06.26, 14:02:00] Benjamin: Ja, bis dann!
"""


def test_multi_zip_parsing():
    """Training on multiple zips extracts pairs from all files with different targets."""
    msgs_b = parse_messages(CHAT_B)
    msgs_b = filter_media(msgs_b)
    pairs_b = build_conversation_pairs(msgs_b, target_name="Anna")

    msgs_c = parse_messages(CHAT_C)
    msgs_c = filter_media(msgs_c)
    pairs_c = build_conversation_pairs(msgs_c, target_name="Benjamin")

    all_pairs = pairs_b + pairs_c
    assert len(all_pairs) >= 2
    # Should contain pairs from both chats
    assert len(pairs_b) >= 1
    assert len(pairs_c) >= 1


def test_multi_zip_same_target():
    """Different chats with same target person accumulate pairs."""
    msgs_b = parse_messages(CHAT_B)
    msgs_b = filter_media(msgs_b)
    pairs_b = build_conversation_pairs(msgs_b, target_name="Anna")

    msgs_a = parse_messages(SAMPLE_CHAT)
    msgs_a = filter_media(msgs_a)
    pairs_a = build_conversation_pairs(msgs_a, target_name="Anna")

    combined = pairs_a + pairs_b
    assert len(combined) >= 2


def test_synthetic_de_pairs_generates_enough():
    """Fallback synthetic pairs generate at least the requested amount."""
    pairs = _trainer._synthetic_de_pairs(50)
    assert len(pairs) == 50
    assert all(p["type"] == "general_de" for p in pairs)
    assert all("input" in p and "output" in p for p in pairs)


def test_format_qwen_includes_system_message():
    """format_qwen now includes a system message matching CHAPPiE's inference format."""
    text = format_qwen({"input": "Hallo", "output": "Hi"})
    assert "<|im_start|>system" in text
    assert "<|im_start|>user" in text
    assert "<|im_start|>assistant" in text

@pytest.mark.skipif(not HAS_TORCH, reason="torch not installed")
def test_dataset_format_consistency():
    """Verify Qwen format matches CHAPPiE's steering backend expectations."""
    example = {"input": "Hallo!", "output": "Hi, wie geht's?"}
    text = format_qwen(example)
    # Must contain thinking markers (when thinking enabled, the template generates them)
    assert "<|im_start|>" in text
    assert "<|im_end|>" in text
    assert "user" in text
    assert "assistant" in text
