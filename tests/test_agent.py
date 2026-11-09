import tempfile
import unittest
from unittest.mock import patch
from pathlib import Path

from pria.core.agent import LocalAgent
from pria.tools.applications import ApplicationLauncher
from pria.tools.files import FileTools


class FakeChat:
    def __init__(self, decisions):
        self.decisions = iter(decisions)

    def decide(self, *_args):
        return next(self.decisions)

    def reply(self, *_args):
        return "Resumo local final."


class LocalAgentTests(unittest.TestCase):
    def test_runs_only_allowlisted_tool_after_explicit_user_request(self):
        with tempfile.TemporaryDirectory() as temp:
            (Path(temp) / "nota.txt").write_text("olá", encoding="utf-8")
            chat = FakeChat([
                {"action": "tool", "tool_name": "list_directory", "arguments": {"path": temp}, "message": ""},
                {"action": "answer", "message": "Encontrei nota.txt.", "tool_name": "", "arguments": {}},
            ])
            agent = LocalAgent(chat, FileTools(), ApplicationLauncher())
            answer = agent.respond([], "Liste os arquivos nesta pasta")
            self.assertIn("nota.txt", answer)

    def test_rejects_tool_suggested_without_user_intent(self):
        chat = FakeChat([
            {"action": "tool", "tool_name": "open_web", "arguments": {"url": "https://example.com"}, "message": ""},
        ])
        agent = LocalAgent(chat, FileTools(), ApplicationLauncher())
        answer = agent.respond([], "Resuma este texto: olá")
        self.assertIn("Não executei", answer)

    def test_code_creation_requires_an_explicit_programming_request(self):
        self.assertTrue(LocalAgent._authorized_by_current_request(
            "create_code_file", "Crie um código para uma calculadora que soma dois números"
        ))
        self.assertFalse(LocalAgent._authorized_by_current_request(
            "create_code_file", "Explique como funciona uma calculadora"
        ))

    def test_natural_window_click_requires_confirmation_and_executes_real_tool(self):
        chat = FakeChat([
            {"action": "tool", "tool_name": "click_window", "arguments": {"x": 400, "y": 300, "button": "left"}, "message": ""},
            {"action": "answer", "message": "Clique realizado.", "tool_name": "", "arguments": {}},
        ])
        agent = LocalAgent(chat, FileTools(), ApplicationLauncher())
        with patch("pria.core.agent.WindowsAutomation") as windows:
            windows.return_value.click.return_value = "Clique enviado para (400, 300)."
            answer = agent.respond([], "Clique em 400, 300", confirm=lambda _text: True)
        self.assertIn("Clique realizado", answer)
        windows.return_value.click.assert_called_once_with(400, 300, "left")

    def test_natural_window_click_is_cancelled_without_touching_mouse(self):
        chat = FakeChat([
            {"action": "tool", "tool_name": "click_window", "arguments": {"x": 400, "y": 300}, "message": ""},
        ])
        agent = LocalAgent(chat, FileTools(), ApplicationLauncher())
        with patch("pria.core.agent.WindowsAutomation") as windows:
            answer = agent.respond([], "Clique em 400, 300", confirm=lambda _text: False)
        self.assertIn("cancelado", answer.casefold())
        windows.return_value.click.assert_not_called()

    def test_service_stop_requires_explicit_current_request_and_confirmation(self):
        chat = FakeChat([
            {"action": "tool", "tool_name": "stop_service", "arguments": {"name": "Spooler"}, "message": ""},
        ])
        agent = LocalAgent(chat, FileTools(), ApplicationLauncher())
        with patch("pria.core.agent.WindowsServices") as services:
            answer = agent.respond([], "Pare o serviço Spooler", confirm=lambda _text: False)
        self.assertIn("cancelada", answer.casefold())
        services.return_value.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
