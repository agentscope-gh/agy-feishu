"""Unit tests for cross-platform process isolation and management."""

import os
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

from utils.process import (
    get_subprocess_popen_kwargs,
    kill_process_tree,
    IS_WINDOWS,
)


class TestProcess(unittest.TestCase):

    def test_popen_kwargs_posix(self):
        with patch("sys.platform", "linux"):
            with patch("utils.process.IS_WINDOWS", False):
                kwargs = get_subprocess_popen_kwargs(cwd="/app", env={"FOO": "BAR"})
                self.assertEqual(kwargs.get("cwd"), "/app")
                self.assertEqual(kwargs.get("env"), {"FOO": "BAR"})
                if hasattr(os, "setsid"):
                    self.assertIn("preexec_fn", kwargs)

    def test_popen_kwargs_windows(self):
        with patch("sys.platform", "win32"):
            with patch("utils.process.IS_WINDOWS", True):
                kwargs = get_subprocess_popen_kwargs(cwd="C:\\app", env={"FOO": "BAR"})
                self.assertEqual(kwargs.get("cwd"), "C:\\app")
                self.assertNotIn("preexec_fn", kwargs)
                self.assertIn("creationflags", kwargs)

    def test_kill_process_tree_noop(self):
        # Should not raise for None, 0, or negative pid
        kill_process_tree(None)
        kill_process_tree(0)
        kill_process_tree(-1)

    def test_live_process_tree_kill(self):
        # Spawn a short-lived sleep process and verify tree kill
        if sys.platform != "win32":
            proc = subprocess.Popen(["sleep", "60"])
            self.assertIsNone(proc.poll())
            kill_process_tree(proc.pid, force=True)
            try:
                proc.wait(timeout=2.0)
            except subprocess.TimeoutExpired:
                proc.kill()
            self.assertIsNotNone(proc.poll())


if __name__ == "__main__":
    unittest.main()
