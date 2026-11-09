import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pria.tools.code_workspace import CodeWorkspace, CodeWorkspaceError


class CodeWorkspaceTests(unittest.TestCase):
    def test_generates_python_checks_syntax_creates_and_opens_without_running(self):
        with tempfile.TemporaryDirectory() as temp:
            chat = Mock()
            chat.reply.return_value = "print('Olá')"
            apps = Mock()
            root = Path(temp) / "PriyaProjects"
            workspace = CodeWorkspace(chat, apps, root=root)
            with patch.object(CodeWorkspace, "_find_vscode", return_value=None):
                result = workspace.create_and_open("ola", "Python", "um programa que imprime Olá no terminal")
            target = root / "ola.py"
            self.assertTrue(target.is_file())
            self.assertIn("Não executei o código", result)
            apps.open_path.assert_called_once_with(target)
            chat.reply.assert_called_once()

    def test_does_not_overwrite_existing_code(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            existing = root / "app.py"
            existing.write_text("preservar", encoding="utf-8")
            workspace = CodeWorkspace(Mock(), Mock(), root=root)
            with self.assertRaises(CodeWorkspaceError):
                workspace.create_and_open("app", "python", "programa para somar dois valores")
            self.assertEqual(existing.read_text(encoding="utf-8"), "preservar")

    def test_asks_for_a_purpose_before_generating_generic_code(self):
        with tempfile.TemporaryDirectory() as temp:
            chat = Mock()
            workspace = CodeWorkspace(chat, Mock(), root=Path(temp) / "projects")
            with self.assertRaisesRegex(CodeWorkspaceError, "o que o programa deve fazer"):
                workspace.create_and_open("codigo", "python", "Crie um código no Visual Studio")
            chat.reply.assert_not_called()

    def test_rejects_python_syntax_error_without_creating_a_file(self):
        with tempfile.TemporaryDirectory() as temp:
            chat = Mock()
            chat.reply.return_value = "def quebrado(:"
            root = Path(temp) / "projects"
            workspace = CodeWorkspace(chat, Mock(), root=root)
            with self.assertRaisesRegex(CodeWorkspaceError, "Python inválido"):
                workspace.create_and_open("app", "python", "programa que calcula a média de notas escolares")
            self.assertFalse(root.exists())


if __name__ == "__main__":
    unittest.main()
