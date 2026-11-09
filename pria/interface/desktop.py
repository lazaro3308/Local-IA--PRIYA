"""Priya's native Windows chat UI, built with Qt Widgets and local services."""

from __future__ import annotations

import threading
import uuid
import difflib
from pathlib import Path
from html import escape

from PySide6.QtCore import Qt, Signal, QObject, QTimer, QSettings
from PySide6.QtGui import QColor, QFont, QFontDatabase, QKeyEvent, QPainter, QPen, QIcon, QTextCursor
from PySide6.QtWidgets import (
    QApplication, QCheckBox, QComboBox, QFrame, QGridLayout, QHBoxLayout, QLabel, QLineEdit, QListWidget,
    QMainWindow, QMessageBox, QPlainTextEdit, QPushButton, QScrollBar,
    QSizePolicy, QSlider, QStackedWidget, QTextBrowser, QVBoxLayout, QWidget, QDialog, QListWidgetItem,
)

from pria.config import load_settings
from pria.core.assistant import Assistant
from pria.core.agent import LocalAgent
from pria.core.calculator import answer_simple_math
from pria.core.local_model import LocalChat, LocalModelError
from pria.core.self_improvement import SelfImprovement, SelfImprovementError
from pria.core.natural_commands import execute_obvious_local_request, requests_local_action
from pria.memory.database import LocalMemory
from pria.tools.applications import ApplicationLauncher
from pria.tools.files import FileTools
from pria.main import execute_command, format_all_memory, is_memory_question


class UiBridge(QObject):
    event = Signal(str, object)


def ensure_ui_fonts() -> None:
    app = QApplication.instance()
    if app is None:
        return
    for font_path in (Path(r"C:\Windows\Fonts\segoeui.ttf"), Path(r"C:\Windows\Fonts\arial.ttf")):
        if font_path.is_file():
            QFontDatabase.addApplicationFont(str(font_path))
    app.setFont(QFont("Segoe UI", 10))


class MessageBox(QPlainTextEdit):
    send_requested = Signal()

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() in (Qt.Key_Return, Qt.Key_Enter):
            if event.modifiers() & Qt.ShiftModifier:
                super().keyPressEvent(event)
            else:
                self.send_requested.emit()
            return
        super().keyPressEvent(event)


class ArasakaMark(QWidget):
    """Small local vector mark: red ring with three connected nodes."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(46, 46)

    def paintEvent(self, _event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        red = QColor("#e34b55")
        painter.setPen(QPen(red, 2))
        painter.setBrush(Qt.NoBrush)
        painter.drawEllipse(3, 3, 40, 40)
        painter.drawLine(23, 10, 23, 22)
        painter.drawLine(23, 22, 14, 32)
        painter.drawLine(23, 22, 32, 32)
        painter.setBrush(red)
        for x, y in ((23, 10), (14, 32), (32, 32)):
            painter.drawEllipse(x - 2, y - 2, 4, 4)
        painter.end()


class PriyaDesktop(QMainWindow):
    def __init__(self):
        super().__init__()
        ensure_ui_fonts()
        self.setWindowTitle("Priya — assistente local")
        self.setObjectName("PriyaWindow")
        self.settings = load_settings()
        self.memory = LocalMemory()
        self.session_id = uuid.uuid4().hex
        self.inherit_history = True
        self.files = FileTools()
        self.apps = ApplicationLauncher()
        self.assistant = Assistant()
        self.chat = LocalChat(self.settings)
        self.self_improver = SelfImprovement(self.chat)
        self.agent = LocalAgent(self.chat, self.files, self.apps)
        self.bridge = UiBridge(self)
        self.bridge.event.connect(self._handle_event)
        self.busy = False
        self.closing = False
        self.transcriber = None
        self.listening = False
        self.last_answer = ""
        self.voice_rate = 1.0
        self.voice_volume = 1.0
        self.tts_cancel_event = None
        self.streaming_text = ""
        self.transcript_rows: list[tuple[str, str]] = []
        self.assistant_pending = False
        preferences = QSettings("PriyaLocal", "Priya")
        self.ui_preferences = preferences
        self.sidebar_collapsed = preferences.value("sidebar_collapsed", False, type=bool)
        self.voice_auto = preferences.value("voice_auto", True, type=bool)
        self.voice_auto_send = preferences.value("voice_auto_send", True, type=bool)
        saved_device = str(preferences.value("microphone_device", ""))
        self.microphone_device = int(saved_device) if saved_device.isdigit() else None
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "priya_arasaka.ico"
        if icon_path.is_file():
            self.setWindowIcon(QIcon(str(icon_path)))
        self._build_ui()
        self.stream_render_timer = QTimer(self)
        self.stream_render_timer.setInterval(120)
        self.stream_render_timer.timeout.connect(self._flush_streaming_reply)

        screen = QApplication.primaryScreen()
        available = screen.availableGeometry() if screen else None
        if available:
            width = min(1180, max(760, available.width() - 64))
            height = min(760, max(520, available.height() - 64))
            self.resize(width, height)
            self.move(available.center() - self.rect().center())
        else:
            self.resize(1180, 760)
        self._set_sidebar_visible(not self.sidebar_collapsed, persist=False)
        self.status_label.setText("PRONTA · LOCAL")
        self._refresh_conversations()
        QTimer.singleShot(120, self._present_window)

    def _build_ui(self) -> None:
        self.setStyleSheet("""
            QMainWindow, QWidget#Root { background: #08090d; color: #ecebf0; }
            QLabel { color: #dedde3; background: transparent; }
            QFrame#Sidebar { background: #0d0e13; border: none; }
            QFrame#Composer { background: #111218; border: 1px solid #30313a; border-radius: 17px; }
            QFrame#Composer:focus-within { border: 1px solid #d93b4b; }
            QTextBrowser#Transcript { background: #0c0d12; color: #ecebf0; border: 1px solid #23242c; border-radius: 15px; padding: 20px; selection-background-color: #4b1821; }
            QWidget#Welcome { background: #0c0d12; border: 1px solid #24252e; border-radius: 15px; }
            QPlainTextEdit#MessageBox { background: #0d0e13; color: #f5f3f4; border: 1px solid #2b2c35; border-radius: 11px; padding: 13px; selection-background-color: #4b1821; font-size: 14px; }
            QPlainTextEdit#MessageBox:focus { border: 1px solid #cf3948; background: #101117; }
            QPushButton { background: #17181f; color: #dedde3; border: 1px solid #30313a; border-radius: 9px; padding: 10px 13px; font-size: 10pt; }
            QPushButton:hover { background: #22232c; border-color: #74303a; color: #fff4f4; }
            QPushButton:disabled { background: #121319; color: #6f7079; }
            QPushButton#SidebarButton { text-align: left; padding: 7px 10px; font-size: 9pt; }
            QPushButton#SidebarButton:hover { border-left: 2px solid #df3e4e; }
            QPushButton#SidebarToggle { background: transparent; border: 1px solid #30313a; color: #e04452; font-size: 16pt; padding: 0; }
            QPushButton#SidebarToggle:hover { background: #1a1419; border-color: #91404a; }
            QPushButton#SendButton { background: #c93143; color: #fff7f7; border: 1px solid #e04755; font-weight: 700; padding: 11px 17px; }
            QPushButton#SendButton:hover { background: #e44251; border-color: #ff6974; }
            QPushButton#Suggestion { background: #13141a; color: #e3e1e6; border: 1px solid #30313a; border-radius: 11px; padding: 14px 15px; text-align: left; font-size: 10pt; }
            QPushButton#Suggestion:hover { background: #1a1419; border-color: #91404a; }
            QLineEdit { background: #111218; color: #f1f0f2; border: 1px solid #30313a; border-radius: 9px; padding: 10px; }
            QCheckBox { color: #b6c3d2; spacing: 7px; }
            QCheckBox::indicator { width: 16px; height: 16px; }
            QCheckBox::indicator:unchecked { background: #101722; border: 1px solid #40566c; border-radius: 4px; }
            QCheckBox::indicator:checked { background: #35dfff; border: 1px solid #35dfff; border-radius: 4px; }
            QListWidget { background: #101117; color: #e3e1e6; border: 1px solid #292a33; border-radius: 9px; padding: 4px; outline: none; }
            QListWidget::item { padding: 8px 9px; border-radius: 6px; }
            QListWidget::item:hover { background: #1a1b23; }
            QListWidget::item:selected { background: #35151b; color: #fff0f1; border-left: 2px solid #df3e4e; }
            QScrollBar:vertical { background: #0d0e13; width: 8px; margin: 0; }
            QScrollBar::handle:vertical { background: #45414a; border-radius: 4px; min-height: 24px; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; border: none; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: transparent; }
            QSlider::groove:horizontal { background: #35333b; height: 4px; border-radius: 2px; }
            QSlider::handle:horizontal { background: #e04452; width: 12px; margin: -5px 0; border-radius: 6px; }
        """)

        root = QWidget()
        root.setObjectName("Root")
        self.setCentralWidget(root)
        shell = QHBoxLayout(root)
        shell.setContentsMargins(0, 0, 0, 0)
        shell.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(248)
        self.sidebar_panel = sidebar
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(20, 22, 20, 20)
        side.setSpacing(7)
        brand = QHBoxLayout()
        name = QLabel("Priya")
        name.setStyleSheet("color:#f1eff1;font-size:27px;font-weight:700;letter-spacing:-0.7px")
        brand.addWidget(name)
        brand.addStretch(1)
        brand.addWidget(ArasakaMark())
        side.addLayout(brand)
        mark_label = QLabel("ARASAKA")
        mark_label.setStyleSheet("color:#e04452;font-size:8px;font-weight:700;letter-spacing:2.3px")
        side.addWidget(mark_label)
        subtitle = QLabel("PERSONAL LOCAL AI")
        subtitle.setStyleSheet("color:#8f9db0;font-size:9px;letter-spacing:1px")
        side.addWidget(subtitle)
        side.addSpacing(12)
        local = QLabel("●  MODELO LOCAL")
        local.setStyleSheet("color:#62e8bf;font-weight:700")
        side.addWidget(local)
        model = QLabel(self.settings.model)
        model.setWordWrap(True)
        model.setStyleSheet("color:#b6c3d2;font-size:9pt")
        side.addWidget(model)
        side.addSpacing(12)
        self._side_button(side, "Nova conversa", self.new_conversation)
        history_label = QLabel("SEUS CHATS")
        history_label.setStyleSheet("color:#8fa0b4;font-size:8pt;font-weight:700;letter-spacing:1px;margin-top:5px")
        side.addWidget(history_label)
        self.chat_history = QListWidget()
        self.chat_history.setObjectName("ChatHistory")
        self.chat_history.setAccessibleName("Histórico de conversas")
        self.chat_history.setToolTip("Abra uma conversa anterior. As mensagens ficam juntas por conversa.")
        self.chat_history.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self.chat_history.setTextElideMode(Qt.ElideRight)
        self.chat_history.setMinimumHeight(110)
        self.chat_history.currentItemChanged.connect(self._history_item_selected)
        side.addWidget(self.chat_history, 1)
        side.addSpacing(12)
        self._side_button(side, "Aplicativos", self.show_apps)
        self._side_button(side, "Microfone", self.show_microphones)
        self._side_button(side, "Mostrar memória", lambda: self.submit_text("/memoria"))
        self._side_button(side, "Ajuda", lambda: self.submit_text("/ajuda"))
        self._side_button(side, "Autoaperfeiçoar código", self.show_self_improvement)
        side.addSpacing(14)
        speed_label = QLabel("VOZ · VELOCIDADE")
        speed_label.setStyleSheet("color:#8fa0b4;font-size:8pt")
        side.addWidget(speed_label)
        speed = QSlider(Qt.Horizontal)
        speed.setRange(60, 150)
        speed.setValue(100)
        speed.valueChanged.connect(lambda value: setattr(self, "voice_rate", value / 100))
        side.addWidget(speed)
        volume_label = QLabel("VOZ · VOLUME")
        volume_label.setStyleSheet("color:#8fa0b4;font-size:8pt")
        side.addWidget(volume_label)
        volume = QSlider(Qt.Horizontal)
        volume.setRange(0, 100)
        volume.setValue(100)
        volume.valueChanged.connect(lambda value: setattr(self, "voice_volume", value / 100))
        side.addWidget(volume)
        offline = QLabel("OFFLINE READY\n\nChat, voz, memória e arquivos são locais. A leitura web precisa de internet.")
        offline.setWordWrap(True)
        offline.setStyleSheet("color:#8292a6;font-size:9pt")
        side.addWidget(offline)
        shell.addWidget(sidebar)

        separator = QFrame()
        separator.setFixedWidth(1)
        separator.setStyleSheet("background:#292a31;border:none")
        self.sidebar_separator = separator
        shell.addWidget(separator)

        content = QWidget()
        layout = QVBoxLayout(content)
        layout.setContentsMargins(26, 18, 26, 16)
        layout.setSpacing(12)
        header = QHBoxLayout()
        self.sidebar_toggle = self._button("‹", self.toggle_sidebar, "SidebarToggle")
        self.sidebar_toggle.setFixedSize(38, 36)
        header.addWidget(self.sidebar_toggle)
        title = QLabel("PRIYA  /  ASSISTENTE LOCAL")
        title.setStyleSheet("font-size:10px;font-weight:700;color:#a5a2aa;letter-spacing:1.6px")
        header.addWidget(title)
        header.addStretch(1)
        self.status_label = QLabel("INICIANDO…")
        self.status_label.setStyleSheet("color:#77d8b2;background:#111a18;border:1px solid #2b443b;border-radius:9px;padding:6px 10px;font-size:8pt;font-weight:700")
        header.addWidget(self.status_label)
        layout.addLayout(header)

        self.screen_stack = QStackedWidget()
        self.welcome = self._make_welcome()
        self.transcript = QTextBrowser()
        self.transcript.setObjectName("Transcript")
        self.transcript.setOpenExternalLinks(False)
        self.transcript.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.transcript.setFont(QFont("Segoe UI", 11))
        self.screen_stack.addWidget(self.welcome)
        self.screen_stack.addWidget(self.transcript)
        layout.addWidget(self.screen_stack, 1)
        self.live_output = QLabel()
        self.live_output.setTextFormat(Qt.PlainText)
        self.live_output.setWordWrap(True)
        self.live_output.setMaximumHeight(74)
        self.live_output.setStyleSheet("color:#bcecf3;background:#101722;border:1px solid #26374a;border-radius:10px;padding:10px")
        self.live_output.hide()

        composer = QFrame()
        composer.setObjectName("Composer")
        compose = QVBoxLayout(composer)
        compose.setContentsMargins(15, 12, 15, 12)
        compose.setSpacing(9)
        input_label = QLabel("MENSAGEM")
        input_label.setStyleSheet("color:#7f95aa;font-size:8pt;font-weight:700;letter-spacing:1px")
        compose.addWidget(input_label)
        self.input = MessageBox()
        self.input.setObjectName("MessageBox")
        self.input.setPlaceholderText("Escreva sua mensagem para a Priya aqui…")
        self.input.setMinimumHeight(78)
        self.input.setMaximumHeight(120)
        self.input.setTabChangesFocus(False)
        self.input.send_requested.connect(self.submit)
        compose.addWidget(self.input)
        controls = QHBoxLayout()
        self.voice_button = self._button("Falar", self.toggle_voice)
        controls.addWidget(self.voice_button)
        self.speak_button = self._button("Ouvir resposta", self.speak_last)
        controls.addWidget(self.speak_button)
        controls.addWidget(self._button("Parar voz", self.stop_voice))
        self.auto_voice = QCheckBox("Falar respostas")
        self.auto_voice.setChecked(self.voice_auto)
        self.auto_voice.setToolTip("Reproduz cada resposta da Priya com a voz local Piper.")
        self.auto_voice.toggled.connect(self._set_auto_voice)
        controls.addWidget(self.auto_voice)
        controls.addStretch(1)
        self.send_button = self._button("ENVIAR MENSAGEM", self.submit, "SendButton")
        controls.addWidget(self.send_button)
        compose.addLayout(controls)
        layout.addWidget(composer)
        self.hint_label = QLabel("Enter envia · Shift+Enter cria outra linha · operações sensíveis pedem confirmação")
        self.hint_label.setStyleSheet("color:#9baabd;font-size:9pt")
        layout.addWidget(self.hint_label)
        shell.addWidget(content, 1)

    def _make_welcome(self) -> QWidget:
        page = QWidget()
        page.setObjectName("Welcome")
        outer = QVBoxLayout(page)
        outer.setContentsMargins(34, 26, 34, 24)
        outer.addStretch(1)

        mark = ArasakaMark()
        mark.setFixedSize(54, 54)
        outer.addWidget(mark, alignment=Qt.AlignHCenter)
        eyebrow = QLabel("PRIVADA  ·  LOCAL  ·  SEM CRÉDITOS")
        eyebrow.setAlignment(Qt.AlignCenter)
        eyebrow.setStyleSheet("color:#e04452;font-size:8pt;font-weight:700;letter-spacing:1.8px;margin-top:10px")
        outer.addWidget(eyebrow)
        heading = QLabel("Olá. O que vamos\nresolver hoje?")
        heading.setAlignment(Qt.AlignCenter)
        heading.setStyleSheet("color:#f1eff1;font-size:30px;font-weight:650;line-height:1.2;margin-top:8px")
        outer.addWidget(heading)
        subtitle = QLabel("Converse por texto ou voz. Seus dados ficam neste computador.")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setWordWrap(True)
        subtitle.setStyleSheet("color:#91a4b8;font-size:10pt;margin-top:4px;margin-bottom:17px")
        outer.addWidget(subtitle)

        section = QLabel("ESCOLHA UM PONTO DE PARTIDA")
        section.setStyleSheet("color:#71869a;font-size:8pt;font-weight:700;letter-spacing:1px;margin-bottom:2px")
        outer.addWidget(section)
        suggestions = QGridLayout()
        suggestions.setSpacing(9)
        cards = (
            ("Estudar um assunto", "Explique um tema passo a passo."),
            ("Escrever ou revisar", "Ajude-me a revisar este texto: "),
            ("Ler um documento", "Leia e resuma o arquivo "),
            ("Abrir um aplicativo", "Abra o aplicativo "),
        )
        self.suggestion_buttons = []
        for index, (label, prompt) in enumerate(cards):
            button = QPushButton(label + "\n" + prompt.rstrip())
            button.setObjectName("Suggestion")
            button.setMinimumHeight(64)
            button.clicked.connect(lambda _checked=False, text=prompt: self._use_suggestion(text))
            suggestions.addWidget(button, index // 2, index % 2)
            self.suggestion_buttons.append(button)
        outer.addLayout(suggestions)
        outer.addStretch(1)
        return page

    def _use_suggestion(self, prompt: str) -> None:
        self.input.setPlainText(prompt)
        self.input.setFocus(Qt.ActiveWindowFocusReason)
        self.input.moveCursor(QTextCursor.End)

    def _present_window(self) -> None:
        if self.closing:
            return
        self.showNormal()
        self.raise_()
        self.activateWindow()
        self.input.setFocus(Qt.ActiveWindowFocusReason)

    @staticmethod
    def _button(text: str, callback, object_name: str = "") -> QPushButton:
        button = QPushButton(text)
        if object_name:
            button.setObjectName(object_name)
        button.clicked.connect(callback)
        return button

    def _side_button(self, layout: QVBoxLayout, text: str, callback) -> None:
        button = self._button(text, callback, "SidebarButton")
        layout.addWidget(button)

    def toggle_sidebar(self) -> None:
        self._set_sidebar_visible(not self.sidebar_panel.isVisible(), persist=True)

    def _set_sidebar_visible(self, visible: bool, persist: bool) -> None:
        self.sidebar_panel.setVisible(visible)
        self.sidebar_separator.setVisible(visible)
        self.sidebar_toggle.setText("‹" if visible else "›")
        self.sidebar_toggle.setToolTip("Ocultar a barra lateral" if visible else "Mostrar a barra lateral")
        self.sidebar_toggle.setAccessibleName(self.sidebar_toggle.toolTip())
        if persist:
            self.ui_preferences.setValue("sidebar_collapsed", not visible)

    def _append(self, speaker: str, text: str) -> None:
        if speaker == "Priya" and self.assistant_pending and self.transcript_rows:
            self.transcript_rows[-1] = (speaker, text)
            self.assistant_pending = False
        else:
            self.transcript_rows.append((speaker, text))
        self._render_transcript()

    def _render_transcript(self) -> None:
        self.screen_stack.setCurrentWidget(self.transcript)
        blocks = []
        for speaker, text in self.transcript_rows:
            is_priya = speaker == "Priya"
            is_user = speaker in {"Você", "Você (voz)"}
            color = "#56cedb" if is_user else "#ed6571" if is_priya else "#d3ae68"
            background = "#111a20" if is_user else "#171317" if is_priya else "#17161b"
            alignment = "right" if is_user else "left"
            spacer_width, message_width = ("32%", "68%") if is_user else ("0%", "100%")
            safe_speaker = escape(speaker)
            safe_text = escape(text).replace("\n", "<br>")
            blocks.append(
                '<table width="100%" cellspacing="0" cellpadding="0"><tr>'
                f'<td width="{spacer_width}">&nbsp;</td><td width="{message_width}" align="{alignment}">'
                f'<table width="100%" cellspacing="0" cellpadding="0"><tr><td bgcolor="{background}" '
                f'style="background-color:{background};border-left:3px solid {color};padding:12px 15px">'
                f'<span style="color:{color};font-size:10pt;font-weight:700">{safe_speaker}</span>'
                f'<div style="color:#e4edf5;font-size:11pt;margin-top:6px">{safe_text or "&nbsp;"}</div>'
                '</td></tr></table></td></tr></table><br>'
            )
        self.transcript.setHtml("".join(blocks))
        self.transcript.verticalScrollBar().setValue(self.transcript.verticalScrollBar().maximum())

    def _update_pending_reply(self, text: str) -> None:
        if not self.assistant_pending or not self.transcript_rows or self.transcript_rows[-1][0] != "Priya":
            return
        self.transcript_rows[-1] = ("Priya", text or "Priya está escrevendo…")
        self._render_transcript()

    def _flush_streaming_reply(self) -> None:
        self.stream_render_timer.stop()
        self._update_pending_reply(self.streaming_text)

    def submit_text(self, text: str) -> None:
        if self.busy:
            return
        self.input.setPlainText(text)
        self.submit()

    def submit(self) -> None:
        if self.busy:
            return
        text = self.input.toPlainText().strip()
        if not text:
            self.input.setFocus()
            return
        self.input.clear()
        command = text.casefold()
        if command in {"/limpar", "/clear"}:
            self.new_conversation()
            return
        if command in {"/novo", "/new"}:
            self.new_conversation()
            return
        self._append("Você", text)
        self.assistant_pending = True
        self.transcript_rows.append(("Priya", "Priya está pensando…"))
        self._render_transcript()
        self.busy = True
        self.send_button.setEnabled(False)
        self.chat_history.setEnabled(False)
        self.status_label.setText("PROCESSANDO LOCALMENTE…")
        threading.Thread(target=self._process, args=(text, self.session_id), daemon=True).start()

    def _confirm_from_worker(self, description: str) -> bool:
        event = threading.Event()
        request = {"description": description, "event": event, "answer": False}
        self.bridge.event.emit("confirm", request)
        while not event.wait(0.1):
            if self.closing:
                return False
        return bool(request["answer"])

    def _process(self, text: str, session_id: str | None = None) -> None:
        session_id = session_id or self.session_id
        try:
            command = text.casefold()
            if command in {"/memoria", "/memory"} or is_memory_question(text):
                answer = format_all_memory(self.memory)
                self.memory.add_message(session_id, "user", text)
                self.memory.add_message(session_id, "assistant", answer)
            elif command.startswith("/guardar "):
                try:
                    self.memory.remember(text[len("/guardar "):])
                    answer = "Memória salva localmente."
                except ValueError as exc:
                    answer = f"Não salvei: {exc}"
                self.memory.add_message(session_id, "user", text)
                self.memory.add_message(session_id, "assistant", answer)
            elif command == "/apagar-memoria":
                if self._confirm_from_worker("Apagar todo o histórico e fatos da memória local?"):
                    self.memory.delete_all()
                    answer = "Memória local apagada."
                else:
                    answer = "Cancelado; memória preservada."
            else:
                self.memory.add_message(session_id, "user", text)
                if text.startswith("/"):
                    answer = execute_command(text, self.assistant, self.files, self.apps, self._confirm_from_worker)
                else:
                    answer = answer_simple_math(text)
                    if answer is None:
                        answer = execute_obvious_local_request(text, self.files, self.apps, self._confirm_from_worker)
                    if answer is None:
                        previous = self.memory.recent_messages(session_id, limit=24)[:-1]
                        if not previous and self.inherit_history:
                            previous = self.memory.recent_messages(None, limit=12)[:-1]
                        self.inherit_history = False
                        if requests_local_action(text):
                            answer = self.agent.respond(
                                previous, text, self.memory.all_facts(), self._confirm_from_worker,
                                on_progress=lambda token: self.bridge.event.emit("stream_chunk", token),
                            )
                        else:
                            self.bridge.event.emit("stream_start", None)
                            answer = self.chat.reply(
                                previous,
                                text,
                                facts=self.memory.all_facts(),
                                on_token=lambda token: self.bridge.event.emit("stream_chunk", token),
                            )
                self.memory.add_message(session_id, "assistant", answer)
            self.bridge.event.emit("result", answer)
        except LocalModelError as exc:
            answer = f"Não consegui responder: {exc}"
            self.memory.add_message(session_id, "assistant", answer)
            self.bridge.event.emit("result", answer)
        except Exception as exc:
            answer = f"Falha local: {type(exc).__name__}: {exc}"
            self.memory.add_message(session_id, "assistant", answer)
            self.bridge.event.emit("result", answer)

    def _handle_event(self, kind: str, payload) -> None:
        if self.closing:
            if kind == "confirm":
                payload["event"].set()
            return
        if kind == "confirm":
            answer = QMessageBox.question(self, "Confirmar operação", payload["description"], QMessageBox.Yes | QMessageBox.No, QMessageBox.No)
            payload["answer"] = answer == QMessageBox.Yes
            payload["event"].set()
        elif kind == "result":
            self.live_output.hide()
            self.stream_render_timer.stop()
            self.streaming_text = ""
            self.last_answer = payload
            self._append("Priya", payload)
            self.busy = False
            self.send_button.setEnabled(True)
            self.chat_history.setEnabled(True)
            self._refresh_conversations()
            self.status_label.setText("PRONTA · LOCAL")
            self.input.setFocus(Qt.ActiveWindowFocusReason)
            if self.voice_auto and payload.strip():
                self._speak_text(payload)
        elif kind == "stream_start":
            self.streaming_text = ""
            self._update_pending_reply("Priya está escrevendo…")
        elif kind == "stream_chunk":
            self.streaming_text = (self.streaming_text + str(payload))[-900:]
            if not self.stream_render_timer.isActive():
                self.stream_render_timer.start()
        elif kind == "voice_ready":
            self.transcriber = payload
            self._toggle_recording()
        elif kind == "voice_error":
            self.status_label.setText("PRONTA · LOCAL")
            self.voice_button.setText("Falar")
            self.voice_button.setEnabled(True)
            self.speak_button.setEnabled(True)
            self.speak_button.setText("Ouvir resposta")
            QMessageBox.warning(self, "Voz local indisponível", str(payload))
        elif kind == "voice_text":
            transcript, overflow = payload if isinstance(payload, tuple) else (str(payload), False)
            transcript = str(transcript).strip()
            self.voice_button.setText("Falar")
            self.voice_button.setEnabled(True)
            self.status_label.setText("PRONTA · LOCAL")
            if transcript:
                self.input.setPlainText(transcript)
                self.input.setFocus(Qt.ActiveWindowFocusReason)
                self.hint_label.setText("Transcrição no campo de mensagem — revise e pressione Enter para enviar." +
                                        (" A captura indicou perda de áudio." if overflow else ""))
                if self.voice_auto_send:
                    self.submit()
            else:
                self._append("Sistema", "Não detectei fala; confira o microfone e tente de novo.")
        elif kind == "voice_partial":
            partial = str(payload).strip()
            if self.listening and partial:
                preview = partial[-64:]
                self.status_label.setText(f"OUVINDO · {preview}")
        elif kind == "tts_done":
            self.speak_button.setEnabled(True)
            self.speak_button.setText("Ouvir resposta")
        elif kind == "self_improve_done":
            self._finish_self_improvement(payload)
        elif kind == "self_improve_progress":
            ui = getattr(self, "self_improvement_ui", None)
            if ui:
                ui["status"].setText(f"Gerando diff no modelo local… {payload} tokens recebidos.")
        elif kind == "self_improve_apply_done":
            self._finish_self_improvement_apply(payload)

    def toggle_voice(self) -> None:
        if self.transcriber is None:
            self.voice_button.setEnabled(False)
            self.voice_button.setText("Carregando voz…")
            def load_voice():
                try:
                    from pria.voice.speech_to_text import SpeechToText
                    self.bridge.event.emit("voice_ready", SpeechToText(device=self.microphone_device))
                except Exception as exc:
                    self.bridge.event.emit("voice_error", str(exc))
            threading.Thread(target=load_voice, daemon=True).start()
            return
        self._toggle_recording()

    def _toggle_recording(self) -> None:
        try:
            if not self.listening:
                self.transcriber.start(on_partial=lambda text: self.bridge.event.emit("voice_partial", text))
                self.listening = True
                self.voice_button.setEnabled(True)
                self.voice_button.setText("Parar de ouvir")
                self.status_label.setText("OUVINDO · CLIQUE PARA TRANSCRITIR")
            else:
                self.listening = False
                self.voice_button.setText("Transcrevendo…")
                self.voice_button.setEnabled(False)
                self.status_label.setText("TRANSCRIÇÃO LOCAL…")
                def transcribe():
                    try:
                        text = self.transcriber.stop()
                        self.bridge.event.emit("voice_text", (text, self.transcriber.audio_overflow))
                    except Exception as exc:
                        self.bridge.event.emit("voice_error", str(exc))
                threading.Thread(target=transcribe, daemon=True).start()
        except Exception as exc:
            self.listening = False
            self.bridge.event.emit("voice_error", str(exc))

    def speak_last(self) -> None:
        if not self.last_answer:
            self._append("Sistema", "Ainda não existe resposta para falar em voz alta.")
            return
        self._speak_text(self.last_answer)

    def _set_auto_voice(self, enabled: bool) -> None:
        self.voice_auto = enabled
        QSettings("PriyaLocal", "Priya").setValue("voice_auto", enabled)

    def _speak_text(self, text: str) -> None:
        # Avoid reading huge document/memory dumps aloud; keep playback user-controlled.
        text = text.strip()
        if len(text) > 5000:
            text = text[:5000] + " … resposta abreviada na voz."
        rate, volume = self.voice_rate, self.voice_volume
        if self.tts_cancel_event:
            self.tts_cancel_event.set()
        try:
            from pria.voice.text_to_speech import TextToSpeech
            TextToSpeech.stop()
        except Exception:
            pass
        cancel_event = threading.Event()
        self.tts_cancel_event = cancel_event
        self.speak_button.setEnabled(False)
        self.speak_button.setText("Falando…")
        def speak():
            try:
                from pria.voice.text_to_speech import TextToSpeech
                if cancel_event.is_set():
                    self.bridge.event.emit("tts_done", None)
                    return
                TextToSpeech().speak(text, rate=rate, volume=volume, cancel_event=cancel_event)
                self.bridge.event.emit("tts_done", None)
            except Exception as exc:
                self.bridge.event.emit("voice_error", str(exc))
        threading.Thread(target=speak, daemon=True).start()

    def stop_voice(self) -> None:
        if self.tts_cancel_event:
            self.tts_cancel_event.set()
        if self.listening and self.transcriber:
            try:
                self.transcriber.cancel()
            except Exception:
                pass
            self.listening = False
            self.voice_button.setText("Falar")
            self.voice_button.setEnabled(True)
        try:
            from pria.voice.text_to_speech import TextToSpeech
            TextToSpeech.stop()
        except Exception:
            pass

    def show_microphones(self) -> None:
        if self.listening:
            QMessageBox.information(self, "Microfone em uso", "Pare a gravação antes de trocar o microfone.")
            return
        try:
            from pria.voice.speech_to_text import SpeechToText
            devices = SpeechToText.input_devices()
        except Exception as exc:
            QMessageBox.warning(self, "Microfones locais", str(exc))
            return
        dialog = QDialog(self)
        dialog.setWindowTitle("Entrada de voz — Priya")
        dialog.setStyleSheet(self.styleSheet())
        dialog.resize(500, 180)
        layout = QVBoxLayout(dialog)
        title = QLabel("ESCOLHA O MICROFONE")
        title.setStyleSheet("color:#55e5ff;font-size:12pt;font-weight:700")
        layout.addWidget(title)
        selector = QComboBox()
        for device in devices:
            selector.addItem(device["name"], device["index"])
        index = selector.findData(self.microphone_device)
        selector.setCurrentIndex(max(0, index))
        layout.addWidget(selector)
        auto_send = QCheckBox("Enviar a transcrição automaticamente ao parar de falar")
        auto_send.setChecked(self.voice_auto_send)
        layout.addWidget(auto_send)
        note = QLabel("O áudio é processado localmente e descartado ao terminar a transcrição.")
        note.setWordWrap(True)
        note.setStyleSheet("color:#91a4b8")
        layout.addWidget(note)
        save = QPushButton("Usar este microfone")
        save.clicked.connect(dialog.accept)
        layout.addWidget(save, alignment=Qt.AlignRight)
        if dialog.exec() == QDialog.Accepted:
            self.microphone_device = selector.currentData()
            preferences = QSettings("PriyaLocal", "Priya")
            preferences.setValue("microphone_device", "" if self.microphone_device is None else self.microphone_device)
            self.voice_auto_send = auto_send.isChecked()
            preferences.setValue("voice_auto_send", self.voice_auto_send)
            self.transcriber = None
            self.status_label.setText("MICROFONE ATUALIZADO · LOCAL")

    def show_apps(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Aplicativos disponíveis — Priya")
        dialog.resize(480, 560)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        label = QLabel("ABRIR APLICATIVO")
        label.setStyleSheet("color:#55e5ff;font-size:13pt;font-weight:700")
        layout.addWidget(label)
        search = QLineEdit()
        search.setPlaceholderText("Pesquisar aplicativo…")
        layout.addWidget(search)
        listing = QListWidget()
        layout.addWidget(listing, 1)
        names = self.apps.names()
        def refresh(value=""):
            listing.clear()
            listing.addItems([item for item in names if value.casefold() in item.casefold()])
        def launch():
            selected = listing.currentItem()
            if not selected:
                return
            try:
                self._append("Sistema", self.apps.open(selected.text()))
                dialog.accept()
            except Exception as exc:
                QMessageBox.warning(dialog, "Não foi possível abrir", str(exc))
        search.textChanged.connect(refresh)
        listing.itemActivated.connect(lambda _item: launch())
        button = QPushButton("Abrir selecionado")
        button.clicked.connect(launch)
        layout.addWidget(button, alignment=Qt.AlignRight)
        refresh()
        search.setFocus()
        dialog.exec()

    def show_self_improvement(self) -> None:
        dialog = QDialog(self)
        dialog.setWindowTitle("Autoaperfeiçoamento local — Priya")
        dialog.resize(800, 650)
        dialog.setStyleSheet(self.styleSheet())
        layout = QVBoxLayout(dialog)
        title = QLabel("PROPOR UMA MELHORIA NO CÓDIGO DA PRIYA")
        title.setStyleSheet("color:#e04452;font-size:13pt;font-weight:700;letter-spacing:1px")
        layout.addWidget(title)
        notice = QLabel("A Priya prepara uma proposta local para você revisar. Depois da sua aprovação, cria um backup, aplica a mudança e roda a suíte de testes. "
                        "Se os testes falharem ou excederem o limite de tempo, restaura automaticamente o arquivo original. "
                        "Os módulos de permissões e ferramentas críticas permanecem protegidos.")
        notice.setWordWrap(True)
        notice.setStyleSheet("color:#aebdce")
        layout.addWidget(notice)
        selector = QComboBox()
        protected = self.self_improver.PROTECTED
        choices = [path.relative_to(Path(__file__).resolve().parents[2]).as_posix()
                   for path in (Path(__file__).resolve().parents[2] / "pria").rglob("*.py")
                   if "__pycache__" not in path.parts
                   and path.stat().st_size <= self.self_improver.MAX_SOURCE
                   and path.relative_to(Path(__file__).resolve().parents[2]).as_posix() not in {item.as_posix() for item in protected}]
        selector.addItems(sorted(choices))
        layout.addWidget(selector)
        objective = QPlainTextEdit()
        objective.setPlaceholderText("Descreva a mudança desejada, por exemplo: melhore as mensagens de erro para ficarem claras em português.")
        objective.setMaximumHeight(85)
        layout.addWidget(objective)
        preview = QPlainTextEdit()
        preview.setReadOnly(True)
        preview.setPlaceholderText("O diff da proposta será mostrado aqui para revisão.")
        layout.addWidget(preview, 1)
        footer = QHBoxLayout()
        status = QLabel("Nenhuma alteração foi feita.")
        status.setWordWrap(True)
        footer.addWidget(status, 1)
        generate = QPushButton("Gerar proposta local")
        apply = QPushButton("Revisar e aplicar…")
        apply.setEnabled(False)
        footer.addWidget(generate)
        footer.addWidget(apply)
        layout.addLayout(footer)
        self.self_improvement_ui = {"dialog": dialog, "selector": selector, "objective": objective,
                                    "preview": preview, "status": status, "generate": generate,
                                    "apply": apply, "proposal": None}

        def request_proposal():
            target, goal = selector.currentText(), objective.toPlainText().strip()
            if not goal:
                status.setText("Escreva o objetivo da mudança primeiro.")
                objective.setFocus()
                return
            generate.setEnabled(False)
            apply.setEnabled(False)
            preview.clear()
            status.setText("Gerando a proposta com o modelo local…")
            def work():
                try:
                    generated = [0]
                    def on_token(_token):
                        generated[0] += 1
                        if generated[0] % 8 == 0:
                            self.bridge.event.emit("self_improve_progress", generated[0])
                    original, replacement = self.self_improver.draft(
                        target, goal,
                        progress=on_token,
                    )
                    diff = "".join(difflib.unified_diff(original.splitlines(True), replacement.splitlines(True),
                                                       fromfile=target, tofile=target + " (proposta)"))
                    result = {"ok": True, "target": target, "original": original,
                              "replacement": replacement, "diff": diff}
                except Exception as exc:
                    result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
                self.bridge.event.emit("self_improve_done", result)
            threading.Thread(target=work, daemon=True).start()

        generate.clicked.connect(request_proposal)
        apply.clicked.connect(self._apply_self_improvement)
        dialog.exec()
        self.self_improvement_ui = None

    def _finish_self_improvement(self, result: dict) -> None:
        ui = getattr(self, "self_improvement_ui", None)
        if not ui:
            return
        ui["generate"].setEnabled(True)
        if not result.get("ok"):
            ui["status"].setText("Não foi possível gerar: " + result.get("error", "erro desconhecido"))
            return
        ui["proposal"] = result
        ui["preview"].setPlainText(result["diff"] or "A proposta não alterou o arquivo.")
        ui["status"].setText(f"Proposta para {result['target']}; revise o diff antes de aplicar.")
        ui["apply"].setEnabled(bool(result["diff"]))

    def _apply_self_improvement(self) -> None:
        ui = getattr(self, "self_improvement_ui", None)
        proposal = ui.get("proposal") if ui else None
        if not proposal:
            return
        confirmation = QMessageBox(self)
        confirmation.setWindowTitle("Confirmar autoaperfeiçoamento")
        confirmation.setIcon(QMessageBox.Warning)
        confirmation.setText(f"Aplicar a mudança proposta em {proposal['target']}?")
        confirmation.setInformativeText("Um backup será criado. Depois de gravar, a Priya rodará os testes locais; se falharem, restaurará o arquivo original. A Priya precisará ser reiniciada para carregar uma mudança aprovada.")
        confirmation.setDetailedText(proposal["diff"][:20000])
        confirmation.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
        confirmation.setDefaultButton(QMessageBox.No)
        if confirmation.exec() != QMessageBox.Yes:
            return
        ui["apply"].setEnabled(False)
        ui["status"].setText("Backup criado; aplicando e verificando os testes locais…")

        def apply_and_verify():
            try:
                backup = self.self_improver.apply(proposal["target"], proposal["original"], proposal["replacement"])
                result = {"ok": True, "backup": str(backup), "target": proposal["target"]}
            except Exception as exc:
                result = {"ok": False, "error": f"{type(exc).__name__}: {exc}"}
            self.bridge.event.emit("self_improve_apply_done", result)

        threading.Thread(target=apply_and_verify, daemon=True).start()

    def _finish_self_improvement_apply(self, result: dict) -> None:
        ui = getattr(self, "self_improvement_ui", None)
        if not ui:
            return
        if not result.get("ok"):
            ui["status"].setText("Não aplicada (arquivo original restaurado quando a gravação já havia começado): " + result.get("error", "erro desconhecido"))
            ui["apply"].setEnabled(True)
            return
        ui["status"].setText(f"Aplicada e testes locais aprovados. Backup: {result['backup']}. Reinicie a Priya para carregar a mudança.")
        ui["apply"].setEnabled(False)
        self._append("Sistema", f"Mudança aplicada em {result['target']}; suíte de testes aprovada. Backup: {result['backup']}")

    def new_conversation(self) -> None:
        if self.busy:
            return
        self.session_id = uuid.uuid4().hex
        self.inherit_history = False
        self.chat_history.blockSignals(True)
        self.chat_history.clearSelection()
        self.chat_history.blockSignals(False)
        self.transcript_rows.clear()
        self.assistant_pending = False
        self.stream_render_timer.stop()
        self.transcript.clear()
        self.screen_stack.setCurrentWidget(self.welcome)
        self.input.setFocus(Qt.ActiveWindowFocusReason)

    def _refresh_conversations(self) -> None:
        if not hasattr(self, "chat_history"):
            return
        selected_id = self.session_id
        self.chat_history.blockSignals(True)
        self.chat_history.clear()
        selected = None
        for conversation in self.memory.list_conversations():
            item = QListWidgetItem(conversation["title"])
            item.setData(Qt.UserRole, conversation["session_id"])
            item.setToolTip(conversation["title"])
            self.chat_history.addItem(item)
            if conversation["session_id"] == selected_id:
                selected = item
        if selected is not None:
            self.chat_history.setCurrentItem(selected)
        else:
            self.chat_history.clearSelection()
        self.chat_history.blockSignals(False)

    def _history_item_selected(self, current, _previous=None) -> None:
        if self.busy or current is None:
            return
        session_id = current.data(Qt.UserRole)
        if not session_id:
            return
        messages = self.memory.conversation_messages(str(session_id))
        self.session_id = str(session_id)
        self.inherit_history = False
        self.assistant_pending = False
        self.transcript_rows = [
            ("Você" if message["role"] == "user" else "Priya", message["content"])
            for message in messages
        ]
        self._render_transcript() if messages else self.transcript.clear()
        self.screen_stack.setCurrentWidget(self.transcript if messages else self.welcome)
        self.input.setFocus(Qt.ActiveWindowFocusReason)

    def closeEvent(self, event) -> None:
        self.closing = True
        self.stop_voice()
        event.accept()


def main() -> int:
    try:
        app = QApplication.instance() or QApplication([])
        app.setApplicationName("Priya")
        app.setOrganizationName("Priya Local")
        icon_path = Path(__file__).resolve().parents[2] / "assets" / "priya_arasaka.ico"
        if icon_path.is_file():
            app.setWindowIcon(QIcon(str(icon_path)))
        window = PriyaDesktop()
        window.showNormal()
        window.raise_()
        window.activateWindow()
        window.input.setFocus(Qt.ActiveWindowFocusReason)
        return app.exec()
    except Exception as exc:
        app = QApplication.instance()
        if app:
            QMessageBox.critical(None, "Falha ao iniciar Priya", str(exc))
        else:
            print(f"Falha ao iniciar Priya: {type(exc).__name__}: {exc}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
