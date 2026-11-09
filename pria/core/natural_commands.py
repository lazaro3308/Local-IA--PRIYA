"""Small transparent Portuguese intent rules for common local actions."""

from __future__ import annotations

import re
import unicodedata
from pathlib import Path

from pria.tools.applications import ApplicationLauncher, ApplicationToolError
from pria.tools.files import FileToolError, FileTools, format_entries
from pria.tools.web import WebToolError, extract_web_page, open_web_page
from pria.tools.windows_automation import WindowsAutomation, WindowsAutomationError
from pria.tools.windows_services import ServiceControlError, WindowsServices


def _argument(value: str) -> str:
    return value.strip().strip('"').strip("'")


def requests_local_action(text: str) -> bool:
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(char) != "Mn"
    )
    action_verbs = (
        "abra", "abre", "abrir", "inicie", "inicia", "iniciar", "execute", "liste", "listar", "mostre",
        "mostra", "ver", "veja", "busque", "buscar", "procure", "encontre", "localize", "pesquise",
        "leia", "ler", "analise", "resuma", "crie", "criar", "copie", "copiar", "mova", "mover",
        "renomeie", "renomear", "apague", "apagar", "exclua", "excluir", "mexa", "mexer", "digite", "escreva", "clique", "feche",
        "pare", "parar", "inicie", "iniciar",
    )
    return any(re.search(rf"\b{re.escape(verb)}\b", normalized) for verb in action_verbs)


def execute_obvious_local_request(text: str, files: FileTools, apps: ApplicationLauncher, confirm=None) -> str | None:
    """Execute only clear, direct requests; return None for ordinary questions."""
    patterns = (
        ("list", re.compile(r"^(?:por favor[, ]*)?(?:liste|listar|mostre|mostra|veja|ver)\s+(?:os?\s+)?(?:arquivos|conte[uú]do|itens)\s+(?:em|na pasta|do diret[oó]rio|de)\s+(.+)$", re.I)),
        ("list", re.compile(r"^(?:por favor[, ]*)?(?:o que tem|quais arquivos existem)\s+(?:em|na pasta|no diret[oó]rio)\s+(.+)$", re.I)),
        ("list_home", re.compile(r"^(?:por favor[, ]*)?(?:liste|listar|mostre|mostra|veja|ver)\s+(?:os?\s+)?(?:arquivos|itens)(?:\s+(?:na minha pasta pessoal|na pasta pessoal|em casa))?\s*[?.!]*$", re.I)),
        ("search", re.compile(r"^(?:por favor[, ]*)?(?:procure|buscar|busque|encontre|localize|pesquise)\s+(.+?)\s+(?:em|na pasta|no diret[oó]rio)\s+(.+)$", re.I)),
        ("read", re.compile(r"^(?:por favor[, ]*)?(?:leia|ler|analise|analisa|resuma)\s+(?:o\s+)?arquivo\s+(.+)$", re.I)),
        ("read_web", re.compile(r"^(?:por favor[, ]*)?(?:leia|resuma|extraia o conte[uú]do de)\s+(?:a\s+)?(?:p[aá]gina|site)\s+(https?://\S+)$", re.I)),
        ("read_web", re.compile(r"^(?:por favor[, ]*)?(?:leia|resuma)\s+(https?://\S+)$", re.I)),
        ("windows_type", re.compile(r"^(?:por favor[, ]*)?(?:digite|escreva)\s+(.+?)\s+na janela\s+(.+)$", re.I)),
        ("windows_click", re.compile(r"^(?:por favor[, ]*)?clique\s+(?:do mouse\s+)?(?:em\s+)?(?:\()?([0-9]{1,5})\s*[, ]\s*([0-9]{1,5})\)?(?:\s+(left|right|double))?$", re.I)),
        ("windows_list", re.compile(r"^(?:por favor[, ]*)?(?:liste|mostre)\s+(?:as\s+)?janelas(?:\s+abertas)?[?.!]*$", re.I)),
        ("windows_activate", re.compile(r"^(?:por favor[, ]*)?(?:ative|traga para frente)\s+(?:a\s+)?janela\s+(.+)$", re.I)),
        ("windows_close", re.compile(r"^(?:por favor[, ]*)?feche\s+(?:a\s+)?janela\s+(.+)$", re.I)),
        ("services_list", re.compile(r"^(?:por favor[, ]*)?(?:liste|mostre|verifique)\s+(?:os?\s+)?servi[cç]os(?:\s+do\s+windows)?[?.!]*$", re.I)),
        ("service_status", re.compile(r"^(?:por favor[, ]*)?(?:qual o )?(?:status|estado|situa[cç][aã]o)\s+(?:do\s+)?servi[cç]o\s+(.+)$", re.I)),
        ("service_start", re.compile(r"^(?:por favor[, ]*)?(?:inicie|iniciar|ligue)\s+(?:o\s+)?servi[cç]o\s+(.+)$", re.I)),
        ("service_stop", re.compile(r"^(?:por favor[, ]*)?(?:pare|parar|interrompa)\s+(?:o\s+)?servi[cç]o\s+(.+)$", re.I)),
        ("open_app", re.compile(r"^(?:por favor[, ]*)?(?:abra|abre|abrir|inicie|inicia|iniciar|execute)\s+(?:o\s+)?(?:app|aplicativo|programa)\s+(.+)$", re.I)),
        ("open_path", re.compile(r"^(?:por favor[, ]*)?(?:abra|abre|abrir)\s+(?:o\s+arquivo|a\s+pasta)\s+(.+)$", re.I)),
        ("open_app_guess", re.compile(r"^(?:por favor[, ]*)?(?:abra|abre|abrir|inicie|inicia|iniciar)\s+(?:o\s+)?([^?.!]+)$", re.I)),
        ("web", re.compile(r"^(?:por favor[, ]*)?(?:abra|abre|acesse|acessa|abrir)\s+(?:o\s+)?site\s+(https?://\S+)$", re.I)),
        ("web", re.compile(r"^(?:por favor[, ]*)?(?:abra|abre|acesse|acessa|abrir)\s+(https?://\S+)$", re.I)),
        ("create_directory", re.compile(r"^(?:por favor[, ]*)?(?:crie|criar)\s+(?:uma?\s+)?pasta\s+(.+)$", re.I)),
        ("create_file", re.compile(r"^(?:por favor[, ]*)?(?:crie|criar)\s+(?:um\s+)?arquivo\s+(.+?)\s+(?:com\s+(?:o\s+)?(?:texto|conte[uú]do)\s+)(.+)$", re.I)),
        ("copy", re.compile(r"^(?:por favor[, ]*)?(?:copie|copiar)\s+(.+?)\s+para\s+(.+)$", re.I)),
        ("move", re.compile(r"^(?:por favor[, ]*)?(?:mova|mover)\s+(.+?)\s+para\s+(.+)$", re.I)),
        ("rename", re.compile(r"^(?:por favor[, ]*)?(?:renomeie|renomear)\s+(.+?)\s+(?:para|como)\s+(.+)$", re.I)),
        ("delete", re.compile(r"^(?:por favor[, ]*)?(?:apague|apagar|exclua|excluir)\s+(.+)$", re.I)),
    )
    for action, pattern in patterns:
        match = pattern.match(text.strip())
        if not match:
            continue
        value = _argument(match.group(1)) if match.lastindex and action != "list_home" else ""
        try:
            if action == "list":
                return format_entries(files.list_directory(value))
            if action == "list_home":
                return format_entries(files.list_directory(Path.home()))
            if action == "search":
                pattern = value
                root = _argument(match.group(2))
                if pattern.casefold() in {"pdf", "pdfs", "arquivos pdf"}:
                    pattern = "*.pdf"
                if pattern.casefold() in {"word", "documentos docx", "docx"}:
                    pattern = "*.docx"
                found, incomplete = files.search_files(root, pattern)
                result = "\n".join(str(item) for item in found) or "(nenhum resultado)"
                if incomplete:
                    result += "\nBusca possivelmente incompleta por limite ou permissões de leitura."
                return result
            if action == "read":
                return files.read_document(value)
            if action == "read_web":
                return extract_web_page(value)
            if action == "windows_list":
                return "Janelas visíveis:\n" + "\n".join(WindowsAutomation().list_windows())
            if action == "windows_activate":
                return WindowsAutomation().activate_window(_argument(match.group(1)))
            if action == "windows_close":
                title = _argument(match.group(1))
                if confirm is None or not confirm(f"Fechar janela '{title}'? O aplicativo pode pedir para salvar alterações."):
                    return "Fechamento cancelado."
                return WindowsAutomation().close_window(title)
            if action == "services_list":
                query = _argument(match.group(1)) if match.lastindex else ""
                rows = WindowsServices().list_services(query)
                return "Serviços Windows:\n" + ("\n".join(
                    f"{row['display_name']} [{row['name']}]: {row['state']}" for row in rows
                ) if rows else "(nenhum serviço encontrado)")
            if action == "service_status":
                return WindowsServices().status(value)
            if action in {"service_start", "service_stop"}:
                verb = "iniciar" if action == "service_start" else "parar"
                if confirm is None or not confirm(f"Confirma {verb} o serviço Windows '{value}' usando sua conta atual?"):
                    return "Operação cancelada; o serviço não foi alterado."
                manager = WindowsServices()
                return manager.start(value) if action == "service_start" else manager.stop(value)
            if action == "windows_type":
                content, title = match.groups()
                if confirm is None or not confirm(f"Digitar na janela '{_argument(title)}'?\n\n{_argument(content)[:500]}"):
                    return "Digitação cancelada."
                return WindowsAutomation().type_into_window(_argument(title), _argument(content))
            if action == "windows_click":
                x, y, button = match.groups()
                button = button or "left"
                if confirm is None or not confirm(f"Enviar clique {button} nas coordenadas ({x}, {y})?"):
                    return "Clique cancelado."
                return WindowsAutomation().click(int(x), int(y), button)
            if action == "open_app":
                return apps.open(value)
            if action == "open_path":
                return apps.open_path(value)
            if action == "open_app_guess":
                names = apps.find_names(value)
                exact = [name for name in names if name.casefold() == value.casefold()]
                matches = exact or names
                if len(matches) != 1:
                    return None
                return apps.open(matches[0])
            if action == "web":
                return open_web_page(value)
            if action == "create_directory":
                return files.create_directory(value)
            if action == "create_file":
                return files.create_text_file(value, _argument(match.group(2)))
            if action in {"copy", "move"}:
                destination = _argument(match.group(2))
                is_folder = Path(value).expanduser().is_dir()
                confirmed = False
                if is_folder:
                    operation = "copiar" if action == "copy" else "mover"
                    if confirm is None or not confirm(f"Confirmar {operation} da pasta e de todo seu conteúdo: {value} -> {destination}"):
                        return "Operação cancelada; nada foi alterado."
                    confirmed = True
                method = files.copy_path if action == "copy" else files.move_path
                return method(value, destination, confirmed=confirmed)
            if action == "rename":
                return files.rename_path(value, _argument(match.group(2)))
            if action == "delete":
                if confirm is None or not confirm(f"Apagar este arquivo ou pasta vazia? {value}"):
                    return "Exclusão cancelada; nada foi apagado."
                return files.delete_path(value, confirmed=True)
        except (FileToolError, ApplicationToolError, WebToolError, WindowsAutomationError) as exc:
            return f"Não concluído: {exc}"
        except ServiceControlError as exc:
            return f"Não concluído: {exc}"
    return None
