"""Small dependency/model/runtime diagnostic for Windows 10 installs."""
from __future__ import annotations

import importlib.util
import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path

from pria.voice.speech_to_text import default_model_dir
from pria.voice.text_to_speech import voice_path


def main() -> int:
    print("=== Diagnóstico PRIA local ===")
    print(f"Sistema: {platform.platform()}")
    print(f"Python: {sys.version.split()[0]} ({sys.executable})")
    print(f"CPU: {platform.processor() or os.environ.get('PROCESSOR_IDENTIFIER', 'indisponível')}")
    print(f"Processadores lógicos: {os.cpu_count() or 'indisponível'}")
    try:
        import ctypes
        class MemoryStatus(ctypes.Structure):
            _fields_ = [("length", ctypes.c_ulong), ("memory_load", ctypes.c_ulong), ("total_phys", ctypes.c_ulonglong), ("avail_phys", ctypes.c_ulonglong), ("total_page", ctypes.c_ulonglong), ("avail_page", ctypes.c_ulonglong), ("total_virtual", ctypes.c_ulonglong), ("avail_virtual", ctypes.c_ulonglong), ("avail_extended", ctypes.c_ulonglong)]
        status = MemoryStatus()
        status.length = ctypes.sizeof(status)
        if ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(status)):
            print(f"RAM física: {status.total_phys / 1024**3:.1f} GiB total; {status.avail_phys / 1024**3:.1f} GiB livre")
    except Exception:
        print("RAM física: consulta indisponível")
    try:
        usage = shutil.disk_usage(Path.cwd().anchor or ".")
        print(f"Disco do projeto: {usage.free / 1024**3:.1f} GiB livre")
    except OSError as exc:
        print(f"Disco: consulta falhou ({exc})")
    gpu = shutil.which("nvidia-smi")
    if gpu:
        try:
            result = subprocess.run([gpu, "--query-gpu=name,memory.total", "--format=csv,noheader"], capture_output=True, text=True, timeout=5, check=False)
            print("GPU NVIDIA: " + (result.stdout.strip() or "não detectada por nvidia-smi"))
        except Exception as exc:
            print(f"GPU NVIDIA: consulta falhou ({exc})")
    else:
        print("GPU NVIDIA: nvidia-smi não encontrado; GPU dedicada não confirmada")
    for module in ("fitz", "docx", "sounddevice", "vosk", "piper", "pywinauto"):
        print(f"Dependência {module}: {'OK' if importlib.util.find_spec(module) else 'ausente'}")
    print(f"Vosk pt-BR: {'OK' if (default_model_dir() / 'final.mdl').is_file() else 'ausente'} ({default_model_dir()})")
    print(f"Piper pt-BR: {'OK' if voice_path().is_file() else 'ausente'} ({voice_path()})")
    ollama = shutil.which("ollama")
    if ollama:
        try:
            result = subprocess.run([ollama, "list"], capture_output=True, text=True, timeout=8, check=False)
            print("Modelos Ollama locais:\n" + (result.stdout.strip() or result.stderr.strip() or "nenhum listado"))
        except Exception as exc:
            print(f"Ollama: consulta falhou ({exc})")
    else:
        print("Ollama: executável não encontrado no PATH")
    try:
        import sounddevice as sd
        devices = [str(item["name"]) for item in sd.query_devices() if item["max_input_channels"] > 0]
        print("Entradas de áudio: " + (", ".join(dict.fromkeys(devices)) if devices else "nenhuma detectada"))
    except Exception as exc:
        print(f"Entradas de áudio: consulta indisponível ({exc})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
