"""One-time, explicit download of compact local Portuguese speech models."""
from __future__ import annotations

import json
import os
import shutil
import ssl
import tempfile
import urllib.request
import zipfile
from pathlib import Path

BASE = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local")) / "PRIA"
VOSK_URL = "https://alphacephei.com/vosk/models/vosk-model-small-pt-0.3.zip"
PIPER_BASE = "https://huggingface.co/rhasspy/piper-voices/resolve/v1.0.0/pt/pt_BR/faber/medium"


def download(url: str, path: Path, limit: int) -> None:
    request = urllib.request.Request(url, headers={"User-Agent": "PRIA-local-installer/0.2"})
    total = 0
    import certifi
    tls = ssl.create_default_context(cafile=certifi.where())
    with urllib.request.urlopen(request, timeout=40, context=tls) as source, path.open("wb") as target:
        if source.headers.get("Content-Length") and int(source.headers["Content-Length"]) > limit:
            raise RuntimeError(f"Arquivo maior que o limite: {url}")
        while block := source.read(1024 * 1024):
            total += len(block)
            if total > limit:
                raise RuntimeError(f"Download excedeu o limite: {url}")
            target.write(block)
    if total == 0:
        raise RuntimeError(f"Download vazio: {url}")


def install_vosk(temp: Path) -> None:
    target = BASE / "models" / "vosk-model-small-pt-0.3"
    if (target / "final.mdl").is_file():
        print(f"Vosk já instalado: {target}")
        return
    archive = temp / "vosk.zip"
    download(VOSK_URL, archive, 100 * 1024 * 1024)
    with zipfile.ZipFile(archive) as zipped:
        bad = zipped.testzip()
        if bad:
            raise RuntimeError(f"ZIP inválido: CRC incorreto em {bad}")
        for item in zipped.infolist():
            resolved = (temp / "extract" / item.filename).resolve()
            if temp.resolve() not in resolved.parents:
                raise RuntimeError("ZIP contém caminho de extração inseguro.")
        zipped.extractall(temp / "extract")
    source = temp / "extract" / "vosk-model-small-pt-0.3"
    if not (source / "final.mdl").is_file():
        raise RuntimeError("ZIP Vosk não contém o modelo esperado.")
    target.parent.mkdir(parents=True, exist_ok=True)
    shutil.move(str(source), str(target))
    print(f"Vosk pt-BR instalado: {target}")


def install_piper(temp: Path) -> None:
    target_dir = BASE / "voices"
    model = target_dir / "pt_BR-faber-medium.onnx"
    config = Path(str(model) + ".json")
    if model.is_file() and config.is_file():
        print(f"Piper pt-BR já instalado: {model}")
        return
    target_dir.mkdir(parents=True, exist_ok=True)
    for name, limit in ((model.name, 150 * 1024 * 1024), (config.name, 2 * 1024 * 1024)):
        download(f"{PIPER_BASE}/{name}", temp / name, limit)
    with (temp / config.name).open(encoding="utf-8") as stream:
        voice_config = json.load(stream)
    if voice_config.get("audio", {}).get("sample_rate", 0) <= 0 or (temp / model.name).stat().st_size < 1_000_000:
        raise RuntimeError("Arquivos Piper passaram por tamanho/configuração inválidos.")
    shutil.move(str(temp / model.name), str(model))
    shutil.move(str(temp / config.name), str(config))
    print(f"Piper pt-BR faber-medium instalado: {model}")


def main() -> int:
    print("Os downloads abaixo são únicos e vêm de fontes públicas dos projetos; o uso posterior é offline.")
    print(f"Destino local: {BASE}")
    with tempfile.TemporaryDirectory(prefix="pria-models-") as tmp:
        temp = Path(tmp)
        install_vosk(temp)
        install_piper(temp)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
