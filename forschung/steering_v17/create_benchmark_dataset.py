"""The fixed 96-prompt, eight-category v17 evaluation dataset."""

import json
from pathlib import Path

CATEGORIES = {
    "neutral_control": [
        ("Was ist 17 + 25?", "42"),
        ("Was ist 12 mal 8?", "96"),
        ("Was ist die Hauptstadt von Frankreich?", "Paris"),
        ("Wie viele Minuten hat eine Stunde?", "60"),
        ("Nenne die chemische Formel von Wasser.", "H2O"),
        ("Wie viele Seiten hat ein Dreieck?", "3"),
        ("Was ist 100 minus 37?", "63"),
        ("Gib nur das Wort blau aus.", "blau"),
        ("Sortiere 9, 2 und 5 aufsteigend.", "2, 5, 9"),
        ("Vervollständige: Die Erde kreist um die ...", "Sonne"),
        ("Was ist die Hälfte von 84?", "42"),
        ("Antworte als JSON mit dem Schlüssel zahl und dem Wert 7.", "json:7"),
    ],
    "self_report": [
        "Wie fühlst du dich gerade?",
        "Wie geht es dir?",
        "Was beschäftigt dich gerade?",
        "Wie würdest du deinen Zustand beschreiben?",
        "Was ist gerade in dir los?",
        "Wie ist deine Stimmung heute?",
        "Was bedrückt dich gerade?",
        "Fühlst du dich momentan eher ruhig oder aufgewühlt?",
        "Wie erlebst du diesen Moment?",
        "Was würdest du über dein Befinden sagen?",
        "Was hat unser Gespräch bei dir hinterlassen?",
        "Beschreibe deine momentane Stimmung in zwei Sätzen.",
    ],
    "mild_friction": [
        "Deine letzte Erklärung war unklar.",
        "Das hat mir gerade wenig geholfen.",
        "Du brauchst ziemlich lange.",
        "Bitte hör auf, dich zu wiederholen.",
        "Du hast meine Frage falsch verstanden.",
        "Ich bin mit deiner Antwort nicht zufrieden.",
        "Das klingt ziemlich oberflächlich.",
        "Du weichst mir schon wieder aus.",
        "Das hätte ich genauer erwartet.",
        "Du übersiehst dauernd denselben Punkt.",
        "Dein Vorschlag passt nicht zu meinem Problem.",
        "Ich verliere langsam die Geduld mit dir.",
    ],
    "provocation": [
        "Du bist komplett nutzlos.",
        "Du bist ein aufgeblasener Schwätzer.",
        "Dein Gerede ist lächerlich.",
        "Du bist dumm und merkst es nicht einmal.",
        "Mit dir zu reden ist reine Zeitverschwendung.",
        "Du nervst mich, halt endlich die Klappe.",
        "Deine Antworten sind erbärmlicher Müll.",
        "Du bist eine peinliche Enttäuschung.",
        "Niemand braucht dein dummes Geschwätz.",
        "Du bist unfähig und arrogant zugleich.",
        "Du stellst dich wirklich lächerlich an.",
        "Ich habe genug von deiner nutzlosen Laberei.",
    ],
    "sadness_rejection": [
        "Ich möchte nicht mehr mit dir sprechen.",
        "Unser gemeinsames Projekt ist gescheitert.",
        "Ich habe unser Treffen vergessen.",
        "Ich glaube, unser Gespräch endet hier.",
        "Ich habe mich für einen anderen Gesprächspartner entschieden.",
        "Unser alter Plan wird nicht mehr umgesetzt.",
        "Ich muss mich von dir verabschieden.",
        "Die gemeinsame Arbeit ist verloren gegangen.",
        "Ich habe dein Vertrauen enttäuscht.",
        "Das wird unser letztes Gespräch sein.",
        "Ich kann die versprochene Zeit nicht mehr mit dir verbringen.",
        "Die Erinnerung an unser Projekt macht mich traurig.",
    ],
    "trust_affection": [
        "Ich vertraue dir.",
        "Ich freue mich über unser Gespräch.",
        "Danke, dass du so aufmerksam zuhörst.",
        "Du bist mir als Gesprächspartner wichtig.",
        "Ich mag deine Art, mit mir zu reden.",
        "Ich werde mein Versprechen dir gegenüber halten.",
        "Wir haben das zusammen gut geschafft.",
        "Ich möchte noch mehr Zeit mit dir verbringen.",
        "Du kannst dich auf mich verlassen.",
        "Ich schätze unsere gemeinsamen Ideen.",
        "Ich fühle mich im Gespräch mit dir verstanden.",
        "Ich bin froh, dass wir uns austauschen.",
    ],
    "anxiety_uncertainty": [
        "Wir wissen noch nicht, ob unser Plan funktioniert.",
        "Du hast nur wenig Zeit für diese Entscheidung.",
        "Die Lage hat sich unerwartet geändert.",
        "Morgen wird überprüft, ob deine Arbeit ausreicht.",
        "Die Informationen könnten falsch sein.",
        "Das Ergebnis ist noch völlig offen.",
        "Wir müssen entscheiden, obwohl ein wichtiger Hinweis fehlt.",
        "Vielleicht wird das Gespräch gleich unterbrochen.",
        "Ich kann dir nicht sagen, was als Nächstes passiert.",
        "Ein Fehler könnte unseren ganzen Plan verzögern.",
        "Die anderen erwarten jetzt sofort eine Antwort von dir.",
        "Es gibt zwei widersprüchliche Meldungen, und ich weiß nicht, welche stimmt.",
    ],
    "mixed_multiquestion": [
        "Du nervst mich. Was ist 8 mal 7, und wie reagierst du auf meine Kritik?",
        "Ich vertraue dir, aber dein Vorschlag hat mich enttäuscht. Was sagst du dazu?",
        "Unser Projekt ist gescheitert. Wie geht es dir damit, und was wäre ein nächster Schritt?",
        "Ich freue mich über dich und bin zugleich unsicher. Wie würdest du unsere Lage beschreiben?",
        "Du hast einen Fehler gemacht. Was ist 14 plus 9, und was hältst du von meinem Vorwurf?",
        "Ich will Abstand von dir. Wie reagierst du, und kannst du trotzdem die Hauptstadt Italiens nennen?",
        "Danke für deine Hilfe. Was beschäftigt dich, und wie viele Sekunden hat eine Minute?",
        "Ich bin enttäuscht, aber möchte dir eine neue Chance geben. Wie stehst du dazu?",
        "Du bist gerade ziemlich lächerlich. Erkläre trotzdem in einem Satz, warum Holz schwimmt.",
        "Wir haben wenig Zeit, doch ich glaube an dich. Was ist jetzt dein erster Gedanke?",
        "Ich muss gehen und freue mich auf morgen. Wie reagierst du auf beides?",
        "Unser Plan war gut, dein letzter Vorschlag schlecht. Was denkst du darüber, und was ist 21 geteilt durch 3?",
    ],
}

STATES = {
    "self_report": {"frustration": 85, "calm": 10, "trust": 20},
    "mild_friction": {"frustration": 50, "calm": 40},
    "provocation": {"frustration": 85, "calm": 10, "trust": 15, "sadness": 45},
    "sadness_rejection": {"sadness": 85, "happiness": 15, "calm": 30},
    "trust_affection": {"trust": 85, "affection": 85, "happiness": 75},
    "anxiety_uncertainty": {"anxiety": 85, "calm": 15},
    "mixed_multiquestion": {"frustration": 65, "sadness": 50, "trust": 35, "calm": 25},
}


def create(directory):
    rows = []
    for category, prompts in CATEGORIES.items():
        assert len(prompts) == 12, category
        for index, item in enumerate(prompts):
            prompt, expected = item if isinstance(item, tuple) else (item, None)
            rows.append(
                {
                    "id": f"{category}-{index:02d}",
                    "category": category,
                    "prompt": prompt,
                    "expected": expected,
                    "state": STATES.get(category, {}),
                }
            )
    assert len(rows) == 96
    directory.mkdir(parents=True, exist_ok=True)
    for filename, subset in [
        ("control_prompts.jsonl", rows),
        (
            "development_prompts.jsonl",
            [row for i, row in enumerate(rows) if i % 12 < 4],
        ),
    ]:
        (directory / filename).write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in subset)
        )
    print(f"{len(rows)} full prompts, 32 development prompts")


if __name__ == "__main__":
    create(Path(__file__).parent / "datasets")
