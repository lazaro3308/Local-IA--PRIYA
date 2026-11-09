"""PowerShell runner with bounded time/output and the current user's privileges."""

from __future__ import annotations

import os
import subprocess


class PowerShellError(RuntimeError):
    pass


class PowerShellTool:
    TIMEOUT_SECONDS = 30
    MAX_OUTPUT_CHARS = 12_000

    def run(self, command: str) -> str:
        if os.name != "nt":
            raise PowerShellError("Esta ferramenta só funciona no Windows.")
        code = command.strip()
        if not code:
            raise PowerShellError("O comando PowerShell está vazio.")
        if len(code) > 8000:
            raise PowerShellError("O comando excede o limite de 8000 caracteres.")
        utf8_wrapper = "$OutputEncoding=[Console]::OutputEncoding=[System.Text.UTF8Encoding]::new(); "
        try:
            completed = subprocess.run(
                ["powershell.exe", "-NoLogo", "-NoProfile", "-NonInteractive", "-Command", utf8_wrapper + code],
                capture_output=True,
                timeout=self.TIMEOUT_SECONDS,
                check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except subprocess.TimeoutExpired as exc:
            raise PowerShellError(f"Comando interrompido após {self.TIMEOUT_SECONDS} segundos.") from exc
        except OSError as exc:
            raise PowerShellError(f"Não foi possível iniciar PowerShell: {exc}") from exc

        stdout = completed.stdout.decode("utf-8", errors="replace").strip()
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        output = "\n".join(part for part in (stdout, stderr) if part)
        if not output:
            output = "(sem saída)"
        if len(output) > self.MAX_OUTPUT_CHARS:
            output = output[:self.MAX_OUTPUT_CHARS] + "\n[saída truncada]"
        return f"Código de saída: {completed.returncode}\n{output}"
