from __future__ import annotations

import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.config import Config, default_config


class ConfigTests(unittest.TestCase):
    def test_default_config_uses_known_folder_paths(self) -> None:
        with patch("sorter.config.Path.home", return_value=Path("C:/Users/Test")):
            with patch("sorter.config.known_folder_path", side_effect=lambda _name, fallback: fallback):
                config = default_config()

        home = Path("C:/Users/Test")
        self.assertEqual(config.downloads_path, str(home / "Downloads"))
        self.assertEqual(config.desktop_path, str(home / "Desktop"))
        self.assertEqual(config.images_path, str(home / "Pictures"))
        self.assertEqual(config.videos_path, str(home / "Videos"))

    def test_load_creates_default_config_when_file_is_missing(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            config_path = Path(root_text) / "config.json"
            defaults = Config("Downloads", "Desktop", "Pictures", "Videos")

            with patch("sorter.config.CONFIG_PATH", config_path):
                with patch("sorter.config.default_config", return_value=defaults):
                    with patch("builtins.print"):
                        loaded = Config.load()

            self.assertEqual(loaded, defaults)
            self.assertTrue(config_path.exists())

    def test_load_sanitizes_invalid_emails_and_excluded_patterns(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            config_path = Path(root_text) / "config.json"
            config_path.write_text(
                json.dumps(
                    {
                        "downloads_path": "D",
                        "desktop_path": "Desk",
                        "images_path": "Img",
                        "videos_path": "Vid",
                        "email_from": "invalid",
                        "email_to": "valid@example.com",
                        "excluded_patterns": ["m122", "bad", "FR"],
                    }
                ),
                encoding="utf-8",
            )
            defaults = Config("DefaultD", "DefaultDesk", "DefaultImg", "DefaultVid")

            with patch("sorter.config.CONFIG_PATH", config_path):
                with patch("sorter.config.default_config", return_value=defaults):
                    with patch("builtins.print"):
                        loaded = Config.load()

            self.assertEqual(loaded.downloads_path, "D")
            self.assertEqual(loaded.email_from, defaults.email_from)
            self.assertEqual(loaded.email_to, "valid@example.com")
            self.assertEqual(loaded.excluded_patterns, ["FR", "M122"])

    def test_load_returns_defaults_for_invalid_json(self) -> None:
        with tempfile.TemporaryDirectory() as root_text:
            config_path = Path(root_text) / "config.json"
            config_path.write_text("{", encoding="utf-8")
            defaults = Config("Downloads", "Desktop", "Pictures", "Videos")

            with patch("sorter.config.CONFIG_PATH", config_path):
                with patch("sorter.config.default_config", return_value=defaults):
                    with patch("builtins.print"):
                        loaded = Config.load()

            self.assertEqual(loaded, defaults)


if __name__ == "__main__":
    unittest.main()
