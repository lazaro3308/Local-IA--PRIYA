"""Text interface for the local-model PRIA assistant."""

from __future__ import annotations

import shlex
import unicodedata
import uuid
from pathlib import Path

from pria.config import load_settings
from pria.core.assistant import Assistant
from pria.core.agent import LocalAgent
from pria.core.calculator import answer_simple_math
from pria.core.local_model import LocalChat, LocalModelError
from pria.core.natural_commands import execute_obvious_local_request, requests_local_action
from pria.memory.database import LocalMemory
from pria.tools.applications import ApplicationLauncher, ApplicationToolError
from pria.tools.files import FileToolError, FileTools, format_entries
from pria.tools.powershell import PowerShellError, PowerShellTool
from pria.tools.web import WebToolError, extract_web_page, open_web_page
from pria.tools.windows_automation import WindowsAutomation, WindowsAutomationError


def execute_command(text: str, assistant: Assistant, files: FileTools, apps: ApplicationLauncher, confirm=None) -> str:
    """Dispatch explicit local commands; never interprets free-form text as code."""
    try:
        parts = shlex.split(text, posix=False)
    except ValueError as exc:
        return f"Erro ao ler argumentos: {exc}"
    if not parts:
        return ""
    command = parts[0].casefold()
    args = parts[1:]
    try:
        if command in {"/ajuda", "/help", "/sobre", "/about"}:
            return assistant.respond(text)
        if command == "/apps":
            return "Aplicativos disponíveis: " + ", ".join(apps.names())
        if command == "/janelas":
            return "Janelas visíveis:\n" + "\n".join(WindowsAutomation().list_windows())
        if command == "/ativar-janela":
            title = " ".join(args).strip('"')
            if not title:
                return 'Uso: /ativar-janela "trecho único do título"'
            return WindowsAutomation().activate_window(title)
        if command == "/fechar-janela":
            title = " ".join(args).strip('"')
            if not title:
                return 'Uso: /fechar-janela "trecho único do título". A ação pede confirmação.'
            if confirm is None or not confirm(f"Fechar a janela '{title}'? O programa pode pedir para salvar alterações."):
                return "Fechamento cancelado."
            return WindowsAutomation().close_window(title)
        if command == "/digitar":
            if len(args) != 2:
                return 'Uso: /digitar "título da janela" "texto". A PRIA pedirá confirmação antes de digitar.'
            title, value = (item.strip('"') for item in args)
            if confirm is None or not confirm(f"Digitar este texto na janela '{title}'?\n\n{value[:500]}"):
                return "Digitação cancelada."
            return WindowsAutomation().type_into_window(title, value)
        if command == "/clique":
            if len(args) not in {2, 3}:
                return "Uso: /clique <x> <y> [left|right|double]. A PRIA pedirá confirmação."
            try:
                x, y = int(args[0]), int(args[1])
            except ValueError:
                return "Coordenadas precisam ser números inteiros."
            button = args[2].casefold() if len(args) == 3 else "left"
            if confirm is None or not confirm(f"Enviar clique {button} na tela na coordenada ({x}, {y})?"):
                return "Clique cancelado."
            return WindowsAutomation().click(x, y, button)
        if command == "/abrir-app":
            if not args:
                return "Uso: /abrir-app <nome>. Digite /apps para listar os nomes disponíveis."
            return apps.open(" ".join(args).strip('"'))
        if command == "/abrir":
            if not args:
                return "Uso: /abrir <caminho de arquivo ou pasta>."
            return apps.open_path(" ".join(args).strip('"'))
        if command == "/web":
            if len(args) != 1:
                return "Uso: /web <URL http ou https>. O site abre no navegador padrão e requer internet."
            return open_web_page(args[0].strip('"'))
        if command == "/listar":
            folder = " ".join(args).strip('"') if args else str(Path.home())
            return format_entries(files.list_directory(folder))
        if command == "/buscar":
            if not args:
                return "Uso: /buscar <nome ou padrão> [pasta]. Exemplo: /buscar *.pdf \"C:\\Users\\Ana\\Documents\""
            pattern = args[0].strip('"')
            root = " ".join(args[1:]).strip('"') if len(args) > 1 else str(Path.home())
            matches, truncated = files.search_files(root, pattern)
            result = "\n".join(str(path) for path in matches) or "(nenhum resultado)"
            if truncated:
                result += "\nBusca possivelmente incompleta: atingiu um limite ou encontrou pastas sem permissão de leitura."
            return result
        if command == "/ler":
            if not args:
                return "Uso: /ler <caminho de arquivo de texto>."
            return files.read_document(" ".join(args).strip('"'))
        if command in {"/ler-web", "/extrair-web"}:
            if len(args) != 1:
                return f"Uso: {command} <URL pública http(s)>"
            return extract_web_page(args[0].strip('"'))
        if command == "/criar-pasta":
            if not args:
                return "Uso: /criar-pasta <caminho>."
            return files.create_directory(" ".join(args).strip('"'))
        if command == "/criar-arquivo":
            if len(args) < 2:
                return 'Uso: /criar-arquivo "<caminho>" "<conteúdo>".'
            return files.create_text_file(args[0].strip('"'), " ".join(args[1:]).strip('"'))
        if command in {"/copiar", "/mover"}:
            if len(args) != 2:
                return f'Uso: {command} "<origem>" "<destino>".'
            source, destination = (item.strip('"') for item in args)
            is_folder = Path(source).expanduser().is_dir()
            confirmed = False
            if is_folder:
                if confirm is None or not confirm(f"A operação inclui a pasta e seu conteúdo: {source} -> {destination}"):
                    return "Operação cancelada; nada foi alterado."
                confirmed = True
            operation = files.copy_path if command == "/copiar" else files.move_path
            return operation(source, destination, confirmed=confirmed)
        if command == "/renomear":
            if len(args) != 2:
                return 'Uso: /renomear "<caminho>" "<novo nome>".'
            return files.rename_path(args[0].strip('"'), args[1].strip('"'))
        if command == "/apagar":
            if not args:
                return 'Uso: /apagar "<caminho>".'
            path = " ".join(args).strip('"')
            if confirm is None or not confirm(f"Apagar este arquivo ou pasta vazia? {path}"):
                return "Exclusão cancelada; nada foi apagado."
            return files.delete_path(path, confirmed=True)
        if command == "/powershell":
            code = " ".join(args).strip('"')
            if not code:
                return 'Uso: /powershell "<comando>". O programa exibirá o comando e pedirá confirmação.'
            if confirm is None or not confirm(f"Executar este comando como usuário atual?\n{code}"):
                return "Comando cancelado; nada foi executado."
            return PowerShellTool().run(code)
        return assistant.respond(text)
    except (FileToolError, ApplicationToolError, WebToolError, PowerShellError, WindowsAutomationError) as exc:
        return f"Não concluído: {exc}"


def format_all_memory(memory: LocalMemory) -> str:
    facts, messages = memory.all_data()
    output = ["Memória local da PRIA", "\nFatos guardados explicitamente:"]
    output.extend(f"- {fact}" for fact in facts)
    if not facts:
        output.append("(nenhum)")
    output.append("\nHistórico completo:")
    output.extend(f"[{created_at}] {role}: {content}" for created_at, role, content in messages)
    if not messages:
        output.append("(nenhuma conversa salva)")
    return "\n".join(output)


def confirm_sensitive_action(description: str) -> bool:
    print(f"\nConfirmação necessária: {description}")
    return input("Digite SIM para confirmar: ").strip().casefold() == "sim"


def is_memory_question(text: str) -> bool:
    normalized = "".join(
        char for char in unicodedata.normalize("NFD", text.casefold())
        if unicodedata.category(char) != "Mn"
    )
    memory_question = "memoria" in normalized and any(
        word in normalized for word in ("minha", "sua", "sabe", "lembra", "mostra", "exibe", "tudo", "qual")
    )
    return memory_question or any(
        phrase in normalized
        for phrase in ("o que voce lembra", "o que sabe sobre mim", "o que voce sabe de mim", "o que voce sabe sobre mim")
    )


def main() -> int:
    try:
        settings = load_settings()
    except (ValueError, OSError) as exc:
        print(f"Configuração da PRIA inválida: {exc}")
        return 2
    assistant = Assistant()
    files = FileTools()
    apps = ApplicationLauncher()
    memory = LocalMemory()
    chat = LocalChat(settings)
    agent = LocalAgent(chat, files, apps)
    session_id = uuid.uuid4().hex
    inherit_history = True
    print(f"PRIA — modelo local {settings.model} | memória SQLite neste computador")
    print("Perguntas em português funcionam offline. Digite /ajuda para ferramentas e /sair para encerrar.\n")
    while True:
        try:
            text = input("Você> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nPRIA encerrada.")
            return 0
        command = text.casefold()
        if command in {"/sair", "/exit", "/quit"}:
            print("PRIA encerrada.")
            return 0
        if command in {"/limpar", "/clear"}:
            print("\x1b[2J\x1b[HPRIA — tela limpa. Digite /ajuda para ver os comandos.\n")
            continue
        if command in {"/novo", "/new"}:
            session_id = uuid.uuid4().hex
            inherit_history = False
            print("Nova conversa iniciada; fatos explícitos guardados continuam disponíveis.\n")
            continue
        if command in {"/memoria", "/memory"} or is_memory_question(text):
            answer = format_all_memory(memory)
            print(f"\n{answer}\n")
            continue
        if command.startswith("/guardar "):
            try:
                memory.remember(text[len("/guardar "):])
                answer = "Memória salva localmente."
            except ValueError as exc:
                answer = f"Não salvei: {exc}"
            print(f"\nPRIA> {answer}\n")
            memory.add_message(session_id, "user", text)
            memory.add_message(session_id, "assistant", answer)
            continue
        if command == "/apagar-memoria":
            confirmation = input("Isso apagará o histórico e fatos guardados. Digite APAGAR MEMORIA para confirmar: ")
            if confirmation.strip().casefold() == "apagar memoria":
                memory.delete_all()
                session_id = uuid.uuid4().hex
                print("Memória local apagada.\n")
            else:
                print("Cancelado; memória preservada.\n")
            continue
        if not text:
            continue

        memory.add_message(session_id, "user", text)
        if text.startswith("/"):
            answer = execute_command(text, assistant, files, apps, confirm_sensitive_action)
        else:
            try:
                answer = answer_simple_math(text)
                if answer is None:
                    answer = execute_obvious_local_request(text, files, apps, confirm_sensitive_action)
                if answer is None:
                    previous = memory.recent_messages(session_id, limit=24)[:-1]
                    if not previous and inherit_history:
                        previous = memory.recent_messages(None, limit=12)[:-1]
                    inherit_history = False
                    if requests_local_action(text):
                        answer = agent.respond(previous, text, facts=memory.all_facts(), confirm=confirm_sensitive_action)
                    else:
                        answer = chat.reply(previous, text, facts=memory.all_facts())
            except LocalModelError as exc:
                answer = f"Não consegui responder: {exc}"
        memory.add_message(session_id, "assistant", answer)
        print(f"\nPRIA> {answer}\n")


if __name__ == "__main__":
    raise SystemExit(main())
