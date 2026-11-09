"""Read-only local file tools used by the PRIA terminal commands."""

from __future__ import annotations

import fnmatch
import os
import shutil
from pathlib import Path


class FileToolError(RuntimeError):
    pass


class ConfirmationRequired(FileToolError):
    pass


class FileTools:
    """Read and search files the current Windows user can access."""

    MAX_RESULTS = 200
    MAX_VISITED = 50_000
    MAX_TEXT_BYTES = 2 * 1024 * 1024
    TEXT_EXTENSIONS = {
        ".txt", ".md", ".csv", ".json", ".py", ".ps1", ".bat", ".cmd",
        ".log", ".ini", ".yaml", ".yml", ".toml", ".xml", ".html", ".css",
        ".js", ".ts", ".sql", ".rst",
    }

    def list_directory(self, path: str | Path, limit: int = 100) -> list[Path]:
        folder = Path(path).expanduser()
        if not folder.exists() or not folder.is_dir():
            raise FileToolError(f"A pasta não existe ou não pode ser acessada: {folder}")
        try:
            return sorted(folder.iterdir(), key=lambda item: (not item.is_dir(), item.name.casefold()))[:limit]
        except OSError as exc:
            raise FileToolError(f"Não foi possível listar {folder}: {exc}") from exc

    def search_files(self, root: str | Path, pattern: str, limit: int = MAX_RESULTS) -> tuple[list[Path], bool]:
        folder = Path(root).expanduser()
        if not folder.exists() or not folder.is_dir():
            raise FileToolError(f"A pasta não existe ou não pode ser acessada: {folder}")
        needle = pattern.casefold()
        if not needle:
            raise FileToolError("Informe parte do nome ou um padrão, por exemplo *.pdf.")

        found: list[Path] = []
        visited = 0
        incomplete = False

        def note_unreadable(_error: OSError) -> None:
            nonlocal incomplete
            incomplete = True

        for current, dirs, files in os.walk(folder, followlinks=False, onerror=note_unreadable):
            dirs[:] = [name for name in dirs if not (Path(current) / name).is_symlink()]
            for name in files:
                visited += 1
                if visited > self.MAX_VISITED:
                    return found, True
                if fnmatch.fnmatch(name.casefold(), needle) or needle in name.casefold():
                    found.append(Path(current) / name)
                    if len(found) >= limit:
                        return found, True
        return found, incomplete

    def read_text(self, path: str | Path) -> str:
        file_path = Path(path).expanduser()
        if not file_path.exists() or not file_path.is_file():
            raise FileToolError(f"O arquivo não existe ou não é um arquivo: {file_path}")
        if file_path.suffix.casefold() not in self.TEXT_EXTENSIONS:
            raise FileToolError(f"Formato de texto não habilitado nesta fase: {file_path.suffix or '(sem extensão)'}")
        try:
            size = file_path.stat().st_size
            if size > self.MAX_TEXT_BYTES:
                raise FileToolError("Arquivo maior que 2 MiB; leitura bloqueada para evitar uso excessivo de memória.")
            return file_path.read_text(encoding="utf-8-sig")
        except UnicodeDecodeError as exc:
            raise FileToolError("O arquivo não está em UTF-8 e não foi lido.") from exc
        except OSError as exc:
            raise FileToolError(f"Não foi possível ler {file_path}: {exc}") from exc

    def read_document(self, path: str | Path) -> str:
        file_path = Path(path).expanduser()
        if file_path.suffix.casefold() in {".pdf", ".docx"}:
            from pria.tools.documents import DocumentTools
            return DocumentTools().read(file_path)
        return self.read_text(file_path)

    @staticmethod
    def _destination(path: str | Path) -> Path:
        target = Path(path).expanduser()
        if not target.parent.exists() or not target.parent.is_dir():
            raise FileToolError(f"A pasta de destino não existe ou não está acessível: {target.parent}")
        if target.exists():
            raise FileToolError(f"O destino já existe; não sobrescrevi: {target}")
        return target

    def create_directory(self, path: str | Path) -> str:
        target = self._destination(path)
        try:
            target.mkdir()
        except OSError as exc:
            raise FileToolError(f"Não foi possível criar a pasta {target}: {exc}") from exc
        return f"Pasta criada: {target}"

    def create_text_file(self, path: str | Path, content: str) -> str:
        target = self._destination(path)
        if len(content.encode("utf-8")) > self.MAX_TEXT_BYTES:
            raise FileToolError("O conteúdo excede 2 MiB.")
        try:
            with target.open("x", encoding="utf-8", newline="") as stream:
                stream.write(content)
        except OSError as exc:
            raise FileToolError(f"Não foi possível criar {target}: {exc}") from exc
        return f"Arquivo criado: {target}"

    def copy_path(self, source: str | Path, destination: str | Path, confirmed: bool = False) -> str:
        src = Path(source).expanduser()
        if not src.exists():
            raise FileToolError(f"A origem não existe ou não está acessível: {src}")
        dst = self._destination(destination)
        if src.is_dir():
            if not confirmed:
                raise ConfirmationRequired(f"Copiar a pasta e seu conteúdo requer confirmação: {src} -> {dst}")
            try:
                shutil.copytree(src, dst)
            except OSError as exc:
                raise FileToolError(f"Falha ao copiar a pasta: {exc}") from exc
        else:
            try:
                shutil.copy2(src, dst)
            except OSError as exc:
                raise FileToolError(f"Falha ao copiar o arquivo: {exc}") from exc
        return f"Cópia criada: {dst}"

    def move_path(self, source: str | Path, destination: str | Path, confirmed: bool = False) -> str:
        src = Path(source).expanduser()
        if not src.exists():
            raise FileToolError(f"A origem não existe ou não está acessível: {src}")
        dst = self._destination(destination)
        if src.is_dir() and not confirmed:
            raise ConfirmationRequired(f"Mover a pasta e todo o conteúdo requer confirmação: {src} -> {dst}")
        try:
            shutil.move(str(src), str(dst))
        except OSError as exc:
            raise FileToolError(f"Falha ao mover o caminho: {exc}") from exc
        return f"Movido: {src} -> {dst}"

    def rename_path(self, source: str | Path, new_name: str) -> str:
        src = Path(source).expanduser()
        if not src.exists():
            raise FileToolError(f"A origem não existe ou não está acessível: {src}")
        if not new_name or Path(new_name).name != new_name or new_name in {".", ".."}:
            raise FileToolError("Informe apenas um nome de arquivo ou pasta, sem caminho.")
        dst = src.with_name(new_name)
        if dst.exists():
            raise FileToolError(f"O destino já existe; não sobrescrevi: {dst}")
        try:
            src.rename(dst)
        except OSError as exc:
            raise FileToolError(f"Falha ao renomear: {exc}") from exc
        return f"Renomeado: {src.name} -> {dst.name}"

    def delete_path(self, path: str | Path, confirmed: bool = False) -> str:
        target = Path(path).expanduser()
        if not target.exists():
            raise FileToolError(f"O caminho não existe ou não está acessível: {target}")
        if not confirmed:
            raise ConfirmationRequired(f"Confirme a exclusão deste item: {target}")
        try:
            if target.is_dir():
                target.rmdir()  # Deliberately refuses non-empty directories.
            else:
                target.unlink()
        except OSError as exc:
            raise FileToolError(f"Falha ao excluir. Pastas com conteúdo não são apagadas nesta versão: {exc}") from exc
        return f"Excluído: {target}"


def format_entries(entries: list[Path]) -> str:
    rows = []
    for entry in entries:
        try:
            suffix = "[pasta]" if entry.is_dir() else f"{entry.stat().st_size} bytes"
        except OSError:
            suffix = "[sem acesso]"
        rows.append(f"{entry.name}  {suffix}")
    return "\n".join(rows) if rows else "(nenhum resultado)"
