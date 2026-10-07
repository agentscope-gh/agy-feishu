"""Unit tests for database module."""

import asyncio
import os
import tempfile
import unittest
from unittest.mock import patch

import storage.database as database


class TestDatabase(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_db_path = os.path.join(self.temp_dir.name, "test_bot.db")
        self.patcher = patch.object(database, "DB_FILE", self.test_db_path)
        self.patcher.start()
        database.init_db()

    def tearDown(self):
        self.patcher.stop()
        self.temp_dir.cleanup()

    def test_init_db_creates_tables(self):
        self.assertTrue(os.path.exists(self.test_db_path))
        with database.get_db() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = {row[0] for row in cursor.fetchall()}
            self.assertIn("chat_sessions", tables)
            self.assertIn("user_profiles", tables)
            self.assertIn("auth_sessions", tables)
            self.assertIn("cron_tasks", tables)

    def test_save_and_get_session(self):
        async def _test():
            chat_id = "test_chat_001"
            data = {"project": "/workspace/my-app", "model": "gemini-3.8-flash-high"}
            await database.save_session_async(chat_id, data)
            retrieved = await database.get_session_async(chat_id)
            self.assertEqual(retrieved.get("project"), "/workspace/my-app")
            self.assertEqual(retrieved.get("model"), "gemini-3.8-flash-high")

        asyncio.run(_test())

    def test_auth_session_lifecycle(self):
        chat_id = "chat_test_auth"
        database.save_auth_session({
            "chat_id": chat_id,
            "chat_type": "p2p",
            "display_name": "Tester",
            "sender_open_id": "ou_123",
            "role": "user",
            "scopes": ["project", "model"]
        })
        sess = database.get_auth_session(chat_id)
        self.assertIsNotNone(sess)
        self.assertEqual(sess["chat_id"], chat_id)
        self.assertEqual(sess["display_name"], "Tester")
        self.assertEqual(sess["role"], "user")
        self.assertIn("project", sess["scopes"])


if __name__ == "__main__":
    unittest.main()
