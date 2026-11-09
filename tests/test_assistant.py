import unittest

from pria.core.assistant import Assistant


class AssistantTests(unittest.TestCase):
    def setUp(self):
        self.assistant = Assistant()

    def test_help_is_available(self):
        self.assertIn("/ajuda", self.assistant.respond("/ajuda"))

    def test_about_reports_local_model_and_explicit_tools(self):
        answer = self.assistant.respond("/sobre")
        self.assertIn("modelo instalado", answer)
        self.assertIn("ferramentas locais", answer)

    def test_unknown_command_is_not_faked(self):
        answer = self.assistant.respond("abra o navegador")
        self.assertIn("não existe", answer)


if __name__ == "__main__":
    unittest.main()
