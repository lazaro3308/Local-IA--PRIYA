"""Read current Windows hardware and storage facts without an LLM."""

from __future__ import annotations

import ctypes
import json
import os
import platform
import shutil
import subprocess
from datetime import datetime
from pathlib import Path


class SystemMonitorError(RuntimeError):
    pass


class _MemoryStatusEx(ctypes.Structure):
    _fields_ = [
        ("dwLength", ctypes.c_ulong),
        ("dwMemoryLoad", ctypes.c_ulong),
        ("ullTotalPhys", ctypes.c_ulonglong),
        ("ullAvailPhys", ctypes.c_ulonglong),
        ("ullTotalPageFile", ctypes.c_ulonglong),
        ("ullAvailPageFile", ctypes.c_ulonglong),
        ("ullTotalVirtual", ctypes.c_ulonglong),
        ("ullAvailVirtual", ctypes.c_ulonglong),
        ("ullAvailExtendedVirtual", ctypes.c_ulonglong),
    ]


def _memory_status() -> tuple[int, int]:
    if os.name != "nt":
        raise SystemMonitorError("A leitura detalhada de memória está disponível nesta versão para Windows.")
    status = _MemoryStatusEx()
    status.dwLength = ctypes.sizeof(status)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
        raise SystemMonitorError("O Windows não conseguiu consultar a memória física.")
    return int(status.ullTotalPhys), int(status.ullAvailPhys)


def _gpu_names() -> list[str]:
    if os.name != "nt":
        return []
    command = (
        "Get-CimInstance Win32_VideoController | "
        "Select-Object -ExpandProperty Name | ConvertTo-Json -Compress"
    )
    try:
        result = subprocess.run(
            ["powershell.exe", "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=8,
            check=False,
            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
        )
    except (OSError, subprocess.TimeoutExpired):
        return []
    if result.returncode != 0 or not result.stdout.strip():
        return []
    try:
        data = json.loads(result.stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, str):
        return [data]
    if isinstance(data, list):
        return [item for item in data if isinstance(item, str)]
    return []


def _gpu_description() -> list[str]:
    """Prefer NVIDIA's exact VRAM report, then fall back to Windows adapter names."""
    if os.name == "nt":
        nvidia_smi = shutil.which("nvidia-smi.exe") or shutil.which("nvidia-smi")
        if nvidia_smi:
            try:
                result = subprocess.run(
                    [nvidia_smi, "--query-gpu=name,memory.total", "--format=csv,noheader"],
                    capture_output=True,
                    text=True,
                    encoding="utf-8",
                    errors="replace",
                    timeout=5,
                    check=False,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                )
                if result.returncode == 0:
                    rows = [line.strip() for line in result.stdout.splitlines() if line.strip()]
                    if rows:
                        return rows
            except (OSError, subprocess.TimeoutExpired):
                pass
    return [f"{name} (VRAM não informada)" for name in _gpu_names()]


def _gb(byte_count: int) -> str:
    return f"{byte_count / (1024 ** 3):.1f} GB"


def system_report() -> str:
    """Return a concise report made only from values read from this computer."""
    total_memory, available_memory = _memory_status()
    root = Path.home().anchor or Path.cwd().anchor
    disk = shutil.disk_usage(root)
    gpus = _gpu_description()
    gpu_text = ", ".join(gpus) if gpus else "não identificado pelo Windows"
    return "\n".join((
        "Informações lidas deste computador:",
        f"Sistema: {platform.system()} {platform.release()} ({platform.version()})",
        f"Processador: {platform.processor() or 'nome não informado pelo Windows'}; {os.cpu_count() or 'núcleos lógicos não informados'} núcleos lógicos",
        f"Memória RAM: {_gb(total_memory)} total; {_gb(total_memory - available_memory)} em uso; {_gb(available_memory)} disponível",
        f"Disco do sistema ({root}): {_gb(disk.total)} total; {_gb(disk.used)} usado; {_gb(disk.free)} livre",
        f"GPU(s): {gpu_text}",
        f"Leitura feita em: {datetime.now().astimezone().strftime('%d/%m/%Y %H:%M:%S %Z')}",
    ))

