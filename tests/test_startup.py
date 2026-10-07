"""Unit tests for startup notification and progressive debounce engine."""

import unittest
from unittest.mock import patch, MagicMock
import time

from core.startup import (
    evaluate_startup_notification,
    record_update_restart,
    BASE_COOLDOWN,
    RAPID_WINDOW,
    MAX_COOLDOWN,
    BACKOFF_FACTOR,
)
from cards import CardBuilder


class TestStartupEngine(unittest.TestCase):

    def setUp(self):
        # In-memory dict mock for bot_meta
        self.mock_meta = {}

        def mock_get(k):
            return self.mock_meta.get(k)

        def mock_set(k, v):
            self.mock_meta[k] = str(v)

        self.patch_get = patch("core.startup.get_bot_meta", side_effect=mock_get)
        self.patch_set = patch("core.startup.set_bot_meta", side_effect=mock_set)
        self.patch_get.start()
        self.patch_set.start()

    def tearDown(self):
        self.patch_get.stop()
        self.patch_set.stop()

    def test_first_boot_notifies(self):
        t0 = 1000000.0
        should_send, info = evaluate_startup_notification(now=t0)
        self.assertTrue(should_send)
        self.assertEqual(info["recovered_from_suppressed"], 0)
        self.assertEqual(self.mock_meta.get("startup_streak"), "0")
        self.assertEqual(self.mock_meta.get("startup_last_time"), str(t0))

    def test_progressive_backoff_cooldown(self):
        t0 = 1000000.0
        # 1. First boot
        should_send, _ = evaluate_startup_notification(now=t0)
        self.assertTrue(should_send)

        # 2. Restart 10 seconds later (rapid repeat #1)
        t1 = t0 + 10.0
        should_send, info1 = evaluate_startup_notification(now=t1)
        self.assertFalse(should_send)
        self.assertEqual(info1["streak"], 1)
        self.assertEqual(info1["cooldown"], BASE_COOLDOWN)  # 60s
        self.assertEqual(info1["suppressed"], 1)

        # 3. Restart 10 seconds later (rapid repeat #2)
        t2 = t1 + 10.0
        should_send, info2 = evaluate_startup_notification(now=t2)
        self.assertFalse(should_send)
        self.assertEqual(info2["streak"], 2)
        self.assertEqual(info2["cooldown"], 120.0)  # 60 * 2^1 = 120s
        self.assertEqual(info2["suppressed"], 2)

        # 4. Restart 10 seconds later (rapid repeat #3)
        t3 = t2 + 10.0
        should_send, info3 = evaluate_startup_notification(now=t3)
        self.assertFalse(should_send)
        self.assertEqual(info3["streak"], 3)
        self.assertEqual(info3["cooldown"], 240.0)  # 60 * 2^2 = 240s
        self.assertEqual(info3["suppressed"], 3)

        # 5. Restart 10 seconds later (rapid repeat #4)
        t4 = t3 + 10.0
        should_send, info4 = evaluate_startup_notification(now=t4)
        self.assertFalse(should_send)
        self.assertEqual(info4["streak"], 4)
        self.assertEqual(info4["cooldown"], 480.0)  # 60 * 2^3 = 480s
        self.assertEqual(info4["suppressed"], 4)

        # 6. Restart after full cooldown (e.g. 500s later > 480s)
        t5 = t4 + 500.0
        should_send, info5 = evaluate_startup_notification(now=t5)
        self.assertTrue(should_send)
        self.assertEqual(info5["recovered_from_suppressed"], 4)
        self.assertEqual(info5["previous_streak"], 4)
        # Verify counters reset
        self.assertEqual(self.mock_meta.get("startup_streak"), "0")
        self.assertEqual(self.mock_meta.get("startup_suppressed_count"), "0")

    def test_max_cooldown_cap(self):
        t = 1000000.0
        evaluate_startup_notification(now=t)

        # Rapidly repeat 10 times
        for i in range(1, 11):
            t += 5.0
            _, info = evaluate_startup_notification(now=t)
            self.assertLessEqual(info["cooldown"], MAX_COOLDOWN)

        self.assertEqual(info["cooldown"], MAX_COOLDOWN)

    def test_record_update_restart_resets_streak(self):
        self.mock_meta["startup_streak"] = "5"
        self.mock_meta["startup_suppressed_count"] = "5"
        self.mock_meta["startup_cooldown"] = "960"

        record_update_restart(now=12345.0)
        self.assertEqual(self.mock_meta.get("startup_streak"), "0")
        self.assertEqual(self.mock_meta.get("startup_suppressed_count"), "0")
        self.assertEqual(self.mock_meta.get("startup_cooldown"), str(BASE_COOLDOWN))
        self.assertEqual(self.mock_meta.get("startup_last_time"), "12345.0")

    def test_startup_card_rendering(self):
        card = CardBuilder.build_startup_card(
            start_time="2026-10-03 13:00:00",
            pid=12345,
            hostname="test-host",
            version_str="v2.1.0 (Build: abcdef)",
            plugins=["cron_scheduler", "server_health"],
            recovery_info={"recovered_from_suppressed": 3, "previous_streak": 3},
        )
        self.assertEqual(card["header"]["template"], "green")
        self.assertEqual(card["header"]["title"]["content"], "🟢 飞书助手服务已上线")
        # Ensure recovery warning is included in markdown elements
        found_recovery = any("频控恢复提示" in el.get("content", "") for el in card["elements"] if el.get("tag") == "markdown")
        self.assertTrue(found_recovery)


if __name__ == "__main__":
    unittest.main()
