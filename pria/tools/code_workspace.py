"""Generate one local source file and open it in the installed Visual Studio Code."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from collections.abc import Callable
from pathlib import Path

from pria.core.local_model import LocalChat


class CodeWorkspaceError(RuntimeError):
    pass


class CodeWorkspace:
    EXTENSIONS = {
        "python": ".py", "javascript": ".js", "typescript": ".ts", "html": ".html",
        "css": ".css", "sql": ".sql", "powershell": ".ps1", "c#": ".cs", "csharp": ".cs",
    }
    GENERIC_TERMS = {
        "priya", "crie", "criar", "faça", "faca", "escreva", "gere", "um", "uma", "codigo",
        "código", "programa", "script", "no", "na", "visual", "studio", "code", "vscode", "para",
        "mim", "por", "favor", "quero", "preciso", "desenvolva", "arquivo", "novo", "nova",
    }

    def __init__(self, chat: LocalChat, apps, root: Path | None = None):
        self.chat = chat
        self.apps = apps
        documents = Path(os.environ.get("USERPROFILE", Path.home())) / "Documents"
        self.root = (root or documents / "PriyaProjects").expanduser().resolve()

    @classmethod
    def has_specific_requirements(cls, text: str) -> bool:
        words = re.findall(r"[\w+#.-]+", text.casefold())
        meaningful = [word for word in words if word not in cls.GENERIC_TERMS]
        return len(meaningful) >= 2

    @staticmethod
    def _code_only(text: str) -> str:
        code = text.strip()
        match = re.fullmatch(r"```(?:[\w+#.-]+)?\s*\n?(.*?)\n?```", code, re.DOTALL)
        if match:
            code = match.group(1).strip()
        if not code:
            raise CodeWorkspaceError("O modelo local não retornou código; nenhum arquivo foi criado.")
        return code + "\n"

    @staticmethod
    def _find_vscode() -> Path | None:
        executable = shutil.which("code.exe")
        candidates = [Path(executable)] if executable else []
        local = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        program_files = Path(os.environ.get("ProgramFiles", r"C:\Program Files"))
        candidates.extend((
            local / "Programs/Microsoft VS Code/Code.exe",
            program_files / "Microsoft VS Code/Code.exe",
        ))
        return next((candidate for candidate in candidates if candidate.is_file()), None)

    def create_and_open(
        self,
        file_name: str,
        language: str,
        requirements: str,
        progress: Callable[[str], None] | None = None,
    ) -> str:
        language_key = language.strip().casefold()
        extension = self.EXTENSIONS.get(language_key)
        if extension is None:
            raise CodeWorkspaceError("Linguagem não suportada nesta ação. Disponíveis: Python, JavaScript, TypeScript, HTML, CSS, SQL, PowerShell e C#.")
        stem = Path(file_name.strip()).stem
        if not stem or stem in {".", ".."} or not re.fullmatch(r"[\w -]{1,50}", stem, re.UNICODE):
            raise CodeWorkspaceError("Nome de arquivo inválido; use apenas letras, números, espaços, hífen ou sublinhado.")
        if not self.has_specific_requirements(requirements):
            raise CodeWorkspaceError("Antes de criar, me diga o que o programa deve fazer. Por exemplo: ‘crie uma calculadora em Python que soma, subtrai e salva o histórico’. Ainda não gravei nenhum arquivo.")

        target = self.root / f"{stem}{extension}"
        if target.exists():
            raise CodeWorkspaceError(f"O arquivo já existe; não sobrescrevi: {target}. Escolha outro nome ou peça para abrir/editar o existente.")
        prompt = (
            f"Escreva um único arquivo de código em {language_key}, em português quando houver textos para o usuário.\n"
            f"Requisitos solicitados pelo proprietário: {requirements.strip()}\n\n"
            "Retorne apenas o conteúdo integral do arquivo, sem Markdown, prefácio ou explicação. "
            "Produza uma implementação pequena, funcional, legível e sem dependências externas desnecessárias. "
            "Não execute comandos, não altere outros arquivos e não inclua conteúdo malicioso."
        )
        generated = self._code_only(
            self.chat.reply([], prompt, on_token=progress, response_token_limit=1000, temperature=0.15)
        )
        if len(generated.encode("utf-8")) > 2 * 1024 * 1024:
            raise CodeWorkspaceError("O código gerado excedeu o limite de 2 MiB; nenhum arquivo foi criado.")
        if extension == ".py":
            try:
                compile(generated, str(target), "exec")
            except SyntaxError as exc:
                raise CodeWorkspaceError(f"O modelo gerou Python inválido na linha {exc.lineno}; nenhum arquivo foi criado: {exc.msg}") from exc

        try:
            self.root.mkdir(parents=True, exist_ok=True)
            with target.open("x", encoding="utf-8", newline="") as stream:
                stream.write(generated)
        except FileExistsError as exc:
            raise CodeWorkspaceError(f"O arquivo apareceu durante a criação; preservei o existente: {target}") from exc
        except OSError as exc:
            raise CodeWorkspaceError(f"Não consegui criar o arquivo {target}: {exc}") from exc

        executable = self._find_vscode()
        try:
            if executable:
                subprocess.Popen([str(executable), "--reuse-window", str(target)], close_fds=True)
                return f"Código criado e o Visual Studio Code recebeu a solicitação para abrir: {target}. Não executei o código."
            opened = self.apps.open_path(target)
            return f"Código criado em {target}. O Visual Studio Code não foi localizado diretamente; pedi ao Windows para abrir pelo aplicativo associado. Resultado: {opened}. Não executei o código."
        except Exception as exc:
            return f"Código criado e verificado em {target}, mas não consegui abrir o editor: {exc}. O arquivo permanece salvo e não foi executado."
