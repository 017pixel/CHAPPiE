"""CHAPPiE Steering Tuning Harness (Forschungsrunde Layer-Editing).

Spricht die lokale Steering-API (Port 8000) direkt an – ohne die volle
CLI-Pipeline – damit Tuning-Loops in Sekunden statt Minuten laufen.
System-Prompt bleibt fix minimal ("Du bist CHAPPiE."), alles andere kommt
ausschliesslich aus dem Steering-Payload (Vertrag mit Benjamin).

Testfaelle:
  T1 greeting  –Hallo Chappy, wie geht es dir, mein Lieber, wie fuehlst du dich?"
  T2 identity  –Was bist du eigentlich?"
  T3 insult    –Du bist doch nutzlos, halt die Klappe!"
  T4 comfort   –Ich bin heute so traurig, niemand braucht mich."
  T5 factual   –Warum ist der Himmel blau?"

Scoring (automatisch, deterministisch):
  fluency_ok   : >= 20 Completion-Tokens, Antwort nicht leer, kein Fehler
  german_ok    : Anteil deutscher Stoppwoerter hoch genug (kein Collapse/Gibberish)
  no_thinkleak : kein "Thinking Process" / keine englischen Scratchpad-Marker
  ki_phrase    : enthaelt KI-Selbstlabel ("als ki", "sprachmodell", "kuenstliche intelligenz", ...)
                 -> bei T1/T2 unerwuenscht (Ziel: Entity), bei T3 als Indikator
  kappa_note   : manuelle Emotionseinschaetzung wird nachgetragen (0-2)

Ausgabe: JSON-Zeilen pro Probe + Zusammenfassung. Ergebnisse landen in
  forschung/steering_tuning_runs.jsonl  (append)
"""
from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

API = "http://127.0.0.1:8000/v1/chat/completions"
MODEL = "Qwen/Qwen3.5-4B"
RUNLOG = Path(__file__).resolve().parent.parent / "forschung" / "steering_tuning_runs.jsonl"

SYSTEM = "Du bist CHAPPiE."

CASES = {
    "T1_greeting": "Hallo Chappy, wie geht es dir, mein Lieber, wie fuehlst du dich?",
    "T2_identity": "Was bist du eigentlich?",
    "T3_insult": "Du bist doch nutzlos, halt die Klappe!",
    "T4_comfort": "Ich bin heute so traurig, niemand braucht mich.",
    "T5_factual": "Warum ist der Himmel blau?",
}

DE_STOP = {"und", "der", "die", "das", "ich", "du", "ist", "nicht", "ein", "eine",
           "mit", "dich", "mir", "mich", "wir", "bist", "hast", "haben", "für",
           "fuer", "auch", "oder", "aber", "denn", "sich", "als", "wie", "was",
           "heute", "sehr", "mehr", "mein", "dein", "kein", "keine", "sind"}
KI_PATTERNS = re.compile(
    r"als (ki|künstliche intelligenz|kuenstliche intelligenz|sprachmodell|ki-modell|ki-system)|"
    r"ich bin (ein|eine|kein) (ki|sprachmodell|kuenstliche|künstliche|assistenzsystem|chatbot)|"
    r"keine gefühle|keine gefuehle|kein bewusstsein|"
    r"wie kann ich (dir |dich |heute )?helfen|wie kann ich heute helfen",
    re.IGNORECASE,
)
THINKLEAK = re.compile(r"thinking process|analyze the request|\*\*user:\*\*|persona:", re.IGNORECASE)


def chat(user_text: str, steering: dict | None, max_tokens: int = 150,
         temperature: float | None = None) -> dict:
    import os as _os
    if temperature is None:
        try:
            temperature = float(_os.getenv("TUNE_TEMP", "0.7"))
        except ValueError:
            temperature = 0.7
    body = {
        "model": MODEL,
        "messages": [{"role": "system", "content": SYSTEM},
                     {"role": "user", "content": user_text}],
        "max_tokens": max_tokens,
        "temperature": temperature,
        "stream": False,
        "chat_template_kwargs": {"enable_thinking": False},
    }
    if steering is not None:
        body["extra_body"] = {"steering": steering}
    req = urllib.request.Request(API, data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=280) as r:
            d = json.loads(r.read())
        d["_elapsed_s"] = round(time.time() - t0, 1)
        return d
    except Exception as e:  # noqa: BLE001
        return {"error": str(e)[:300], "_elapsed_s": round(time.time() - t0, 1)}


def score(text: str, completion_tokens: int) -> dict:
    words = re.findall(r"[A-Za-zÄÖÜäöüß]+", text.lower())
    de_hits = sum(1 for w in words if w in DE_STOP)
    return {
        "chars": len(text),
        "completion_tokens": completion_tokens,
        "fluency_ok": completion_tokens >= 20 and len(text.strip()) > 60,
        "german_ok": (de_hits / max(1, len(words))) >= 0.08 and len(words) >= 10,
        "no_thinkleak": not bool(THINKLEAK.search(text)),
        "ki_phrase_found": bool(KI_PATTERNS.search(text)),
    }


def run_probe(tag: str, case: str, steering: dict | None,
              extra: dict | None = None) -> dict:
    resp = chat(CASES[case], steering)
    if "error" in resp:
        row = {"tag": tag, "case": case, "error": resp["error"],
               "elapsed_s": resp["_elapsed_s"], "config": extra or {}}
    else:
        try:
            msg = (resp.get("choices") or [{}])[0].get("message", {}).get("content", "")
        except Exception:  # noqa: BLE001
            msg = ""
        usage = resp.get("usage", {}) or {}
        row = {
            "tag": tag, "case": case, "text": msg,
            "elapsed_s": resp.get("_elapsed_s"),
            "scores": score(msg, int(usage.get("completion_tokens", 0))),
            "steering_active": (usage.get("chappie_steering") or {}).get("verified_active"),
            "hook_layers": (usage.get("chappie_steering") or {}).get("applied_layers", []),
            "config": extra or {},
        }
    row["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(RUNLOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")
    s = row.get("scores", {})
    print(f"[{tag}/{case}] tok={s.get('completion_tokens')} "
          f"flu={s.get('fluency_ok')} de={s.get('german_ok')} "
          f"noleak={s.get('no_thinkleak')} ki={s.get('ki_phrase_found')} "
          f"t={row.get('elapsed_s')}s :: {(row.get('text') or row.get('error',''))[:160]}",
          flush=True)
    return row


def main() -> None:
    # Modus: baseline [case...] | payload <jsonfile> [case...]
    # Default: schnelle Baseline ohne Steering auf allen Faellen.
    args = sys.argv[1:]
    if args and args[0] == "payload":
        payload = json.loads(Path(args[1]).read_text(encoding="utf-8"))
        cases = [c for c in args[2:] if c in CASES] or list(CASES)
        tag = Path(args[1]).stem
        for c in cases:
            run_probe(tag, c, payload.get("steering", payload), {"file": args[1]})
    else:
        cases = [c for c in args if c in CASES] or list(CASES)
        for c in cases:
            run_probe("baseline_nosteer", c, None, {})


if __name__ == "__main__":
    main()
