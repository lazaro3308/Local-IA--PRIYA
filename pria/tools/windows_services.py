"""Read and narrowly control Windows services as the current user."""
from __future__ import annotations

import os
import re
import shutil
import subprocess
import time
import ctypes
from pathlib import Path


class ServiceControlError(RuntimeError):
    pass


class WindowsServices:
    STATES = {
        "1": "STOPPED", "2": "START_PENDING", "3": "STOP_PENDING", "4": "RUNNING",
        "5": "CONTINUE_PENDING", "6": "PAUSE_PENDING", "7": "PAUSED",
    }

    def _sc(self, *arguments: str) -> tuple[int, str]:
        executable = shutil.which("sc.exe")
        if not executable:
            root = os.environ.get("SystemRoot", r"C:\Windows")
            executable = str(Path(root) / "System32" / "sc.exe")
        try:
            encoding = f"cp{ctypes.windll.kernel32.GetOEMCP()}"
            result = subprocess.run(
                [executable, *arguments], capture_output=True, text=True,
                encoding=encoding, errors="replace", timeout=20, check=False,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
            )
        except (OSError, subprocess.TimeoutExpired) as exc:
            raise ServiceControlError(f"sc.exe falhou: {exc}") from exc
        return result.returncode, (result.stdout + "\n" + result.stderr).strip()

    @classmethod
    def parse_services(cls, output: str) -> list[dict[str, str]]:
        services = []
        for block in re.split(r"(?=^\s*(?:SERVICE_NAME|NOME_DO_SERVIÇO)\s*:)", output, flags=re.M | re.I):
            # sc.exe localizes its labels to the Windows display language.
            name = re.search(r"^\s*(?:SERVICE_NAME|NOME_DO_SERVIÇO)\s*:\s*(.+)$", block, flags=re.M | re.I)
            if not name:
                continue
            display = re.search(r"^\s*(?:DISPLAY_NAME|NOME_PARA_EXIBIÇÃO)\s*:\s*(.+)$", block, flags=re.M | re.I)
            state = re.search(r"^\s*(?:STATE|ESTADO)\s*:\s*(\d+)\s+([A-Z_]+)", block, flags=re.M | re.I)
            code = state.group(1) if state else "?"
            services.append({
                "name": name.group(1).strip(),
                "display_name": display.group(1).strip() if display else name.group(1).strip(),
                "state": cls.STATES.get(code, state.group(2).upper() if state else "UNKNOWN"),
            })
        return services

    def list_services(self, query: str = "", limit: int = 60) -> list[dict[str, str]]:
        code, output = self._sc("query", "state=", "all")
        if code:
            raise ServiceControlError(output[-1200:] or f"sc.exe retornou código {code}.")
        needle = query.casefold().strip()
        rows = self.parse_services(output)
        if needle:
            rows = [row for row in rows if needle in row["name"].casefold() or needle in row["display_name"].casefold()]
        return rows[:max(1, min(limit, 100))]

    def _resolve(self, service: str) -> dict[str, str]:
        requested = service.strip()
        if not requested or len(requested) > 256:
            raise ServiceControlError("Informe o nome ou o nome de exibição do serviço.")
        rows = self.list_services(requested, limit=100)
        exact = [row for row in rows if row["name"].casefold() == requested.casefold()
                 or row["display_name"].casefold() == requested.casefold()]
        matches = exact or rows
        if not matches:
            raise ServiceControlError(f"Não encontrei o serviço '{requested}'.")
        if len(matches) != 1:
            labels = ", ".join(f"{row['display_name']} [{row['name']}]" for row in matches[:8])
            raise ServiceControlError(f"Nome ambíguo; especifique o nome exato: {labels}")
        return matches[0]

    def status(self, service: str) -> str:
        row = self._resolve(service)
        return f"{row['display_name']} [{row['name']}]: {row['state']}"

    def _change(self, service: str, action: str, expected: str) -> str:
        row = self._resolve(service)
        if row["state"] == expected:
            return f"Nenhuma mudança: {row['display_name']} já está {expected}."
        code, output = self._sc(action, row["name"])
        if code:
            raise ServiceControlError(f"O Windows recusou {action} para {row['display_name']}: {output[-900:]}")
        deadline = time.monotonic() + 12
        state = "UNKNOWN"
        while time.monotonic() < deadline:
            code, status_output = self._sc("query", row["name"])
            if code:
                break
            parsed = self.parse_services(status_output)
            state = parsed[0]["state"] if parsed else "UNKNOWN"
            if state == expected:
                return f"Verificado: {row['display_name']} agora está {expected}."
            if state not in {"START_PENDING", "STOP_PENDING", "CONTINUE_PENDING", "PAUSE_PENDING"}:
                break
            time.sleep(0.5)
        raise ServiceControlError(f"O Windows aceitou a solicitação, mas o estado final não foi confirmado (estado: {state}).")

    def start(self, service: str) -> str:
        return self._change(service, "start", "RUNNING")

    def stop(self, service: str) -> str:
        return self._change(service, "stop", "STOPPED")
