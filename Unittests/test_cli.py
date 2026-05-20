from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.cli import ask_days, ask_email, ask_path, ensure_email_ready, has_resend_api_key
from sorter.config import Config


class CliTests(unittest.TestCase):
    def test_ask_path_keeps_current_value_on_empty_input(self) -> None:
        with patch("builtins.input", return_value=""):
            self.assertEqual(ask_path("Downloads", "current"), "current")

    def test_ask_email_reprompts_until_valid(self) -> None:
        with patch("builtins.input", side_effect=["bad", "user@example.com"]):
            with patch("builtins.print") as print_mock:
                result = ask_email("Recipient", "old@example.com")

        self.assertEqual(result, "user@example.com")
        print_mock.assert_called_once()

    def test_ask_days_accepts_empty_invalid_and_negative_values(self) -> None:
        with patch("builtins.input", return_value=""):
            self.assertIsNone(ask_days(3))
        with patch("builtins.input", return_value="abc"):
            with patch("builtins.print"):
                self.assertEqual(ask_days(3), 3)
        with patch("builtins.input", return_value="-5"):
            self.assertEqual(ask_days(None), 0)

    def test_has_resend_api_key_checks_config_and_environment(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch.dict(os.environ, {}, clear=True):
            self.assertFalse(has_resend_api_key(config))

        with patch.dict(os.environ, {"RESEND_API_KEY": " env-key "}, clear=True):
            self.assertTrue(has_resend_api_key(config))

        config.resend_api_key = "config-key"
        with patch.dict(os.environ, {}, clear=True):
            self.assertTrue(has_resend_api_key(config))

    def test_ensure_email_ready_installs_package_and_requires_api_key(self) -> None:
        config = Config("D", "Desk", "Img", "Vid", resend_api_key="key")

        with patch("sorter.cli.has_resend_package", side_effect=[False]):
            with patch("sorter.cli.install_resend_package", return_value=True) as install_mock:
                self.assertTrue(ensure_email_ready(config))

        install_mock.assert_called_once()

    def test_ensure_email_ready_opens_settings_when_key_is_missing(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        def set_key(received_config: Config, force_api_key: bool = False) -> None:
            self.assertTrue(force_api_key)
            received_config.resend_api_key = "key"

        with patch("sorter.cli.has_resend_package", return_value=True):
            with patch("sorter.cli.edit_email_settings", side_effect=set_key) as edit_mock:
                with patch("builtins.print"):
                    self.assertTrue(ensure_email_ready(config))

        edit_mock.assert_called_once()


if __name__ == "__main__":
    unittest.main()
