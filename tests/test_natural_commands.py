import tempfile
import unittest
from unittest.mock import Mock, patch
from unittest.mock import patch
from pathlib import Path

from pria.core.natural_commands import execute_obvious_local_request, requests_local_action
from pria.tools.files import FileTools


class NoApps:
    pass


class NaturalCommandTests(unittest.TestCase):
    def test_plain_portuguese_request_lists_user_selected_folder(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "arquivo local.txt"
            target.write_text("hello", encoding="utf-8")
            result = execute_obvious_local_request(
                f'Liste os arquivos em "{temp}"', FileTools(), NoApps()
            )
            self.assertIn("arquivo local.txt", result)

    def test_plain_portuguese_file_read(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "nota.txt"
            target.write_text("conteúdo de teste", encoding="utf-8")
            result = execute_obvious_local_request(
                f'Leia o arquivo "{target}"', FileTools(), NoApps()
            )
            self.assertEqual(result, "conteúdo de teste")

    def test_plain_open_app_name_uses_start_menu_match(self):
        # Keep the test isolated from real Windows app launches.
        apps = Mock()
        apps.find_names.return_value = ["Spotify"]
        apps.open.return_value = "Solicitei ao Windows a abertura de Spotify."
        result = execute_obvious_local_request("Abra Spotify", FileTools(), apps)
        self.assertEqual(result, "Solicitei ao Windows a abertura de Spotify.")
        apps.open.assert_called_once_with("Spotify")

    def test_unmatched_question_is_left_for_local_model(self):
        self.assertIsNone(execute_obvious_local_request("Explique a gravidade", FileTools(), NoApps()))
        self.assertFalse(requests_local_action("Explique o que é um navegador"))
        self.assertTrue(requests_local_action("Abra o aplicativo Calculadora"))
        self.assertTrue(requests_local_action("Mexa no meu computador"))

    def test_natural_create_and_delete_require_confirmation_for_delete(self):
        with tempfile.TemporaryDirectory() as temp:
            target = Path(temp) / "nota.txt"
            result = execute_obvious_local_request(
                f'Crie um arquivo "{target}" com texto "olá local"', FileTools(), NoApps()
            )
            self.assertIn("Arquivo criado", result)
            self.assertEqual(target.read_text(encoding="utf-8"), "olá local")
            cancelled = execute_obvious_local_request(f'Apague "{target}"', FileTools(), NoApps(), lambda _q: False)
            self.assertIn("cancelada", cancelled.casefold())
            self.assertTrue(target.exists())
            deleted = execute_obvious_local_request(f'Apague "{target}"', FileTools(), NoApps(), lambda _q: True)
            self.assertIn("Excluído", deleted)
            self.assertFalse(target.exists())

    def test_service_read_is_direct_and_start_requires_confirmation(self):
        with patch("pria.core.natural_commands.WindowsServices") as services:
            services.return_value.list_services.return_value = [
                {"display_name": "Windows Update", "name": "wuauserv", "state": "RUNNING"}
            ]
            listed = execute_obvious_local_request("Liste os serviços do Windows", FileTools(), NoApps())
            self.assertIn("wuauserv", listed)
            cancelled = execute_obvious_local_request(
                "Inicie o serviço Spooler", FileTools(), NoApps(), lambda _prompt: False
            )
        self.assertIn("cancelada", cancelled.casefold())
        services.return_value.start.assert_not_called()


if __name__ == "__main__":
    unittest.main()
