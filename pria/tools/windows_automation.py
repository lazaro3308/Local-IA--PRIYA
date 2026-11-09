"""Opt-in, explicit Windows UI actions using UI Automation (no elevation)."""
from __future__ import annotations


class WindowsAutomationError(RuntimeError):
    pass


class WindowsAutomation:
    @staticmethod
    def _desktop():
        try:
            from pywinauto import Desktop
            return Desktop(backend="uia")
        except ImportError as exc:
            raise WindowsAutomationError("Instale pywinauto para habilitar automação de interface.") from exc

    def list_windows(self) -> list[str]:
        try:
            rows = []
            for win in self._desktop().windows(visible_only=True):
                title = (win.window_text() or "").strip()
                if title:
                    rows.append(f"{title} (PID {win.process_id()})")
            return rows[:100]
        except Exception as exc:
            raise WindowsAutomationError(f"Falha ao listar janelas: {exc}") from exc

    def type_into_window(self, title: str, text: str) -> str:
        if not title.strip() or len(text) > 5000:
            raise WindowsAutomationError("Informe título e texto de até 5.000 caracteres.")
        try:
            import re
            matches = self._desktop().windows(title_re=f"(?i).*{re.escape(title.strip())}.*", visible_only=True)
            if not matches:
                raise WindowsAutomationError(f"Janela não encontrada: {title}")
            if len(matches) != 1:
                raise WindowsAutomationError("O título corresponde a mais de uma janela; especifique melhor: " + ", ".join(w.window_text() for w in matches[:10]))
            win = matches[0]
            win.set_focus()
            from pywinauto.keyboard import send_keys
            send_keys(text, with_spaces=True, pause=0.002)
            return f"Texto enviado para a janela '{win.window_text()}'. Verifique o resultado na tela."
        except WindowsAutomationError:
            raise
        except Exception as exc:
            raise WindowsAutomationError(f"Falha ao digitar na janela: {exc}") from exc

    def activate_window(self, title: str) -> str:
        import re
        try:
            matches = self._desktop().windows(title_re=f"(?i).*{re.escape(title.strip())}.*", visible_only=True)
            if len(matches) != 1:
                raise WindowsAutomationError(f"A busca encontrou {len(matches)} janelas; informe um título que seja único.")
            matches[0].set_focus()
            return f"Janela ativada: {matches[0].window_text()}"
        except WindowsAutomationError:
            raise
        except Exception as exc:
            raise WindowsAutomationError(f"Falha ao ativar janela: {exc}") from exc

    def close_window(self, title: str) -> str:
        import re
        try:
            matches = self._desktop().windows(title_re=f"(?i).*{re.escape(title.strip())}.*", visible_only=True)
            if len(matches) != 1:
                raise WindowsAutomationError(f"A busca encontrou {len(matches)} janelas; informe um título que seja único.")
            name = matches[0].window_text()
            matches[0].close()
            return f"Solicitei fechar a janela: {name}. O aplicativo pode pedir para salvar alterações."
        except WindowsAutomationError:
            raise
        except Exception as exc:
            raise WindowsAutomationError(f"Falha ao fechar janela: {exc}") from exc

    def click(self, x: int, y: int, button: str = "left") -> str:
        if not (0 <= x <= 20000 and 0 <= y <= 20000) or button not in {"left", "right", "double"}:
            raise WindowsAutomationError("Coordenadas ou botão inválidos.")
        try:
            from pywinauto import mouse
            mouse.click(button="left" if button == "double" else button, coords=(x, y))
            if button == "double":
                mouse.click(button="left", coords=(x, y))
            return f"Clique {button} enviado para ({x}, {y}); confirme visualmente o resultado."
        except Exception as exc:
            raise WindowsAutomationError(f"Falha ao clicar: {exc}") from exc

