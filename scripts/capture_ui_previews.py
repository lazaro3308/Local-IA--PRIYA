"""Render clean UI preview images using synthetic chat data only."""

from __future__ import annotations

import os
import sys
import tempfile
import time
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
os.environ.setdefault("PYTHONUTF8", "1")

from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QPoint

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from pria.interface.desktop import PriyaDesktop
from pria.memory.database import LocalMemory


ASSETS = ROOT / "assets"


def main() -> int:
    app = QApplication.instance() or QApplication([])
    ASSETS.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="priya-ui-preview-") as temp:
        memory = LocalMemory(Path(temp) / "preview.sqlite3")
        memory.add_message("demo-privacy", "user", "Como minhas conversas ficam protegidas?")
        memory.add_message(
            "demo-privacy",
            "assistant",
            "O histórico fica no SQLite deste computador. O modelo roda pelo Ollama local; "
            "a PRIA não envia a conversa para uma API de IA na nuvem.",
        )
        memory.add_message("demo-project", "user", "Me ajude a organizar meu projeto")
        memory.add_message(
            "demo-project",
            "assistant",
            "Vamos separar o objetivo, os arquivos envolvidos e uma primeira etapa pequena.",
        )
        with patch("pria.interface.desktop.LocalMemory", return_value=memory), \
             patch("pria.interface.desktop.QSettings") as preferences:
            preferences.return_value.value.side_effect = lambda _key, default=None, **_kwargs: default
            window = PriyaDesktop()
        window.resize(1440, 900)
        window._set_sidebar_visible(True, persist=False)
        window.show()
        app.processEvents()
        welcome_path = ASSETS / "priya-interface-welcome.png"
        if not window.grab().save(str(welcome_path)):
            raise RuntimeError(f"Não foi possível salvar {welcome_path}")

        window.resize(1440, 560)
        app.processEvents()
        window._update_welcome_density()
        app.processEvents()
        if window.welcome_scroll.verticalScrollBar().maximum() > 2:
            raise RuntimeError("A tela compacta ainda excede a altura disponível.")
        compact_path = ASSETS / "priya-interface-compact.png"
        if not window.grab().save(str(compact_path)):
            raise RuntimeError(f"Não foi possível salvar {compact_path}")

        window.resize(1440, 900)
        app.processEvents()
        window.session_id = "demo-privacy"
        window.transcript_rows = [
            ("Você" if message["role"] == "user" else "Priya", message["content"])
            for message in memory.conversation_messages("demo-privacy")
        ]
        window._refresh_conversations()
        window._render_transcript()
        window.layout().activate() if window.layout() else None
        window.repaint()
        app.processEvents()
        time.sleep(0.15)
        app.processEvents()
        chat_path = ASSETS / "priya-interface-chat.png"
        if not window.grab().save(str(chat_path)):
            raise RuntimeError(f"Não foi possível salvar {chat_path}")
        print(
            "Geometria da captura:",
            window.size().width(), window.size().height(),
            *[(widget.objectName(), widget.geometry().getRect(), widget.mapTo(window, QPoint(0, 0)).toTuple())
              for widget in (window.centralWidget(), window.sidebar_panel, window.status_label,
                             window.screen_stack, window.transcript, window.input.parentWidget())],
        )
        window.closing = True
        window.close()
        app.processEvents()
    print(welcome_path)
    print(compact_path)
    print(chat_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

