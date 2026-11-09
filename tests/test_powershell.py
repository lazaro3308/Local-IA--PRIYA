import subprocess
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from pria.tools.powershell import PowerShellError, PowerShellTool
from pria.main import execute_command
from pria.core.assistant import Assistant
from pria.tools.applications import ApplicationLauncher
from pria.tools.files import FileTools


class PowerShellToolTests(unittest.TestCase):
    def test_runs_as_current_user_without_shell_and_reports_output(self):
        completed = SimpleNamespace(returncode=0, stdout=b"14\r\n", stderr=b"")
        with patch("pria.tools.powershell.subprocess.run", return_value=completed) as run:
            result = PowerShellTool().run("Get-Date")
        self.assertIn("Código de saída: 0", result)
        self.assertIn("14", result)
        args, kwargs = run.call_args
        self.assertEqual(args[0][-2], "-Command")
        self.assertIn("Get-Date", args[0][-1])
        self.assertEqual(kwargs["timeout"], 30)
        self.assertFalse(kwargs.get("shell", False))

    def test_timeout_is_reported(self):
        with patch("pria.tools.powershell.subprocess.run", side_effect=subprocess.TimeoutExpired("powershell.exe", 30)):
            with self.assertRaises(PowerShellError):
                PowerShellTool().run("Start-Sleep 60")

    def test_empty_command_is_rejected(self):
        with self.assertRaises(PowerShellError):
            PowerShellTool().run("  ")

    def test_terminal_command_is_not_run_when_user_rejects_confirmation(self):
        with patch("pria.main.PowerShellTool.run") as run:
            result = execute_command(
                '/powershell "Get-Date"', Assistant(), FileTools(), ApplicationLauncher(), lambda _q: False
            )
        self.assertIn("cancelado", result.casefold())
        run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
