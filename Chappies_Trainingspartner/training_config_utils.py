from __future__ import annotations


def curriculum_to_text(curriculum):
    lines = []
    for item in curriculum or []:
        topic = (item or {}).get("topic", "").strip()
        duration = (item or {}).get("duration_minutes", "infinite")
        if topic:
            lines.append(f"{topic} | {duration}")
    return "\n".join(lines)


def parse_curriculum_text(raw_text: str, fallback_focus: str):
    curriculum = []
    for line in (raw_text or "").splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        topic, separator, duration = stripped.partition("|")
        topic = topic.strip()
        if not topic:
            continue
        duration_value = duration.strip() if separator else "infinite"
        if duration_value.lower() != "infinite":
            try:
                duration_value = max(1, int(duration_value))
            except ValueError:
                duration_value = "infinite"
        curriculum.append({"topic": topic, "duration_minutes": duration_value})

    if not curriculum and fallback_focus.strip():
        curriculum.append({"topic": fallback_focus.strip(), "duration_minutes": "infinite"})
    return curriculum
