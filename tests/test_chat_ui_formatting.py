import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from api.services.text_formatting import parse_emotional_text


def test_parse_emotional_text():
    assert parse_emotional_text("Hallo...") == "Hallo<br/><br/><em>...</em><br/><br/>"
    assert parse_emotional_text("Das ist... schwer.") == "Das ist<br/><br/><em>...</em><br/><br/> schwer."
    assert parse_emotional_text("Habe nachgedacht..... wirklich.") == "Habe nachgedacht<br/><br/><em>.....</em><br/><br/> wirklich."
    assert parse_emotional_text("Hallo *lacht*") == "Hallo <br/><br/><em>*lacht*</em><br/><br/>"
    assert parse_emotional_text('Hallo """" was?"') == 'Hallo <br/><br/><em>""""</em><br/><br/> was?"'
    assert parse_emotional_text('Ich... *seufzt* """" ueberlege') == 'Ich<br/><br/><em>...</em><br/><br/> <br/><br/><em>*seufzt*</em><br/><br/> <br/><br/><em>""""</em><br/><br/> ueberlege'


if __name__ == "__main__":
    test_parse_emotional_text()
    print("OK: test_chat_ui_formatting")
