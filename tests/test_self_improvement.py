import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import pria.core.self_improvement as module
from pria.core.self_improvement import SelfImprovement, SelfImprovementError


class FakeChat:
    def __init__(self, answer):
        self.answer = answer

    def reply(self, *_args, **_kwargs):
        return self.answer


class SelfImprovementTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "pria" / "core").mkdir(parents=True)
        self.target = self.root / "pria" / "core" / "example.py"
        self.target.write_text("VALUE = 1\n", encoding="utf-8")
        self.root_patch = patch.object(module, "ROOT", self.root)
        self.root_patch.start()

    def tearDown(self):
        self.root_patch.stop()
        self.temp.cleanup()

    def test_protects_sensitive_modules_and_path_traversal(self):
        tool = SelfImprovement(FakeChat(""))
        for path in ("pria/config.py", "pria/main.py", "pria/core/self_improvement.py",
                     "pria/tools/powershell.py", "pria/tools/windows_automation.py",
                     "pria/security/__init__.py", "../secret.py"):
            with self.subTest(path=path), self.assertRaises(SelfImprovementError):
                tool.target_path(path)

    def test_draft_validates_python_and_returns_complete_replacement(self):
        tool = SelfImprovement(FakeChat('{"find":"VALUE = 1", "replace":"VALUE = 2"}'))
        original, replacement = tool.draft("pria/core/example.py", "Altere o valor")
        self.assertEqual(original, "VALUE = 1\n")
        self.assertEqual(replacement, "VALUE = 2\n")
        invalid = '{"find":"VALUE = 1", "replace":"not valid python !!!"}'
        with self.assertRaises(SelfImprovementError):
            SelfImprovement(FakeChat(invalid)).draft("pria/core/example.py", "Altere")

    def test_change_must_target_one_exact_literal_match(self):
        wrong = '{"find":"VALUE = 9", "replace":"VALUE = 2"}'
        with self.assertRaises(SelfImprovementError):
            SelfImprovement(FakeChat(wrong)).draft("pria/core/example.py", "Altere")

    def test_change_rejects_ambiguous_literal(self):
        self.target.write_text("VALUE = 1\nVALUE = 1\n", encoding="utf-8")
        proposal = '{"find":"VALUE = 1", "replace":"VALUE = 2"}'
        with self.assertRaises(SelfImprovementError):
            SelfImprovement(FakeChat(proposal)).draft("pria/core/example.py", "Altere")

    def test_apply_creates_backup_and_refuses_stale_files(self):
        tool = SelfImprovement(FakeChat(""))
        original = self.target.read_text(encoding="utf-8")
        replacement = "VALUE = 2\n"
        with tempfile.TemporaryDirectory() as local:
            with patch.dict(os.environ, {"LOCALAPPDATA": local}):
                backup = tool.apply("pria/core/example.py", original, replacement)
                self.assertTrue(backup.is_file())
                self.assertEqual(backup.read_text(encoding="utf-8"), original)
                self.assertEqual(self.target.read_text(encoding="utf-8"), replacement)
                with self.assertRaises(SelfImprovementError):
                    tool.apply("pria/core/example.py", original, "VALUE = 3\n")

    def test_apply_restores_original_when_local_test_suite_fails(self):
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_example.py").write_text("", encoding="utf-8")
        tool = SelfImprovement(FakeChat(""))
        original = self.target.read_text(encoding="utf-8")
        failed = type("Result", (), {"returncode": 1, "stdout": "", "stderr": "FAIL"})()
        with tempfile.TemporaryDirectory() as local, patch.dict(os.environ, {"LOCALAPPDATA": local}), \
                patch.object(module.subprocess, "run", return_value=failed):
            with self.assertRaisesRegex(SelfImprovementError, "restaurei o arquivo original"):
                tool.apply("pria/core/example.py", original, "VALUE = 2\n")
        self.assertEqual(self.target.read_text(encoding="utf-8"), original)

    def test_apply_runs_test_suite_before_reporting_success(self):
        (self.root / "tests").mkdir()
        (self.root / "tests" / "test_example.py").write_text("", encoding="utf-8")
        tool = SelfImprovement(FakeChat(""))
        original = self.target.read_text(encoding="utf-8")
        passed = type("Result", (), {"returncode": 0, "stdout": "OK", "stderr": ""})()
        with tempfile.TemporaryDirectory() as local, patch.dict(os.environ, {"LOCALAPPDATA": local}), \
                patch.object(module.subprocess, "run", return_value=passed) as run:
            tool.apply("pria/core/example.py", original, "VALUE = 2\n")
        run.assert_called_once()


if __name__ == "__main__":
    unittest.main()
