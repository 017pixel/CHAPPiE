"""Shared syntax, help and completion metadata for CLI and API commands."""
from dataclasses import dataclass
from config.emotions import EMOTION_ORDER

@dataclass(frozen=True)
class CommandSpec:
    name: str
    description: str
    group: str
    subcommands: tuple[str, ...] = ()

COMMANDS = (
    CommandSpec('/status', 'Status + Life', 'Chat-Befehle', ()),
    CommandSpec('/clear', 'Neue Sitzung', 'Chat-Befehle', ()),
    CommandSpec('/new', 'Neue Sitzung', 'Chat-Befehle', ()),
    CommandSpec('/sessions', 'Sessions auflisten', 'Chat-Befehle', ()),
    CommandSpec('/session', 'Session wechseln', 'Chat-Befehle', ()),
    CommandSpec('/history', 'Verlauf anzeigen', 'Chat-Befehle', ()),
    CommandSpec('/copy', 'Session-JSON kopieren', 'Chat-Befehle', ('standard', 'debug')),
    CommandSpec('/md', 'soul, user, Prefs', 'Chat-Befehle', ()),
    CommandSpec('/restart', 'Neustart: chappie | cli', 'Chat-Befehle', ('chappie', 'cli')),
    CommandSpec('/exit', 'Beenden', 'Chat-Befehle', ()),
    CommandSpec('/help', 'Diese Hilfe', 'Chat-Befehle', ()),
    CommandSpec('/runtime', 'Modell, Provider', 'Forschungs-Befehle', ()),
    CommandSpec('/model', 'Modell wechseln', 'Forschungs-Befehle', ()),
    CommandSpec('/thinking', 'Reasoning an/aus', 'Forschungs-Befehle', ('on', 'off', 'status')),
    CommandSpec('/steering', 'Steering an/aus, Status, Modus', 'Forschungs-Befehle', ('on', 'off', 'status', 'mode')),
    CommandSpec('/emotion', 'Emotionen setzen', 'Forschungs-Befehle', ()),
    CommandSpec('/preset', 'Emotions-Preset setzen', 'Forschungs-Befehle', ('schlecht', 'neutral', 'wohl')),
    CommandSpec('/emofreeze', 'Emotionen einfrieren', 'Forschungs-Befehle', ('on', 'off', 'status')),
    CommandSpec('/default', 'Alle Settings auf Standard', 'Forschungs-Befehle', ()),
    CommandSpec('/resetemotions', 'Emotionen reset', 'Forschungs-Befehle', ()),
    CommandSpec('/sleep', 'Schlafphase', 'Forschungs-Befehle', ()),
    CommandSpec('/memory', 'Memory an/aus, Status, Suche', 'Forschungs-Befehle', ('on', 'off', 'status', 'search')),
    CommandSpec('/debug', 'Debug an/aus', 'Forschungs-Befehle', ('on', 'off')),
    CommandSpec('/last', 'Voller Report', 'Nach Ausgabe Befehle', ()),
    CommandSpec('/raw', 'Step 1 + Raw Output', 'Nach Ausgabe Befehle', ()),
    CommandSpec('/trace', 'Causal Trace', 'Nach Ausgabe Befehle', ()),
    CommandSpec('/compact', 'Kompakter Report', 'Nach Ausgabe Befehle', ()),
    CommandSpec('/full', 'Voller Report', 'Nach Ausgabe Befehle', ()),
    CommandSpec('/live', 'Streaming an/aus', 'Forschungs-Befehle', ('on', 'off', 'status')),
    CommandSpec('/stats', 'Systemstatistik', 'Weitere Befehle', ()),
    CommandSpec('/daily', 'Kurzzeitgedächtnis', 'Weitere Befehle', ()),
    CommandSpec('/personality', 'Persönlichkeit', 'Weitere Befehle', ()),
    CommandSpec('/consolidate', 'Memory konsolidieren', 'Weitere Befehle', ()),
    CommandSpec('/reflect', 'Reflexionen', 'Weitere Befehle', ()),
    CommandSpec('/functions', 'Funktionen', 'Weitere Befehle', ()),
    CommandSpec('/life', 'Life-Status', 'Weitere Befehle', ()),
    CommandSpec('/world', 'Weltmodell', 'Weitere Befehle', ()),
    CommandSpec('/habits', 'Gewohnheiten', 'Weitere Befehle', ()),
    CommandSpec('/stage', 'Entwicklungsstufe', 'Weitere Befehle', ()),
    CommandSpec('/plan', 'Aktiver Plan', 'Weitere Befehle', ()),
    CommandSpec('/forecast', 'Prognose', 'Weitere Befehle', ()),
    CommandSpec('/arc', 'Entwicklung', 'Weitere Befehle', ()),
    CommandSpec('/timeline', 'Zeitverlauf', 'Weitere Befehle', ()),
    CommandSpec('/step1', 'Intent-Diagnose', 'Weitere Befehle', ()),
    CommandSpec('/soul', 'Selbstkontext', 'Weitere Befehle', ()),
    CommandSpec('/user', 'Nutzerkontext', 'Weitere Befehle', ()),
    CommandSpec('/prefs', 'Vorlieben', 'Weitere Befehle', ()),
    CommandSpec('/twostep', 'Turn-Pipeline', 'Weitere Befehle', ()),
)
COMMAND_REGISTRY = {spec.name: spec for spec in COMMANDS}
HELP_COLUMNS = tuple((group, [(spec.name, spec.description) for spec in COMMANDS if spec.group == group])
                     for group in dict.fromkeys(spec.group for spec in COMMANDS) if group != "Weitere Befehle")

def command_candidates(text):
    if not text.startswith("/"):
        return []
    parts = text.split()
    if len(parts) <= 1 and not text.endswith(" "):
        candidates = [spec.name for spec in COMMANDS if spec.name.startswith(text.lower())]
        return sorted(candidates, key=lambda name: (name != "/emotion", name))
    command = parts[0].lower()
    prefix = "" if text.endswith(" ") else parts[-1].lower()
    position = len(parts) if text.endswith(" ") else len(parts)-1
    if command == "/emotion" and position == 1:
        candidates = list(EMOTION_ORDER)
    elif command == "/steering" and len(parts) >= 2 and parts[1] == "mode" and position == 2:
        candidates = ["off", "activation", "sequence", "combined"]
    elif position == 1 and command in COMMAND_REGISTRY:
        candidates = list(COMMAND_REGISTRY[command].subcommands)
    else:
        candidates = []
    return [item for item in candidates if item.startswith(prefix)]

def help_markdown():
    return "**CHAPPiE Commands:**\n\n" + "\n".join(
        f"- **{spec.name}** {(' | '.join(spec.subcommands) + ': ') if spec.subcommands else ''}{spec.description}"
        for spec in COMMANDS)
