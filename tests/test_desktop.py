import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt
from PySide6.QtTest import QTest
from PySide6.QtWidgets import QApplication, QPushButton

from pria.interface.desktop import PriyaDesktop
from pria.memory.database import LocalMemory


class DesktopInputTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = QApplication.instance() or QApplication([])

    def test_composer_accepts_keyboard_input_and_has_real_send_controls(self):
        window = PriyaDesktop()
        window.show()
        self.app.processEvents()
        self.assertIs(window.screen_stack.currentWidget(), window.welcome)
        window.suggestion_buttons[0].click()
        self.assertEqual(window.input.toPlainText(), "Explique um tema passo a passo.")
        window.input.clear()
        QTest.mouseClick(window.input.viewport(), Qt.LeftButton, pos=window.input.viewport().rect().center())
        QTest.keyClicks(window.input, "mensagem de teste")
        self.assertEqual(window.input.toPlainText(), "mensagem de teste")
        self.assertTrue(window.send_button.isVisible())
        self.assertTrue(window.voice_button.isVisible())
        self.assertTrue(window.auto_voice.isChecked())
        self.assertFalse(window.windowIcon().isNull())
        window._append("Você", "Olá, Priya")
        window._append("Priya", "Olá! Como posso ajudar?")
        self.assertIs(window.screen_stack.currentWidget(), window.transcript)
        transcript = window.transcript.toPlainText()
        self.assertLess(transcript.index("Você"), transcript.index("Priya"))
        window.closing = True
        window.close()
        window.deleteLater()

    def test_history_opens_messages_together_in_one_chat_view(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = LocalMemory(Path(temp) / "memory.sqlite3")
            memory.add_message("chat-a", "user", "Minha pergunta salva")
            memory.add_message("chat-a", "assistant", "Minha resposta salva")
            with patch("pria.interface.desktop.LocalMemory", return_value=memory):
                window = PriyaDesktop()
            self.app.processEvents()
            self.assertEqual(window.chat_history.count(), 1)
            window.chat_history.setCurrentRow(0)
            self.app.processEvents()
            self.assertEqual(window.session_id, "chat-a")
            transcript = window.transcript.toPlainText()
            self.assertIn("Minha pergunta salva", transcript)
            self.assertIn("Minha resposta salva", transcript)
            self.assertLess(transcript.index("Você"), transcript.index("Priya"))
            window.closing = True
            window.close()
            window.deleteLater()

    def test_reply_and_live_status_stay_under_the_user_message(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = LocalMemory(Path(temp) / "memory.sqlite3")
            with patch("pria.interface.desktop.LocalMemory", return_value=memory):
                window = PriyaDesktop()
            window._append("Você", "Minha pergunta")
            window.assistant_pending = True
            window.transcript_rows.append(("Priya", "Priya está pensando…"))
            window._render_transcript()
            window._update_pending_reply("Priya está escrevendo…")
            live = window.transcript.toPlainText()
            self.assertLess(live.index("Minha pergunta"), live.index("Priya está escrevendo"))
            window._append("Priya", "Minha resposta")
            final = window.transcript.toPlainText()
            self.assertLess(final.index("Minha pergunta"), final.index("Minha resposta"))
            self.assertNotIn("Priya está escrevendo", final)
            self.assertEqual(len(window.transcript_rows), 2)
            window.closing = True
            window.close()
            window.deleteLater()

    def test_sidebar_tools_do_not_overlap_history_and_sidebar_can_collapse(self):
        window = PriyaDesktop()
        window.show()
        self.app.processEvents()
        window._set_sidebar_visible(True, persist=False)
        applications = next(button for button in window.findChildren(QPushButton) if button.text() == "Aplicativos")
        self.assertGreater(applications.geometry().top(), window.chat_history.geometry().bottom())
        saved = window.ui_preferences.value("sidebar_collapsed", False, type=bool)
        was_visible = window.sidebar_panel.isVisible()
        window.toggle_sidebar()
        self.app.processEvents()
        self.assertFalse(window.sidebar_panel.isVisible())
        self.assertTrue(window.sidebar_toggle.isVisible())
        self.assertEqual(window.sidebar_toggle.toolTip(), "Mostrar a barra lateral")
        window.toggle_sidebar()
        self.app.processEvents()
        self.assertTrue(window.sidebar_panel.isVisible())
        window.ui_preferences.setValue("sidebar_collapsed", saved)
        if not was_visible:
            window._set_sidebar_visible(False, persist=False)
        window.closing = True
        window.close()
        window.deleteLater()


if __name__ == "__main__":
    unittest.main()
