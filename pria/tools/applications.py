"""Launch allowlisted Windows programs and Start Menu shortcuts; never parse shell input."""

from __future__ import annotations

import os
import platform
from pathlib import Path


class ApplicationToolError(RuntimeError):
    pass


class ApplicationLauncher:
    # Fixed executable names only. User input is never interpreted as a shell command.
    APPLICATIONS = {
        "bloco de notas": "notepad.exe",
        "notepad": "notepad.exe",
        "explorador": "explorer.exe",
        "explorer": "explorer.exe",
        "calculadora": "calc.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "painel de controle": "control.exe",
        "control": "control.exe",
    }

    def names(self) -> list[str]:
        names = {"Bloco de Notas", "Explorador", "Calculadora", "Paint", "Painel de Controle"}
        for shortcut in self._shortcuts():
            names.add(shortcut.stem)
        return sorted(names, key=str.casefold)

    def find_names(self, query: str = "") -> list[str]:
        names = self.names()
        needle = query.strip().casefold()
        return [name for name in names if not needle or needle in name.casefold()]

    @staticmethod
    def _shortcuts() -> list[Path]:
        roots = [
            Path(os.environ.get("APPDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
            Path(os.environ.get("PROGRAMDATA", "")) / "Microsoft/Windows/Start Menu/Programs",
        ]
        shortcuts = []
        for root in roots:
            if root.is_dir():
                try:
                    shortcuts.extend(root.rglob("*.lnk"))
                except OSError:
                    continue
        return shortcuts[:2000]

    def _find_shortcut(self, name: str) -> Path | None:
        wanted = name.strip().casefold()
        return next((shortcut for shortcut in self._shortcuts() if shortcut.stem.casefold() == wanted), None)

    def open(self, name: str) -> str:
        if platform.system() != "Windows":
            raise ApplicationToolError("A abertura de aplicativos desta fase é específica do Windows.")
        executable = self.APPLICATIONS.get(name.strip().casefold())
        shortcut = None if executable else self._find_shortcut(name)
        if executable is None and shortcut is None:
            matches = self.find_names(name)
            if len(matches) == 1:
                shortcut = self._find_shortcut(matches[0])
            elif len(matches) > 1:
                raise ApplicationToolError("Encontrei mais de um aplicativo parecido: " + ", ".join(matches[:20]) + ". Informe o nome exato.")
        if executable is None and shortcut is None:
            raise ApplicationToolError("Não encontrei esse aplicativo nos atalhos do menu Iniciar. Use /apps para consultar.")
        try:
            os.startfile(executable or str(shortcut))  # type: ignore[attr-defined]
        except OSError as exc:
            raise ApplicationToolError(f"Falha ao abrir {name}: {exc}") from exc
        return f"Solicitei ao Windows a abertura de {name}."

    def open_path(self, path: str | Path) -> str:
        if platform.system() != "Windows":
            raise ApplicationToolError("A abertura de arquivos desta fase é específica do Windows.")
        target = Path(path).expanduser()
        if not target.exists():
            raise ApplicationToolError(f"O caminho não existe ou não está acessível: {target}")
        try:
            os.startfile(str(target))  # type: ignore[attr-defined]
        except OSError as exc:
            raise ApplicationToolError(f"Falha ao abrir {target}: {exc}") from exc
        return f"Solicitei ao Windows a abertura de {target}."
