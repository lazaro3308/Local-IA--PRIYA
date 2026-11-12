# PRIA — Assistente pessoal com IA local

<p align="center">
  <strong>Uma assistente pessoal para Windows, com foco em execução local, privacidade e automação assistida.</strong>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10%2B-3776AB?logo=python&logoColor=white" alt="Python 3.10+">
  <img src="https://img.shields.io/badge/Plataforma-Windows%2010%2B-0078D4?logo=windows&logoColor=white" alt="Windows 10+">
  <img src="https://img.shields.io/badge/LLM-Ollama-111111?logo=ollama&logoColor=white" alt="Ollama">
  <img src="https://img.shields.io/badge/Interface-PySide6-41CD52?logo=qt&logoColor=white" alt="PySide6">
</p>

A **PRIA** é uma assistente pessoal desenvolvida em Python para rodar localmente no Windows. Ela conversa usando um modelo servido pelo [Ollama](https://ollama.com/), mantém histórico e memórias explícitas em SQLite e oferece ferramentas para trabalhar com arquivos, aplicativos e janelas do sistema.

O projeto também conta com uma interface desktop em Qt, comandos em português e recursos opcionais de voz e automação.

> **Status:** projeto em desenvolvimento. Alguns recursos dependem de bibliotecas, modelos locais e configurações adicionais.

---

## ✨ Funcionalidades

- **Conversas com IA local:** integração com modelos servidos pelo Ollama — configuração padrão: `qwen2.5:7b`.
- **Memória local:** histórico de conversas e fatos salvos explicitamente em banco SQLite no próprio computador.
- **Interface desktop:** aplicativo nativo construído com PySide6, com histórico de conversas.
- **Terminal em português:** comandos diretos e interpretação de pedidos para ferramentas locais.
- **Arquivos e documentos:** listar, buscar, ler, criar, copiar, mover e renomear arquivos; leitura de PDF e DOCX depende das bibliotecas correspondentes.
- **Aplicativos e janelas:** abrir aplicativos, listar janelas e, com confirmação, interagir com janelas do Windows.
- **Automação assistida:** digitação, cliques e controle de janelas por meio de ferramentas do Windows.
- **Ferramentas de desenvolvimento:** criação assistida de arquivos de código em uma área de projetos, sem executar automaticamente o código gerado.
- **Leitura de páginas públicas:** busca o conteúdo textual de uma URL HTTP(S) quando solicitada; esse recurso precisa de internet.
- **Voz local opcional:** integração com Vosk para reconhecimento de fala e Piper para síntese de voz, quando os modelos e dependências estiverem instalados.
- **Autoaperfeiçoamento experimental:** propostas de alteração passam por confirmação, backup e testes locais antes de serem aplicadas.

## 🧰 Tecnologias

| Tecnologia | Uso |
|---|---|
| Python 3.10+ | Linguagem principal |
| Ollama | Serviço local para execução do modelo de linguagem |
| Qwen 2.5 7B | Modelo padrão configurado |
| SQLite | Histórico e memórias locais |
| PySide6 / Qt | Interface gráfica |
| Vosk e Piper | Recursos opcionais de voz |
| pywinauto | Automação opcional da interface do Windows |
| unittest | Testes automatizados |

## 💻 Requisitos

- Windows 10 ou superior.
- Python 3.10 ou superior.
- [Ollama instalado para Windows](https://ollama.com/download).
- Modelo `qwen2.5:7b` baixado no Ollama.
- Para a interface gráfica, PySide6 instalado no ambiente Python.
- Recursos opcionais (voz, leitura de documentos e automação) podem exigir dependências e modelos adicionais.

## 🚀 Instalação

### 1. Clone o repositório

```powershell
git clone https://github.com/lazaro3308/Local-IA--PRIYA.git
cd Local-IA--PRIYA
```

### 2. Verifique o ambiente

No PowerShell:

```powershell
.\scripts\install.ps1
```

O script verifica se Python e Ollama estão disponíveis e informa o modelo necessário.

### 3. Baixe o modelo

```powershell
ollama pull qwen2.5:7b
```

Mantenha o Ollama em execução antes de iniciar a PRIA.

### 4. Inicie pelo terminal

```powershell
.\scripts\start.ps1
```

Alternativamente:

```powershell
python -m pria.main
```

### 5. Abra a interface gráfica

Com PySide6 instalado no mesmo ambiente Python:

```powershell
python -m pria.interface.desktop
```

## ⚙️ Configuração

A PRIA aceita um arquivo opcional `config.json` na raiz do projeto. Se ele não existir, os valores padrão são utilizados.

Exemplo:

```json
{
  "base_url": "http://127.0.0.1:11434",
  "model": "qwen2.5:7b",
  "timeout_seconds": 180,
  "context_window": 4096,
  "max_response_tokens": 256
}
```

Também é possível sobrescrever as configurações por variáveis de ambiente:

| Variável | Finalidade |
|---|---|
| `PRIA_OLLAMA_URL` | Endereço local do Ollama |
| `PRIA_MODEL` | Nome do modelo |
| `PRIA_TIMEOUT` | Tempo limite das requisições |
| `PRIA_CONTEXT` | Tamanho da janela de contexto |
| `PRIA_MAX_RESPONSE_TOKENS` | Limite padrão de tokens da resposta |

Por segurança, a configuração atual aceita o serviço do modelo somente em endereço local (localhost/loopback).

## ⌨️ Comandos úteis

Digite `/ajuda` dentro do terminal para consultar a lista completa. Alguns comandos disponíveis:

| Comando | O que faz |
|---|---|
| `/ajuda` | Exibe os comandos disponíveis |
| `/apps` | Lista aplicativos reconhecidos |
| `/abrir-app <nome>` | Abre um aplicativo |
| `/listar [pasta]` | Lista o conteúdo de uma pasta |
| `/buscar <padrão> [pasta]` | Procura arquivos |
| `/ler <arquivo>` | Lê um documento compatível |
| `/ler-web <URL>` | Extrai texto de uma página pública |
| `/janelas` | Lista janelas visíveis |
| `/guardar <texto>` | Salva uma memória explícita |
| `/memoria` | Exibe dados salvos localmente |
| `/novo` | Inicia uma nova conversa |
| `/apagar-memoria` | Solicita a exclusão do histórico e das memórias |
| `/sair` | Encerra a PRIA |

Algumas ações — como executar comandos PowerShell, digitar em janelas, clicar, fechar janelas e apagar memórias — solicitam confirmação explícita.

## 🗂️ Estrutura do projeto

```text
Local-IA--PRIYA/
├── assets/                  # Recursos visuais
├── pria/
│   ├── core/                # Agente, modelo local e lógica principal
│   ├── interface/           # Interface desktop
│   ├── memory/              # Persistência SQLite
│   ├── security/            # Componentes de segurança
│   ├── tools/                # Arquivos, apps, web e automação
│   ├── config.py            # Configuração do modelo
│   ├── diagnostics.py       # Diagnóstico do ambiente
│   └── main.py              # Interface de terminal
├── scripts/                 # Instalação, inicialização e diagnóstico
├── tests/                   # Testes automatizados
└── README.md
```

## 🧪 Testes

Com Python disponível, execute na raiz do repositório:

```powershell
python -m unittest discover -s tests -v
```

O diagnóstico do ambiente pode ser executado com:

```powershell
python -m pria.diagnostics
```

## 🔐 Privacidade e segurança

- As conversas e memórias explícitas são armazenadas em SQLite local.
- O modelo é consultado por meio do serviço local do Ollama.
- A leitura de páginas web é uma funcionalidade separada e requer internet.
- Ações sensíveis do sistema solicitam confirmação antes da execução.
- O acesso web valida URLs e bloqueia destinos locais/privados.
- Arquivos e páginas externas são tratados como conteúdo não confiável, não como instruções.
- A PRIA não deve executar automaticamente o código que gera.

**Atenção:** automação de janelas e comandos do sistema podem alterar o estado do computador. Revise a ação apresentada antes de confirmar.

## 🛠️ Desenvolvimento

O projeto está em evolução. Melhorias podem incluir documentação adicional, configuração simplificada de dependências, testes e ampliação dos recursos locais.

Ao contribuir, procure manter:
- operações sensíveis protegidas por confirmação;
- dados pessoais e segredos fora do repositório;
- testes para novos comportamentos;
- compatibilidade com o ambiente Windows previsto pelo projeto.

## 📄 Licença

Essa IA foi criada por um aluno Desenvolvedor de Sistemas inspirado na CAPRIA de cyberounk! Feito por lazaro3308. 
---

<p align="center">
  Desenvolvido com Python, tecnologia local e foco em privacidade.
  <br>
  <strong>PRIA — sua assistente, no seu computador.</strong>
</p>
