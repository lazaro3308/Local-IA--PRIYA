import unittest
from unittest.mock import patch

from pria.tools.system_monitor import _gb, system_report


class SystemMonitorTests(unittest.TestCase):
    def test_formats_binary_gigabytes(self):
        self.assertEqual(_gb(1024 ** 3), "1.0 GB")

    def test_report_uses_local_measurements_and_lists_gpu(self):
        with patch("pria.tools.system_monitor._memory_status", return_value=(16 * 1024**3, 6 * 1024**3)), \
             patch("pria.tools.system_monitor._gpu_description", return_value=["GPU de teste"]):
            report = system_report()
        self.assertIn("Memória RAM: 16.0 GB total; 10.0 GB em uso; 6.0 GB disponível", report)
        self.assertIn("GPU(s): GPU de teste", report)
        self.assertIn("Processador:", report)
        self.assertIn("Disco do sistema", report)
        self.assertIn("Leitura feita em:", report)

    def test_nvidia_vram_is_included_when_nvidia_smi_reports_it(self):
        from unittest.mock import Mock

        with patch("pria.tools.system_monitor.os.name", "nt"), \
             patch("pria.tools.system_monitor.shutil.which", return_value="nvidia-smi.exe"), \
             patch("pria.tools.system_monitor.subprocess.run", return_value=Mock(
                 returncode=0, stdout="NVIDIA GeForce MX150, 4096 MiB\n"
             )):
            from pria.tools.system_monitor import _gpu_description
            self.assertEqual(_gpu_description(), ["NVIDIA GeForce MX150, 4096 MiB"])


if __name__ == "__main__":
    unittest.main()

