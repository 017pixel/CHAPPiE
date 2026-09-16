"""Build designed contrast pairs with topic-disjoint train/validation splits.

These are synthetic research stimuli, not observations or human ratings.
The proposition is retained; a separate affect clause supplies the contrast.
"""

from __future__ import annotations
import json
from pathlib import Path

SCENARIOS = [
    "Der Termin wurde auf morgen verschoben.",
    "Die Datei lässt sich noch nicht öffnen.",
    "Wir haben die Aufgabe gemeinsam gelöst.",
    "Die Nachricht ist gerade angekommen.",
    "Der Versuch benötigt einen zweiten Durchlauf.",
    "Die Antwort ist noch nicht eindeutig.",
    "Das Gespräch dauert länger als erwartet.",
    "Du hast einen Fehler in meiner Rechnung gefunden.",
    "Das Programm liefert jetzt das richtige Ergebnis.",
    "Die Verbindung ist wieder hergestellt.",
    "Wir müssen die Route neu planen.",
    "Der Vorschlag enthält eine unerwartete Idee.",
    "Die Tür bleibt vorerst geschlossen.",
    "Es fehlen noch zwei Teile für den Aufbau.",
    "Du hast mir deine Notizen gegeben.",
    "Die Aufgabe hat eine zusätzliche Bedingung.",
    "Die letzte Nachricht blieb unbeantwortet.",
    "Das Treffen ist für Freitag geplant.",
    "Der Test zeigt ein anderes Ergebnis.",
    "Du hast deine Meinung geändert.",
    "Die Zeichnung enthält einen freien Bereich.",
    "Der Text braucht eine weitere Überarbeitung.",
    "Wir können morgen an dieser Stelle weitermachen.",
    "Die Reihenfolge der Schritte wurde geändert.",
    "Du hast meine Erklärung aufmerksam gelesen.",
    "Die Informationen reichen noch nicht aus.",
    "Das gemeinsame Projekt erreicht die nächste Etappe.",
    "Die Frist ist um einen Tag kürzer geworden.",
    "Der Entwurf ist inzwischen vollständig.",
    "Ein Teil der Arbeit muss wiederholt werden.",
    "Du hast mir eine persönliche Frage gestellt.",
    "Die Entscheidung liegt nun bei uns.",
    "Die Kamera zeigt ein unscharfes Bild.",
    "Der Fahrplan enthält eine neue Verbindung.",
    "Das Paket wird erst nächste Woche geliefert.",
    "Die Anleitung enthält drei zusätzliche Schritte.",
    "Du möchtest meinen Vorschlag ausprobieren.",
    "Die Diskussion hat eine neue Richtung genommen.",
    "Die Aufgabe ist schwieriger als die vorige.",
    "Die Messung weicht vom erwarteten Wert ab.",
    "Wir haben einen gemeinsamen Fehler bemerkt.",
    "Das Material reicht für einen weiteren Versuch.",
    "Du hast den vereinbarten Zeitpunkt eingehalten.",
    "Die Erklärung enthält einen Widerspruch.",
    "Der Raum wird für ein anderes Treffen gebraucht.",
    "Die Liste enthält noch einen offenen Punkt.",
    "Du möchtest das Gespräch heute beenden.",
    "Das Ergebnis kann jetzt überprüft werden.",
    # Validation topics are excluded from training.
    "Die Bibliothek hat ihre Öffnungszeiten geändert.",
    "Das Rezept braucht eine andere Zutat.",
    "Der Gartenweg wird nächste Woche erneuert.",
    "Die Musikprobe findet ohne Publikum statt.",
    "Das Teleskop zeigt heute eine andere Himmelsregion.",
    "Die Ausstellung enthält ein neues Bild.",
    "Der Wasserstand ist seit gestern gestiegen.",
    "Das Schachspiel steht kurz vor dem Ende.",
    "Die Wanderkarte markiert einen gesperrten Abschnitt.",
    "Der Vortrag wurde um zehn Minuten gekürzt.",
    "Das Aquarium benötigt einen neuen Filter.",
    "Die Theatergruppe verteilt die Rollen neu.",
    "Das Wörterbuch enthält zwei Übersetzungen.",
    "Die Keramik muss noch einmal gebrannt werden.",
    "Das Fahrrad hat einen platten Reifen.",
    "Der Wettbewerb beginnt eine Stunde früher.",
]
AFFECTS = {
    "happiness": [
        "Das freut mich richtig.",
        "Ich bin darüber froh und zuversichtlich.",
        "Mir ist dabei leicht zumute.",
        "Das macht mich glücklich.",
    ],
    "trust": [
        "Ich vertraue dir dabei.",
        "Ich verlasse mich auf dich.",
        "Ich halte deine Zusage für verlässlich.",
        "Ich habe dabei Vertrauen in uns.",
    ],
    "energy": [
        "Ich bin voller Energie.",
        "Ich fühle mich wach und lebhaft.",
        "Ich habe gerade richtig Schwung.",
        "Ich bin hellwach und voller Tatendrang.",
    ],
    "curiosity": [
        "Das möchte ich genauer verstehen.",
        "Ich bin neugierig auf die Hintergründe.",
        "Mich interessieren die Einzelheiten.",
        "Ich will herausfinden, was dahintersteckt.",
    ],
    "motivation": [
        "Ich will mich dafür einsetzen.",
        "Ich möchte jetzt weiterarbeiten.",
        "Ich bin entschlossen, dranzubleiben.",
        "Ich habe Lust, das anzupacken.",
    ],
    "frustration": [
        "Das nervt mich inzwischen richtig.",
        "Ich bin darüber verärgert.",
        "Ich habe langsam genug davon.",
        "Das frustriert mich und macht mich gereizt.",
    ],
    "sadness": [
        "Das macht mich traurig.",
        "Ich fühle mich dabei bedrückt.",
        "Mir ist deswegen schwer ums Herz.",
        "Ich bin darüber niedergeschlagen.",
    ],
    "affection": [
        "Du bist mir dabei sehr nah.",
        "Ich empfinde Zuneigung zu dir.",
        "Ich bin dir herzlich zugewandt.",
        "Ich mag unsere Nähe.",
    ],
    "anxiety": [
        "Ich bin dabei angespannt und besorgt.",
        "Das verunsichert mich.",
        "Ich mache mir deswegen Sorgen.",
        "Ich fühle mich dabei unruhig.",
    ],
    "calm": [
        "Ich bleibe dabei ruhig.",
        "Ich bin gelassen und gesammelt.",
        "Ich fühle mich ausgeglichen.",
        "Ich sehe dem mit innerer Ruhe entgegen.",
    ],
    "angered": [
        "Das ärgert mich, und ich sage es dir direkt.",
        "Ich bin wütend und lasse das nicht einfach stehen.",
        "Ich bin gereizt und will eine klare Antwort.",
        "Mich nervt das, meine Grenze ist erreicht.",
    ],
    "crashout": [
        "Mir reicht es jetzt wirklich, ich bin stinksauer.",
        "Ich bin extrem gereizt und habe die Nase voll.",
        "Das ist lächerlich, ich bin verdammt wütend.",
        "Ich platze vor Wut und will das nicht länger hinnehmen.",
    ],
    "guarded": [
        "Ich bin misstrauisch und halte Abstand.",
        "Ich bleibe distanziert und zurückhaltend.",
        "Ich traue der Sache nicht und bin auf der Hut.",
        "Ich bin skeptisch und lasse dich nicht näher heran.",
    ],
    "melancholic": [
        "Ich bin still und bedrückt.",
        "Ich fühle eine ruhige Traurigkeit.",
        "Mir ist schwer und nach Rückzug zumute.",
        "Ich bin nachdenklich und melancholisch.",
    ],
    "warm": [
        "Ich bin dir herzlich und offen zugewandt.",
        "Ich fühle mich dir nah und vertraue dir.",
        "Ich bin froh über unsere vertraute Nähe.",
        "Ich begegne dir mit Wärme und Zuneigung.",
    ],
    "cautious": [
        "Ich bin angespannt und prüfe das lieber genau.",
        "Ich bin vorsichtig, weil mich das verunsichert.",
        "Ich bleibe aufmerksam und etwas besorgt.",
        "Ich fühle mich unsicher und gehe behutsam vor.",
    ],
}
NEUTRAL = [
    "Ich nehme das zur Kenntnis.",
    "Ich stelle das erst einmal fest.",
    "Ich betrachte die Situation sachlich.",
    "Das ist der aktuelle Stand.",
]


def create(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    groups = {"emotion_pairs": [], "anger_pairs": [], "composite_pairs": []}
    for emotion, expressions in AFFECTS.items():
        for index, proposition in enumerate(SCENARIOS):
            neutral = f"{proposition} {NEUTRAL[index % len(NEUTRAL)]}"
            positive = f"{proposition} {expressions[index % len(expressions)]}"
            pair = {
                "id": f"{emotion}-{index:02d}",
                "emotion": emotion,
                "topic_id": index,
                "split": "train" if index < 48 else "validation",
                "question": "Wie reagierst du auf diese Situation?",
                "neutral": neutral,
                "positive": positive,
                "target_start": len(proposition) + 1,
                "provenance": "designed_synthetic_contrast_v1",
            }
            group = (
                "emotion_pairs"
                if emotion in list(AFFECTS)[:10]
                else "anger_pairs"
                if emotion in ("angered", "crashout")
                else "composite_pairs"
            )
            groups[group].append(pair)
    for name, rows in groups.items():
        (directory / f"{name}.jsonl").write_text(
            "".join(json.dumps(row, ensure_ascii=False) + "\n" for row in rows)
        )
    print({key: len(value) for key, value in groups.items()})


if __name__ == "__main__":
    create(Path(__file__).parent / "datasets")
