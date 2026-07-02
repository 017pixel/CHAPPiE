"""
Umfassende Tests fuer Context-File Tool Calling System.

Testet:
1. FunctionRegistry.get_openai_tools()
2. Context-File Tools (update_soul, update_user, update_preferences)
3. GroqBrain.generate_with_tools()
4. CONTEXT_FILE_TOOL_INSTRUCTION im System-Prompt
5. IntentProcessor Context-Defaults
6. MemoryAgent Results -> Context Updates
7. Native Tool Execution (backend_wrapper)
"""

import sys
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest
from unittest.mock import MagicMock, patch, PropertyMock
from datetime import datetime

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))


def _make_temp_context_files(tmp_dir):
    """Create ContextFilesManager in temp dir."""
    from memory.context_files import ContextFilesManager
    return ContextFilesManager(base_dir=Path(tmp_dir))


class FunctionRegistryToolsTests(unittest.TestCase):
    """Tests fuer FunctionRegistry Tool-Export."""

    def test_get_openai_tools_returns_correct_format(self):
        from memory.function_registry import get_function_registry
        registry = get_function_registry()
        tools = registry.get_openai_tools()
        self.assertIsInstance(tools, list)
        self.assertGreater(len(tools), 3)
        for tool in tools:
            self.assertEqual(tool["type"], "function")
            self.assertIn("name", tool["function"])
            self.assertIn("description", tool["function"])
            self.assertIn("parameters", tool["function"])

    def test_context_file_tools_registered(self):
        from memory.function_registry import get_function_registry
        registry = get_function_registry()
        self.assertTrue(registry.has_function("update_soul"))
        self.assertTrue(registry.has_function("update_user"))
        self.assertTrue(registry.has_function("update_preferences"))

    def test_update_soul_tool_executes(self):
        with TemporaryDirectory() as tmp_dir:
            cfs = _make_temp_context_files(tmp_dir)
            with patch("memory.context_files.get_context_files_manager", return_value=cfs):
                from memory.function_registry import get_function_registry
                registry = get_function_registry()
                result = registry.execute("update_soul", {
                    "evolution_note": "Test Erkenntnis",
                    "self_perception": "Ich bin ein Test",
                })
                self.assertIn("aktualisiert", result.lower())
            soul_content = (Path(tmp_dir) / "soul.md").read_text(encoding="utf-8")
            self.assertIn("Test Erkenntnis", soul_content)

    def test_update_user_tool_executes(self):
        with TemporaryDirectory() as tmp_dir:
            cfs = _make_temp_context_files(tmp_dir)
            with patch("memory.context_files.get_context_files_manager", return_value=cfs):
                from memory.function_registry import get_function_registry
                registry = get_function_registry()
                result = registry.execute("update_user", {
                    "name": "TestUser",
                    "learning": "Der User mag Python",
                })
                self.assertIn("aktualisiert", result.lower())

    def test_update_preferences_tool_executes(self):
        with TemporaryDirectory() as tmp_dir:
            cfs = _make_temp_context_files(tmp_dir)
            with patch("memory.context_files.get_context_files_manager", return_value=cfs):
                from memory.function_registry import get_function_registry
                registry = get_function_registry()
                result = registry.execute("update_preferences", {
                    "new_preference": "Ich mag kurze Antworten",
                })
                self.assertIn("aktualisiert", result.lower())

    def test_get_openai_tools_includes_context_tools(self):
        from memory.function_registry import get_function_registry
        registry = get_function_registry()
        tools = registry.get_openai_tools()
        names = [t["function"]["name"] for t in tools]
        for expected in ["update_soul", "update_user", "update_preferences"]:
            self.assertIn(expected, names, f"Tool {expected} missing from openai tools")


class SystemPromptTests(unittest.TestCase):
    """Tests fuer Tool-Instruktionen im System-Prompt."""

    def test_build_system_prompt_includes_tool_instruction(self):
        from config.prompts import build_system_prompt  # from config/prompts.py
        prompt = build_system_prompt(include_emotion_status=True, use_chain_of_thought=False)
        self.assertIn("soul.md", prompt or "")
        self.assertIn("user.md", prompt or "")
        self.assertIn("CHAPPiEsPreferences.md", prompt or "")
        self.assertIn("AKTUALISIEREN", prompt or "")

    def test_system_prompt_with_emotions_includes_tools(self):
        from config.prompts import get_system_prompt_with_emotions  # from config/prompts.py
        prompt = get_system_prompt_with_emotions(include_emotion_status=True, use_chain_of_thought=True)
        self.assertIn("soul.md", prompt)
        self.assertIn("CHAPPiEsPreferences.md", prompt)


class IntentProcessorContextDefaultsTests(unittest.TestCase):
    """Tests fuer korrekte Context-Defaults."""

    def test_quick_classify_has_true_defaults(self):
        from memory.intent_processor import IntentProcessor
        processor = IntentProcessor()
        result = processor._quick_classify("hallo")
        if result:
            self.assertTrue(result.context_requirements.get("need_user_context", False))
            self.assertTrue(result.context_requirements.get("need_preferences", False))

    def test_parse_intent_result_has_true_defaults(self):
        from memory.intent_processor import IntentProcessor
        processor = IntentProcessor()
        result = processor._parse_intent_result({})
        self.assertTrue(result.context_requirements.get("need_user_context", False))
        self.assertTrue(result.context_requirements.get("need_preferences", False))

    def test_fallback_result_has_true_defaults(self):
        from memory.intent_processor import IntentProcessor
        processor = IntentProcessor()
        result = processor._create_fallback_result()
        self.assertTrue(result.context_requirements.get("need_user_context", False))
        self.assertTrue(result.context_requirements.get("need_preferences", False))


class MemoryAgentResultTests(unittest.TestCase):
    """Tests fuer MemoryAgent Results -> Context Updates."""

    def test_apply_memory_agent_updates_soul(self):
        with TemporaryDirectory() as tmp_dir:
            from memory.context_files import ContextFilesManager
            from brain.brain_pipeline import BrainPipeline
            cfs = ContextFilesManager(base_dir=Path(tmp_dir))
            pipeline = BrainPipeline()
            pipeline._apply_memory_agent_updates(cfs, {
                "soul_updates": {"evolution_note": "MemoryAgent test", "trust_level": 75},
            })
            soul = (Path(tmp_dir) / "soul.md").read_text(encoding="utf-8")
            self.assertIn("MemoryAgent test", soul)

    def test_apply_memory_agent_updates_user(self):
        with TemporaryDirectory() as tmp_dir:
            from memory.context_files import ContextFilesManager
            from brain.brain_pipeline import BrainPipeline
            cfs = ContextFilesManager(base_dir=Path(tmp_dir))
            pipeline = BrainPipeline()
            pipeline._apply_memory_agent_updates(cfs, {
                "user_updates": {"name": "TestName", "learning": "User mag Tests"},
            })
            user = (Path(tmp_dir) / "user.md").read_text(encoding="utf-8")
            self.assertIn("TestName", user)

    def test_apply_memory_agent_updates_empty_data(self):
        with TemporaryDirectory() as tmp_dir:
            from memory.context_files import ContextFilesManager
            from brain.brain_pipeline import BrainPipeline
            cfs = ContextFilesManager(base_dir=Path(tmp_dir))
            pipeline = BrainPipeline()
            # Should not raise
            pipeline._apply_memory_agent_updates(cfs, {})


class GroqBrainToolTests(unittest.TestCase):
    """Tests fuer GroqBrain Tool-Support."""

    def test_parse_tool_calls_empty(self):
        from brain.groq_brain import GroqBrain
        brain = GroqBrain.__new__(GroqBrain)
        result = brain._parse_tool_calls_from_response(MagicMock(tool_calls=None))
        self.assertIsNone(result)

    def test_generate_accepts_tools_parameter(self):
        from brain.groq_brain import GroqBrain
        import inspect
        sig = inspect.signature(GroqBrain.generate)
        self.assertIn("tools", sig.parameters)
        self.assertIn("tool_choice", sig.parameters)


class ToolExecutionTests(unittest.TestCase):
    """Tests fuer Tool-Execution."""

    def test_native_tool_calls_execute(self):
        with TemporaryDirectory() as tmp_dir:
            cfs = _make_temp_context_files(tmp_dir)
            with patch("memory.context_files.get_context_files_manager", return_value=cfs):
                from memory.function_registry import get_function_registry
                registry = get_function_registry()
                result = registry.execute("update_soul", {"evolution_note": "Test native call"})
                self.assertIn("aktualisiert", result.lower())

    def test_native_tool_calls_bad_arg(self):
        from memory.function_registry import get_function_registry
        registry = get_function_registry()
        result = registry.execute("nonexistent_tool", {})
        self.assertIn("Unbekannte Funktion", result)


if __name__ == "__main__":
    unittest.main()
