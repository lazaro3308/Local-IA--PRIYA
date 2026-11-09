import tempfile
import unittest
from pathlib import Path

from pria.memory.database import LocalMemory
from pria.main import is_memory_question


class LocalMemoryTests(unittest.TestCase):
    def test_persists_chat_and_explicit_memories(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = LocalMemory(Path(temp) / "memory.sqlite3")
            memory.add_message("session-1", "user", "Olá")
            memory.add_message("session-1", "assistant", "Oi")
            memory.remember("Prefere respostas curtas")
            reopened = LocalMemory(Path(temp) / "memory.sqlite3")
            self.assertEqual(reopened.recent_messages("session-1"), [
                {"role": "user", "content": "Olá"},
                {"role": "assistant", "content": "Oi"},
            ])
            facts, messages = reopened.all_data()
            self.assertEqual(facts, ["Prefere respostas curtas"])
            self.assertEqual(len(messages), 2)

    def test_redacts_secret_like_text_from_history(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = LocalMemory(Path(temp) / "memory.sqlite3")
            memory.add_message("session-1", "user", "senha=nao-salvar-123")
            stored = memory.recent_messages("session-1")[0]["content"]
            self.assertNotIn("nao-salvar-123", stored)
            with self.assertRaises(ValueError):
                memory.remember("token:abc-secret-token")

    def test_lists_chats_by_latest_activity_and_loads_full_thread(self):
        with tempfile.TemporaryDirectory() as temp:
            memory = LocalMemory(Path(temp) / "memory.sqlite3")
            memory.add_message("older", "user", "Conversa antiga")
            memory.add_message("older", "assistant", "Resposta antiga")
            memory.add_message("newer", "user", "Conversa recente com título muito longo " * 3)
            memory.add_message("newer", "assistant", "Resposta recente")
            chats = memory.list_conversations()
            self.assertEqual([chat["session_id"] for chat in chats], ["newer", "older"])
            self.assertLessEqual(len(chats[0]["title"]), 54)
            self.assertEqual(memory.conversation_messages("older"), [
                {"role": "user", "content": "Conversa antiga"},
                {"role": "assistant", "content": "Resposta antiga"},
            ])

    def test_memory_question_is_recognized_with_portuguese_accents(self):
        self.assertTrue(is_memory_question("qual a sua memória?"))
        self.assertTrue(is_memory_question("o que você lembra sobre mim?"))
        self.assertFalse(is_memory_question("quanto é 2+2?"))


if __name__ == "__main__":
    unittest.main()
