"""Unit tests for /menu command and interactive quick commands card."""

import asyncio
import unittest
from unittest.mock import patch, MagicMock

from core.commands import handle_slash_command
from cards import CardBuilder


class TestCommandsMenu(unittest.TestCase):

    def setUp(self):
        self.session_data = {"model": "gemini-2.5-pro", "chat_id": "test_chat_123"}
        self.running_processes = {}
        self.chat_queues = {}
        self.chat_workers = {}

    def test_menu_card_structure(self):
        """Test build_commands_menu_card for user and admin."""
        user_card = CardBuilder.build_commands_menu_card(is_admin=False)
        self.assertEqual(user_card.get("header", {}).get("template"), "blue")
        self.assertIn("elements", user_card)

        admin_card = CardBuilder.build_commands_menu_card(is_admin=True)
        # Admin card should have more elements than user card
        self.assertGreater(len(admin_card["elements"]), len(user_card["elements"]))

    def test_slash_command_menu_routing(self):
        """Test that /menu, /commands, /cmds, and /shortcuts invoke send_interactive_card_sdk."""
        for cmd in ["/menu", "/commands", "/cmds", "/shortcuts"]:
            with patch("core.commands.send_interactive_card_sdk") as mock_send, \
                 patch("core.commands.is_admin", return_value=True):
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                try:
                    handled, text = loop.run_until_complete(
                        handle_slash_command(
                            cmd,
                            "msg_123",
                            "chat_456",
                            self.session_data,
                            self.running_processes,
                            self.chat_queues,
                            self.chat_workers,
                        )
                    )
                    self.assertTrue(handled, f"Command {cmd} was not handled")
                    self.assertTrue(mock_send.called, f"send_interactive_card_sdk not called for {cmd}")
                    sent_card = mock_send.call_args[0][1]
                    self.assertIn("快捷指令中心", sent_card.get("header", {}).get("title", {}).get("content", ""))
                finally:
                    loop.close()

    def test_card_action_user_choice_toast(self):
        """Test that user_choice action produces immediate toast feedback."""
        from handlers.card_actions import do_p2_card_action_trigger
        from core import app_state

        mock_event = MagicMock()
        mock_event.event.action.value = {
            "action": "user_choice",
            "choice": "/model",
            "label": "切换模型"
        }
        mock_event.event.action.tag = "button"
        mock_event.event.context.open_message_id = "card_msg_001"
        mock_event.event.context.open_chat_id = "chat_001"
        mock_event.event.operator.open_id = "ou_001"

        loop = asyncio.new_event_loop()
        app_state.main_loop = loop
        try:
            with patch("handlers.card_actions.get_role", return_value="admin"):
                resp = do_p2_card_action_trigger(mock_event)
                self.assertIsNotNone(resp)
                self.assertIsNotNone(resp.toast)
                self.assertEqual(resp.toast.content, "⚡ 正在执行：切换模型")
                self.assertEqual(resp.toast.type, "info")
        finally:
            loop.close()
            app_state.main_loop = None


if __name__ == "__main__":
    unittest.main()
