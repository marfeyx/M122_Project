from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

PROJECT_DIR = Path(__file__).resolve().parents[1] / "Downloads Folder Sorter"
sys.path.insert(0, str(PROJECT_DIR))

from sorter.cli import (
    ask_days,
    change_paths,
    config_menu,
    edit_email_settings,
    edit_excluded_paths,
    edit_excluded_patterns,
    ensure_email_ready,
    has_resend_api_key,
    main,
)
from sorter.config import Config


class CliTests(unittest.TestCase):
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

    def test_edit_email_settings_updates_key_and_addresses(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch(
            "builtins.input",
            side_effect=["y", "api-key", "sender@example.com", "to@example.com"],
        ):
            with patch("builtins.print"):
                with patch.object(config, "save") as save_mock:
                    edit_email_settings(config)

        self.assertEqual(config.resend_api_key, "api-key")
        self.assertEqual(config.email_from, "sender@example.com")
        self.assertEqual(config.email_to, "to@example.com")
        save_mock.assert_called_once()

    def test_edit_email_settings_forced_key_keeps_missing_key_visible(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("builtins.input", side_effect=["", "", ""]):
            with patch("builtins.print") as print_mock:
                with patch.object(config, "save"):
                    edit_email_settings(config, force_api_key=True)

        self.assertTrue(
            any(
                "required before cleaning" in str(call.args[0])
                for call in print_mock.call_args_list
                if call.args
            )
        )

    def test_edit_excluded_paths_adds_removes_and_returns(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("builtins.input", side_effect=["1", '"C:/skip"', "2", "1", "3"]):
            with patch("builtins.print"):
                with patch.object(config, "save") as save_mock:
                    edit_excluded_paths(config)

        self.assertEqual(config.excluded_paths, [])
        self.assertEqual(save_mock.call_count, 2)

    def test_edit_excluded_patterns_normalizes_and_saves(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("builtins.input", return_value="m122, bad, M320"):
            with patch("builtins.print"):
                with patch.object(config, "save") as save_mock:
                    edit_excluded_patterns(config)

        self.assertEqual(config.excluded_patterns, ["M122", "M320"])
        save_mock.assert_called_once()

    def test_change_paths_updates_all_folders(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("builtins.input", side_effect=["Downloads", "Images", "Videos", "Desktop"]):
            with patch("builtins.print"):
                with patch.object(config, "save") as save_mock:
                    change_paths(config)

        self.assertEqual(config.downloads_path, "Downloads")
        self.assertEqual(config.images_path, "Images")
        self.assertEqual(config.videos_path, "Videos")
        self.assertEqual(config.desktop_path, "Desktop")
        save_mock.assert_called_once()

    def test_config_menu_routes_each_option(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("builtins.input", side_effect=["1", "2", "3", "4", "5", "6"]):
            with patch("builtins.print"):
                with patch("sorter.cli.edit_excluded_paths") as paths_mock:
                    with patch("sorter.cli.ask_days", return_value=4) as days_mock:
                        with patch("sorter.cli.edit_excluded_patterns") as patterns_mock:
                            with patch("sorter.cli.change_paths") as change_paths_mock:
                                with patch("sorter.cli.edit_email_settings") as email_mock:
                                    with patch.object(config, "save") as save_mock:
                                        config_menu(config)

        paths_mock.assert_called_once_with(config)
        days_mock.assert_called_once_with(None)
        patterns_mock.assert_called_once_with(config)
        change_paths_mock.assert_called_once_with(config)
        email_mock.assert_called_once_with(config)
        save_mock.assert_called_once()
        self.assertEqual(config.exclude_newer_than_days, 4)

    def test_ensure_email_ready_returns_false_when_install_fails(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("sorter.cli.has_resend_package", return_value=False):
            with patch("sorter.cli.install_resend_package", return_value=False):
                self.assertFalse(ensure_email_ready(config))

    def test_main_handles_invalid_choice_config_cleaning_and_exit(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("sorter.cli.Config.load", return_value=config):
            with patch("builtins.input", side_effect=["x", "2", "1", "", "3"]):
                with patch("sorter.cli.config_menu") as config_menu_mock:
                    with patch("sorter.cli.ensure_email_ready", return_value=True):
                        with patch("sorter.cli.clean_downloads", return_value=Mock()) as clean_mock:
                            with patch("sorter.cli.send_summary_email") as email_mock:
                                with patch("builtins.print"):
                                    self.assertEqual(main(), 0)

        config_menu_mock.assert_called_once_with(config)
        clean_mock.assert_called_once_with(config)
        email_mock.assert_called_once()

    def test_main_continues_when_email_not_ready_and_reports_send_error(self) -> None:
        config = Config("D", "Desk", "Img", "Vid")

        with patch("sorter.cli.Config.load", return_value=config):
            with patch("builtins.input", side_effect=["1", "", "1", "", "3"]):
                with patch("sorter.cli.ensure_email_ready", side_effect=[False, True]):
                    with patch("sorter.cli.clean_downloads", return_value=Mock()):
                        with patch("sorter.cli.send_summary_email", side_effect=RuntimeError("bad")):
                            with patch("builtins.print") as print_mock:
                                self.assertEqual(main(), 0)

        self.assertTrue(
            any("could not be sent" in str(call.args[0]) for call in print_mock.call_args_list if call.args)
        )


if __name__ == "__main__":
    unittest.main()
