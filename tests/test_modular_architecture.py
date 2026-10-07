"""Unit tests verifying modular architecture (Core / Client / Storage / Plugins)."""

import unittest


class TestModularArchitecture(unittest.TestCase):

    def test_core_package_imports(self):
        import core.executor
        import core.session_pool
        import core.commands
        import core.app_state
        import core.stats
        import core.garbage_collection

        self.assertTrue(hasattr(core.executor, "execute_antigravity"))
        self.assertTrue(hasattr(core.session_pool, "SessionPool"))
        self.assertTrue(hasattr(core.commands, "handle_slash_command"))
        self.assertTrue(hasattr(core.stats, "record_success"))
        self.assertTrue(hasattr(core.garbage_collection, "garbage_collector"))

    def test_storage_package_imports(self):
        import storage.database
        self.assertTrue(hasattr(storage.database, "init_db"))
        self.assertTrue(hasattr(storage.database, "get_db"))
        self.assertTrue(hasattr(storage.database, "save_session_async"))

    def test_client_package_imports(self):
        import client.lark_client
        import client.multimodal
        import client.send_to_feishu
        self.assertTrue(hasattr(client.lark_client, "send_text_to_chat_sdk"))
        self.assertTrue(hasattr(client.multimodal, "extract_and_upload_resources"))
        self.assertTrue(hasattr(client.send_to_feishu, "send_file"))

    def test_plugins_package_imports(self):
        import plugins.base
        import plugins.manager
        import plugins.cron_engine
        self.assertTrue(hasattr(plugins.base, "BasePlugin"))
        self.assertTrue(hasattr(plugins.manager, "PluginManager"))
        self.assertTrue(hasattr(plugins.cron_engine, "CronEngine"))


if __name__ == "__main__":
    unittest.main()

