import sys
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import mock
import unittest

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from Chappies_Trainingspartner import daemon_manager


class TrainingDaemonLifecycleTests(unittest.TestCase):
    def _swap_paths(self, tmp_dir: str):
        original = (
            daemon_manager.PID_FILE,
            daemon_manager.LOG_FILE,
            daemon_manager.STATE_FILE,
            daemon_manager.CONFIG_FILE,
        )
        daemon_manager.PID_FILE = Path(tmp_dir) / "training.pid"
        daemon_manager.LOG_FILE = Path(tmp_dir) / "training_daemon.log"
        daemon_manager.STATE_FILE = Path(tmp_dir) / "training_state.json"
        daemon_manager.CONFIG_FILE = Path(tmp_dir) / "training_config.json"
        return original

    @staticmethod
    def _restore_paths(original):
        (
            daemon_manager.PID_FILE,
            daemon_manager.LOG_FILE,
            daemon_manager.STATE_FILE,
            daemon_manager.CONFIG_FILE,
        ) = original

    def test_stop_daemon_is_idempotent_when_not_running(self):
        with mock.patch("Chappies_Trainingspartner.daemon_manager.is_daemon_running", return_value=None):
            result = daemon_manager.stop_daemon()
        self.assertTrue(result["success"])
        self.assertIn("bereits gestoppt", result["message"])

    def test_restart_daemon_calls_start_after_stop(self):
        with mock.patch("Chappies_Trainingspartner.daemon_manager.stop_daemon", return_value={"success": True, "message": "ok"}) as stop_mock:
            with mock.patch(
                "Chappies_Trainingspartner.daemon_manager.start_daemon",
                return_value={"success": True, "pid": 77, "message": "started"},
            ) as start_mock:
                result = daemon_manager.restart_daemon(new=True, config_overrides={"focus_area": "Test"})

        self.assertTrue(result["success"])
        stop_mock.assert_called_once()
        start_mock.assert_called_once()

    def test_get_training_snapshot_flags_stale_pid(self):
        with TemporaryDirectory() as tmp_dir:
            original = self._swap_paths(tmp_dir)
            try:
                daemon_manager.PID_FILE.write_text("abc", encoding="utf-8")
                snapshot = daemon_manager.get_training_snapshot()
            finally:
                self._restore_paths(original)

        self.assertFalse(snapshot["running"])
        self.assertEqual(snapshot["status_code"], "stopped_stale_pid")
        self.assertTrue(any("PID" in msg for msg in snapshot["diagnostic_messages"]))

    def test_start_daemon_confirms_running_pid(self):
        with TemporaryDirectory() as tmp_dir:
            original = self._swap_paths(tmp_dir)
            try:
                with mock.patch("Chappies_Trainingspartner.daemon_manager.is_daemon_running", side_effect=[None, 456]):
                    with mock.patch("Chappies_Trainingspartner.daemon_manager.subprocess.Popen") as popen_mock:
                        with mock.patch("Chappies_Trainingspartner.daemon_manager.time.sleep", return_value=None):
                            popen_mock.return_value.pid = 456
                            result = daemon_manager.start_daemon()
            finally:
                self._restore_paths(original)

        self.assertTrue(result["success"])
        self.assertEqual(result["pid"], 456)
        self.assertIn("gestartet", result["message"])


if __name__ == "__main__":
    unittest.main()
