import unittest

from pria.tools.windows_services import ServiceControlError, WindowsServices


SPOOLER_RUNNING = """SERVICE_NAME: Spooler
        TYPE               : 10  WIN32_OWN_PROCESS
        STATE              : 4  RUNNING
        WIN32_EXIT_CODE    : 0  (0x0)
SERVICE_NAME: wuauserv
        DISPLAY_NAME       : Windows Update
        STATE              : 1  STOPPED
"""


class FakeServices(WindowsServices):
    def __init__(self, output=SPOOLER_RUNNING):
        self.output = output
        self.calls = []

    def _sc(self, *arguments):
        self.calls.append(arguments)
        if arguments[:1] == ("start",):
            self.output = "SERVICE_NAME: Spooler\nSTATE : 4 RUNNING\n"
            return 0, "START_PENDING"
        if arguments[:1] == ("stop",):
            self.output = "SERVICE_NAME: Spooler\nSTATE : 1 STOPPED\n"
            return 0, "STOP_PENDING"
        return 0, self.output


class WindowsServicesTests(unittest.TestCase):
    def test_parse_and_search_service_names_and_states(self):
        rows = WindowsServices.parse_services(SPOOLER_RUNNING)
        self.assertEqual(rows[0], {"name": "Spooler", "display_name": "Spooler", "state": "RUNNING"})
        self.assertEqual(rows[1]["display_name"], "Windows Update")
        self.assertEqual(rows[1]["state"], "STOPPED")
        manager = FakeServices()
        self.assertEqual(manager.status("Windows Update"), "Windows Update [wuauserv]: STOPPED")

    def test_parse_portuguese_windows_service_labels(self):
        localized = """NOME_DO_SERVIÇO: Spooler
NOME_PARA_EXIBIÇÃO: Spooler de Impressão
        ESTADO              : 4  RUNNING
NOME_DO_SERVIÇO: wuauserv
NOME_PARA_EXIBIÇÃO: Windows Update
        ESTADO              : 1  STOPPED
"""
        rows = WindowsServices.parse_services(localized)
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]["display_name"], "Spooler de Impressão")
        self.assertEqual(rows[1]["state"], "STOPPED")

    def test_start_is_verified_with_status_query(self):
        manager = FakeServices("SERVICE_NAME: Spooler\nSTATE : 1 STOPPED\n")
        answer = manager.start("Spooler")
        self.assertIn("verificado", answer.casefold())
        self.assertIn(("start", "Spooler"), manager.calls)

    def test_ambiguous_service_is_not_changed(self):
        listing = """SERVICE_NAME: update1
        DISPLAY_NAME : Updater
        STATE : 1 STOPPED
SERVICE_NAME: update2
        DISPLAY_NAME : Updater
        STATE : 1 STOPPED
"""
        manager = FakeServices(listing)
        with self.assertRaises(ServiceControlError):
            manager.start("Updater")
        self.assertFalse(any(args[0] == "start" for args in manager.calls))


if __name__ == "__main__":
    unittest.main()
