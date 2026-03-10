"""UI-Helfer für Emotionen und Command-Layout prüfen."""

import os
import sys

TEST_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(TEST_DIR)
sys.path.insert(0, PROJECT_ROOT)

from web_infrastructure.ui_utils import EMOTION_DEFAULTS, bootstrap_current_emotions, build_steering_state_rows, chunk_items, clamp_numeric_value, normalize_emotions, split_steering_vectors


def test_normalize_emotions_supports_legacy_joy_and_missing_values():
    normalized = normalize_emotions({"joy": 61, "trust": 55, "sadness": 7})
    assert normalized["happiness"] == 61
    assert normalized["trust"] == 55
    assert normalized["sadness"] == 7
    assert normalized["frustration"] == EMOTION_DEFAULTS["frustration"]
    assert set(normalized) == set(EMOTION_DEFAULTS)


def test_normalize_emotions_clamps_values():
    normalized = normalize_emotions({"happiness": 130, "sadness": -12})
    assert normalized["happiness"] == 100
    assert normalized["sadness"] == 0


def test_chunk_items_breaks_commands_into_rows_of_five():
    rows = chunk_items(["/sleep", "/life", "/world", "/habits", "/stage", "/plan"], 5)
    assert rows == [["/sleep", "/life", "/world", "/habits", "/stage"], ["/plan"]]


def test_clamp_numeric_value_handles_out_of_range_widget_defaults():
    assert clamp_numeric_value(99, 0, 31, default=0) == 31.0
    assert clamp_numeric_value(-3, 0, 31, default=0) == 0.0
    assert clamp_numeric_value("bad", 0, 31, default=7) == 7.0


def test_build_steering_state_rows_exposes_all_vital_signs_for_ui_tables():
    rows = build_steering_state_rows(
        {
            "emotion_state": {
                "happiness": 81,
                "trust": 74,
                "energy": 71,
                "curiosity": 68,
                "motivation": 66,
                "frustration": 19,
                "sadness": 22,
            },
            "emotion_intensities": {
                "happiness": 0.91,
                "trust": 0.66,
                "energy": 0.55,
                "curiosity": 0.0,
                "motivation": 0.29,
                "frustration": -0.62,
                "sadness": -0.58,
            },
            "base_vectors": [
                {"name": "happiness", "direction": "positive", "layer_range": [18, 28], "surface_effect": "warm"},
                {"name": "frustration", "direction": "negative", "layer_range": [17, 29], "surface_effect": "ruhig"},
            ],
            "base_vector_config": [
                {"emotion": key, "layer_start": 10, "layer_end": 26, "default_alpha": 0.3}
                for key in EMOTION_DEFAULTS
            ],
        }
    )
    assert len(rows) == len(EMOTION_DEFAULTS)
    assert rows[0]["emotion"] == "Freude"
    frustration_row = next(row for row in rows if row["emotion"] == "Frustration")
    assert frustration_row["richtung"] == "daempfend"
    assert frustration_row["layer_range"] == "17-29"
    assert frustration_row["basisvektor_konfiguriert"] is True
    trust_row = next(row for row in rows if row["emotion"] == "Vertrauen")
    assert trust_row["basisvektor_konfiguriert"] is True
    assert trust_row["im_payload_aktiv"] is True
    curiosity_row = next(row for row in rows if row["emotion"] == "Neugier")
    assert curiosity_row["basisvektor_konfiguriert"] is True
    assert curiosity_row["im_payload_aktiv"] is False


def test_bootstrap_current_emotions_prefers_persisted_backend_state_on_fresh_ui_load():
    current, loaded = bootstrap_current_emotions(
        session_emotions={},
        backend_emotions={"happiness": 77, "trust": 66, "energy": 12, "curiosity": 91, "frustration": 3, "motivation": 87, "sadness": 4},
        already_loaded=False,
    )

    assert loaded is True
    assert current["happiness"] == 77
    assert current["curiosity"] == 91


def test_bootstrap_current_emotions_keeps_loaded_session_values():
    current, loaded = bootstrap_current_emotions(
        session_emotions={"happiness": 61, "trust": 62, "energy": 63, "curiosity": 64, "frustration": 5, "motivation": 65, "sadness": 6},
        backend_emotions={"happiness": 50, "trust": 50, "energy": 100, "curiosity": 50, "frustration": 0, "motivation": 80, "sadness": 0},
        already_loaded=True,
    )

    assert loaded is True
    assert current["happiness"] == 61
    assert current["motivation"] == 65


def test_split_steering_vectors_prefers_explicit_base_and_composite_lists():
    base_vectors, composite_vectors = split_steering_vectors(
        {
            "base_vectors": [{"name": "happiness", "source": "base"}],
            "composite_vectors": [{"name": "warm", "source": "composite"}],
            "active_vectors": [{"name": "ignored", "source": "base"}],
        }
    )
    assert base_vectors[0]["name"] == "happiness"
    assert composite_vectors[0]["name"] == "warm"


if __name__ == "__main__":
    test_normalize_emotions_supports_legacy_joy_and_missing_values()
    test_normalize_emotions_clamps_values()
    test_chunk_items_breaks_commands_into_rows_of_five()
    test_clamp_numeric_value_handles_out_of_range_widget_defaults()
    test_build_steering_state_rows_exposes_all_vital_signs_for_ui_tables()
    test_bootstrap_current_emotions_prefers_persisted_backend_state_on_fresh_ui_load()
    test_bootstrap_current_emotions_keeps_loaded_session_values()
    test_split_steering_vectors_prefers_explicit_base_and_composite_lists()
    print("OK: web UI emotion handling and command layout helpers are consistent")