"""Unit tests for Feishu CardBuilder schemas."""

import unittest
from cards import CardBuilder


class TestCardBuilder(unittest.TestCase):

    def test_help_card_structure(self):
        card = CardBuilder.build_help_card()
        self.assertIsInstance(card, dict)
        self.assertIn("elements", card)
        self.assertTrue(len(card["elements"]) > 0)
        self.assertTrue(card.get("config", {}).get("wide_screen_mode", False))

    def test_typing_indicator(self):
        card = CardBuilder.build_typing_indicator(
            user_text="测试任务",
            think_seconds=3
        )
        self.assertIsInstance(card, dict)
        self.assertIn("elements", card)
        self.assertIn("header", card)

    def test_tool_indicator(self):
        card = CardBuilder.build_tool_indicator(
            tool_action="正在分析代码依赖",
            user_text="优化系统架构",
            think_seconds=2
        )
        self.assertIsInstance(card, dict)
        self.assertIn("elements", card)

    def test_ai_response_card(self):
        card = CardBuilder.build_ai_response(
            reply_text="Hello World! 这是生成的回复内容。",
            current_model="gemini-3.8-flash-high"
        )
        self.assertIsInstance(card, dict)
        self.assertIn("elements", card)
        self.assertIn("header", card)

    def test_model_panel_card(self):
        card = CardBuilder.build_model_panel(
            current_model="gemini-3.8-flash-high",
            available_models=["gemini-3.8-flash-high", "claude-3-7-sonnet"]
        )
        self.assertIsInstance(card, dict)
        self.assertIn("elements", card)

    def test_security_warning_card(self):
        card = CardBuilder.build_security_warning("rm -rf /")
        self.assertIsInstance(card, dict)
        self.assertEqual(card.get("header", {}).get("template"), "red")

    def test_welcome_card(self):
        card = CardBuilder.build_welcome_card()
        self.assertIsInstance(card, dict)
        self.assertEqual(card.get("header", {}).get("template"), "green")

    def test_stall_cards(self):
        warn_card = CardBuilder.build_stall_warning_card("测试", 60, 30)
        self.assertIsInstance(warn_card, dict)
        self.assertEqual(warn_card.get("header", {}).get("template"), "orange")

        err_card = CardBuilder.build_stall_error_card("测试", 180, 120)
        self.assertIsInstance(err_card, dict)
        self.assertEqual(err_card.get("header", {}).get("template"), "red")

    def test_locales_import(self):
        from cards.locales import INTENT_MODES, DYNAMIC_THINKING_PHRASES, STALL_WARNING
        self.assertIn("code", INTENT_MODES)
        self.assertTrue(len(DYNAMIC_THINKING_PHRASES) > 0)
        self.assertIn("title", STALL_WARNING)

    def test_commands_menu_card_structure(self):
        card = CardBuilder.build_commands_menu_card(is_admin=False)
        self.assertIsInstance(card, dict)
        self.assertEqual(card.get("header", {}).get("template"), "blue")
        self.assertIn("快捷指令中心", card.get("header", {}).get("title", {}).get("content", ""))

        # Check action buttons in elements
        action_choices = []
        for elem in card.get("elements", []):
            if elem.get("tag") == "action":
                for act in elem.get("actions", []):
                    val = act.get("value", {})
                    if "choice" in val:
                        action_choices.append(val["choice"])

        # Regular user commands should be present
        self.assertIn("/model", action_choices)
        self.assertIn("/conversations", action_choices)
        self.assertIn("/project", action_choices)
        self.assertIn("/quota", action_choices)
        self.assertIn("/note", action_choices)
        self.assertIn("/cron", action_choices)
        # Admin-only commands should NOT be present
        self.assertNotIn("/status", action_choices)
        self.assertNotIn("/user", action_choices)

        # Admin user commands test
        admin_card = CardBuilder.build_commands_menu_card(is_admin=True)
        admin_choices = []
        for elem in admin_card.get("elements", []):
            if elem.get("tag") == "action":
                for act in elem.get("actions", []):
                    val = act.get("value", {})
                    if "choice" in val:
                        admin_choices.append(val["choice"])
        self.assertIn("/status", admin_choices)
        self.assertIn("/user", admin_choices)
        self.assertIn("/plugin", admin_choices)
        self.assertIn("/update", admin_choices)

    def test_quote_normalization(self):
        from cards.common import normalize_markdown_for_feishu
        from core.executor import extract_final_chinese_response

        # 1. Normal prose quotes should be normalized
        prose = "我们建议采用“方案 A”，而不是‘方案 B’。"
        expected = "我们建议采用「方案 A」，而不是『方案 B』。"
        self.assertEqual(normalize_markdown_for_feishu(prose), expected)
        self.assertEqual(extract_final_chinese_response(prose), expected)

        # 2. Quotes inside inline code should NOT be corrupted
        inline_code = "使用 `print('hello “world”')` 打印。"
        self.assertEqual(normalize_markdown_for_feishu(inline_code), inline_code)
        self.assertEqual(extract_final_chinese_response(inline_code), inline_code)

        # 3. Quotes inside fenced code blocks should NOT be corrupted
        fenced_code = "这是代码：\n```python\nmsg = '“测试”'\nprint(msg)\n```\n结论如上。"
        res = normalize_markdown_for_feishu(fenced_code)
        self.assertIn("msg = '“测试”'", res)
        self.assertIn("```python", res)


if __name__ == "__main__":
    unittest.main()

