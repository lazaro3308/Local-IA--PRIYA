"""Command descriptions and non-model fallbacks for the PRIA shell."""

from __future__ import annotations


class Assistant:
    name = "PRIA"

    def respond(self, text: str) -> str:
        command = text.strip().casefold()
        if command in {"/ajuda", "/help"}:
            return (
                "Comandos: /ajuda, /sobre, /listar [pasta], /buscar <nome ou padrão> [pasta], "
                "/ler <TXT/PDF/DOCX>, /ler-web <URL pública>, /abrir <arquivo ou pasta>, /abrir-app <nome>, "
                "/apps, /janelas, /ativar-janela, /digitar \"janela\" \"texto\", /clique x y [left|right|double], /fechar-janela, /web <URL>, /criar-pasta, /criar-arquivo, /copiar, /mover, /renomear, /apagar, "
                "/powershell, /guardar, /memoria, /apagar-memoria, /novo, /limpar e /sair. Também posso entender pedidos em português livre."
            )
        if command in {"/sobre", "/about"}:
            return (
                "PRIA é um assistente local em desenvolvimento. As respostas livres usam o modelo instalado neste computador e ferramentas locais. "
                "Ela abre aplicativos do menu Iniciar; /janelas, /ativar-janela, /digitar e /clique controlam janelas; /fechar-janela pede confirmação. /ler-web extrai páginas HTTP(S) públicas, requer internet e trata o conteúdo como dado não confiável."
            )
        return (
            "Esse comando não existe. Digite /ajuda para ver os comandos locais disponíveis."
        )
