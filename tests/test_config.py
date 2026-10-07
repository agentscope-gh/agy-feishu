"""Unit tests for config module."""

import os
import sys
import unittest
from unittest.mock import patch

import config


class TestConfig(unittest.TestCase):

    def test_paths_not_empty(self):
        self.assertTrue(config.BASE_DIR)
        self.assertTrue(os.path.isdir(config.BASE_DIR))
        self.assertTrue(config.get_antigravity_home())
        self.assertTrue(config.get_brain_dir())

    def test_transcript_path_resolution(self):
        conv_id = "test-conv-1234"
        p = config.get_transcript_path(conv_id)
        self.assertTrue(p.endswith("transcript.jsonl"))
        self.assertIn(conv_id, p)

    def test_find_antigravity_bin_mock_win32(self):
        with patch("sys.platform", "win32"):
            with patch("shutil.which", return_value="C:\\fake\\npm\\agy.cmd"):
                bin_path = config.find_antigravity_bin()
                self.assertEqual(bin_path, "C:\\fake\\npm\\agy.cmd")

    def test_find_antigravity_bin_mock_posix(self):
        with patch("sys.platform", "linux"):
            with patch("shutil.which", return_value="/usr/local/bin/agy"):
                bin_path = config.find_antigravity_bin()
                self.assertEqual(bin_path, "/usr/local/bin/agy")


if __name__ == "__main__":
    unittest.main()
