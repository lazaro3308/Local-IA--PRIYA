"""Install user-level Windows shortcuts for Priya; no admin rights or persistence."""
from __future__ import annotations

import sys
from pathlib import Path

import win32com.client


PROJECT = Path(__file__).resolve().parents[1]
ICON = PROJECT / "assets" / "priya_arasaka.ico"


def install_shortcut(shell, folder: Path, name: str, pythonw: Path) -> Path:
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.lnk"
    shortcut = shell.CreateShortcut(str(path))
    shortcut.TargetPath = str(pythonw)
    shortcut.Arguments = "-m pria.interface.desktop"
    shortcut.WorkingDirectory = str(PROJECT)
    shortcut.Description = "Priya — assistente local privado"
    shortcut.IconLocation = str(ICON) if ICON.is_file() else f"{pythonw},0"
    shortcut.Save()
    if not path.is_file() or path.stat().st_size < 100:
        raise RuntimeError(f"O Windows não confirmou a criação do atalho: {path}")
    return path


def main() -> int:
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    if not pythonw.is_file():
        pythonw = Path(sys.executable)
    shell = win32com.client.Dispatch("WScript.Shell")
    desktop = Path(shell.SpecialFolders("Desktop"))
    programs = Path(shell.SpecialFolders("Programs")) / "Priya"
    # Remove only the two legacy links created by the previous installer.
    legacy_links = (desktop / "PRIA.lnk", Path(shell.SpecialFolders("Programs")) / "PRIA" / "PRIA.lnk")
    for old_link in legacy_links:
        if old_link.is_file():
            old_link.unlink()
    if not ICON.is_file():
        raise RuntimeError(f"Ícone da Priya ausente: {ICON}. Gere-o com scripts\\create_app_icon.py.")
    shortcuts = [
        install_shortcut(shell, desktop, "Priya", pythonw),
        install_shortcut(shell, programs, "Priya", pythonw),
    ]
    print("Priya instalada para o usuário atual; não são necessários privilégios de administrador.")
    for shortcut in shortcuts:
        print(f"Atalho verificado: {shortcut}")
    print(f"Ícone configurado: {ICON}")
    print("Abra Priya pela Área de Trabalho ou pelo menu Iniciar > Priya.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
