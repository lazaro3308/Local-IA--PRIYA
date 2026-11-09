import json
import threading
import unittest
from http.server import BaseHTTPRequestHandler, HTTPServer

from pria.config import Settings, load_settings
from pria.core.local_model import LocalChat, LocalModelError


class ModelHandler(BaseHTTPRequestHandler):
    captured = None
    response_content = "Olá! Sou a PRIA local."

    def do_POST(self):
        self.__class__.captured = json.loads(self.rfile.read(int(self.headers["Content-Length"])))
        if self.__class__.captured.get("stream"):
            chunks = [self.__class__.response_content[:5], self.__class__.response_content[5:]]
            body = b"".join(
                (json.dumps({"message": {"content": chunk}, "done": False}) + "\n").encode()
                for chunk in chunks
            ) + (json.dumps({"message": {"content": ""}, "done": True}) + "\n").encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/x-ndjson")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return
        body = json.dumps({"message": {"role": "assistant", "content": self.__class__.response_content}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *_args):
        pass


class LocalModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.server = HTTPServer(("127.0.0.1", 0), ModelHandler)
        cls.thread = threading.Thread(target=cls.server.serve_forever, daemon=True)
        cls.thread.start()
        cls.settings = Settings(base_url=f"http://127.0.0.1:{cls.server.server_port}")

    @classmethod
    def tearDownClass(cls):
        cls.server.shutdown()
        cls.server.server_close()
        cls.thread.join()

    def test_sends_context_and_memory_to_loopback_client(self):
        answer = LocalChat(self.settings).reply(
            [{"role": "user", "content": "Meu nome é Ana"}],
            "Qual é meu nome?",
            ["Prefere respostas curtas"],
        )
        self.assertIn("PRIA local", answer)
        self.assertEqual(ModelHandler.captured["model"], "qwen2.5:7b")
        self.assertEqual(ModelHandler.captured["messages"][-1]["content"], "Qual é meu nome?")
        self.assertIn("Prefere respostas curtas", ModelHandler.captured["messages"][0]["content"])

    def test_rejects_non_loopback_configuration(self):
        import tempfile
        from pathlib import Path

        with tempfile.TemporaryDirectory() as folder:
            config = Path(folder) / "config.json"
            config.write_text('{"base_url":"http://example.com:11434"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                load_settings(config)

    def test_empty_response_is_an_error(self):
        old = ModelHandler.response_content
        ModelHandler.response_content = ""
        try:
            with self.assertRaises(LocalModelError):
                LocalChat(self.settings).reply([], "teste")
        finally:
            ModelHandler.response_content = old

    def test_streams_local_tokens_as_they_arrive(self):
        tokens = []
        answer = LocalChat(self.settings).reply([], "teste", on_token=tokens.append)
        self.assertEqual(answer, ModelHandler.response_content)
        self.assertEqual("".join(tokens), answer)
        self.assertTrue(ModelHandler.captured["stream"])
        self.assertEqual(ModelHandler.captured["keep_alive"], "10m")

    def test_tool_decision_uses_validated_json_shape(self):
        old = ModelHandler.response_content
        ModelHandler.response_content = json.dumps({
            "action": "tool",
            "message": "",
            "tool_name": "list_directory",
            "arguments": {"path": "C:\\PRIA"},
        })
        try:
            decision = LocalChat(self.settings).decide([], "Liste os arquivos em C:\\PRIA", [], "{}")
            self.assertEqual(decision["action"], "tool")
            self.assertEqual(decision["tool_name"], "list_directory")
        finally:
            ModelHandler.response_content = old


if __name__ == "__main__":
    unittest.main()
