"""CHAPPiE WhatsApp Fine-Tune Trainer -- Qwen3.5 LoRA Training.

Usage:
    python -m brain.whatsapp_finetune_trainer --config models/benjamin_2026-06-03/training_config.json --background
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
import zipfile
from collections import Counter
from pathlib import Path
from typing import Any, Dict, List, Optional

WHATSAPP_LINE_RE = re.compile(
    r"^\[(\d{2}\.\d{2}\.\d{2}, \d{2}:\d{2}:\d{2})\] ([^:]+): (.+)$"
)
MEDIA_PATTERNS = (
    re.compile(r"weggelassen", re.I),
    re.compile(r"^\s*(Audio|Bild|Video|Sticker|GIF)\s*$", re.I),
)


def _log(msg: str) -> None:
    print(f"[WhatsAppTrainer] {msg}")


def _write_status(path: Path, data: Dict[str, Any]) -> None:
    try:
        path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    except Exception as e:
        _log(f"Warnung: Status nicht schreibbar: {e}")


# ───────────────────────── WhatsApp Parsing ─────────────────────────


def extract_chat_from_zip(zip_path: str) -> str:
    with zipfile.ZipFile(zip_path, "r") as zf:
        for name in zf.namelist():
            if name.endswith("_chat.txt"):
                return zf.read(name).decode("utf-8", errors="replace")
        for name in zf.namelist():
            if name.endswith(".txt"):
                return zf.read(name).decode("utf-8", errors="replace")
    raise ValueError(f"Keine Chat-Datei in {zip_path} gefunden")


def parse_messages(raw_text: str) -> List[Dict[str, str]]:
    messages: List[Dict[str, str]] = []
    for line in raw_text.splitlines():
        match = WHATSAPP_LINE_RE.match(line)
        if match:
            messages.append({
                "timestamp": match.group(1),
                "sender": match.group(2).strip(),
                "text": match.group(3).strip(),
            })
        elif messages:
            messages[-1]["text"] += "\n" + line.strip()
    return messages


def filter_media(messages: List[Dict[str, str]]) -> List[Dict[str, str]]:
    return [
        msg for msg in messages
        if not any(p.search(msg["text"]) for p in MEDIA_PATTERNS)
    ]


def detect_participants(messages: List[Dict[str, str]]) -> List[str]:
    counts = Counter(msg["sender"] for msg in messages)
    return [sender for sender, _ in counts.most_common()]


def build_conversation_pairs(
    messages: List[Dict[str, str]], target_name: str, context_turns: int = 2
) -> List[Dict[str, Any]]:
    pairs: List[Dict[str, Any]] = []
    for i in range(len(messages) - 1):
        if messages[i]["sender"] != target_name and messages[i + 1]["sender"] == target_name:
            pairs.append({
                "input": messages[i]["text"],
                "output": messages[i + 1]["text"],
                "type": "single",
            })
    for i in range(len(messages) - context_turns):
        window = messages[i : i + context_turns + 1]
        if window[-1]["sender"] != target_name:
            continue
        context_parts = []
        for msg in window[:-1]:
            label = "Du:" if msg["sender"] == target_name else f"{msg['sender']}:"
            context_parts.append(f"{label} {msg['text']}")
        pairs.append({
            "input": "\n".join(context_parts),
            "output": window[-1]["text"],
            "type": "multi",
        })
    return pairs


# ───────────────────────── Dataset Building ─────────────────────────


def format_qwen(example: Dict[str, str]) -> str:
    """Formatiert ein Input/Output-Paar im Qwen3.5-Chat-Template (Thinking aktiviert, mit System-Message)."""
    return (
        "<|im_start|>system\n"
        "Du bist ein hilfreicher Assistent. Antworte direkt und natuerlich.\n"
        "<|im_end|>\n"
        f"<|im_start|>user\n{example['input']}<|im_end|>\n"
        f"<|im_start|>assistant\n{example['output']}<|im_end|>"
    )


def build_dataset(
    chat_pairs: List[Dict[str, Any]],
    general_pairs: List[Dict[str, Any]],
    general_ratio: float = 0.15,
    seed: int = 42,
) -> Dict[str, List[Dict[str, str]]]:
    import random
    random.seed(seed)
    all_pairs = list(chat_pairs)
    n_general = int(len(all_pairs) * general_ratio)
    if general_pairs and n_general > 0:
        all_pairs.extend(random.sample(general_pairs, min(n_general, len(general_pairs))))
    random.shuffle(all_pairs)
    n = len(all_pairs)
    train_end = int(n * 0.8)
    val_end = min(train_end + max(1, int(n * 0.1)), n)
    if val_end == train_end:
        val_end = n
    return {
        "train": [{"text": format_qwen(p)} for p in all_pairs[:train_end]],
        "val": [{"text": format_qwen(p)} for p in all_pairs[train_end:val_end]] if val_end > train_end else [],
        "test": [{"text": format_qwen(p)} for p in all_pairs[val_end:]] if val_end < n else [],
    }


def save_dataset(split_data: Dict[str, List[Dict[str, str]]], output_dir: Path) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)
    for split, data in split_data.items():
        path = output_dir / f"{split}.jsonl"
        with open(path, "w", encoding="utf-8") as f:
            for item in data:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
    stats = {
        "total_pairs": sum(len(v) for v in split_data.values()),
        "splits": {k: len(v) for k, v in split_data.items()},
        "created": __import__("datetime").datetime.now().isoformat(),
    }
    (output_dir / "stats.json").write_text(json.dumps(stats, indent=2, ensure_ascii=False) + "\n")


# ───────────────────────── Training ─────────────────────────


def load_model_and_tokenizer(model_name: str, max_seq_length: int, use_bf16: bool):
    import torch
    from unsloth import FastLanguageModel
    dtype = None if use_bf16 else torch.float16
    model, tokenizer = FastLanguageModel.from_pretrained(
        model_name=model_name,
        max_seq_length=max_seq_length,
        dtype=dtype,
        load_in_4bit=not use_bf16,
    )
    return model, tokenizer


def setup_lora(model, r: int = 16, alpha: int = 32):
    from unsloth import FastLanguageModel
    model = FastLanguageModel.get_peft_model(
        model,
        r=r,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
        lora_alpha=alpha,
        lora_dropout=0.05,
        bias="none",
        use_gradient_checkpointing="unsloth",
        random_state=3407,
    )
    return model


def train_model(model, tokenizer, train_data, val_data, output_dir: Path, config: Dict[str, Any], status_path: Optional[Path] = None):
    from datasets import Dataset
    from trl import SFTTrainer
    from transformers import TrainingArguments, TrainerCallback

    train_ds = Dataset.from_list(train_data)
    val_ds = Dataset.from_list(val_data) if val_data else None

    per_device = config.get("batch_size", 4)
    grad_accum = config.get("grad_accum", 4)
    effective_batch = per_device * grad_accum

    use_bf16 = config.get("bf16", True)

    class StatusCallback(TrainerCallback):
        def on_log(self, args, state, control, logs=None, **kwargs):
            if status_path and logs:
                elapsed = int(time.time() - start_time)
                steps_done = max(1, state.global_step)
                total = max(1, state.max_steps)
                eta = int(elapsed / steps_done * (total - steps_done))
                data = {
                    "status": "training",
                    "current_step": steps_done,
                    "total_steps": total,
                    "current_loss": logs.get("loss"),
                    "eval_loss": logs.get("eval_loss"),
                    "elapsed_seconds": elapsed,
                    "eta_seconds": eta,
                    "progress_pct": round(steps_done / total * 100, 2),
                }
                _write_status(status_path, data)

    start_time = time.time()
    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        dataset_text_field="text",
        max_seq_length=config.get("max_seq_length", 512),
        args=TrainingArguments(
            output_dir=str(output_dir),
            num_train_epochs=config.get("epochs", 1),
            per_device_train_batch_size=per_device,
            gradient_accumulation_steps=grad_accum,
            optim="adamw_8bit",
            learning_rate=config.get("learning_rate", 2e-4),
            lr_scheduler_type="cosine",
            warmup_ratio=0.1,
            bf16=use_bf16,
            fp16=not use_bf16,
            logging_steps=10,
            eval_strategy="steps" if val_ds else "no",
            eval_steps=50 if val_ds else None,
            save_strategy="no",
            report_to="none",
            dataloader_num_workers=0,
        ),
        callbacks=[StatusCallback()],
    )
    trainer.train()
    return trainer


def save_adapter(trainer, output_dir: Path):
    trainer.model.save_pretrained(str(output_dir))
    trainer.tokenizer.save_pretrained(str(output_dir))
    config = {
        "model": trainer.model.config._name_or_path,
        "lora_r": trainer.model.peft_config["default"].r,
        "lora_alpha": trainer.model.peft_config["default"].lora_alpha,
    }
    (output_dir / "finetune_config.json").write_text(json.dumps(config, indent=2) + "\n")


# ───────────────────────── General DE Data ─────────────────────────


def _synthetic_de_pairs(count: int) -> List[Dict[str, str]]:
    """Generiert synthetische deutsche Frage-Antwort-Paare als Fallback."""
    templates = [
        ("Erklaere kurz: {topic}", "{topic} bezeichnet {answer}."),
        ("Was versteht man unter {topic}?", "Unter {topic} versteht man {answer}."),
        ("Nenne einen Vorteil von {topic}.", "Ein Vorteil von {topic} ist {answer}."),
        ("Definiere {topic}.", "{topic} ist {answer}."),
        ("Wofuer wird {topic} verwendet?", "{topic} wird verwendet, um {answer}."),
    ]
    topics = [
        ("Photosynthese", "den Prozess, bei dem Pflanzen Licht in Energie umwandeln"),
        ("Kuenstliche Intelligenz", "die Simulation menschlicher Intelligenz durch Maschinen"),
        ("Klimawandel", "die langfristige Veraenderung des globalen Klimas"),
        ("Demokratie", "eine Regierungsform, bei der das Volk die Macht ausuebt"),
        ("Blockchain", "eine dezentrale, unveraenderliche Datenbank"),
        ("Quantencomputer", "einen Computer, der Quantenmechanik zur Berechnung nutzt"),
        ("DNA", "den Traeger der genetischen Information in Lebewesen"),
        ("Schwerkraft", "die Anziehungskraft zwischen Massen"),
        ("Photoshop", "eine Software zur Bildbearbeitung"),
        ("Python", "eine vielseitige, interpretierte Programmiersprache"),
        ("Mikroorganismen", "mikroskopisch kleine Lebewesen wie Bakterien"),
        ("Ernaehrung", "die Aufnahme von Nahrung zur Energieversorgung"),
        ("Meteorologie", "die Wissenschaft vom Wetter und der Atmosphaere"),
        ("Oekonomie", "die Lehre vom wirtschaftlichen Handeln"),
        ("Philosophie", "die Lehre vom Denken und der Existenz"),
    ]
    pairs = []
    topic_idx = 0
    while len(pairs) < count:
        topic, answer = topics[topic_idx % len(topics)]
        template_input, template_output = templates[topic_idx % len(templates)]
        pairs.append({
            "input": template_input.format(topic=topic),
            "output": template_output.format(topic=topic, answer=answer),
            "type": "general_de",
        })
        topic_idx += 1
    return pairs


def load_bactrian_de(max_samples: int = 200) -> List[Dict[str, str]]:
    """Laedt deutsche Instruktionen aus Bactrian-X als Anti-Forgetting-Daten."""
    try:
        from datasets import load_dataset
        ds = load_dataset("MBZUAI/Bactrian-X", "de", split="train", streaming=True)
        pairs = []
        for item in ds:
            if item.get("instruction") and item.get("output"):
                pairs.append({
                    "input": item["instruction"],
                    "output": item["output"],
                    "type": "general_de",
                })
            if len(pairs) >= max_samples:
                break
        if pairs:
            return pairs
    except Exception:
        pass
    _log("Bactrian-X DE nicht verfuegbar, generiere synthetische Beispiele")
    return _synthetic_de_pairs(max_samples)


# ───────────────────────── Main Flow ─────────────────────────


def main():
    parser = argparse.ArgumentParser(description="CHAPPiE WhatsApp Fine-Tune Trainer")
    parser.add_argument("--config", required=True, help="Pfad zur training_config.json")
    parser.add_argument("--background", action="store_true", help="Hintergrund-Modus (kein interaktives Chat)")
    args = parser.parse_args()

    config_path = Path(args.config)
    if not config_path.exists():
        _log(f"Config nicht gefunden: {config_path}")
        sys.exit(1)

    with open(config_path, "r", encoding="utf-8") as f:
        config = json.load(f)

    status_path = Path(config["status_path"]) if config.get("status_path") else None
    meta_path = Path(config["meta_path"]) if config.get("meta_path") else None
    adapter_output_dir = Path(config["adapter_output_dir"])

    # Update meta: training
    if meta_path:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["status"] = "training"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    # Parse chats
    config_dir = config_path.parent
    all_pairs = []
    for zip_path_str in config.get("chat_zips", []):
        zip_path = Path(zip_path_str)
        if not zip_path.is_absolute():
            zip_path = config_dir / zip_path
        if not zip_path.exists():
            _log(f"ZIP nicht gefunden: {zip_path}")
            continue
        try:
            raw = extract_chat_from_zip(str(zip_path))
            messages = parse_messages(raw)
            messages = filter_media(messages)
            pairs = build_conversation_pairs(messages, config["target_person"])
            all_pairs.extend(pairs)
            _log(f"{zip_path.name}: {len(pairs)} Paare extrahiert")
        except Exception as e:
            _log(f"Fehler beim Parsen von {zip_path}: {e}")

    if len(all_pairs) < 10:
        _log(f"Zu wenige Paare: {len(all_pairs)} (mindestens 10 erforderlich)")
        if status_path:
            _write_status(status_path, {"status": "failed", "error": "Zu wenige Trainingspaare"})
        sys.exit(1)

    _log(f"Gesamt: {len(all_pairs)} Paare")

    # Load general DE data
    general_pairs = load_bactrian_de(max_samples=int(len(all_pairs) * config.get("general_de_ratio", 0.15)))

    # Build dataset
    split_data = build_dataset(all_pairs, general_pairs, general_ratio=config.get("general_de_ratio", 0.15))
    dataset_dir = adapter_output_dir.parent / "dataset"
    save_dataset(split_data, dataset_dir)
    _log(f"Dataset gespeichert: {dataset_dir}")

    # Update meta
    if meta_path:
        meta = json.loads(meta_path.read_text(encoding="utf-8"))
        meta["total_pairs"] = len(all_pairs)
        meta["status"] = "training"
        meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    # Training
    use_bf16 = config.get("bf16", True)
    try:
        _log(f"Lade Modell: {config['model_name']} (bf16={use_bf16})")
        model, tokenizer = load_model_and_tokenizer(
            config["model_name"],
            config.get("max_seq_length", 512),
            use_bf16,
        )
        _log("Setup LoRA...")
        model = setup_lora(model, r=config.get("lora_r", 16), alpha=config.get("lora_alpha", 32))
        _log("Starte Training...")
        trainer = train_model(
            model, tokenizer,
            split_data["train"], split_data.get("val"),
            adapter_output_dir, config, status_path,
        )
        _log("Speichere Adapter...")
        save_adapter(trainer, adapter_output_dir)
        _log(f"Adapter gespeichert: {adapter_output_dir}")

        if status_path:
            _write_status(status_path, {
                "status": "completed",
                "progress_pct": 100.0,
                "current_step": trainer.state.global_step,
                "total_steps": trainer.state.max_steps,
            })
        if meta_path:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["status"] = "completed"
            meta["final_loss"] = trainer.state.log_history[-1].get("loss") if trainer.state.log_history else None
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")

    except Exception as e:
        _log(f"Training fehlgeschlagen: {e}")
        import traceback
        traceback.print_exc()
        if status_path:
            _write_status(status_path, {"status": "failed", "error": str(e)})
        if meta_path:
            meta = json.loads(meta_path.read_text(encoding="utf-8"))
            meta["status"] = "failed"
            meta["error"] = str(e)
            meta_path.write_text(json.dumps(meta, indent=2, ensure_ascii=False) + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()