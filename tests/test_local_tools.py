import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

from pria.tools.applications import ApplicationLauncher, ApplicationToolError
from pria.tools.files import ConfirmationRequired, FileToolError, FileTools
from pria.tools.web import WebToolError, extract_web_page, open_web_page
from pria.tools.windows_automation import WindowsAutomation, WindowsAutomationError


class FileToolsTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)
        (self.root / "nota.txt").write_text("Conteúdo local", encoding="utf-8")
        (self.root / "relatorio.pdf").write_bytes(b"not parsed in this phase")
        self.tools = FileTools()

    def tearDown(self):
        self.temp.cleanup()

    def test_list_and_search(self):
        names = {p.name for p in self.tools.list_directory(self.root)}
        matches, truncated = self.tools.search_files(self.root, "*.pdf")
        self.assertEqual(names, {"nota.txt", "relatorio.pdf"})
        self.assertEqual([p.name for p in matches], ["relatorio.pdf"])
        self.assertFalse(truncated)

    def test_read_text_file(self):
        self.assertEqual(self.tools.read_text(self.root / "nota.txt"), "Conteúdo local")

    def test_binary_document_is_not_misreported_as_readable(self):
        with self.assertRaises(FileToolError):
            self.tools.read_text(self.root / "relatorio.pdf")

    def test_create_copy_move_and_rename_without_overwriting(self):
        created = self.root / "novo.txt"
        self.tools.create_text_file(created, "original")
        with self.assertRaises(FileToolError):
            self.tools.create_text_file(created, "overwrite")
        copied = self.root / "copia.txt"
        self.tools.copy_path(created, copied)
        moved = self.root / "movido.txt"
        self.tools.move_path(copied, moved)
        self.tools.rename_path(moved, "renomeado.txt")
        self.assertFalse(moved.exists())
        self.assertEqual((self.root / "renomeado.txt").read_text(encoding="utf-8"), "original")

    def test_delete_requires_confirmation_and_refuses_nonempty_directory(self):
        with self.assertRaises(ConfirmationRequired):
            self.tools.delete_path(self.root / "nota.txt")
        empty = self.root / "empty"
        empty.mkdir()
        self.tools.delete_path(empty, confirmed=True)
        with self.assertRaises(FileToolError):
            self.tools.delete_path(self.root, confirmed=True)


class WindowsToolTests(unittest.TestCase):
    def test_application_input_is_fixed_and_not_a_shell_command(self):
        launcher = ApplicationLauncher()
        with patch("pria.tools.applications.platform.system", return_value="Windows"), patch(
            "pria.tools.applications.os.startfile", create=True
        ) as startfile:
            launcher.open("calculadora")
            startfile.assert_called_once_with("calc.exe")
            with self.assertRaises(ApplicationToolError):
                launcher.open("calc.exe & del C:\\important.txt")
            self.assertEqual(startfile.call_count, 1)

    def test_open_path_uses_windows_shell_association(self):
        launcher = ApplicationLauncher()
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory) / "sample.txt"
            target.write_text("content", encoding="utf-8")
            with patch("pria.tools.applications.platform.system", return_value="Windows"), patch(
                "pria.tools.applications.os.startfile", create=True
            ) as startfile:
                result = launcher.open_path(target)
                self.assertIn("Solicitei", result)
                startfile.assert_called_once_with(str(target))

    def test_windows_mouse_and_keyboard_are_scoped_and_validate_inputs(self):
        automation = WindowsAutomation()
        with self.assertRaises(WindowsAutomationError):
            automation.type_into_window("", "texto")
        with self.assertRaises(WindowsAutomationError):
            automation.click(-1, 99999)
        window = Mock()
        window.window_text.return_value = "Bloco de Notas"
        desktop = Mock()
        desktop.windows.return_value = [window]
        with patch("pywinauto.Desktop", return_value=desktop), patch("pywinauto.keyboard.send_keys") as send_keys:
            self.assertIn("Bloco de Notas", automation.type_into_window("Bloco de Notas", "Olá PRIA"))
            window.set_focus.assert_called_once_with()
            send_keys.assert_called_once_with("Olá PRIA", with_spaces=True, pause=0.002)
        with patch("pywinauto.mouse.click") as click:
            self.assertIn("(100, 200)", automation.click(100, 200, "left"))
            click.assert_called_once_with(button="left", coords=(100, 200))

    def test_application_search_resolves_one_unambiguous_shortcut(self):
        launcher = ApplicationLauncher()
        self.assertIn("Calculadora", launcher.find_names("calcul"))

    def test_web_open_requires_http_or_https_and_uses_browser(self):
        with patch("pria.tools.web._validate_url"), patch("pria.tools.web.webbrowser.open", return_value=True) as browser:
            message = open_web_page("https://example.com")
            self.assertIn("navegador", message)
            browser.assert_called_once()
            self.assertEqual(browser.call_count, 1)
        with self.assertRaises(WebToolError):
            open_web_page("file:///C:/Windows/win.ini")

    def test_web_extraction_strips_scripts_and_labels_source(self):
        class Response:
            headers = type("Headers", (), {"get_content_type": lambda self: "text/html", "get_content_charset": lambda self: "utf-8"})()
            def __enter__(self): return self
            def __exit__(self, *args): return None
            def geturl(self): return "https://example.com/test"
            def read(self, limit): return b"<html><head><title>Teste</title><script>nao execute</script></head><body><p>Conteudo util</p></body></html>"
        class Opener:
            def open(self, request, timeout): return Response()
        with patch("pria.tools.web._validate_url"), patch("pria.tools.web.build_opener", return_value=Opener()):
            result = extract_web_page("https://example.com/test")
        self.assertIn("Fonte: https://example.com/test", result)
        self.assertIn("Conteudo util", result)
        self.assertNotIn("nao execute", result)

    def test_web_extraction_blocks_local_addresses(self):
        with self.assertRaises(WebToolError):
            open_web_page("http://127.0.0.1:11434")


if __name__ == "__main__":
    unittest.main()
