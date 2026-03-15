import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from web_infrastructure.chat_ui import _parse_emotional_text

def test_parse_emotional_text():
    # Test 3 dots
    assert _parse_emotional_text("Hallo...") == "Hallo<br/><br/><em>...</em><br/><br/>"
    assert _parse_emotional_text("Das ist... schwer.") == "Das ist<br/><br/><em>...</em><br/><br/> schwer."
    
    # Test > 3 dots
    assert _parse_emotional_text("Habe nachgedacht..... wirklich.") == "Habe nachgedacht<br/><br/><em>.....</em><br/><br/> wirklich."

    # Test asterisk
    assert _parse_emotional_text("Hallo *lacht*") == "Hallo <br/><br/><em>*lacht*</em><br/><br/>"
    
    # Test multiple quotes
    assert _parse_emotional_text('Hallo """" was?"') == 'Hallo <br/><br/><em>""""</em><br/><br/> was?"'
    
    # Test combined
    assert _parse_emotional_text('Ich... *seufzt* """" überlege') == 'Ich<br/><br/><em>...</em><br/><br/> <br/><br/><em>*seufzt*</em><br/><br/> <br/><br/><em>""""</em><br/><br/> überlege'

if __name__ == "__main__":
    test_parse_emotional_text()
    print("OK: test_chat_ui_formatting")
